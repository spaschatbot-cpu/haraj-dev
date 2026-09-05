"""T109–T115 — the deposit's whole life.

In: a deposit. Reserved: a hold for an auction. Pinned: a lock against a debt.
Out: a refund, or a confiscation someone signed for. And the money that
arrives with no name on it, which is kept rather than dropped.
"""

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    AccountKind,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceSource,
    InvoiceState,
    Transaction,
    TransactionKind,
)
from apps.money.services import InsufficientFunds, MoneyError
from apps.money.tests.test_posting import run_in_threads
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db(transaction=True)

TEN_K = Decimal("10000.00")


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def held(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_HELD).balance


def locked(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_LOCKED).balance


def fund(user, amount=TEN_K, reference="SEED"):
    return services.deposit_insurance(
        user=user, amount=amount, source="cash", reference=f"{reference}:{user.pk}"
    )


# ---------------------------------------------------------------------------
# T109 — the deposit
# ---------------------------------------------------------------------------


class TestDeposit:
    def test_cash_lands_in_free_insurance(self, customer):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D/1"
        )

        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.EXTERNAL_CASH).balance == -TEN_K

    def test_card_lands_in_free_insurance_from_the_card_bucket(self, customer):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="card", reference="D/2"
        )

        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.EXTERNAL_CARD).balance == -TEN_K

    def test_an_unknown_source_is_refused_as_a_money_error_not_a_key_error(
        self, customer
    ):
        """A typo in a webhook payload must read as a refusal an operator can
        act on, not as a KeyError halfway down a stack trace."""
        with pytest.raises(MoneyError, match="مصدر تمويل غير معروف"):
            services.deposit_insurance(
                user=customer, amount=TEN_K, source="bitcoin", reference="D/3"
            )

        assert Transaction.objects.filter(idempotency_key__contains="D/3").count() == 0

    def test_the_reference_is_the_key_so_a_replay_credits_once(self, customer):
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D/4"
        )
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="D/4"
        )

        assert free(customer) == TEN_K


# ---------------------------------------------------------------------------
# T110 — the hold for bidding
# ---------------------------------------------------------------------------


class TestHoldForAuction:
    def test_it_moves_free_insurance_into_held(self, customer, auction):
        fund(customer)

        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        assert free(customer) == Decimal("0.00")
        assert held(customer) == TEN_K

    def test_twenty_sequential_calls_produce_one_hold(self, customer, auction):
        fund(customer)

        for _ in range(20):
            services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        assert Hold.objects.filter(owner=customer, auction=auction).count() == 1
        assert held(customer) == TEN_K

    def test_twenty_concurrent_calls_produce_one_hold(self, customer, auction):
        """Real threads. Every one of them can pass the pre-check before any
        of them inserts, so the partial unique index has to be the thing that
        decides — and the losers must return the winner's hold, not an error.
        """
        fund(customer)
        services.account_for(customer, AccountKind.INSURANCE_HELD)

        def take_hold(_i):
            return services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        results, errors = run_in_threads(take_hold, 20)

        assert [e for e in errors if e is not None] == []
        assert len({r.pk for r in results if r is not None}) == 1
        assert Hold.objects.filter(owner=customer, auction=auction).count() == 1
        assert held(customer) == TEN_K
        assert verify_ledger() == []

    def test_a_second_auction_takes_its_own_hold(self, customer, auction, other_auction):
        fund(customer, amount=Decimal("20000.00"))

        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        services.hold_for_auction(user=customer, auction=other_auction, amount=TEN_K)

        assert Hold.objects.filter(owner=customer, state=HoldState.ACTIVE).count() == 2
        assert held(customer) == Decimal("20000.00")

    def test_a_customer_without_the_deposit_cannot_hold(self, customer, auction):
        with pytest.raises(InsufficientFunds):
            services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        assert Hold.objects.filter(owner=customer).count() == 0


# ---------------------------------------------------------------------------
# T111 — releasing a hold
# ---------------------------------------------------------------------------


class TestReleaseHold:
    def test_the_money_goes_back_to_free(self, customer, auction):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        services.release_hold(hold)

        assert free(customer) == TEN_K
        assert held(customer) == Decimal("0.00")

    def test_the_hold_records_what_ended_it(self, customer, auction):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        services.release_hold(hold)

        hold.refresh_from_db()
        assert hold.state == HoldState.RELEASED
        assert hold.ended_by_transaction is not None
        assert hold.ended_at is not None

    def test_releasing_an_already_released_hold_does_nothing_and_does_not_raise(
        self, customer, auction
    ):
        """The settlement job runs again after a crash. It must be able to
        finish the work it already did without erroring or paying twice."""
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        services.release_hold(hold)
        transactions_before = Transaction.objects.count()

        services.release_hold(hold)

        assert Transaction.objects.count() == transactions_before
        assert free(customer) == TEN_K

    def test_the_customer_can_hold_again_after_a_release(self, customer, auction):
        """The partial unique index only covers active holds, so a released
        one must not block the next bid in the same auction."""
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        services.release_hold(hold)

        again = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        assert again.pk != hold.pk
        assert held(customer) == TEN_K


# ---------------------------------------------------------------------------
# T112 — locking against an invoice
# ---------------------------------------------------------------------------


@pytest.fixture
def invoice(customer, vehicle):
    return Invoice.objects.create(
        customer=customer,
        number="INV/2026/0001",
        amount=Decimal("7000.00"),
        vehicle=vehicle,
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.LOCAL,
    )


class TestLockForInvoice:
    def test_it_locks_the_outstanding_amount_when_that_is_the_smaller(
        self, customer, invoice
    ):
        fund(customer)

        hold = services.lock_for_invoice(user=customer, invoice=invoice)

        assert hold.amount == Decimal("7000.00")
        assert locked(customer) == Decimal("7000.00")
        assert free(customer) == Decimal("3000.00")

    def test_it_locks_only_what_is_available_when_that_is_the_smaller(
        self, customer, invoice
    ):
        """A lock is a guarantee, not a penalty: it cannot pin money that is
        not there, and it must not fail either — it takes what it can."""
        fund(customer, amount=Decimal("2000.00"))

        hold = services.lock_for_invoice(user=customer, invoice=invoice)

        assert hold.amount == Decimal("2000.00")
        assert locked(customer) == Decimal("2000.00")
        assert free(customer) == Decimal("0.00")

    def test_nothing_available_is_refused_with_both_numbers_named(
        self, customer, invoice
    ):
        with pytest.raises(MoneyError, match="لا يوجد تأمين متاح") as raised:
            services.lock_for_invoice(user=customer, invoice=invoice)

        assert "7000.00" in str(raised.value)

    def test_a_second_lock_on_the_same_invoice_returns_the_first(self, customer, invoice):
        fund(customer)
        first = services.lock_for_invoice(user=customer, invoice=invoice)

        second = services.lock_for_invoice(user=customer, invoice=invoice)

        assert first.pk == second.pk
        assert locked(customer) == Decimal("7000.00")

    def test_the_database_refuses_a_second_active_hold_on_one_invoice(
        self, customer, invoice
    ):
        """B6, tested by going around the service entirely.

        This is the constraint added in T102. Without it the only thing
        stopping a double lock was a pre-check, which is what failed in v1.
        """
        from django.db import IntegrityError, transaction

        fund(customer)
        first = services.lock_for_invoice(user=customer, invoice=invoice)

        with pytest.raises(IntegrityError), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                invoice=invoice,
                amount=Decimal("1.00"),
                reason=HoldReason.DUES,
                created_by_transaction=first.created_by_transaction,
            )


# ---------------------------------------------------------------------------
# T113 — the refund, and the debtor who cannot have one
# ---------------------------------------------------------------------------


class TestRefund:
    def test_free_insurance_can_leave(self, customer):
        fund(customer)

        services.refund_insurance(user=customer, amount=TEN_K, reference="R/1")

        assert free(customer) == Decimal("0.00")
        assert services.system_account(AccountKind.EXTERNAL_REFUND).balance == TEN_K

    def test_held_money_cannot_be_refunded(self, customer, auction):
        fund(customer)
        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        with pytest.raises(InsufficientFunds):
            services.refund_insurance(user=customer, amount=TEN_K, reference="R/2")

    def test_a_debtor_cannot_be_refunded_and_no_gate_says_so(self, customer, invoice):
        """The v1 hole, closed by arithmetic instead of by a rule.

        There is no `if customer_owes_us()` anywhere in the refund path. The
        money is simply not in the bucket a refund draws from, so the refusal
        cannot be forgotten, bypassed, or ordered wrongly relative to another
        check. Nobody has to remember it, which is the point.
        """
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)

        with pytest.raises(InsufficientFunds):
            services.refund_insurance(user=customer, amount=TEN_K, reference="R/3")

        assert locked(customer) == Decimal("7000.00")

    def test_the_debtor_can_refund_what_is_genuinely_spare(self, customer, invoice):
        """Locking is not punishment: whatever exceeds the debt stays theirs."""
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)

        services.refund_insurance(
            user=customer, amount=Decimal("3000.00"), reference="R/4"
        )

        assert free(customer) == Decimal("0.00")
        assert locked(customer) == Decimal("7000.00")


# ---------------------------------------------------------------------------
# T114 — confiscation
# ---------------------------------------------------------------------------


class TestConfiscate:
    def test_a_held_deposit_moves_to_the_confiscated_bucket(
        self, customer, auction, staff
    ):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        services.confiscate(hold, reason="انسحب بعد الترسية", by=staff)

        assert held(customer) == Decimal("0.00")
        assert services.system_account(AccountKind.CONFISCATED).balance == TEN_K

    def test_a_locked_deposit_can_be_confiscated_too(self, customer, invoice, staff):
        fund(customer)
        hold = services.lock_for_invoice(user=customer, invoice=invoice)

        services.confiscate(hold, reason="لم يسدّد خلال المهلة", by=staff)

        assert locked(customer) == Decimal("0.00")
        assert services.system_account(AccountKind.CONFISCATED).balance == Decimal(
            "7000.00"
        )

    def test_confiscation_without_a_reason_is_refused(self, customer, auction, staff):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        with pytest.raises(MoneyError, match="سبباً مكتوباً"):
            services.confiscate(hold, reason="   ", by=staff)

        assert held(customer) == TEN_K

    def test_confiscation_without_a_named_operator_is_refused(self, customer, auction):
        """No default, no `by=None`. A cron cannot confiscate by accident."""
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        with pytest.raises(MoneyError, match="منفّذاً مسمّى"):
            services.confiscate(hold, reason="سبب حقيقي", by=None)

        assert held(customer) == TEN_K

    def test_the_record_carries_the_operator_the_reason_and_the_amount(
        self, customer, auction, staff
    ):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        txn = services.confiscate(hold, reason="انسحب بعد الترسية", by=staff)

        assert txn.created_by_id == staff.pk
        assert "انسحب بعد الترسية" in txn.memo
        assert txn.total == TEN_K

        hold.refresh_from_db()
        assert hold.state == HoldState.CONSUMED
        assert hold.ended_by_transaction_id == txn.pk

    def test_an_ended_hold_cannot_be_confiscated(self, customer, auction, staff):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)
        services.release_hold(hold)

        with pytest.raises(MoneyError, match="ليس قائماً"):
            services.confiscate(hold, reason="متأخر", by=staff)

    def test_the_ledger_stays_clean_after_a_confiscation(self, customer, auction, staff):
        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        services.confiscate(hold, reason="سبب", by=staff)

        assert verify_ledger() == []


# ---------------------------------------------------------------------------
# T115 — money that arrives with no name on it
# ---------------------------------------------------------------------------


class TestSuspense:
    def test_it_is_kept_in_suspense_not_dropped(self):
        """v1's instinct was to drop what it could not place, and money went
        missing in exactly that gap."""
        services.receive_unattributed(amount=TEN_K, source="cash", reference="U/1")

        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K

    def test_attributing_it_moves_the_whole_amount_to_the_customer(self, customer):
        services.receive_unattributed(amount=TEN_K, source="cash", reference="U/2")

        services.attribute(user=customer, amount=TEN_K, reference="U/2")

        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("0.00")

    def test_attributing_part_of_it_leaves_the_rest_in_suspense(self, customer):
        """One transfer covering two customers: the first is placed, the rest waits.

        The part attributed is a whole deposit, because the part is what lands
        in `insurance_free` and the deposit is a unit (HR-03). A transfer that
        does not divide into deposits stays whole in suspense until a person
        says what it was.
        """
        services.receive_unattributed(amount=TEN_K * 2, source="cash", reference="U/3")

        services.attribute(user=customer, amount=TEN_K, reference="U/3-part")

        assert free(customer) == TEN_K
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K

    def test_attributing_more_than_is_there_is_refused(self, customer):
        """Suspense is a platform bucket with no CHECK floor, so this guard is
        the only thing between a typo and invented money."""
        services.receive_unattributed(
            amount=Decimal("1000.00"), source="cash", reference="U/4"
        )

        with pytest.raises(MoneyError, match="المعلّق فيه"):
            services.attribute(user=customer, amount=TEN_K, reference="U/4-too-much")

        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("1000.00")
        assert free(customer) == Decimal("0.00")

    def test_attribution_is_recorded_as_its_own_kind(self, customer):
        services.receive_unattributed(amount=TEN_K, source="cash", reference="U/5")

        txn = services.attribute(user=customer, amount=TEN_K, reference="U/5")

        assert txn.kind == TransactionKind.ATTRIBUTION


class TestConfiscationIsAudited:
    """The one movement that leaves a customer poorer with no service rendered.

    `apps.core.audit.record` existed from the day core merged and was called
    from nowhere in the tree, while this function still carried a TODO saying
    "once that exists". A TODO in a docstring fails no CI step, so the condition
    came due and nothing said so.
    """

    def test_it_writes_an_audit_row_naming_the_operator_and_the_reason(
        self, customer, auction, staff
    ):
        from apps.core.models import AuditLog

        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction)

        services.confiscate(hold, reason="انسحب بعد الترسية", by=staff)

        entry = AuditLog.objects.get(action="money.confiscate")
        assert entry.actor_id == staff.pk
        assert entry.entity_id == str(hold.pk)
        assert "انسحب بعد الترسية" in entry.note

    def test_the_row_says_what_the_hold_was_before_it_was_taken(
        self, customer, auction, staff
    ):
        """A dispute asks what was taken, not only that something was.

        The amounts are strings, never floats: an audit row reading
        10000.000000000001 is worse than no row at all (Article 3-2).
        """
        from apps.core.models import AuditLog

        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction)

        services.confiscate(hold, reason="مخالفة", by=staff)

        entry = AuditLog.objects.get(action="money.confiscate")
        assert entry.before["state"] == HoldState.ACTIVE
        assert entry.before["amount"] == "10000.00"
        assert entry.after["state"] == HoldState.CONSUMED

    def test_a_refused_confiscation_writes_no_audit_row(self, customer, auction, staff):
        from apps.core.models import AuditLog

        fund(customer)
        hold = services.hold_for_auction(user=customer, auction=auction)
        services.confiscate(hold, reason="مرة واحدة", by=staff)
        AuditLog.objects.all().delete()

        with pytest.raises(MoneyError):
            services.confiscate(hold, reason="مرة ثانية", by=staff)

        assert not AuditLog.objects.filter(action="money.confiscate").exists()
