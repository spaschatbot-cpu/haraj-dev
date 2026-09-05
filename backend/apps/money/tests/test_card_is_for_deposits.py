"""HR-08 — the card rail carries deposits, and a car is not a deposit.

``PHASE_02`` §5-1. Two costs, and v1 paid both:

* customers put purchases of **over a hundred thousand riyals** on bank cards,
  and the interchange on those "كبّد الشركة عمولات بنكية ضخمة";
* a card charge can be reversed months later — against a car that left the yard
  the same week, with nothing left to take back.

Most of this was already true when the task was picked up, and in the best way:
``PaymentMethod`` has no card member and ``PaymentPurpose`` has only the
deposit, so the schema says it rather than a screen remembering to. **One hole
was open**: ``record_payment`` took ``source`` as free text and accepted
``"card"`` — it would have settled an invoice off the card account. Nothing
called it that way, which is not a rule. It is a coincidence waiting for the
next integration.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    AccountKind,
    Invoice,
    InvoicePaymentSource,
    InvoiceSource,
    InvoiceState,
    PaymentMethod,
    PaymentPurpose,
)
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966501234567", full_name="عميل", national_id="1234567890"
    )


@pytest.fixture
def invoice(customer) -> Invoice:
    return Invoice.objects.create(
        customer=customer,
        number="V-CARD-TEST",
        amount=Decimal("120000.00"),
        state=InvoiceState.OPEN,
        source=InvoiceSource.LOCAL,
        issued_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# The hole that was open
# ---------------------------------------------------------------------------


def test_a_car_cannot_be_settled_with_a_card(customer, invoice):
    """The 120,000 purchase that v1 put on a bank card, refused."""
    with pytest.raises(services.CardNotForPurchases) as raised:
        services.record_payment(
            invoice=invoice,
            amount=Decimal("120000.00"),
            source="card",
            reference="gateway/1",
        )

    assert "البطاقة" in str(raised.value)
    invoice.refresh_from_db()
    assert invoice.amount_paid == Decimal("0.00")
    assert verify_ledger() == []


def test_the_refusal_names_the_way_that_does_work(customer, invoice):
    """A refusal that does not say what to do instead is a support ticket."""
    with pytest.raises(services.CardNotForPurchases) as raised:
        services.record_payment(
            invoice=invoice,
            amount=TEN_K,
            source="card",
            reference="gateway/2",
        )

    message = str(raised.value)
    assert "تحويل بنكي" in message
    assert "الرصيد" in message


def test_a_bank_transfer_settles_it(customer, invoice):
    services.record_payment(
        invoice=invoice,
        amount=Decimal("120000.00"),
        source=InvoicePaymentSource.CASH,
        reference="bank/1",
    )

    invoice.refresh_from_db()
    assert invoice.state == InvoiceState.PAID
    assert verify_ledger() == []


def test_locked_insurance_settles_it(customer, invoice):
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="seed/1"
    )
    services.lock_for_invoice(user=customer, invoice=invoice)

    services.record_payment(
        invoice=invoice,
        amount=TEN_K,
        source=InvoicePaymentSource.INSURANCE,
        reference="ins/1",
    )

    invoice.refresh_from_db()
    assert invoice.amount_paid == TEN_K
    assert verify_ledger() == []


def test_an_unknown_source_is_still_refused_as_unknown(customer, invoice):
    """The card gets its own sentence; anything else stays a plain refusal."""
    with pytest.raises(services.MoneyError) as raised:
        services.record_payment(
            invoice=invoice, amount=TEN_K, source="crypto", reference="x/1"
        )

    assert not isinstance(raised.value, services.CardNotForPurchases)


# ---------------------------------------------------------------------------
# And the card rail itself stays narrow
# ---------------------------------------------------------------------------


def test_the_card_gateway_knows_one_purpose():
    """Narrow by construction: there is no second member to pass by mistake."""
    assert list(PaymentPurpose) == [PaymentPurpose.INSURANCE_DEPOSIT]


def test_a_customer_settling_an_invoice_is_never_offered_a_card():
    assert PaymentMethod.BALANCE in PaymentMethod
    assert PaymentMethod.BANK_TRANSFER in PaymentMethod
    assert not any("card" in method.value for method in PaymentMethod)


def test_a_topup_intent_is_a_deposit_and_carries_no_invoice(customer):
    intent = services.start_topup(user=customer)

    assert intent.purpose == PaymentPurpose.INSURANCE_DEPOSIT
    assert intent.amount == services.deposit_amount_for()
    assert not hasattr(intent, "invoice_id") or intent.invoice_id is None


def test_the_card_account_is_never_debited_for_a_purchase(customer, invoice):
    """The ledger's own answer, independent of which function refused."""
    before = services.system_account(AccountKind.EXTERNAL_CARD).balance

    with pytest.raises(services.CardNotForPurchases):
        services.record_payment(
            invoice=invoice, amount=TEN_K, source="card", reference="gateway/3"
        )

    assert services.system_account(AccountKind.EXTERNAL_CARD).balance == before
