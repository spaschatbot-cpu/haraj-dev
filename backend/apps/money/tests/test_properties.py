"""T121 — properties that must hold for *any* sequence of valid movements.

The example-based tests elsewhere each check one story someone thought of.
This file checks the three invariants that have to survive stories nobody
thought of, over thousands of generated ones.

Hypothesis drives Django's ORM here rather than pure functions, so the
generation is done up front and replayed inside one database transaction:
`@given` cannot manage database state across its own retries.

Why every reference carries a run id
------------------------------------
`@given` re-invokes the body with the *same* function-scoped fixtures — which
is precisely why `HealthCheck.function_scoped_fixture` has to be suppressed —
and pytest-django resets the database once per test *function*, not per
example. So the rows an example writes are still there for the next one. When
the references were the deterministic `P/{index}`, examples 2 through 200
replayed keys example 1 had already recorded: `post` recognised each key and
returned without validating, locking or writing anything, and the effective
coverage of «200 سيناريو» was the twenty-five operations of the first example.
Minting a fresh run id *inside the body* is what makes each example move real
money, and the assertion that the transaction count grew is what makes a
regression to a shared key fail loudly instead of silently emptying the
property. The id is minted rather than drawn on purpose: Hypothesis replays an
example — from its own database, and while shrinking — and a drawn id would
come back identical on the replay, putting the collision straight back.
"""

import uuid
from decimal import Decimal

import pytest
from django.db.models import Sum
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from apps.money import services
from apps.money.models import Account, AccountKind, Entry, Transaction, TransactionKind
from apps.money.services import InsufficientFunds, Leg, MoneyError, Unbalanced
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

# Whole riyals keep the generated cases readable; the two decimal places are
# exercised by the example tests. Amounts stay well inside Decimal(14,2).
amounts = st.decimals(
    min_value=Decimal("1"),
    max_value=Decimal("100000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)

# Each operation is (name, amount). The runner decides whether it is legal
# against the state at that moment; an illegal one must be *refused*, not
# silently absorbed, and that refusal is itself part of the property.
operations = st.lists(
    st.tuples(
        st.sampled_from(["deposit", "refund", "hold", "release", "confiscate"]),
        amounts,
    ),
    min_size=1,
    max_size=25,
)


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(script=operations)
def test_any_sequence_of_movements_leaves_the_ledger_consistent(
    script, customer, auction, staff, django_db_reset_sequences
):
    """Whatever happens, all three of these hold afterwards:

    1. every entry in the book sums to zero overall;
    2. no customer bucket is negative;
    3. `verify_ledger` finds nothing.

    A refusal counts as a valid outcome — what must never happen is a partial
    movement, an unexplained hold, or a bucket that drifted from its entries.
    """
    run = uuid.uuid4().hex
    before = Transaction.objects.count()
    hold = None
    for index, (operation, amount) in enumerate(script):
        reference = f"P/{run}/{index}"
        try:
            if operation == "deposit":
                services.deposit_insurance(
                    user=customer, amount=amount, source="cash", reference=reference
                )
            elif operation == "refund":
                services.refund_insurance(
                    user=customer, amount=amount, reference=reference
                )
            elif operation == "hold":
                hold = services.hold_for_auction(
                    user=customer, auction=auction, amount=amount
                )
            elif operation == "release" and hold is not None:
                services.release_hold(hold)
                hold = None
            elif operation == "confiscate" and hold is not None:
                services.confiscate(hold, reason="اختبار خصائص", by=staff)
                hold = None
        except (InsufficientFunds, MoneyError):
            # A refusal is a correct outcome. The invariants below are what
            # must survive it — in particular, that it left nothing half-done.
            continue

    # The property is worthless if the example moved nothing. A script whose
    # every operation was legitimately refused is the one exception — and the
    # first operation of any script can only be a deposit or a refusal.
    if script[0][0] == "deposit":
        assert Transaction.objects.count() > before, (
            "this example recorded no transaction at all — the references have "
            "collided with an earlier example's and the property is empty"
        )

    total = Entry.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    assert total == Decimal("0.00"), f"the whole book sums to {total}, not zero"

    negative = Account.objects.filter(
        kind__in=AccountKind.customer_owned(), balance__lt=Decimal("0.00")
    )
    assert not negative.exists(), f"negative customer buckets: {list(negative)}"

    assert verify_ledger() == []


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(legs=st.lists(amounts, min_size=1, max_size=5))
def test_every_posted_transaction_sums_to_zero(legs, customer, django_db_reset_sequences):
    """The property, pointed at the writer instead of at arithmetic.

    What stood here built ``[*legs, -sum(legs)]`` and asserted the sum was
    zero — a statement about its own construction that no input Hypothesis can
    draw could falsify, and that would still pass with `apps.money.services`
    deleted. It was nevertheless cited as half of B1's evidence.

    This posts the generated movement through `post` and reads the entries back
    out of the database, so what is being asserted is that *the writer* balances
    what it records.
    """
    run = uuid.uuid4().hex
    total_in = sum(legs, start=Decimal("0.00"))
    buckets = [
        services.account_for(customer, AccountKind.INSURANCE_FREE),
        services.system_account(AccountKind.SUSPENSE),
        services.system_account(AccountKind.REVENUE),
    ]
    movement = [
        Leg(buckets[i % len(buckets)], amount) for i, amount in enumerate(legs)
    ] + [Leg(services.system_account(AccountKind.EXTERNAL_CASH), -total_in)]

    txn = services.post(
        kind=TransactionKind.CORRECTION,
        idempotency_key=f"prop/{run}",
        legs=movement,
    )

    recorded = Entry.objects.filter(transaction=txn).aggregate(total=Sum("amount"))
    assert recorded["total"] == Decimal("0.00")
    assert verify_ledger() == []


@settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(legs=st.lists(amounts, min_size=2, max_size=5))
def test_an_unbalanced_movement_is_refused_and_writes_nothing(
    legs, customer, django_db_reset_sequences
):
    """A refusal must cost no rows. `post` checks every balance before the
    first write precisely so that a rejected movement leaves no trace to clean
    up — which is only true if nothing was written at all."""
    run = uuid.uuid4().hex
    before = Transaction.objects.count()
    free = services.account_for(customer, AccountKind.INSURANCE_FREE)
    cash = services.system_account(AccountKind.EXTERNAL_CASH)

    with pytest.raises(Unbalanced):
        services.post(
            kind=TransactionKind.CORRECTION,
            idempotency_key=f"unbalanced/{run}",
            # One leg short of answering the others, whatever they are.
            legs=[Leg(free, legs[0]), Leg(cash, -sum(legs, start=Decimal("0.00")))],
        )

    assert Transaction.objects.count() == before
