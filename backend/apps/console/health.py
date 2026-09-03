"""شاشة صحة المال — the three ways money can be wrong, on one page. T813/T220.

Three questions, and they are genuinely different questions:

1. **Does the ledger agree with itself?** `verify_ledger` re-derives every
   balance from the entries and reports each disagreement.
2. **Does it agree with Odoo?** Odoo is the book of record (Article 2-5), and
   green on question 1 says nothing about question 2 — v1 could prove its own
   consistency while a customer bid with 10,000 that Odoo's ledger closed at
   zero. That comparison is `BalanceCheck`, from phase 003.
3. **Is there money here that belongs to nobody yet?** The suspense bucket:
   real riyals that arrived and have not been attributed to a customer.

Why they are not added up
-------------------------
There is no headline "total missing" on this screen, and that is a decision
rather than an omission. A 500 drift in the cache and a 500 difference against
Odoo may well be the *same* 500 seen from two sides; adding them reports 1,000
missing when 500 is missing. The screen shows three counts and three lists, and
lets the person reading decide what one incident it is.

Which is the same rule as the one governing every figure here, and the task
states it as a warning rather than a requirement: **لا يُبالَغ في أي مبلغ
معروض**. A health screen that overstates a shortfall once is a health screen
nobody opens again — and the two ways to overstate one are both closed here.
The notes are recomputed on every render, so a fixed cause is gone from the page
without anyone marking it resolved; and the suspense total is the bucket's own
balance, never the sum of the receipts that have ever landed in it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render

from apps.money.models import ZERO, Account, AccountKind, Entry, TransactionKind
from apps.money.verification import Finding, verify_ledger
from apps.odoo.reconciliation import open_differences

from .views import console_page

#: Suspense movements shown. The bucket is meant to be nearly empty; a page of
#: fifty lines here is itself the finding.
MOVEMENT_LIMIT = 50


@dataclass(frozen=True)
class Suspense:
    """Money that arrived and has not been given an owner.

    :attr:`balance` is the account's balance and nothing else. It is emphatically
    not the sum of the receipts below it: `attribute` moves money out of the
    pool without settling any particular receipt, so a per-receipt "still
    outstanding" column would be a number this codebase does not know. The
    movements are shown as movements — what came in and what went out — and the
    one authoritative figure is the pool.
    """

    balance: Decimal
    derived: Decimal
    movements: list[Entry]

    @property
    def agrees(self) -> bool:
        """Whether the stored pool matches its own entries."""
        return self.balance == self.derived


def suspense_state() -> Suspense:
    """What is sitting unattributed, and the movements that put it there."""
    account = Account.objects.filter(
        kind=AccountKind.SUSPENSE, owner__isnull=True
    ).first()
    if account is None:
        return Suspense(balance=ZERO, derived=ZERO, movements=[])

    derived = (
        Entry.objects.filter(account=account).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )

    movements = list(
        Entry.objects.filter(
            account=account,
            transaction__kind__in=(
                TransactionKind.UNATTRIBUTED_RECEIPT,
                TransactionKind.ATTRIBUTION,
            ),
        ).select_related("transaction")[:MOVEMENT_LIMIT]
    )
    return Suspense(balance=account.balance, derived=derived, movements=movements)


@dataclass(frozen=True)
class Health:
    """Everything the screen renders, gathered once."""

    findings: list[Finding]
    differences: list
    suspense: Suspense

    @property
    def is_clean(self) -> bool:
        """No note of any of the three kinds. The only state worth a green line."""
        return (
            not self.findings
            and not self.differences
            and self.suspense.balance == ZERO
            and self.suspense.agrees
        )


def health_report() -> Health:
    """The three checks, run now.

    Run rather than looked up, which is what makes a note close by itself. There
    is no table of open findings anywhere in this codebase — a stored note has
    to be closed by somebody noticing that it should be, and in v1 the
    reconciliation queue's oldest entries were all things that had been fixed
    months earlier and never ticked off, so the queue was ignored wholesale.
    """
    return Health(
        findings=verify_ledger(),
        differences=list(open_differences()),
        suspense=suspense_state(),
    )


@console_page("console:money-health")
def health(request):
    return render(request, "console/money_health.html", {"report": health_report()})


__all__ = ["Health", "Suspense", "health", "health_report", "suspense_state"]
