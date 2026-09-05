"""HR-15 — a deduction passes one ceiling, and it is the ceiling of the sum.

``R2-03`` §6, and the line the map left open: "**before running any
settlement: the deduction must pass a single ceiling** (`CustomerLedger::
headroom`), or it is deducted from the account twice — **which happened, for
20,000**."

The v1 shape, exactly. A settlement wrote two deductions in one operation, each
checked on its own against the balance it read before either was applied. Each
one fitted. Together they were twice what the customer had, and the customer
was short twenty thousand riyals with nothing in the ledger that looked wrong.

There are two ways that shape reaches us, and the acceptance criterion —
"no deduction exceeds what the customer owns across the whole group" — is only
met if **both** are closed:

1. **Two legs, one posting.** `post` sums the legs per account *before*
   checking, so the ceiling applies to the total. Untested until now: the one
   test that touched this collapses two *credits* and asserts the resulting
   balance, which is true whether the ceiling is on the sum or on each leg.
2. **Two postings, one account.** The second must see what the first wrote.
   `post` re-reads under `SELECT ... FOR UPDATE` inside the transaction, so a
   caller holding a stale `Account` in memory cannot spend the same money
   twice — asserted here with a genuinely stale object, and with real threads.

**"The whole group" is one row here, and that is worth saying rather than
assuming.** In v1 one Odoo customer mapped to two or three `userss` rows
(`customer_links` = 14,708), and mixing them is what made the double deduction
possible at all. Our model is one account per customer per bucket, so the
per-account ceiling *is* the group ceiling — but only while that stays true,
which is why the last test asserts it instead of leaving it to a reader.

Amounts are the incident's: ten thousand held, ten thousand twice attempted,
twenty thousand the gap.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import connections, transaction

from apps.money import services
from apps.money.models import (
    Account,
    AccountKind,
    Entry,
    Transaction,
    TransactionKind,
)
from apps.money.services import InsufficientFunds, Leg
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db(transaction=True)

TEN_K = Decimal("10000.00")
TWENTY_K = Decimal("20000.00")


def free_account(user) -> Account:
    return services.account_for(user, AccountKind.INSURANCE_FREE)


def cash_account() -> Account:
    return services.system_account(AccountKind.EXTERNAL_CASH)


@pytest.fixture
def funded(customer):
    """A customer holding exactly ten thousand — the incident's balance."""
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="HR15/seed"
    )
    return customer


def _deduct_twice(customer, key: str, each: Decimal) -> Transaction:
    """One posting, two deductions against the same bucket.

    This is the settlement's shape, not a contrived one: a run that resolves
    two shortfall cases for the same customer writes two legs, and whether
    they are checked apart or together is the whole question.
    """
    free = free_account(customer)
    return services.post(
        kind=TransactionKind.CORRECTION,
        idempotency_key=key,
        legs=[
            Leg(free, -each),
            Leg(free, -each),
            Leg(cash_account(), each * 2),
        ],
    )


# ---------------------------------------------------------------------------
# One posting, two deductions
# ---------------------------------------------------------------------------


def test_two_deductions_in_one_posting_are_measured_against_their_sum(funded):
    """The incident. Each leg fits; together they are twice the balance."""
    with pytest.raises(InsufficientFunds) as refused:
        _deduct_twice(funded, "hr15/twice", TEN_K)

    assert refused.value.available == TEN_K
    #: The *sum*, not the last leg. A per-leg check would report ten thousand
    #: needed against ten thousand available and let it through.
    assert refused.value.needed == TWENTY_K


def test_the_refused_double_deduction_writes_nothing(funded):
    """A refusal that half-wrote is the incident with a paper trail."""
    transactions, entries = Transaction.objects.count(), Entry.objects.count()

    with pytest.raises(InsufficientFunds):
        _deduct_twice(funded, "hr15/nothing", TEN_K)

    assert Transaction.objects.count() == transactions
    assert Entry.objects.count() == entries
    assert free_account(funded).balance == TEN_K


def test_two_deductions_that_fit_together_are_allowed(funded):
    """The other half, and the reason this is a ceiling and not a ban.

    A guard that refuses correct work is switched off in a week, so the same
    shape at half the amount must go through — and land as one movement on one
    account.
    """
    _deduct_twice(funded, "hr15/fits", Decimal("5000.00"))

    free = free_account(funded)
    assert free.balance == Decimal("0.00")
    assert Entry.objects.filter(account=free).count() == 3  # deposit + two legs


# ---------------------------------------------------------------------------
# Two postings, one account
# ---------------------------------------------------------------------------


def test_a_stale_balance_in_memory_cannot_spend_the_money_twice(funded):
    """The caller's `Account` object is not what the ceiling is read from.

    A settlement that loads every customer once and then walks its cases holds
    an object whose `balance` is minutes old. If the ceiling were read from
    that object, the second case would be measured against money the first
    already spent — which is the same twenty thousand by another road.
    """
    stale = free_account(funded)
    services.refund_insurance(user=funded, amount=TEN_K, reference="HR15/first")
    assert stale.balance == TEN_K, "التجهيزة نفسها فاسدة: الكائن لم يعد قديماً"

    with pytest.raises(InsufficientFunds) as refused:
        services.post(
            kind=TransactionKind.CORRECTION,
            idempotency_key="hr15/stale",
            legs=[Leg(stale, -TEN_K), Leg(cash_account(), TEN_K)],
        )

    assert refused.value.available == Decimal("0.00")


def test_two_concurrent_deductions_leave_one_survivor(funded):
    """Real threads and real connections — a mocked race proves nothing.

    **The barrier is what makes this a test of the lock.** Written without
    one it passed with `select_for_update` removed: the threads happened to
    take turns, so the second read the balance after the first had committed
    and was refused for the wrong reason. A race test that the race never
    wins is a green light with nothing behind it.

    With the barrier both threads are inside their transaction and about to
    post when the other is too. Unlocked, both read ten thousand, both compute
    a new balance of zero, and both write it: two deductions, ten thousand
    gone, twenty thousand accounted for — and **the `CHECK` does not catch it,
    because zero is not negative**. That is the v1 incident to the riyal, and
    only the ledger recount sees it.
    """
    import threading

    outcomes: list[str] = [""] * 2
    both_ready = threading.Barrier(2, timeout=20)

    def deduct(index: int) -> None:
        try:
            with transaction.atomic():
                #: Inside the transaction, before the posting: this is the
                #: instant at which the two must overlap for the lock to be
                #: the thing that separates them.
                both_ready.wait()
                services.post(
                    kind=TransactionKind.CORRECTION,
                    idempotency_key=f"hr15/race-{index}",
                    legs=[
                        Leg(free_account(funded), -TEN_K),
                        Leg(cash_account(), TEN_K),
                    ],
                )
            outcomes[index] = "posted"
        except InsufficientFunds:
            outcomes[index] = "refused"
        except Exception as exc:  # noqa: BLE001 — the name of it is the report
            outcomes[index] = f"{type(exc).__name__}: {exc}"
        finally:
            connections.close_all()

    threads = [threading.Thread(target=deduct, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == ["posted", "refused"], outcomes
    assert free_account(funded).balance == Decimal("0.00")
    #: The recount is the only witness to a double deduction that lands on a
    #: legal balance. Without it this test passes while ten thousand riyals
    #: are missing.
    assert verify_ledger() == []
    posted = Transaction.objects.filter(idempotency_key__startswith="hr15/race")
    assert posted.count() == 1


# ---------------------------------------------------------------------------
# "The whole group" — one row, and asserted rather than assumed
# ---------------------------------------------------------------------------


def test_a_customer_has_exactly_one_account_per_bucket(funded, other_customer):
    """Why the per-account ceiling is the group ceiling, stated as a test.

    v1's double deduction needed two rows to spread across: one Odoo customer
    against two or three `userss` rows. Here `account_for` is get-or-create on
    (owner, kind), so the group is one row and the ceiling covers all of it.
    The day that stops being true, this fails and R2-03 §6 reopens with it.
    """
    services.deposit_insurance(
        user=other_customer, amount=TEN_K, source="cash", reference="HR15/other"
    )

    for kind in AccountKind.customer_owned():
        services.account_for(funded, kind)
        assert Account.objects.filter(owner=funded, kind=kind).count() == 1, kind

    assert free_account(funded).pk != free_account(other_customer).pk
