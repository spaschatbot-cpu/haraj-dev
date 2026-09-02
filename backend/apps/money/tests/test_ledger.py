"""What the money engine must never get wrong.

Each test here corresponds to something that actually went wrong in v1. If one
of them starts failing, a real customer is about to lose or gain money they
should not have.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.money import services
from apps.money.models import (
    Account,
    AccountKind,
    Entry,
    Hold,
    HoldState,
    Invoice,
    InvoiceState,
    Transaction,
)

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


class TestPosting:
    def test_a_deposit_moves_the_money_and_balances(self, customer):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )

        assert free(customer) == TEN_K
        external = services.system_account(AccountKind.EXTERNAL_CASH)
        assert external.balance == -TEN_K
        assert sum(e.amount for e in Entry.objects.all()) == Decimal("0.00")

    def test_the_same_payment_heard_twice_credits_once(self, customer):
        """v1 replayed an old payment and credited it a second time."""
        first = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        second = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )

        assert first.pk == second.pk
        assert free(customer) == TEN_K
        assert Transaction.objects.count() == 1

    def test_an_unbalanced_movement_is_refused(self, customer):
        with pytest.raises(services.Unbalanced):
            services.post(
                kind="correction",
                idempotency_key="bad:1",
                legs=[
                    services.Leg(
                        services.account_for(customer, AccountKind.INSURANCE_FREE), TEN_K
                    ),
                    services.Leg(
                        services.system_account(AccountKind.EXTERNAL_CASH),
                        -Decimal("9000.00"),
                    ),
                ],
            )
        assert Transaction.objects.count() == 0

    def test_a_customer_bucket_cannot_go_negative(self, customer):
        """The 20,000 over-debit of v1 fails here on arithmetic, not on a gate."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )

        with pytest.raises(services.InsufficientFunds):
            services.refund_insurance(
                user=customer, amount=Decimal("15000.00"), reference="R-1"
            )

        assert free(customer) == TEN_K

    def test_the_database_refuses_a_negative_balance_even_without_the_service(
        self, customer
    ):
        account = services.account_for(customer, AccountKind.INSURANCE_FREE)
        account.balance = Decimal("-1.00")
        with pytest.raises(IntegrityError), transaction.atomic():
            account.save(update_fields=["balance"])


class TestReversal:
    def test_a_reversal_undoes_the_money_and_keeps_the_history(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )

        services.reverse(original, reason="أودو ألغت الدفعة")

        assert free(customer) == Decimal("0.00")
        assert Transaction.objects.filter(pk=original.pk).exists()
        assert Entry.objects.filter(transaction=original).count() == 2

    def test_a_transaction_cannot_be_reversed_twice(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        services.reverse(original, reason="مرة")

        with pytest.raises(services.MoneyError):
            services.reverse(original, reason="مرتين")


class TestHolds:
    def test_bidding_moves_insurance_from_free_to_held(self, customer, auction):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )

        hold = services.hold_for_auction(user=customer, auction=auction)

        assert free(customer) == Decimal("0.00")
        assert (
            services.account_for(customer, AccountKind.INSURANCE_HELD).balance == TEN_K
        )
        assert hold.state == HoldState.ACTIVE

    def test_bidding_twice_in_one_auction_holds_once(self, customer, auction):
        """v1's over-lock race pinned two deposits to a single debt."""
        services.deposit_insurance(
            user=customer, amount=Decimal("20000.00"), source="cash", reference="P1"
        )

        first = services.hold_for_auction(user=customer, auction=auction)
        second = services.hold_for_auction(user=customer, auction=auction)

        assert first.pk == second.pk
        assert (
            services.account_for(customer, AccountKind.INSURANCE_HELD).balance == TEN_K
        )
        assert Hold.objects.filter(state=HoldState.ACTIVE).count() == 1

    def test_held_money_cannot_be_refunded_away(self, customer, auction):
        """A bidder's guarantee is not available cash while the auction runs."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        services.hold_for_auction(user=customer, auction=auction)

        with pytest.raises(services.InsufficientFunds):
            services.refund_insurance(user=customer, amount=TEN_K, reference="R-1")

    def test_releasing_a_hold_returns_the_money(self, customer, auction):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        hold = services.hold_for_auction(user=customer, auction=auction)

        services.release_hold(hold)

        assert free(customer) == TEN_K
        assert (
            services.account_for(customer, AccountKind.INSURANCE_HELD).balance
            == Decimal("0.00")
        )


class TestDues:
    def test_a_debtors_deposit_is_locked_and_cannot_be_refunded(self, customer):
        """The hole that let a debtor bid for free, then walk away with the cash."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        invoice = Invoice.objects.create(
            customer=customer,
            number="INV/001",
            amount=Decimal("50000.00"),
            state=InvoiceState.OPEN,
            issued_at="2026-01-01T00:00:00Z",
        )

        services.lock_for_invoice(user=customer, invoice=invoice)

        assert free(customer) == Decimal("0.00")
        assert (
            services.account_for(customer, AccountKind.INSURANCE_LOCKED).balance == TEN_K
        )
        with pytest.raises(services.InsufficientFunds):
            services.refund_insurance(user=customer, amount=TEN_K, reference="R-1")


class TestSuspense:
    def test_money_we_cannot_place_is_kept_not_dropped(self):
        services.receive_unattributed(
            amount=TEN_K, source="card", reference="moyasar_abc"
        )

        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K

    def test_attributing_it_later_moves_it_to_the_customer(self, customer):
        services.receive_unattributed(
            amount=TEN_K, source="card", reference="moyasar_abc"
        )

        services.attribute(user=customer, amount=TEN_K, reference="moyasar_abc")

        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("0.00")


class TestVerification:
    def test_a_clean_ledger_reports_nothing(self, customer, auction):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        services.hold_for_auction(user=customer, auction=auction)

        assert services.verify_ledger() == []

    def test_a_tampered_balance_is_caught(self, customer):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        Account.objects.filter(
            owner=customer, kind=AccountKind.INSURANCE_FREE
        ).update(balance=Decimal("99999.00"))

        findings = services.verify_ledger()

        assert any(f.check == "cached_balance" for f in findings)

    def test_held_money_without_a_hold_is_caught(self, customer, auction):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="PCSH/001"
        )
        hold = services.hold_for_auction(user=customer, auction=auction)
        Hold.objects.filter(pk=hold.pk).update(state=HoldState.RELEASED)

        findings = services.verify_ledger()

        assert any(f.check == "holds_explain_bucket" for f in findings)
