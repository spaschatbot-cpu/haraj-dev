"""Money that arrived before we knew whose it was.

Two failures live here, and both were silent — which is what made them
expensive. A payment that landed in suspense shared its idempotency key with
the attributed deposit for the very same payment, so the second telling moved
nothing and every caller reported success over an empty wallet. And the guard
that stops suspense being over-attributed read the balance without locking it,
so two operators walked through it together.
"""

from __future__ import annotations

import threading
from decimal import Decimal
from unittest import mock

import pytest
from django.db import IntegrityError, transaction

from apps.money import services
from apps.money.models import Account, AccountKind, TransactionKind
from apps.money.services import MoneyError
from apps.money.tests.test_posting import run_in_threads
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db(transaction=True)

TEN_K = Decimal("10000.00")


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def suspense() -> Decimal:
    return services.system_account(AccountKind.SUSPENSE).balance


class TestTheTwoKeysAreNotOneKey:
    def test_a_suspense_receipt_does_not_swallow_the_deposit_for_it(self, customer):
        """The collision, at its sharpest point.

        Both used to build ``{source}:{reference}``. So a receipt that landed in
        suspense made ``deposit_insurance`` for that same payment a no-op:
        ``post`` recognised the key, moved nothing, and returned the suspense
        transaction — while the caller wrote «تمت» on the customer's screen.
        """
        services.receive_unattributed(amount=TEN_K, source="card", reference="PAY-9")

        credited = services.credit_payment(
            user=customer, amount=TEN_K, source="card", reference="PAY-9"
        )

        assert free(customer) == TEN_K
        assert suspense() == Decimal("0.00")
        assert credited.kind == TransactionKind.ATTRIBUTION
        assert verify_ledger() == []

    def test_the_money_leaves_suspense_rather_than_arriving_twice(self, customer):
        """One payment arrived, so the outside world is charged once.

        Namespacing the keys alone would have made the second telling post a
        *fresh* deposit: `external_card` twice for one 10,000 that arrived once,
        and an orphan in suspense nobody would ever claim.
        """
        services.receive_unattributed(amount=TEN_K, source="card", reference="PAY-9")

        services.credit_payment(
            user=customer, amount=TEN_K, source="card", reference="PAY-9"
        )

        assert services.system_account(AccountKind.EXTERNAL_CARD).balance == -TEN_K

    def test_a_plain_deposit_still_happens_when_nothing_is_in_suspense(self, customer):
        txn = services.credit_payment(
            user=customer, amount=TEN_K, source="cash", reference="ODOO-1"
        )

        assert txn.kind == TransactionKind.INSURANCE_TOPUP
        assert free(customer) == TEN_K

    def test_crediting_the_same_payment_twice_credits_once(self, customer):
        services.credit_payment(
            user=customer, amount=TEN_K, source="cash", reference="ODOO-1"
        )
        services.credit_payment(
            user=customer, amount=TEN_K, source="cash", reference="ODOO-1"
        )

        assert free(customer) == TEN_K

    def test_a_suspense_receipt_of_a_different_size_is_not_guessed_at(self, customer):
        """Two numbers for one payment is a question for a person.

        Crediting either figure silently is how a discrepancy becomes a loss
        nobody notices, so the money stays whole where it is.
        """
        services.receive_unattributed(
            amount=Decimal("1.00"), source="card", reference="PAY-9"
        )

        with pytest.raises(MoneyError, match="قراراً بشرياً"):
            services.credit_payment(
                user=customer, amount=TEN_K, source="card", reference="PAY-9"
            )

        assert free(customer) == Decimal("0.00")
        assert suspense() == Decimal("1.00")


class TestSuspenseCannotGoNegative:
    def test_the_schema_refuses_a_negative_suspense(self):
        """B-style: proven by going around the service entirely.

        `post` refuses a negative balance only for customer buckets, and
        suspense belongs to the platform — so before this constraint the only
        thing standing between us and inventing money was one Python
        comparison (Article 3-3).
        """
        account = services.system_account(AccountKind.SUSPENSE)

        with pytest.raises(IntegrityError, match="suspense_never_goes_negative"):
            with transaction.atomic():
                Account.objects.filter(pk=account.pk).update(balance=Decimal("-1.00"))

    def test_two_operators_attributing_one_receipt_credit_it_once(
        self, customer, staff
    ):
        """The check-then-write that the row lock closes.

        Both callers are held at the posting step until the other has reached
        it too, so a decision taken outside a lock is taken by both of them
        before either writes. With the lock, the second caller cannot even read
        the balance until the first has committed, and it then refuses with a
        sentence instead of an IntegrityError from the CHECK behind it.
        """
        services.receive_unattributed(amount=TEN_K, source="card", reference="S/1")
        users = [customer, staff]

        barrier = threading.Barrier(2)
        real_post = services.post

        def paused_post(**kwargs):
            try:
                barrier.wait(timeout=3)
            except threading.BrokenBarrierError:
                # Expected once the lock serialises them: the loser never
                # arrives, and the winner must not wait for it forever.
                pass
            return real_post(**kwargs)

        with mock.patch.object(services, "post", paused_post):

            def worker(i):
                return services.attribute(
                    user=users[i], amount=TEN_K, reference=f"r{i}"
                )

            results, errors = run_in_threads(worker, 2)

        refusals = [e for e in errors if e is not None]
        assert len(refusals) == 1, f"expected exactly one refusal, got {errors}"
        assert isinstance(refusals[0], MoneyError), (
            f"the loser must be refused with a sentence, not {refusals[0]!r}"
        )
        assert suspense() == Decimal("0.00")
        assert free(customer) + free(staff) == TEN_K
        assert verify_ledger() == []
