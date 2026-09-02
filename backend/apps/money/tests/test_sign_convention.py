"""T103 — what the numbers in the ledger mean.

This file is documentation first and a check second. If you are trying to
understand how to read a transaction, read this test and nothing else.

The rule, in one sentence: **a balance is how many riyals are sitting in that
bucket**, and every movement is a list of signed lines that add up to zero.

There is no debit and no credit. A positive number means money arrived here; a
negative number means it left. The outside world is a bucket too, and it goes
negative by exactly as much as has come in from it — which is what makes the
zero add up.
"""

from decimal import Decimal

import pytest

from apps.money import services
from apps.money.models import AccountKind

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


def test_a_ten_thousand_cash_deposit_reads_exactly_like_this(customer):
    """A customer hands over 10,000 in cash.

    Two lines are written:

        EXTERNAL_CASH               -10,000.00     it left the outside world
        <customer> insurance_free   +10,000.00     it arrived in their bucket
                                   ────────────
                                          0.00     every movement sums to zero
    """
    txn = services.deposit_insurance(
        user=customer,
        amount=TEN_K,
        source="cash",
        reference="PCSH/2026/001",
    )

    lines = {entry.account.kind: entry.amount for entry in txn.entries.all()}

    assert lines[AccountKind.EXTERNAL_CASH] == Decimal("-10000.00")
    assert lines[AccountKind.INSURANCE_FREE] == Decimal("10000.00")
    assert sum(lines.values()) == Decimal("0.00")


def test_the_customers_bucket_now_holds_ten_thousand(customer):
    """After that deposit, the question "how much does this customer have
    available?" is answered by reading one number, not by adding anything up."""
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="PCSH/2026/002"
    )

    available = services.account_for(customer, AccountKind.INSURANCE_FREE)

    assert available.balance == Decimal("10000.00")


def test_the_outside_world_bucket_is_negative_and_that_is_correct(customer):
    """A negative EXTERNAL_CASH balance is not an error and not a debt.

    It reads as: "10,000 riyals have come into the platform through cash." The
    further below zero it goes, the more money customers have deposited. Only
    customer buckets are forbidden from going negative.
    """
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="PCSH/2026/003"
    )

    cash = services.system_account(AccountKind.EXTERNAL_CASH)

    assert cash.balance == Decimal("-10000.00")


def test_moving_money_between_two_of_the_customers_own_buckets(customer, auction):
    """Placing a bid does not take money from the customer. It moves it from
    the bucket they can spend to the bucket that is spoken for.

        <customer> insurance_free   -10,000.00     no longer available
        <customer> insurance_held   +10,000.00     reserved for this auction
                                   ────────────
                                          0.00

    The customer's total is unchanged; only what they may do with it changed.
    """
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="PCSH/2026/004"
    )

    hold = services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

    free = services.account_for(customer, AccountKind.INSURANCE_FREE).balance
    held = services.account_for(customer, AccountKind.INSURANCE_HELD).balance

    assert free == Decimal("0.00")
    assert held == Decimal("10000.00")
    assert free + held == TEN_K
    assert hold.amount == TEN_K
