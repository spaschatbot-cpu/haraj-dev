"""A gateway message that failed must stay re-interpretable. T913 follow-up.

T913 closed a real hole by teaching `apps.odoo` to touch nothing but Odoo's own
messages. What it did not do was give the payment gateway's messages a path of
their own, and the two together left a shape nobody intended:

* `apps.odoo.tasks.due_messages` filters on `source="odoo"`, so no cron ever
  looks at a gateway row again once it lands in `failed`;
* the console's only button called `apps.odoo.processing.process`, which
  answers a foreign source with `ignored` — a **terminal** state that `process`
  itself then refuses to leave.

So the one button offered to a person turned "we could not apply this payment"
into "nobody will ever look at this payment again", while the money had already
reached the gateway. The tests here are written as that sequence rather than as
the fix, because "the row says failed" passes for reasons unrelated to the hole.
"""

from __future__ import annotations

import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.core.permissions import Role
from apps.money import inbound, services, tasks
from apps.money.models import PaymentIntentState
from apps.odoo.models import CustomerLink, InboundMessage, InboundState

from .conftest import free_balance

pytestmark = pytest.mark.django_db

SECRET = "test-webhook-secret"


@pytest.fixture
def payments_on(settings):
    settings.PAYMENT_WEBHOOK_SECRET = SECRET
    settings.PAYMENT_SUCCESS_STATUSES = ["paid"]
    return settings


@pytest.fixture
def intent(bidder):
    return services.start_topup(user=bidder, client_key="replay-test")


@pytest.fixture
def operator(client) -> User:
    """Finance holds `odoo.inbox` — a replay can credit a customer's account."""
    user = User.objects.create_user(
        phone="966500000062", full_name="موظف مالية", password="x"
    )
    user.is_staff = True
    user.console_role = Role.FINANCE
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def linked_customer(db) -> User:
    customer = User.objects.create_user(
        phone="966555555702", full_name="عميل أودو", password="x"
    )
    CustomerLink.objects.create(
        user=customer, odoo_customer_id="ODOO-702", is_primary=True
    )
    return customer


def gateway_body(intent, *, pid: str = "pay_1"):
    return {
        "id": pid,
        "status": "paid",
        "amount": str(intent.amount),
        "metadata": {"reference": intent.reference},
    }


def send_callback(api_client, payload: dict):
    raw = json.dumps(payload).encode()
    signature = hmac.new(SECRET.encode(), raw, "sha256").hexdigest()
    return api_client.post(
        reverse("money:payment-callback"),
        data=raw,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature,
    )


def a_transient_failure(api_client, intent) -> InboundMessage:
    """Deliver a genuine, signed payment while applying it happens to raise.

    A lock timeout, a dropped connection — the class of failure that is gone by
    the time anybody reads the row. The message is stored `failed` with the
    exception written on it, which is Article 2-2 working as intended: the
    evidence is kept. What has to follow is a way back.
    """
    with mock.patch.object(
        services, "apply_gateway_payment", side_effect=OSError("connection reset")
    ):
        send_callback(api_client, gateway_body(intent))
    message = InboundMessage.objects.get(source="payment_gateway")
    assert message.state == InboundState.FAILED
    return message


# ---------------------------------------------------------------------------
# The money can still be credited
# ---------------------------------------------------------------------------


def test_replaying_a_failed_payment_credits_the_customer(
    payments_on, api_client, intent, bidder
):
    message = a_transient_failure(api_client, intent)

    inbound.interpret(message)
    message.refresh_from_db()

    assert message.state == InboundState.PROCESSED
    assert free_balance(bidder) == intent.amount
    intent.refresh_from_db()
    assert intent.state == PaymentIntentState.SUCCEEDED


def test_the_odoo_interpreter_is_a_one_way_trip_for_a_gateway_row(
    payments_on, api_client, intent, bidder
):
    """The exact sequence the console used to run, asserted as damage.

    `process` is right to refuse a foreign source. Handing it one anyway is what
    turned a retryable failure into a terminal `ignored` — after which nothing,
    including the correct interpreter, can put the money where it belongs.
    """
    from apps.odoo.processing import process

    message = a_transient_failure(api_client, intent)

    process(message)
    message.refresh_from_db()
    assert message.state == InboundState.IGNORED

    inbound.interpret(message)
    message.refresh_from_db()
    assert free_balance(bidder) == Decimal("0.00")


# ---------------------------------------------------------------------------
# The console button reaches the right interpreter
# ---------------------------------------------------------------------------


def test_the_button_credits_a_failed_gateway_payment(
    payments_on, client, operator, api_client, intent, bidder
):
    message = a_transient_failure(api_client, intent)

    response = client.post(reverse("console:odoo-replay", args=[message.pk]), follow=True)

    assert response.status_code == 200
    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free_balance(bidder) == intent.amount


def test_a_source_nobody_interprets_is_offered_no_button(client, operator):
    """The general form of the bug: a button whose only outcome is to end the row.

    A source neither boundary claims cannot be replayed into anything, so
    offering the press is offering a one-way trip to `ignored`.
    """
    message = InboundMessage.objects.create(
        source="some_future_partner",
        event="whatever.happened",
        delivery_id="fut-1",
        payload={},
        state=InboundState.FAILED,
    )

    page = client.get(reverse("console:odoo-message", args=[message.pk]))
    body = page.content.decode()

    assert reverse("console:odoo-replay", args=[message.pk]) not in body


def test_pressing_it_anyway_leaves_the_row_alone(client, operator):
    message = InboundMessage.objects.create(
        source="some_future_partner",
        event="whatever.happened",
        delivery_id="fut-2",
        payload={},
        state=InboundState.FAILED,
    )

    client.post(reverse("console:odoo-replay", args=[message.pk]), follow=True)
    message.refresh_from_db()

    assert message.state == InboundState.FAILED, "صفٌّ بلا مفسّر صار نهائياً"


def test_the_odoo_button_still_works(client, operator, linked_customer):
    """The fix must not cost the path it is bolted beside."""
    message = InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        delivery_id="D-replay-1",
        payload={
            "payment_id": "P-1",
            "customer_id": "ODOO-702",
            "amount": "10000.00",
        },
        state=InboundState.FAILED,
    )

    client.post(reverse("console:odoo-replay", args=[message.pk]), follow=True)
    message.refresh_from_db()

    assert message.state == InboundState.PROCESSED
    assert free_balance(linked_customer) == Decimal("10000.00")


# ---------------------------------------------------------------------------
# Forgery stays out — the replay path must not reopen T913
# ---------------------------------------------------------------------------


def test_an_unsigned_gateway_body_is_not_interpreted_by_hand(
    payments_on, api_client, intent, bidder
):
    raw = json.dumps(gateway_body(intent)).encode()
    api_client.post(
        reverse("money:payment-callback"),
        data=raw,
        content_type="application/json",
        HTTP_X_SIGNATURE="not-the-signature",
    )
    message = InboundMessage.objects.get(source="payment_gateway")
    assert message.state == InboundState.REJECTED_SIGNATURE

    inbound.interpret(message)
    message.refresh_from_db()

    assert message.state == InboundState.REJECTED_SIGNATURE
    assert free_balance(bidder) == Decimal("0.00")


def test_the_gateway_interpreter_refuses_an_odoo_message(linked_customer):
    """Mirror of `process`'s own source guard, in the other direction.

    The table is shared. An Odoo body carrying `amount` and `status` would
    otherwise be read here as a card payment — and, worse, left terminal, so
    Odoo's own retry queue never offers it again.
    """
    message = InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        delivery_id="odoo-1",
        payload={"payment_id": "p-1", "customer_id": "ODOO-702", "amount": "50000.00"},
        state=InboundState.FAILED,
    )

    inbound.interpret(message)
    message.refresh_from_db()

    assert message.state == InboundState.FAILED, (
        "المفسّر الغريب جعل رسالة أودو نهائية، فلا كرون أودو يراها بعدها"
    )
    assert free_balance(linked_customer) == Decimal("0.00")


# ---------------------------------------------------------------------------
# And an automatic queue, so a person is not the only way back
# ---------------------------------------------------------------------------


def _make_it_due(message: InboundMessage) -> None:
    InboundMessage.objects.filter(pk=message.pk).update(
        processed_at=message.processed_at - tasks.next_attempt_after(message.attempts)
    )


def test_a_failed_gateway_message_becomes_due_for_retry(payments_on, api_client, intent):
    message = a_transient_failure(api_client, intent)
    _make_it_due(message)

    assert [m.pk for m in tasks.due_gateway_messages()] == [message.pk]


def test_the_retry_task_credits_it_and_holds_a_lock(
    payments_on, api_client, intent, bidder
):
    message = a_transient_failure(api_client, intent)
    _make_it_due(message)

    assert tasks.retry_failed_gateway() == {
        "attempted": 1,
        "processed": 1,
        "still_failing": 0,
    }
    assert free_balance(bidder) == intent.amount

    with mock.patch("apps.money.tasks.single_instance") as lock:
        lock.return_value.__enter__.return_value = False
        assert "skipped" in tasks.retry_failed_gateway()


def test_the_gateway_queue_does_not_offer_odoo_messages():
    InboundMessage.objects.create(
        source="odoo",
        event="payment.posted",
        delivery_id="odoo-2",
        payload={},
        state=InboundState.FAILED,
    )

    assert tasks.due_gateway_messages() == []


def test_the_gateway_queue_does_not_offer_an_unsigned_body():
    InboundMessage.objects.create(
        source="payment_gateway",
        event="paid",
        delivery_id="forged-1",
        payload={},
        state=InboundState.REJECTED_SIGNATURE,
    )

    assert tasks.due_gateway_messages() == []
