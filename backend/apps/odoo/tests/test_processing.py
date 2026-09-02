"""T206–T211 — interpreting a stored message.

The centrepiece is `TestTheV1Sequence`: the three-message exchange that broke
in production, replayed end to end.
"""

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    AccountKind,
    Invoice,
    InvoiceState,
    RefundRequestState,
    Transaction,
)
from apps.money.verification import verify_ledger
from apps.odoo import processing
from apps.odoo.models import CustomerLink, InboundMessage, InboundState
from apps.odoo.processing import process

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000001", full_name="عميل أودو", password="x"
    )


@pytest.fixture
def linked(customer):
    CustomerLink.objects.create(user=customer, odoo_customer_id="ODOO-1", is_primary=True)
    return customer


def stored(event: str, payload: dict, **kwargs) -> InboundMessage:
    """A message as the webhook would have stored it."""
    return InboundMessage.objects.create(
        source="odoo",
        event=event,
        delivery_id=payload.get("delivery_id", ""),
        subject_ref=str(payload.get("invoice_id") or payload.get("payment_id") or ""),
        payload={**payload, "event": event},
        state=InboundState.RECEIVED,
        **kwargs,
    )


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


# ---------------------------------------------------------------------------
# T206 — three endings, never a fourth
# ---------------------------------------------------------------------------


class TestThreeEndings:
    def test_a_understood_message_ends_processed(self, linked):
        message = stored(
            "payment.posted",
            {"payment_id": "P1", "amount": "10000.00", "customer_id": "ODOO-1"},
        )

        process(message)

        assert message.state == InboundState.PROCESSED
        assert message.note != ""
        assert message.processed_at is not None

    def test_an_unknown_event_ends_ignored_with_its_name(self, linked):
        """`ignored`, not `failed`: retrying will never teach us what
        `sale.order.confirmed` means. A person reads it and adds a branch."""
        message = stored("sale.order.confirmed", {"amount": "1.00"})

        process(message)

        assert message.state == InboundState.IGNORED
        assert "sale.order.confirmed" in message.note

    def test_an_unusable_message_ends_failed_with_the_error(self, linked):
        message = stored("payment.posted", {"amount": "10000.00"})

        process(message)

        assert message.state == InboundState.FAILED
        assert "معرّف دفعة" in message.note

    def test_a_raising_handler_ends_failed_and_does_not_crash(self, linked):
        message = stored(
            "payment.posted",
            {"payment_id": "P/boom", "amount": "1.00", "customer_id": "ODOO-1"},
        )
        with mock.patch.object(
            processing, "_handle_payment", side_effect=RuntimeError("boom")
        ):
            process(message)

        assert message.state == InboundState.FAILED
        assert "RuntimeError: boom" in message.note

    def test_every_ending_carries_a_written_reason(self, linked):
        """Article 2-2, enforced at construction: an Outcome with a blank note
        cannot be built, so a branch cannot end silently even by accident."""
        with pytest.raises(ValueError, match="states its reason"):
            processing.Outcome(InboundState.IGNORED, "   ")

    def test_no_branch_in_the_module_returns_without_an_outcome(self):
        """Reads the source. Every `return` inside an interpretation function
        must return an Outcome — a bare `return` is the silent ending this
        whole design forbids."""
        tree = ast.parse(
            Path(processing.__file__).read_text(encoding="utf-8"),
            filename=processing.__file__,
        )
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith(("_handle_", "_interpret")):
                continue
            for statement in ast.walk(node):
                if isinstance(statement, ast.Return) and statement.value is None:
                    offenders.append(f"{node.name}:{statement.lineno}")
        assert offenders == [], f"bare returns in interpretation: {offenders}"

    def test_an_already_processed_message_is_left_alone(self, linked):
        message = stored(
            "payment.posted",
            {"payment_id": "P2", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        process(message)
        attempts = message.attempts

        process(message)

        assert message.attempts == attempts
        assert free(linked) == TEN_K


# ---------------------------------------------------------------------------
# T207 — Odoo's word is kept, never branched on
# ---------------------------------------------------------------------------


class TestRawState:
    def test_an_invented_state_is_stored_and_drops_nothing(self, linked):
        """C3, and the v1 incident: an enum column rejected an unfamiliar value
        and rolled back the whole insert, so the webhook looked stopped while
        it was working perfectly."""
        message = stored(
            "invoice.posted",
            {
                "invoice_id": "INV-1",
                "amount": "7000.00",
                "customer_id": "ODOO-1",
                "state": "posted_and_partially_reconciled_v18",
            },
        )

        process(message)

        assert message.state == InboundState.PROCESSED
        invoice = Invoice.objects.get(odoo_invoice_id="INV-1")
        assert invoice.odoo_state_raw == "posted_and_partially_reconciled_v18"
        assert invoice.state == InvoiceState.OPEN

    def test_nothing_in_the_module_branches_on_the_raw_state(self):
        source = Path(processing.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("if ", "elif ")) and "odoo_state_raw" in stripped:
                pytest.fail(f"branch on Odoo's own word: {stripped}")

    def test_a_later_message_updates_the_stored_word(self, linked):
        process(
            stored(
                "invoice.posted",
                {
                    "invoice_id": "INV-2",
                    "amount": "7000.00",
                    "customer_id": "ODOO-1",
                    "state": "draft",
                },
            )
        )

        process(
            stored(
                "invoice.updated",
                {
                    "invoice_id": "INV-2",
                    "amount": "7000.00",
                    "customer_id": "ODOO-1",
                    "state": "posted",
                },
            )
        )

        assert Invoice.objects.get(odoo_invoice_id="INV-2").odoo_state_raw == "posted"


# ---------------------------------------------------------------------------
# T208 — the key comes from the event, so replay is free
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_processing_the_same_message_twice_credits_once(self, linked):
        """C4."""
        first = stored(
            "payment.posted",
            {"payment_id": "P3", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        process(first)

        replay = stored(
            "payment.posted",
            {"payment_id": "P3", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        process(replay)

        assert free(linked) == TEN_K
        assert (
            Transaction.objects.filter(
                idempotency_key=services.deposit_key("cash", "odoo:P3")
            ).count()
            == 1
        )

    def test_the_key_is_the_payments_identity_not_the_message_row(self, linked):
        message = stored(
            "payment.posted",
            {"payment_id": "P4", "amount": "10000.00", "customer_id": "ODOO-1"},
        )

        process(message)

        assert message.resulting_transaction.idempotency_key == services.deposit_key(
            "cash", "odoo:P4"
        )


# ---------------------------------------------------------------------------
# T209 — the sequence that broke in v1
# ---------------------------------------------------------------------------


class TestTheV1Sequence:
    def test_the_three_message_exchange_ends_in_the_right_place(self, linked):
        """The whole reason phase 003 is written the way it is.

        Odoo sends three messages about one payment:

        1. `payment.posted`  — no invoice link, because Odoo does not have one yet
        2. `invoice.posted`  — the invoice itself
        3. `payment.updated` — the same payment, now carrying the invoice link

        In v1 a dedup rule keyed on the subject threw away the third, so the
        deposit stayed in the customer's free balance and went on showing as
        refundable long after the debt it had settled.
        """
        process(
            stored(
                "payment.posted",
                {
                    "payment_id": "P10",
                    "amount": "10000.00",
                    "customer_id": "ODOO-1",
                    "invoice_id": None,
                },
            )
        )
        assert free(linked) == TEN_K, "step 1 credits the deposit"

        process(
            stored(
                "invoice.posted",
                {
                    "invoice_id": "INV-10",
                    "amount": "7000.00",
                    "customer_id": "ODOO-1",
                    "state": "posted",
                },
            )
        )

        third = stored(
            "payment.updated",
            {
                "payment_id": "P10",
                "amount": "10000.00",
                "customer_id": "ODOO-1",
                "invoice_id": "INV-10",
            },
        )
        process(third)

        invoice = Invoice.objects.get(odoo_invoice_id="INV-10")
        assert third.state == InboundState.PROCESSED
        assert invoice.state == InvoiceState.PAID
        assert free(linked) == Decimal("3000.00"), (
            "only the change is refundable — the 7,000 that settled the debt "
            "must not still look available"
        )
        assert verify_ledger() == []

    def test_the_third_message_does_not_credit_the_deposit_again(self, linked):
        process(
            stored(
                "payment.posted",
                {"payment_id": "P11", "amount": "10000.00", "customer_id": "ODOO-1"},
            )
        )
        process(
            stored(
                "invoice.posted",
                {"invoice_id": "INV-11", "amount": "7000.00", "customer_id": "ODOO-1"},
            )
        )

        process(
            stored(
                "payment.updated",
                {
                    "payment_id": "P11",
                    "amount": "10000.00",
                    "customer_id": "ODOO-1",
                    "invoice_id": "INV-11",
                },
            )
        )

        assert (
            Transaction.objects.filter(
                idempotency_key=services.deposit_key("cash", "odoo:P11")
            ).count()
            == 1
        )

    def test_a_payment_naming_an_invoice_we_have_not_seen_says_so_plainly(self, linked):
        """Not a failure. The invoice message may simply not have arrived yet,
        and the money is already safely recorded as insurance."""
        message = stored(
            "payment.posted",
            {
                "payment_id": "P12",
                "amount": "10000.00",
                "customer_id": "ODOO-1",
                "invoice_id": "INV-not-yet",
            },
        )

        process(message)

        assert message.state == InboundState.PROCESSED
        assert "لم تصلنا بعد" in message.note
        assert free(linked) == TEN_K


# ---------------------------------------------------------------------------
# T211 — a replay must not recreate a refunded charge
# ---------------------------------------------------------------------------


class TestReplayChecksForALaterRefund:
    def test_a_payment_refunded_after_the_message_is_not_replayed(self, linked):
        """The v1 incident, exactly: a dropped payment was replayed weeks later
        onto a customer who had already had that same 10,000 returned, turning
        a fixed bug into a fresh debt.

        A dropped payment is not automatically still owed.
        """
        message = stored(
            "payment.posted",
            {"payment_id": "P20", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        # The customer deposited and was refunded through another channel,
        # after this message arrived and before anyone replayed it.
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="OTHER"
        )
        services.refund_insurance(
            user=linked,
            amount=TEN_K,
            reference="R1",
            occurred_at=timezone.now() + timedelta(hours=1),
        )
        balance_before = free(linked)

        process(message)

        assert message.state == InboundState.IGNORED
        assert "استُرد له" in message.note
        assert free(linked) == balance_before
        assert not Transaction.objects.filter(
            idempotency_key=services.deposit_key("cash", "odoo:P20")
        ).exists()

    def test_a_refund_of_a_different_amount_does_not_block_the_replay(self, linked):
        message = stored(
            "payment.posted",
            {"payment_id": "P21", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="OTHER2"
        )
        services.refund_insurance(
            user=linked,
            amount=Decimal("500.00"),
            reference="R2",
            occurred_at=timezone.now() + timedelta(hours=1),
        )

        process(message)

        assert message.state == InboundState.PROCESSED

    def test_a_refund_before_the_message_does_not_block_it(self, linked):
        """Only a refund *after* the message says the money went back. An
        earlier one is unrelated history."""
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="OTHER3"
        )
        services.refund_insurance(
            user=linked,
            amount=TEN_K,
            reference="R3",
            occurred_at=timezone.now() - timedelta(days=2),
        )
        message = stored(
            "payment.posted",
            {"payment_id": "P22", "amount": "10000.00", "customer_id": "ODOO-1"},
        )

        process(message)

        assert message.state == InboundState.PROCESSED


# ---------------------------------------------------------------------------
# Unlinked customers — money is kept, never guessed at
# ---------------------------------------------------------------------------


class TestUnlinkedCustomer:
    def test_money_for_an_unknown_customer_goes_to_suspense(self, customer):
        message = stored(
            "payment.posted",
            {"payment_id": "P30", "amount": "10000.00", "customer_id": "ODOO-UNKNOWN"},
        )

        process(message)

        assert message.state == InboundState.PROCESSED
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K
        assert "غير مربوط" in message.note

    def test_links_without_a_primary_are_a_human_decision_not_a_guess(
        self, customer, django_user_model
    ):
        """Picking the newest or the first link is exactly the guess that
        debited 20,000 twice in v1."""
        second = django_user_model.objects.create_user(
            phone="966500000002", full_name="حساب ثانٍ", password="x"
        )
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-2", is_primary=False
        )
        CustomerLink.objects.create(
            user=second, odoo_customer_id="ODOO-2", is_primary=False
        )
        message = stored(
            "payment.posted",
            {"payment_id": "P31", "amount": "10000.00", "customer_id": "ODOO-2"},
        )

        process(message)

        assert "قراراً بشرياً" in message.note
        assert free(customer) == Decimal("0.00")
        assert free(second) == Decimal("0.00")
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K


# ---------------------------------------------------------------------------
# The payment that arrived before we knew whose it was
# ---------------------------------------------------------------------------


class TestASuspensePaymentThatLaterFindsItsOwner:
    def test_linking_the_customer_credits_the_money_already_in_suspense(self, customer):
        """`posted` arrives unlinked, the link is made, `updated` arrives.

        Before the fix the two paths shared one idempotency key, so the second
        message found the suspense transaction, skipped the deposit entirely,
        and left the customer with nothing — measured: free 0.00, suspense
        10,000, and the message FAILED on every retry because the lock it then
        tried to take had no free insurance to take from.
        """
        first = stored(
            "payment.posted",
            {"payment_id": "P90", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
        process(first)
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K

        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-1", is_primary=True
        )
        second = stored(
            "payment.updated",
            {
                "payment_id": "P90",
                "amount": "10000.00",
                "customer_id": "ODOO-1",
                "delivery_id": "D/90b",
            },
        )
        process(second)

        assert second.state == InboundState.PROCESSED
        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("0.00")
        # One payment arrived, so the outside world is charged once.
        assert services.system_account(AccountKind.EXTERNAL_CASH).balance == -TEN_K
        assert verify_ledger() == []

    def test_and_it_then_settles_the_invoice_the_link_named(self, customer):
        """The whole v1 sequence, with the first message unattributed."""
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-9", is_primary=True
        )
        invoice = Invoice.objects.create(
            customer=customer,
            number="INV/ODOO/90",
            amount=TEN_K,
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
            odoo_invoice_id="ODOO-INV-90",
        )
        # Stored while the link did not exist yet.
        unlinked = stored(
            "payment.posted",
            {"payment_id": "P91", "amount": "10000.00", "customer_id": "ODOO-UNKNOWN"},
        )
        process(unlinked)
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K

        # Odoo re-sends the same payment, this time naming a customer we know.
        linked_again = stored(
            "payment.updated",
            {
                "payment_id": "P91",
                "amount": "10000.00",
                "customer_id": "ODOO-9",
                "invoice_id": "ODOO-INV-90",
                "delivery_id": "D/91b",
            },
        )
        process(linked_again)

        invoice.refresh_from_db()
        assert linked_again.state == InboundState.PROCESSED
        assert invoice.state == InvoiceState.PAID
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("0.00")
        assert verify_ledger() == []


# ---------------------------------------------------------------------------
# The refund Odoo confirmed — the only inbound branch that pays a customer out
# ---------------------------------------------------------------------------


class TestRefundConfirmed:
    """Four endings, and the request the payout answers.

    This branch is the only one that moves money *towards* a customer, and it
    had no test at all: not the failures, not the success, and nothing anywhere
    ever advanced a `RefundRequest` past `requested`.
    """

    def test_a_refund_without_an_id_fails_with_its_reason(self, linked):
        message = stored("refund.confirmed", {"amount": "1000.00"})

        process(message)

        assert message.state == InboundState.FAILED
        assert "بلا معرّف" in message.note

    def test_an_unreadable_amount_fails_with_its_reason(self, linked):
        message = stored(
            "refund.confirmed",
            {"refund_id": "R1", "amount": "ألف", "customer_id": "ODOO-1"},
        )

        process(message)

        assert message.state == InboundState.FAILED
        assert "مبلغ غير صالح" in message.note

    def test_an_unlinked_customer_fails_rather_than_guessing(self, customer):
        message = stored(
            "refund.confirmed",
            {"refund_id": "R2", "amount": "1000.00", "customer_id": "ODOO-NOBODY"},
        )

        process(message)

        assert message.state == InboundState.FAILED
        assert "غير مربوط" in message.note
        assert free(customer) == Decimal("0.00")

    def test_a_confirmed_refund_takes_the_money_out_of_free_insurance(self, linked):
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="SEED/R"
        )
        message = stored(
            "refund.confirmed",
            {"refund_id": "R3", "amount": "4000.00", "customer_id": "ODOO-1"},
        )

        process(message)

        assert message.state == InboundState.PROCESSED
        assert free(linked) == Decimal("6000.00")
        assert services.system_account(AccountKind.EXTERNAL_REFUND).balance == Decimal(
            "4000.00"
        )
        assert verify_ledger() == []

    def test_it_closes_the_request_that_asked_for_it(self, linked):
        """The lifecycle, end to end.

        Nothing in the tree ever wrote `RefundRequestState`, so a customer's
        request read «مُقدَّم» forever after the money had already left — and
        because one open request is all a customer may have, they could never
        ask for anything again. The `a_confirmed_refund_names_its_transaction`
        CHECK, the schema's expression of Article 1-6, was unreachable.
        """
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="SEED/R"
        )
        request = services.request_refund(user=linked, amount=Decimal("4000.00"))
        assert request.state == RefundRequestState.REQUESTED

        message = stored(
            "refund.confirmed",
            {
                "refund_id": "R4",
                "amount": "4000.00",
                "customer_id": "ODOO-1",
                "reference": request.reference,
            },
        )
        process(message)

        request.refresh_from_db()
        assert message.state == InboundState.PROCESSED
        assert request.state == RefundRequestState.CONFIRMED
        assert request.resulting_transaction_id == message.resulting_transaction_id
        assert free(linked) == Decimal("6000.00")
        assert verify_ledger() == []

    def test_a_payout_with_no_reference_still_records_why_nothing_closed(self, linked):
        """Article 2-2: no branch here ends in a silent return."""
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="SEED/R"
        )
        services.request_refund(user=linked, amount=Decimal("4000.00"))

        message = stored(
            "refund.confirmed",
            {"refund_id": "R5", "amount": "4000.00", "customer_id": "ODOO-1"},
        )
        process(message)

        assert message.state == InboundState.PROCESSED
        assert "بلا مرجع طلب" in message.note

    def test_the_customer_can_ask_again_once_the_first_is_executed(self, linked):
        services.deposit_insurance(
            user=linked, amount=TEN_K, source="cash", reference="SEED/R"
        )
        first = services.request_refund(user=linked, amount=Decimal("4000.00"))
        process(
            stored(
                "refund.confirmed",
                {
                    "refund_id": "R6",
                    "amount": "4000.00",
                    "customer_id": "ODOO-1",
                    "reference": first.reference,
                },
            )
        )

        second = services.request_refund(user=linked, amount=Decimal("1000.00"))

        assert second.pk != first.pk


class TestOdooCannotEraseDuesByLoweringAnInvoice:
    def test_lowering_below_what_is_paid_is_refused_with_its_reason(self, linked):
        """15,000 of real dues used to disappear from every report.

        `_handle_invoice` wrote `amount` without looking at `amount_paid`, so a
        20,000 invoice settled from a customer's insurance and then lowered to
        5,000 read `outstanding = 0`, derived PAID, and left no reversing entry
        and no note. `check_locked_not_above_dues` computed zero outstanding
        too, so nothing reported it.
        """
        services.deposit_insurance(
            user=linked, amount=Decimal("20000.00"), source="cash", reference="SEED/INV"
        )
        invoice = Invoice.objects.create(
            customer=linked,
            number="INV/LOWER/1",
            amount=Decimal("20000.00"),
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
            odoo_invoice_id="ODOO-LOWER-1",
        )
        services.lock_for_invoice(user=linked, invoice=invoice)
        services.record_payment(
            invoice=invoice,
            amount=Decimal("20000.00"),
            source="insurance",
            reference="paid-in-full",
        )

        message = stored(
            "invoice.updated",
            {
                "invoice_id": "ODOO-LOWER-1",
                "amount": "5000.00",
                "customer_id": "ODOO-1",
                "state": "posted",
            },
        )
        process(message)

        invoice.refresh_from_db()
        assert message.state == InboundState.FAILED
        assert "تخفيضها تحت المسدَّد" in message.note
        assert invoice.amount == Decimal("20000.00")
        assert verify_ledger() == []

    def test_the_schema_refuses_it_too(self, linked):
        """B6 — reached by going around the interpreter entirely."""
        from django.db import IntegrityError, transaction

        invoice = Invoice.objects.create(
            customer=linked,
            number="INV/LOWER/2",
            amount=Decimal("100.00"),
            amount_paid=Decimal("100.00"),
            state=InvoiceState.PAID,
            issued_at=timezone.now(),
        )

        invoice.amount = Decimal("50.00")
        with pytest.raises(IntegrityError, match="invoice_paid_not_above_amount"):
            with transaction.atomic():
                invoice.save(update_fields=["amount"])

    def test_raising_an_invoice_is_still_allowed(self, linked):
        """Odoo adding a line is ordinary. Only going below the paid total is
        the thing that erases dues."""
        invoice = Invoice.objects.create(
            customer=linked,
            number="INV/LOWER/3",
            amount=Decimal("100.00"),
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
            odoo_invoice_id="ODOO-LOWER-3",
        )

        message = stored(
            "invoice.updated",
            {
                "invoice_id": "ODOO-LOWER-3",
                "amount": "500.00",
                "customer_id": "ODOO-1",
                "state": "posted",
            },
        )
        process(message)

        invoice.refresh_from_db()
        assert message.state == InboundState.PROCESSED
        assert invoice.amount == Decimal("500.00")
