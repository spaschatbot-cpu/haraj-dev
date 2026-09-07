"""HR-16 — Odoo's `"/"` is a placeholder, and it was being used as a key.

``R3-02`` §4: "**an empty draft is a phantom debt**: opening a blank form in
Odoo sends `created` with `invoice_id:"/"` and zeros — **they are ignored**."
The map carried "⚠️ needs a test case" against that line since the phase
closed.

**Measured before anything was changed, and the measurement moved the task.**

* `invoice.created` is not routed at all, so a blank draft arriving as
  `created` is ignored — but as an *unknown event*, which is a reason that has
  nothing to do with this rule. It would stop being true the day `created`
  gains a branch, and §4 would be unguarded again with nothing to say so.
* On `invoice.updated`, where invoices are actually mirrored, the blank draft
  was **`failed`** — and `failed` is labelled "قابلة لإعادة التشغيل" on the
  model itself. The retry queue picks it up, fails again on the arithmetic
  ("مبلغ غير موجب: 0.00"), and the case stands in the review list forever. Ten
  blank forms in a morning is ten permanent alarms about nothing, and a queue
  of false alarms is a queue nobody reads — v1's silent skip reached from the
  other side.
* **And the half the rule does not name:** a message carrying `"/"` **with a
  real amount** was mirrored, writing `"/"` into `odoo_invoice_id` as an
  identity. It is not one — it is Odoo's word for *unnumbered*, the same
  string for every draft in the system. The next such message finds the first
  by `filter(odoo_invoice_id="/")` and updates it: two unrelated invoices
  collapsed into one row whose amount is whichever arrived last, with nothing
  raised and nothing logged as wrong.

So `"/"` is now recognised before anything else is read, and it ends two ways:
nothing with it is **ignored** with a sentence naming the abandoned form,
money with it is **failed** for a person — because a placeholder plus an
amount is a contradiction, and resolving a contradiction by guessing is what
Article 2-3 forbids.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.money.models import Invoice
from apps.odoo.models import CustomerLink, InboundMessage, InboundState
from apps.odoo.processing import process

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000091", full_name="عميل أودو", password="x"
    )


@pytest.fixture
def linked(customer):
    CustomerLink.objects.create(
        user=customer, odoo_customer_id="ODOO-91", is_primary=True
    )
    return customer


def stored(payload: dict) -> InboundMessage:
    return InboundMessage.objects.create(
        source="odoo",
        event="invoice.updated",
        delivery_id=payload.get("delivery_id", ""),
        subject_ref=str(payload.get("invoice_id") or ""),
        payload={**payload, "event": "invoice.updated"},
        state=InboundState.RECEIVED,
    )


def a_blank_draft(**over) -> dict:
    """What Odoo sends when somebody opens the form and touches nothing."""
    return {
        "invoice_id": "/",
        "customer_id": "ODOO-91",
        "amount": "0.00",
        "amount_residual": "0.00",
        "state": "draft",
        "delivery_id": "blank-1",
        **over,
    }


def test_a_blank_draft_creates_no_invoice(linked):
    """The phantom debt, refused. This is the half that already worked."""
    process(stored(a_blank_draft()))

    assert Invoice.objects.count() == 0


def test_a_blank_draft_is_ignored_deliberately_not_left_to_be_retried(linked):
    """‏«تُتجاهَل» — and `IGNORED` is the state that word names.

    `FAILED` is labelled "قابلة لإعادة التشغيل" on the model itself, so a
    blank form opened in Odoo would come back through the retry queue every
    run and settle into the review list permanently. Ten blank forms in a
    morning is ten standing cases about nothing, and a queue of false alarms
    is a queue nobody reads.
    """
    message = process(stored(a_blank_draft()))

    assert message.state == InboundState.IGNORED
    assert message.processed_at is not None, "متجاهَلة ولم تُختم بوقت"


def test_the_reason_names_the_blank_draft_rather_than_the_arithmetic(linked):
    """A note somebody can act on — or decide not to.

    "مبلغ غير موجب: 0" is true and useless: it describes the arithmetic, not
    what happened. Whoever reads the queue needs to know this was a form
    somebody opened and abandoned.
    """
    message = process(stored(a_blank_draft()))

    assert "مسودّة" in message.note
    assert "/" in message.note


def test_a_placeholder_reference_carrying_money_is_not_swallowed(linked):
    """Narrow on purpose: `"/"` alone is not enough to ignore something.

    A message with Odoo's placeholder reference *and* a real amount is a
    contradiction we cannot resolve, and resolving it by guessing is what
    Article 2-3 forbids. It goes to a person.
    """
    message = process(stored(a_blank_draft(amount="1500.00")))

    assert message.state != InboundState.IGNORED
    assert Invoice.objects.count() == 0


def test_a_real_invoice_with_no_amount_still_fails_for_a_person_to_see(linked):
    """The other side of the same narrowness.

    A numbered invoice that arrives with nothing in it is not a blank form —
    it is an invoice we cannot mirror, and it must stay in the queue.
    """
    message = process(stored(a_blank_draft(invoice_id="INV/2026/0042")))

    assert message.state == InboundState.FAILED
    assert Invoice.objects.count() == 0


def test_a_normal_invoice_is_still_mirrored(linked):
    """A guard that quietly widened would show up here first."""
    message = process(
        stored(a_blank_draft(invoice_id="4242", amount="8000.00", delivery_id="real-1"))
    )

    assert message.state == InboundState.PROCESSED
    invoice = Invoice.objects.get(odoo_invoice_id="4242")
    assert invoice.amount == Decimal("8000.00")


def test_two_unnumbered_drafts_never_collapse_into_one_row(linked):
    """The half the rule does not name, and the reason the refusal is flat.

    ‏`"/"` is not an invoice's identity — it is Odoo's word for *unnumbered*,
    and every draft in the system carries the same string. Written into
    `odoo_invoice_id` it becomes a key that matches the next draft too: the
    second message finds the first by `filter(odoo_invoice_id="/")` and
    **updates it**, so two unrelated invoices end as one row whose amount is
    whichever arrived last. Nothing raises, nothing is logged as wrong, and
    the mirror quietly disagrees with Odoo.
    """
    process(stored(a_blank_draft(amount="1500.00", delivery_id="d1")))
    process(stored(a_blank_draft(amount="9000.00", delivery_id="d2")))

    assert not Invoice.objects.filter(odoo_invoice_id="/").exists()
    assert Invoice.objects.count() == 0
