"""T104–T108 — the posting contract.

Validation, lock ordering, idempotency, the negative-balance refusal, and
reversal. The concurrency tests here use real threads against real PostgreSQL
connections; a mocked race proves nothing about `SELECT ... FOR UPDATE`.
"""

import threading
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, connections, transaction

from apps.money import services
from apps.money.models import (
    Account,
    AccountKind,
    Entry,
    Transaction,
    TransactionKind,
)
from apps.money.services import InsufficientFunds, Leg, MoneyError, Unbalanced

pytestmark = pytest.mark.django_db(transaction=True)

TEN_K = Decimal("10000.00")


def free_account(user) -> Account:
    return services.account_for(user, AccountKind.INSURANCE_FREE)


def cash_account() -> Account:
    return services.system_account(AccountKind.EXTERNAL_CASH)


def run_in_threads(target, count):
    """Run `target(index)` in `count` real threads and collect the outcomes.

    Each thread closes its own database connection afterwards; a leaked
    connection makes the next test hang on a lock instead of failing.
    """
    results: list = [None] * count
    errors: list = [None] * count

    def wrapped(i):
        try:
            results[i] = target(i)
        except Exception as exc:  # noqa: BLE001 — the test inspects the type
            errors[i] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    return results, errors


# ---------------------------------------------------------------------------
# T104 — validation and balance
# ---------------------------------------------------------------------------


class TestValidation:
    """Every refusal must leave the ledger exactly as it found it."""

    def test_a_movement_needs_two_sides(self, customer):
        before = Transaction.objects.count()

        with pytest.raises(Unbalanced, match="طرفين على الأقل"):
            services.post(
                kind=TransactionKind.CORRECTION,
                idempotency_key="one-legged",
                legs=[Leg(free_account(customer), TEN_K)],
            )

        assert Transaction.objects.count() == before

    def test_a_leg_of_zero_is_refused(self, customer):
        before = Transaction.objects.count()

        with pytest.raises(Unbalanced, match="طرف بصفر"):
            services.post(
                kind=TransactionKind.CORRECTION,
                idempotency_key="zero-leg",
                legs=[
                    Leg(cash_account(), -TEN_K),
                    Leg(free_account(customer), TEN_K),
                    Leg(services.system_account(AccountKind.REVENUE), Decimal("0.00")),
                ],
            )

        assert Transaction.objects.count() == before

    def test_legs_that_do_not_sum_to_zero_are_refused(self, customer):
        before = Transaction.objects.count()

        with pytest.raises(Unbalanced, match="مجموع الأطراف"):
            services.post(
                kind=TransactionKind.CORRECTION,
                idempotency_key="unbalanced",
                legs=[
                    Leg(cash_account(), -TEN_K),
                    Leg(free_account(customer), Decimal("9999.99")),
                ],
            )

        assert Transaction.objects.count() == before

    def test_a_refusal_writes_no_entries_either(self, customer):
        before = Entry.objects.count()

        with pytest.raises(Unbalanced):
            services.post(
                kind=TransactionKind.CORRECTION,
                idempotency_key="no-entries",
                legs=[
                    Leg(cash_account(), -TEN_K),
                    Leg(free_account(customer), Decimal("1.00")),
                ],
            )

        assert Entry.objects.count() == before

    def test_two_legs_on_one_account_are_collapsed_into_one_movement(self, customer):
        """Two legs naming the same bucket must not lock or move it twice."""
        free = free_account(customer)

        services.post(
            kind=TransactionKind.CORRECTION,
            idempotency_key="collapsed",
            legs=[
                Leg(cash_account(), -TEN_K),
                Leg(free, Decimal("6000.00")),
                Leg(free, Decimal("4000.00")),
            ],
        )

        free.refresh_from_db()
        assert free.balance == TEN_K


# ---------------------------------------------------------------------------
# T105 — lock ordering
# ---------------------------------------------------------------------------


class TestLockOrdering:
    def test_accounts_are_locked_in_ascending_primary_key_order(self, customer):
        """The ordering is what prevents a deadlock, so assert on the SQL.

        A future refactor that drops `.order_by("pk")` still passes every
        behavioural test on a quiet machine and deadlocks under load. This is
        the only check that catches it deterministically.
        """
        free = free_account(customer)
        cash = cash_account()

        recorder = _Recorder()
        with connection.execute_wrapper(recorder):
            services.post(
                kind=TransactionKind.INSURANCE_TOPUP,
                idempotency_key="lock-order",
                legs=[Leg(cash, -TEN_K), Leg(free, TEN_K)],
            )

        locking = [q for q in recorder.queries if "FOR UPDATE" in q]
        assert locking, "post() did not take a row lock at all"
        assert any('ORDER BY "money_account"."id" ASC' in q for q in locking), locking

    def test_two_opposing_postings_on_the_same_pair_do_not_deadlock(
        self, customer, other_customer
    ):
        """Two threads move money between the same two buckets, in opposite
        directions, at the same time. Without a stable lock order this is the
        textbook deadlock; with it, one simply waits for the other.
        """
        a = free_account(customer)
        b = free_account(other_customer)
        services.post(
            kind=TransactionKind.INSURANCE_TOPUP,
            idempotency_key="seed-a",
            legs=[Leg(cash_account(), -TEN_K), Leg(a, TEN_K)],
        )
        services.post(
            kind=TransactionKind.INSURANCE_TOPUP,
            idempotency_key="seed-b",
            legs=[Leg(cash_account(), -TEN_K), Leg(b, TEN_K)],
        )

        amount = Decimal("1000.00")

        def move(i):
            source, target = (a, b) if i % 2 == 0 else (b, a)
            return services.post(
                kind=TransactionKind.CORRECTION,
                idempotency_key=f"swap-{i}",
                legs=[Leg(source, -amount), Leg(target, amount)],
            )

        results, errors = run_in_threads(move, 10)

        assert [e for e in errors if e is not None] == []
        assert all(r is not None for r in results)

        a.refresh_from_db()
        b.refresh_from_db()
        assert a.balance + b.balance == TEN_K * 2
        assert services.verify_ledger() == []


class _Recorder:
    """Captures the SQL Django actually sends."""

    def __init__(self):
        self.queries: list[str] = []

    def __call__(self, execute, sql, params, many, context):
        self.queries.append(sql)
        return execute(sql, params, many, context)


# ---------------------------------------------------------------------------
# T106 — idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_the_same_key_twice_returns_the_first_transaction(self, customer):
        first = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="IDEM/1"
        )
        second = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="IDEM/1"
        )

        assert first.pk == second.pk
        assert Transaction.objects.filter(idempotency_key="cash:IDEM/1").count() == 1
        assert free_account(customer).balance == TEN_K

    def test_the_second_call_does_not_move_money_even_with_a_different_amount(
        self, customer
    ):
        """A replay carrying a different amount is still a replay.

        The key names a real-world event. If the amount disagrees, the ledger
        keeps what it recorded the first time — silently re-crediting would be
        exactly the double-credit this key exists to prevent.
        """
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="IDEM/2"
        )
        services.deposit_insurance(
            user=customer,
            amount=Decimal("99999.00"),
            source="cash",
            reference="IDEM/2",
        )

        assert free_account(customer).balance == TEN_K

    def test_two_threads_with_the_same_key_produce_one_transaction(self, customer):
        """The unique index is the arbiter, not the pre-check.

        Both threads can pass `filter(...).first()` before either inserts. The
        loser must come back with the winner's transaction — an inbound
        webhook delivered twice at once has to succeed twice and credit once.
        """
        services.account_for(customer, AccountKind.INSURANCE_FREE)
        services.system_account(AccountKind.EXTERNAL_CASH)

        def deposit(_i):
            return services.deposit_insurance(
                user=customer, amount=TEN_K, source="cash", reference="RACE/1"
            )

        results, errors = run_in_threads(deposit, 8)

        assert [e for e in errors if e is not None] == []
        pks = {r.pk for r in results if r is not None}
        assert len(pks) == 1, f"expected one transaction, got {pks}"
        assert Transaction.objects.filter(idempotency_key="cash:RACE/1").count() == 1
        assert free_account(customer).balance == TEN_K
        assert services.verify_ledger() == []


# ---------------------------------------------------------------------------
# T107 — the negative balance refusal
# ---------------------------------------------------------------------------


class TestNegativeBalance:
    def test_the_service_names_the_bucket_the_available_and_the_needed(self, customer):
        services.deposit_insurance(
            user=customer, amount=Decimal("500.00"), source="cash", reference="SHORT/1"
        )

        with pytest.raises(InsufficientFunds) as raised:
            services.refund_insurance(user=customer, amount=TEN_K, reference="TOO-MUCH")

        message = str(raised.value)
        assert "تأمين متاح" in message
        assert "500.00" in message
        assert "10000.00" in message
        assert raised.value.available == Decimal("500.00")
        assert raised.value.needed == TEN_K

    def test_the_refusal_happens_before_anything_is_written(self, customer):
        services.deposit_insurance(
            user=customer, amount=Decimal("500.00"), source="cash", reference="SHORT/2"
        )
        transactions_before = Transaction.objects.count()
        entries_before = Entry.objects.count()

        with pytest.raises(InsufficientFunds):
            services.refund_insurance(user=customer, amount=TEN_K, reference="TOO-MUCH-2")

        assert Transaction.objects.count() == transactions_before
        assert Entry.objects.count() == entries_before

    def test_the_database_refuses_it_too_when_the_service_is_bypassed(self, customer):
        """The Python check is a courtesy; the CHECK constraint is the guard.

        This writes straight to the table, the way a stray admin action or a
        migration script would, and the database must still say no.
        """
        account = free_account(customer)

        with pytest.raises(IntegrityError), transaction.atomic():
            Account.objects.filter(pk=account.pk).update(balance=Decimal("-1.00"))

    def test_a_system_bucket_is_allowed_to_go_negative(self, customer):
        """EXTERNAL_CASH going negative is how the ledger records money coming
        in. Only customer buckets carry the floor."""
        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="NEG/1"
        )

        assert cash_account().balance == -TEN_K


# ---------------------------------------------------------------------------
# T108 — reversal
# ---------------------------------------------------------------------------


class TestReverse:
    def test_a_reversal_mirrors_every_leg(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/1"
        )

        reversal = services.reverse(original, reason="أُودعت لعميل خاطئ")

        original_legs = {e.account_id: e.amount for e in original.entries.all()}
        reversal_legs = {e.account_id: e.amount for e in reversal.entries.all()}

        assert set(original_legs) == set(reversal_legs)
        for account_id, amount in original_legs.items():
            assert reversal_legs[account_id] == -amount
        assert free_account(customer).balance == Decimal("0.00")

    def test_the_reversal_points_at_what_it_reverses(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/2"
        )

        reversal = services.reverse(original, reason="خطأ إدخال")

        assert reversal.reverses_id == original.pk
        assert reversal.kind == TransactionKind.REVERSAL

    def test_the_original_survives_intact(self, customer):
        """Article 1-4: history stays reconstructable. The original keeps its
        entries and its amounts, so a dispute can be replayed years later."""
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/3"
        )
        legs_before = {e.account_id: e.amount for e in original.entries.all()}

        services.reverse(original, reason="خطأ")

        original.refresh_from_db()
        assert original.pk is not None
        assert {e.account_id: e.amount for e in original.entries.all()} == legs_before

    def test_reversing_twice_is_refused(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/4"
        )
        services.reverse(original, reason="مرة")

        with pytest.raises(MoneyError, match="معكوسة بالفعل"):
            services.reverse(original, reason="مرتين")

    def test_a_reversal_is_not_itself_reversible(self, customer):
        """Undoing an undo is a correction with its own reason, not a silent
        re-application of the original movement."""
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/5"
        )
        reversal = services.reverse(original, reason="مرة")

        with pytest.raises(MoneyError, match="هي نفسها عكس"):
            services.reverse(reversal, reason="تراجع عن التراجع")

    def test_the_ledger_is_still_clean_after_a_reversal(self, customer):
        original = services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="REV/6"
        )
        services.reverse(original, reason="خطأ")

        assert services.verify_ledger() == []
