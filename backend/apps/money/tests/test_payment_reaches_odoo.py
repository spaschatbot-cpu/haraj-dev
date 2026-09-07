"""HR-17 — the one payment Odoo cannot learn about, and nothing carried it.

`R3-01` §3 is about the *reference* a payment carries to Odoo: "the memo is the
payment's reference, and Odoo rejects a repeat — a partial payment needs its
own, or 223 attempts across 26 invoices are refused". The map has carried
"⚠️ needs verification" against that line since the phase closed.

**Verifying it found something else.** The rule is implemented
(`outbox.payment_reference` builds from the payment's own uuid) and it is
tested, thoroughly, including the concurrency shape that used to lose a
payment. What no test asked is who calls it — and the answer was **nobody**.
`queue_payment` had no caller outside tests.

That is not a dead function; it is a hole with a shape:

* `record_payment`'s only caller is the Odoo webhook handler, so every payment
  it books already came *from* Odoo. Sending those back is the echo HR-10 was
  written about, and not queuing them is right.
* `pay_invoice_from_balance` — a customer pressing "pay" against their own
  insurance balance — happens entirely on our side. Our invoice read `paid`,
  our ledger agreed, and **Odoo still showed the debt**. Finance works in
  Odoo. So finance chases a customer who has paid, and the mirror disagrees
  with the source, which is the one thing this boundary exists to prevent.

**Queuing is not sending, and that distinction is the whole of Article 5-2.**
The outbox is "something we owe Odoo, written down before we try to send it".
`send` is called by nothing scheduled — there is no beat schedule in this
project at all — and `client` refuses outright while `ODOO_ENABLED` is false,
which it is by default in every environment. The last test here asserts that,
because a task queued in a system that decides to send on its own is a
different task from this one.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import Invoice, InvoiceSource, InvoiceState, PaymentMethod
from apps.money.verification import verify_ledger
from apps.odoo import outbox
from apps.odoo.models import OutboxMessage, OutboxState

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")
FEE = Decimal("2000.00")


@pytest.fixture
def funded(customer):
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="HR17/seed"
    )
    return customer


def an_invoice(customer, *, odoo_id: str = "", amount: Decimal = FEE) -> Invoice:
    """An invoice for `customer`, optionally one Odoo already knows about."""
    return Invoice.objects.create(
        customer=customer,
        number=f"INV/HR17/{odoo_id or 'local'}",
        amount=amount,
        odoo_invoice_id=odoo_id,
        state=InvoiceState.OPEN,
        source=InvoiceSource.ODOO_SYNC if odoo_id else InvoiceSource.LOCAL,
        issued_at=timezone.now(),
    )


def payments_queued() -> list[OutboxMessage]:
    return list(OutboxMessage.objects.filter(endpoint="payments"))


# ---------------------------------------------------------------------------
# The hole
# ---------------------------------------------------------------------------


def test_paying_an_odoo_invoice_from_balance_is_queued_for_odoo(funded):
    """The defect. Before HR-17 this queued nothing and Odoo kept the debt."""
    invoice = an_invoice(funded, odoo_id="4242")

    txn = services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )

    (queued,) = payments_queued()
    assert queued.reference == outbox.payment_reference(invoice, txn)
    assert queued.payload["invoice"] == "4242"
    #: A string, not a float. Article 3-2 does not stop at our boundary.
    assert queued.payload["amount"] == "2000.00"
    assert isinstance(queued.payload["amount"], str)
    assert queued.source_transaction_id == txn.pk
    assert verify_ledger() == []


def test_the_invoice_and_the_message_agree_on_the_amount(funded):
    """What we tell Odoo is what we actually took, not what was billed.

    They differ the moment anything was paid before, and a message carrying
    the invoice total would over-credit in Odoo by whatever was already
    settled.
    """
    invoice = an_invoice(funded, odoo_id="4243", amount=Decimal("3000.00"))
    services.record_payment(
        invoice=invoice,
        amount=Decimal("1000.00"),
        source="cash",
        reference="odoo:earlier",
    )
    invoice.refresh_from_db()

    services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )

    (queued,) = payments_queued()
    assert queued.payload["amount"] == "2000.00", "أرسل الإجمالي لا المتبقّي"
    invoice.refresh_from_db()
    assert invoice.state == InvoiceState.PAID
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# What must *not* be queued
# ---------------------------------------------------------------------------


def test_a_payment_that_came_from_odoo_is_not_sent_back(funded):
    """The echo (HR-10). `record_payment`'s caller is the webhook."""
    invoice = an_invoice(funded, odoo_id="4244")

    services.record_payment(
        invoice=invoice, amount=FEE, source="cash", reference="odoo:pay-1"
    )

    assert payments_queued() == []
    assert verify_ledger() == []


def test_an_invoice_odoo_never_issued_is_not_reported_to_it(funded):
    """The phantom debt from the other direction.

    An invoice we raised ourselves has no `account.move` behind it. Telling
    Odoo about a payment on something it does not have is asking it to invent
    the thing being paid.
    """
    invoice = an_invoice(funded)
    assert invoice.odoo_invoice_id == ""

    services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )

    assert payments_queued() == []
    invoice.refresh_from_db()
    assert invoice.state == InvoiceState.PAID
    assert verify_ledger() == []


def test_a_replayed_payment_queues_one_message_and_not_two(funded):
    """A retried request must not become a second payment in Odoo.

    ‏`pay_invoice_from_balance` is idempotent on its own key, so the replay
    returns the first transaction and never reaches the queuing at all — the
    call is below that early return, deliberately. And even if it did, the
    outbox reference is built from the payment's own identity, so the repeat
    would find the standing row rather than open a second one. Two rows would
    mean two calls to Odoo and a customer credited twice for one payment.
    """
    invoice = an_invoice(funded, odoo_id="4245")

    first = services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )
    invoice.refresh_from_db()
    again = services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )

    assert again.pk == first.pk, "الإعادة أنتجت حركةً ثانية"
    (queued,) = payments_queued()
    assert queued.source_transaction_id == first.pk
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# Queued is not sent
# ---------------------------------------------------------------------------


def test_the_message_is_written_down_and_not_sent(funded, settings):
    """Article 5-2, asserted rather than promised.

    The approval that rule asks for is about *scheduling a send*. Nothing here
    schedules anything: the row is pending, and the client refuses while the
    brake is on — which it is by default in every environment.
    """
    settings.ODOO_ENABLED = False
    invoice = an_invoice(funded, odoo_id="4246")

    services.pay_invoice_from_balance(
        user=funded, invoice=invoice, method=PaymentMethod.BALANCE
    )

    (queued,) = payments_queued()
    assert queued.state == OutboxState.PENDING
    assert queued.sent_at is None
    assert queued.attempts == 0
