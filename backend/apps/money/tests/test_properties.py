"""T121 — properties that must hold for *any* sequence of valid movements.

The example-based tests elsewhere each check one story someone thought of.
This file checks the three invariants that have to survive stories nobody
thought of, over thousands of generated ones.

Hypothesis drives Django's ORM here rather than pure functions, so the
generation is done up front and replayed inside one database transaction:
`@given` cannot manage database state across its own retries.
"""

from decimal import Decimal

import pytest
from django.db.models import Sum
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from apps.money import services
from apps.money.models import Account, AccountKind, Entry
from apps.money.services import InsufficientFunds, MoneyError
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
    hold = None
    for index, (operation, amount) in enumerate(script):
        reference = f"P/{index}"
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

    total = Entry.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    assert total == Decimal("0.00"), f"the whole book sums to {total}, not zero"

    negative = Account.objects.filter(
        kind__in=AccountKind.customer_owned(), balance__lt=Decimal("0.00")
    )
    assert not negative.exists(), f"negative customer buckets: {list(negative)}"

    assert verify_ledger() == []


@settings(max_examples=1000, deadline=None)
@given(legs=st.lists(amounts, min_size=1, max_size=6))
def test_a_balanced_movement_always_sums_to_zero_by_construction(legs):
    """The arithmetic underneath the ledger, checked without a database.

    Every movement is a set of positive amounts and one negative that answers
    them. Decimal makes this exact; the same test written with `float` fails
    on values as ordinary as 0.10 + 0.20, which is why Article 3-2 exists.
    """
    total_in = sum(legs, start=Decimal("0.00"))
    movement = [*legs, -total_in]

    assert sum(movement, start=Decimal("0.00")) == Decimal("0.00")
    assert all(leg != Decimal("0.00") for leg in movement)
