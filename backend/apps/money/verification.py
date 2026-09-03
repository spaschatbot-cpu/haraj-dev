"""Independent re-derivation of everything the ledger claims.

This module imports **nothing** from :mod:`apps.money.services`. That is the
whole point of it: a bug in the writing path has to show up here rather than
be confirmed by it. If verification called the same helpers that produced the
data, a wrong balance and a wrong check would agree with each other and the
report would come back clean.

So it reads tables. Only tables.

What it cannot do
-----------------
It proves the ledger is consistent **with itself**. It says nothing about
whether we agree with Odoo, which is the actual book of record (Article 2-5).
That comparison is `BalanceCheck`, in phase 003, and no amount of green here
substitutes for it.

Run after every deploy, nightly, and at the end of any test that touches money.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Sum

from .models import (
    ZERO,
    Account,
    AccountKind,
    Entry,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceState,
    Transaction,
)


@dataclass(frozen=True)
class Finding:
    """One disagreement between what is stored and what the entries say."""

    check: str
    subject: str
    detail: str

    def __str__(self) -> str:
        return f"[{self.check}] {self.subject}: {self.detail}"


def verify_ledger() -> list[Finding]:
    """Run all four checks and return every disagreement found."""
    return [
        *check_transactions_balance(),
        *check_cached_balances(),
        *check_holds_explain_buckets(),
        *check_locked_not_above_dues(),
    ]


def verify_customer(owner) -> list[Finding]:
    """Everything :func:`verify_ledger` would say about **one** customer.

    The console's deposits ledger (T810) shows a customer their buckets, and the
    number it shows has to be a number this module would stand behind. Rather
    than let the screen re-derive its own totals — a second derivation is a
    second thing that can be right when the first is wrong — it calls the checks
    themselves, narrowed to one owner.

    `check_transactions_balance` is not among them: a transaction spans two
    accounts and often two parties, so "this customer's transactions" is not a
    set that means anything. Its findings belong to the health screen, which
    looks at the whole book.
    """
    return [
        *check_cached_balances(owner=owner),
        *check_holds_explain_buckets(owner=owner),
        *check_locked_not_above_dues(owner=owner),
    ]


def _accounts(*, owner=None):
    """Every account, or one customer's — the same rows either way.

    The scoping exists so a screen about one person does not read the whole
    table. It is a filter and nothing else: no check answers differently for a
    narrowed set than it would for that customer inside the full run.
    """
    accounts = Account.objects.all()
    return accounts if owner is None else accounts.filter(owner=owner)


def check_transactions_balance() -> list[Finding]:
    """1. Every transaction's entries sum to exactly zero.

    A transaction that does not is money created or destroyed inside our own
    books, which is the one thing double-entry exists to make visible.
    """
    findings = []
    rows = (
        Transaction.objects.annotate(total=Sum("entries__amount"))
        .filter(total__isnull=False)
        .exclude(total=ZERO)
        .values("pk", "idempotency_key", "total")
    )
    for row in rows:
        findings.append(
            Finding(
                "balanced_transactions",
                f"txn {row['pk']} ({row['idempotency_key']})",
                f"مجموع القيود {row['total']} وليس صفراً",
            )
        )
    return findings


def check_cached_balances(*, owner=None) -> list[Finding]:
    """2. Every stored balance equals the sum of that account's entries.

    `Account.balance` is a cache, adjusted by delta under a row lock. This is
    the check that makes the cache trustworthy: it is re-derived from the
    entries and any drift is reported. Without this the design would be v1's
    mistake wearing better clothes.
    """
    findings = []
    sums = {
        row["account"]: row["total"]
        for row in Entry.objects.values("account").annotate(total=Sum("amount"))
    }
    for account in _accounts(owner=owner).iterator():
        actual = sums.get(account.pk, ZERO)
        if account.balance != actual:
            findings.append(
                Finding(
                    "cached_balance",
                    str(account),
                    f"المخزَّن {account.balance} والقيود تقول {actual}",
                )
            )
    return findings


def check_holds_explain_buckets(*, owner=None) -> list[Finding]:
    """3. Not one riyal sits in `held` or `locked` without a hold naming why.

    Money that is reserved but unexplained is money nobody can release,
    because nobody knows what releasing it would undo. In v1 this state was
    reachable and support resolved it by hand, from memory.
    """
    findings = []
    for kind, reason in (
        (AccountKind.INSURANCE_HELD, HoldReason.BIDDING),
        (AccountKind.INSURANCE_LOCKED, HoldReason.DUES),
    ):
        holds = Hold.objects.filter(reason=reason, state=HoldState.ACTIVE)
        if owner is not None:
            holds = holds.filter(owner=owner)
        claimed_by_owner = {
            row["owner"]: row["total"]
            for row in holds.values("owner").annotate(total=Sum("amount"))
        }
        accounts = _accounts(owner=owner).filter(kind=kind).exclude(balance=ZERO)
        for account in accounts.iterator():
            claimed = claimed_by_owner.get(account.owner_id, ZERO)
            if claimed != account.balance:
                findings.append(
                    Finding(
                        "holds_explain_bucket",
                        str(account),
                        f"الدلو فيه {account.balance} والحجوزات القائمة تدّعي {claimed}",
                    )
                )

        # And the mirror image: a hold claiming money that is not in the
        # bucket at all. Checking only one direction leaves the other open.
        for owner_id, claimed in claimed_by_owner.items():
            if not accounts.filter(owner_id=owner_id).exists() and claimed != ZERO:
                findings.append(
                    Finding(
                        "holds_explain_bucket",
                        f"owner {owner_id} / {kind}",
                        f"حجوزات قائمة بـ{claimed} والدلو فارغ",
                    )
                )
    return findings


def check_locked_not_above_dues(*, owner=None) -> list[Finding]:
    """4. Nobody's locked insurance exceeds what they actually owe.

    A lock is a guarantee, not a penalty. Holding more than the debt is
    money taken out of a customer's reach for no reason we could defend to
    them — and a refund they were entitled to and did not get.
    """
    findings = []
    outstanding_by_customer: dict[int, Decimal] = {}
    invoices = Invoice.objects.exclude(state=InvoiceState.CANCELLED)
    if owner is not None:
        invoices = invoices.filter(customer=owner)
    rows = invoices.values("customer").annotate(
        owed=Sum("amount"), paid=Sum("amount_paid")
    )
    for row in rows:
        owed = row["owed"] or ZERO
        paid = row["paid"] or ZERO
        outstanding_by_customer[row["customer"]] = max(owed - paid, ZERO)

    accounts = (
        _accounts(owner=owner)
        .filter(kind=AccountKind.INSURANCE_LOCKED)
        .exclude(balance=ZERO)
    )
    for account in accounts.iterator():
        outstanding = outstanding_by_customer.get(account.owner_id, ZERO)
        if account.balance > outstanding:
            findings.append(
                Finding(
                    "locked_not_above_dues",
                    str(account),
                    f"المقفول {account.balance} والمستحق {outstanding}",
                )
            )
    return findings
