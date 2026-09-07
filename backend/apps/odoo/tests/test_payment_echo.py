"""HR-10 — Odoo echoing back what we pushed it, and the order that makes it a defect.

``PHASE_02`` §3, and it produced **42 phantom deposits** in v1. The sequence is
the whole of it:

1. the customer pays by card and we credit them locally, keyed on the gateway's
   payment id;
2. we push the entry to Odoo;
3. **Odoo fires its webhook the moment the payment is created — before our push
   has finished being written**;
4. the webhook carries *Odoo's* payment id, not the gateway's, so our
   idempotency key does not recognise it.

Ten thousand riyals become twenty, "من العدم".

Idempotency is the first layer, and reading the code says it is enough — it is
not, and the reason is subtle: the key answers *"have we seen this event?"*, and
the echo **is a different event describing the same money**. Nothing that keys
on event identity can see across that.

So the question is not "do we have idempotency?" but "when is the event's
identity written, relative to the request going out?" — and that is not
answerable by reading. It needs a test that **reverses the order on purpose**,
which is what this module is.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import AccountKind
from apps.money.verification import verify_ledger
from apps.odoo.models import CustomerLink, InboundMessage, InboundState
from apps.odoo.processing import CARD_ECHO_WINDOW_MINUTES, process

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def linked(customer):
    CustomerLink.objects.create(user=customer, odoo_customer_id="ODOO-1", is_primary=True)
    return customer


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def topped_up_by_card(user, amount: Decimal = TEN_K, *, payment_id="MOYASAR-77"):
    """The customer pays by card, and we credit them — step 1 of the sequence."""
    intent = services.start_topup(user=user, client_key=payment_id)
    return services.apply_gateway_payment(
        reference=intent.reference,
        payment_id=payment_id,
        amount=amount,
        status_raw="paid",
        succeeded=True,
    )


def odoo_says_paid(
    *, odoo_payment_id: str, amount: str = "10000.00", customer="ODOO-1", received_at=None
) -> InboundMessage:
    """Odoo's own webhook for that money — step 3, carrying *their* identifier."""
    message = InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        delivery_id=f"D-{odoo_payment_id}",
        payload={
            "payment_id": odoo_payment_id,
            "amount": amount,
            "customer_id": customer,
            "event": "payment.posted",
        },
        state=InboundState.RECEIVED,
    )
    if received_at is not None:
        InboundMessage.objects.filter(pk=message.pk).update(received_at=received_at)
        message.refresh_from_db()
    return message


# ---------------------------------------------------------------------------
# The incident, by name
# ---------------------------------------------------------------------------


def test_odoos_echo_does_not_double_the_balance(linked):
    """Ten thousand stays ten thousand. Before HR-10 this read 20,000."""
    topped_up_by_card(linked)
    assert free(linked) == TEN_K

    echo = odoo_says_paid(odoo_payment_id="ODOO-PAY-9")
    process(echo)

    echo.refresh_from_db()
    assert free(linked) == TEN_K, "تضاعف الرصيد من العدم"
    assert echo.state == InboundState.IGNORED
    assert verify_ledger() == []


def test_the_skip_says_it_was_the_second_layer(linked):
    """`[layer2]`, so a reader can tell which defence answered and why.

    The first layer is the idempotency key and it cannot see this: the echo is
    a different event about the same money.
    """
    topped_up_by_card(linked)

    echo = odoo_says_paid(odoo_payment_id="ODOO-PAY-9")
    process(echo)

    echo.refresh_from_db()
    assert "[layer2]" in echo.note
    assert "صدى دفعة" in echo.note
    assert "بالبطاقة" in echo.note


def test_the_message_is_kept_whole_so_a_person_can_replay_it(linked):
    """Ignored is not dropped (Article 2-2). The payload survives the refusal."""
    topped_up_by_card(linked)
    echo = odoo_says_paid(odoo_payment_id="ODOO-PAY-9")

    process(echo)

    echo.refresh_from_db()
    assert echo.payload["payment_id"] == "ODOO-PAY-9"
    assert echo.payload["amount"] == "10000.00"
    assert echo.note, "رُفضت بلا سبب مكتوب"


def test_the_echo_arriving_before_our_push_is_still_caught(linked):
    """The order that made it a defect, run in that order.

    Odoo fires on creation, before our push is written. Idempotency keyed on
    the gateway's id cannot help here, because that id is not in this message
    at all — which is exactly why the second layer asks about the *money*.
    """
    outcome = topped_up_by_card(linked)
    assert outcome.transaction is not None

    # No outbox row for this payment exists yet — the push has not landed.
    echo = odoo_says_paid(odoo_payment_id="ODOO-PAY-EARLY")
    process(echo)

    echo.refresh_from_db()
    assert echo.state == InboundState.IGNORED
    assert free(linked) == TEN_K


def test_two_echoes_of_one_top_up_are_both_refused(linked):
    """Odoo sends `posted` then `updated`; neither may credit."""
    topped_up_by_card(linked)

    for odoo_id in ("ODOO-PAY-A", "ODOO-PAY-B"):
        message = odoo_says_paid(odoo_payment_id=odoo_id)
        process(message)
        message.refresh_from_db()
        assert message.state == InboundState.IGNORED

    assert free(linked) == TEN_K


# ---------------------------------------------------------------------------
# And money that is genuinely new still lands
# ---------------------------------------------------------------------------


def test_a_payment_with_no_card_top_up_behind_it_is_credited(linked):
    """The guard must not become a wall. A bank payment is new money."""
    message = odoo_says_paid(odoo_payment_id="ODOO-PAY-NEW")

    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == TEN_K
    assert verify_ledger() == []


def test_a_different_amount_is_not_an_echo(linked):
    """The echo is the *same* money. A different figure is a different payment."""
    topped_up_by_card(linked)

    message = odoo_says_paid(odoo_payment_id="ODOO-PAY-X", amount="20000.00")
    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == Decimal("30000.00")
    assert verify_ledger() == []


def test_a_payment_long_after_the_top_up_is_not_an_echo(linked):
    """Outside the window it is a customer paying again, not a machine echoing."""
    topped_up_by_card(linked)
    later = timezone.now() + timezone.timedelta(minutes=CARD_ECHO_WINDOW_MINUTES + 5)

    message = odoo_says_paid(odoo_payment_id="ODOO-PAY-LATER", received_at=later)
    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == Decimal("20000.00")
    assert verify_ledger() == []


def test_another_customers_card_top_up_does_not_shield_this_one(
    linked, django_user_model
):
    """The window is per customer. Two people paying 10,000 at once is ordinary."""
    other = django_user_model.objects.create_user(
        phone="966509999999", full_name="آخر", national_id="1122334455"
    )
    topped_up_by_card(other)

    message = odoo_says_paid(odoo_payment_id="ODOO-PAY-OTHER")
    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == TEN_K
    assert free(other) == TEN_K
    assert verify_ledger() == []
