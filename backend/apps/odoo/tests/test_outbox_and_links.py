"""T212–T214, T216–T218 — sending, and knowing whose money it is.

Two v1 incidents drive this file. A retry cron with no unique reference opened
a second refund on a live account; and assuming an Odoo customer id named
exactly one platform account debited 20,000 twice.
"""

import ast
from decimal import Decimal
from pathlib import Path
from unittest import mock

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import AccountKind, Invoice, InvoiceState
from apps.odoo import outbox, reconciliation
from apps.odoo.client import OdooDisabled, OdooUnreachable
from apps.odoo.models import (
    BalanceCheck,
    CustomerLink,
    InboundMessage,
    InboundState,
    OutboxMessage,
    OutboxState,
)
from apps.odoo.processing import process

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000001", full_name="عميل", password="x"
    )


@pytest.fixture
def second_account(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000002", full_name="نفس الشخص، حساب آخر", password="x"
    )


@pytest.fixture
def invoice(customer):
    return Invoice.objects.create(
        customer=customer,
        number="INV/2026/0001",
        amount=Decimal("7000.00"),
        state=InvoiceState.OPEN,
        odoo_invoice_id="ODOO-INV-1",
        issued_at=timezone.now(),
    )


@pytest.fixture
def a_payment(invoice):
    """Record a payment and hand back its transaction.

    The outbox reference is derived from this transaction rather than from a
    count of the rows already queued, so a test that wants two references has
    to produce two payments — which is the point: two payments that cannot name
    themselves apart are two payments Odoo hears about once.
    """

    def make(amount=Decimal("1000.00"), reference="P/1"):
        return services.record_payment(
            invoice=invoice, amount=amount, source="cash", reference=reference
        )

    return make


# ---------------------------------------------------------------------------
# T212 — nothing calls Odoo except the sender
# ---------------------------------------------------------------------------


class TestOutboxTable:
    def test_an_intention_becomes_a_row_not_a_call(self, invoice, a_payment):
        message = outbox.queue_payment(
            invoice, Decimal("1000.00"), source_transaction=a_payment()
        )

        assert message.state == OutboxState.PENDING
        assert message.attempts == 0

    def test_queuing_the_same_reference_twice_returns_one_row(self, invoice):
        first = outbox.enqueue(endpoint="payments", payload={"a": 1}, reference="REF/1")
        second = outbox.enqueue(endpoint="payments", payload={"a": 1}, reference="REF/1")

        assert first.pk == second.pk
        assert OutboxMessage.objects.filter(reference="REF/1").count() == 1

    def test_no_module_outside_the_client_and_sender_calls_odoo(self):
        """The text check the task asks for, done by parsing rather than
        grepping so a call inside a string or comment does not fail it."""
        allowed = {"client.py", "outbox.py", "reconciliation.py"}
        offenders = []

        for path in sorted(Path(outbox.__file__).parent.rglob("*.py")):
            if path.name in allowed or "test" in path.parts or "migrations" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in (
                    "post",
                    "get",
                    "put",
                ):
                    if isinstance(node.value, ast.Name) and node.value.id == "requests":
                        offenders.append(f"{path.name}:{node.lineno}")
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    names = (
                        [a.name for a in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
                    if any(n and n.startswith("requests") for n in names):
                        offenders.append(f"{path.name}:{node.lineno} imports requests")

        assert offenders == [], f"HTTP to Odoo outside the sender: {offenders}"

    def test_the_client_refuses_loudly_when_the_integration_is_off(
        self, settings, invoice
    ):
        """Article 2-6. A disabled client that returns quietly is how a staging
        deploy convinces you a real invoice was issued."""
        settings.ODOO_ENABLED = False

        with pytest.raises(OdooDisabled):
            from apps.odoo.client import call

            call("payments", {}, reference="REF/off")


# ---------------------------------------------------------------------------
# T213 — retry that cannot act twice
# ---------------------------------------------------------------------------


class TestSending:
    def test_a_confirmed_send_records_the_response(self, invoice, a_payment, settings):
        settings.ODOO_ENABLED = True
        message = outbox.queue_payment(
            invoice, Decimal("1000.00"), source_transaction=a_payment()
        )

        with mock.patch("apps.odoo.outbox.call", return_value={"id": 42}) as called:
            outbox.send(message)

        assert message.state == OutboxState.CONFIRMED
        assert message.response == {"id": 42}
        assert called.call_count == 1

    def test_a_network_failure_then_success_makes_one_effective_call(
        self, invoice, a_payment, settings
    ):
        """C5, and the v1 incident. The reference is unchanged across attempts,
        so even if the first call did reach Odoo, the second cannot act twice.
        """
        settings.ODOO_ENABLED = True
        message = outbox.queue_payment(
            invoice, Decimal("1000.00"), source_transaction=a_payment()
        )
        reference_first_attempt = message.reference

        with mock.patch("apps.odoo.outbox.call", side_effect=OdooUnreachable("timeout")):
            outbox.send(message)
        assert message.state == OutboxState.FAILED

        with mock.patch("apps.odoo.outbox.call", return_value={"ok": True}) as ok:
            outbox.send(message)

        assert message.state == OutboxState.CONFIRMED
        assert ok.call_args.kwargs["reference"] == reference_first_attempt
        assert OutboxMessage.objects.count() == 1

    def test_a_refusal_is_abandoned_not_retried_forever(
        self, invoice, a_payment, settings
    ):
        """Odoo considered it and said no. Sending the same thing again gets
        the same answer; a person has to change something."""
        settings.ODOO_ENABLED = True
        message = outbox.queue_payment(
            invoice, Decimal("1000.00"), source_transaction=a_payment()
        )

        with mock.patch(
            "apps.odoo.outbox.call", side_effect=ValueError("أودو رفضت: 400")
        ):
            outbox.send(message)

        assert message.state == OutboxState.ABANDONED
        assert message not in outbox.due()

    def test_unreachable_is_kept_distinct_from_refused(self, invoice, settings):
        """Article 2-4. Not reaching them proves nothing about whether they
        acted — a five-second timeout read as 'no money moved' pulled 10,000
        from a real customer in v1. One retries; the other must not."""
        settings.ODOO_ENABLED = True
        unreachable = outbox.enqueue(
            endpoint="payments", payload={}, reference="REF/unreachable"
        )
        refused = outbox.enqueue(endpoint="payments", payload={}, reference="REF/refused")

        with mock.patch("apps.odoo.outbox.call", side_effect=OdooUnreachable("timeout")):
            outbox.send(unreachable)
        with mock.patch("apps.odoo.outbox.call", side_effect=ValueError("400")):
            outbox.send(refused)

        assert unreachable.state == OutboxState.FAILED
        assert refused.state == OutboxState.ABANDONED

    def test_a_message_out_of_attempts_leaves_the_queue(self, invoice, a_payment):
        message = outbox.queue_payment(
            invoice, Decimal("1000.00"), source_transaction=a_payment()
        )
        OutboxMessage.objects.filter(pk=message.pk).update(
            attempts=outbox.MAX_ATTEMPTS, state=OutboxState.FAILED
        )

        assert OutboxMessage.objects.get(pk=message.pk) not in outbox.due()


# ---------------------------------------------------------------------------
# T214 — a reference per partial payment
# ---------------------------------------------------------------------------


class TestPartialPaymentReferences:
    def test_three_partial_payments_get_three_references(self, invoice, a_payment):
        """223 attempts across 26 invoices were refused in v1 for exactly this:
        every partial payment reused the invoice's own memo, and Odoo rejects a
        reference it has already seen."""
        payments = [a_payment(reference=f"P/{i}") for i in range(3)]
        references = [
            outbox.queue_payment(
                invoice, Decimal("1000.00"), source_transaction=payment
            ).reference
            for payment in payments
        ]

        assert len(set(references)) == 3
        assert references == [f"{invoice.number}/P{payment.uuid}" for payment in payments]

    def test_two_payments_recorded_at_once_still_get_two_references(
        self, invoice, a_payment
    ):
        """The reference no longer counts rows, so it cannot count them wrongly.

        This is the shape that used to lose a payment: both callers took
        ``COUNT(*)`` before either had inserted, both built ``…/P1``, and
        ``enqueue`` — correctly treating a repeated caller-supplied reference as
        already queued — handed the loser the winner's row and the winner's
        payload. Our ledger held two payments, Odoo heard about one, and there
        was nothing left to replay. Building the reference from each payment's
        own identity removes the shared input entirely, so this passes without
        any ordering between the two callers.
        """
        first, second = a_payment(reference="P/a"), a_payment(reference="P/b")

        # Both references are decided before either message is inserted.
        references = [
            outbox.payment_reference(invoice, first),
            outbox.payment_reference(invoice, second),
        ]
        rows = [
            outbox.enqueue(endpoint="payments", payload={"n": i}, reference=reference)
            for i, reference in enumerate(references)
        ]

        assert len(set(references)) == 2
        assert OutboxMessage.objects.count() == 2
        assert [row.payload["n"] for row in rows] == [0, 1]

    def test_the_reference_names_the_invoice_it_belongs_to(self, invoice, a_payment):
        reference = outbox.queue_payment(
            invoice, Decimal("1.00"), source_transaction=a_payment()
        ).reference

        assert reference.startswith(invoice.number)

    def test_amounts_leave_as_strings_not_floats(self, invoice, a_payment):
        """Article 3-2 does not stop at our boundary."""
        message = outbox.queue_payment(
            invoice, Decimal("10000.50"), source_transaction=a_payment()
        )

        assert message.payload["amount"] == "10000.50"
        assert isinstance(message.payload["amount"], str)


# ---------------------------------------------------------------------------
# T216 — identity is a graph, not an equality
# ---------------------------------------------------------------------------


class TestCustomerLinks:
    def test_one_odoo_customer_with_three_accounts_pays_only_the_primary(
        self, customer, second_account, django_user_model
    ):
        """C6, on the real v1 shape. Assuming the id named one account paired
        money keyed by Odoo with deposits keyed by user, and 20,000 was
        debited twice."""
        third = django_user_model.objects.create_user(
            phone="966500000003", full_name="حساب ثالث", password="x"
        )
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-9", is_primary=True
        )
        CustomerLink.objects.create(
            user=second_account, odoo_customer_id="ODOO-9", is_primary=False
        )
        CustomerLink.objects.create(
            user=third, odoo_customer_id="ODOO-9", is_primary=False
        )

        message = InboundMessage.objects.create(
            source="odoo",
            event="payment.posted",
            payload={
                "event": "payment.posted",
                "payment_id": "P/graph",
                "amount": "10000.00",
                "customer_id": "ODOO-9",
            },
            state=InboundState.RECEIVED,
        )
        process(message)

        assert services.account_for(customer, AccountKind.INSURANCE_FREE).balance == TEN_K
        for other in (second_account, third):
            assert services.account_for(
                other, AccountKind.INSURANCE_FREE
            ).balance == Decimal("0.00")

    def test_the_database_allows_only_one_primary_per_odoo_customer(
        self, customer, second_account
    ):
        from django.db import IntegrityError, transaction

        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-10", is_primary=True
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            CustomerLink.objects.create(
                user=second_account, odoo_customer_id="ODOO-10", is_primary=True
            )

    def test_one_account_can_belong_to_several_odoo_customers(self, customer):
        """The graph goes both ways. A person with two Odoo records is as real
        as an Odoo record with two accounts."""
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-11", is_primary=True
        )
        CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-12", is_primary=True
        )

        assert CustomerLink.objects.filter(user=customer).count() == 2


# ---------------------------------------------------------------------------
# T218 — an unknown customer is never guessed at
# ---------------------------------------------------------------------------


class TestUnknownCustomer:
    def test_the_money_is_kept_and_no_account_is_invented(
        self, customer, django_user_model
    ):
        """v1 matched on phone as a fallback. One placeholder row with an empty
        phone matched everybody, and a unique index on phone took the whole
        safety net down with it."""
        accounts_before = django_user_model.objects.count()
        message = InboundMessage.objects.create(
            source="odoo",
            event="payment.posted",
            payload={
                "event": "payment.posted",
                "payment_id": "P/unknown",
                "amount": "10000.00",
                "customer_id": "ODOO-NOBODY",
            },
            state=InboundState.RECEIVED,
        )

        process(message)

        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K
        assert django_user_model.objects.count() == accounts_before
        assert message.state == InboundState.PROCESSED
        assert "غير مربوط" in message.note

    def test_nothing_matches_on_phone_or_name(self):
        """Enforced by reading the source: a fallback added later would pass
        every test above while reopening the exact hole."""
        from apps.odoo import processing

        source = Path(processing.__file__).read_text(encoding="utf-8")
        for line in source.splitlines():
            if "filter(" in line and ("phone" in line or "full_name" in line):
                pytest.fail(f"customer matched by identity guess: {line.strip()}")


# ---------------------------------------------------------------------------
# T217 — comparing with the book of record (Q2 resolved)
# ---------------------------------------------------------------------------


class TestBalanceCheck:
    @pytest.fixture
    def link(self, customer):
        return CustomerLink.objects.create(
            user=customer, odoo_customer_id="ODOO-B", is_primary=True
        )

    def _odoo_says(self, subscriptions, refunds):
        def fake_call(endpoint, payload, *, reference):
            if "subscriptions" in reference:
                return {"records": subscriptions}
            return {"records": refunds}

        return mock.patch("apps.odoo.reconciliation.call", side_effect=fake_call)

    def test_agreement_is_recorded_too_not_only_disagreement(self, link, customer):
        """A comparison that only records differences cannot tell "we checked
        and it matched" from "we never checked"."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D1"
        )

        with self._odoo_says([{"amount_total": "10000.00", "state": "paid"}], []):
            check = reconciliation.check_customer(link)

        assert check.ours == TEN_K
        assert check.theirs == TEN_K
        assert check.difference == Decimal("0.00")

    def test_a_difference_opens_a_record_and_moves_nothing(self, link, customer):
        """C7. The v1 case exactly: we show 10,000, Odoo closes at zero."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D2"
        )
        balance_before = services.account_for(
            customer, AccountKind.INSURANCE_FREE
        ).balance

        with self._odoo_says([], []):
            check = reconciliation.check_customer(link)

        assert check.difference == TEN_K
        assert check.resolved_at is None
        assert check in reconciliation.open_differences()
        assert (
            services.account_for(customer, AccountKind.INSURANCE_FREE).balance
            == balance_before
        ), "reconciliation must never move money"

    def test_our_side_counts_held_and_locked_too(self, link, customer):
        """Money held for an auction is still the customer's, and still
        corresponds to something Odoo recorded."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D3"
        )
        invoice = Invoice.objects.create(
            customer=customer,
            number="INV/B/1",
            amount=Decimal("4000.00"),
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
        )
        services.lock_for_invoice(user=customer, invoice=invoice)

        assert reconciliation.our_balance(customer) == TEN_K

    def test_subscriptions_minus_refunds_is_the_formula(self, link, customer):
        with self._odoo_says(
            [
                {"amount_total": "10000.00", "state": "paid"},
                {"amount_total": "5000.00", "state": "posted"},
            ],
            [{"amount_total": "3000.00", "state": "paid"}],
        ):
            check = reconciliation.check_customer(link)

        assert check.theirs == Decimal("12000.00")
        assert check.detail["subscriptions"] == "15000.00"
        assert check.detail["refunds"] == "3000.00"

    def test_draft_rows_are_not_counted(self, link, customer):
        with self._odoo_says(
            [
                {"amount_total": "10000.00", "state": "paid"},
                {"amount_total": "9999.00", "state": "draft"},
            ],
            [],
        ):
            check = reconciliation.check_customer(link)

        assert check.theirs == TEN_K

    def test_an_unknown_odoo_state_is_neither_counted_nor_silently_dropped(
        self, link, customer
    ):
        """Article 2-3. A new state on their side may be real money we do not
        know how to count — so the figure is marked incomplete and the state
        is named, rather than the row vanishing into a sum."""
        with self._odoo_says(
            [
                {"amount_total": "10000.00", "state": "paid"},
                {"amount_total": "5000.00", "state": "partially_reconciled_v18"},
            ],
            [],
        ):
            check = reconciliation.check_customer(link)

        assert check.theirs == TEN_K
        assert check.detail["complete"] is False
        assert check.detail["unknown_states"] == {"partially_reconciled_v18": 1}
        assert "partially_reconciled_v18" in check.detail["note"]
        assert "لا يصلح للمقارنة وحده" in check.detail["note"]

    def test_the_method_and_its_version_are_recorded(self, link, customer):
        """Q2's condition. When the definition changes, old rows stay readable
        as products of the old rule instead of blending into the new."""
        with self._odoo_says([], []):
            check = reconciliation.check_customer(link)

        assert check.method == "subscriptions_minus_refunds/v1"
        assert BalanceCheck.objects.get(pk=check.pk).method == check.method

    def test_an_unreadable_amount_is_counted_as_a_gap(self, link, customer):
        with self._odoo_says([{"amount_total": "not a number", "state": "paid"}], []):
            check = reconciliation.check_customer(link)

        assert check.detail["unreadable_amounts"] == 1
        assert check.detail["complete"] is False
