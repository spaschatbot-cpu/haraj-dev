"""The only writer of money.

No view, task, serializer or admin action creates an :class:`Entry` directly.
Everything goes through :func:`post`, which is the one place that knows how to
lock accounts, balance a transaction, and refuse an impossible one.

Concurrency
-----------
:func:`post` locks every account it touches with ``SELECT ... FOR UPDATE``, in
ascending primary-key order so two concurrent postings can never deadlock
against each other. That lock is what makes the cached balances safe to adjust
by delta; :func:`verify_ledger` independently recomputes them from the entries
and reports any drift, so the cache is checked rather than trusted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import transaction as db_transaction
from django.db.models import Sum
from django.utils import timezone

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
    TransactionKind,
)

log = logging.getLogger(__name__)


class MoneyError(Exception):
    """A refused money operation. Always safe to show to an operator."""


class Unbalanced(MoneyError):
    pass


class InsufficientFunds(MoneyError):
    def __init__(self, account: Account, needed: Decimal):
        self.account = account
        self.needed = needed
        super().__init__(
            f"{account.kind} for owner {account.owner_id} holds {account.balance}, "
            f"needs {needed}"
        )


@dataclass(frozen=True)
class Leg:
    """One side of a movement. ``amount`` is signed: positive means money in."""

    account: Account
    amount: Decimal


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


def account_for(user, kind: str) -> Account:
    """The customer's bucket of this kind, created on first use."""
    if kind not in AccountKind.customer_owned():
        raise MoneyError(f"{kind} is not a customer bucket")
    account, _ = Account.objects.get_or_create(owner=user, kind=kind)
    return account


def system_account(kind: str) -> Account:
    """The single platform-wide bucket of this kind."""
    if kind in AccountKind.customer_owned():
        raise MoneyError(f"{kind} belongs to a customer, not the platform")
    account, _ = Account.objects.get_or_create(owner=None, kind=kind)
    return account


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------


@db_transaction.atomic
def post(
    *,
    kind: str,
    idempotency_key: str,
    legs: list[Leg],
    occurred_at=None,
    memo: str = "",
    created_by=None,
    reverses: Transaction | None = None,
) -> Transaction:
    """Record a balanced money movement, exactly once.

    Calling this twice with the same ``idempotency_key`` returns the transaction
    from the first call and moves nothing — which is what lets every webhook
    handler, retry cron and manual replay run without fear of double-crediting.
    """
    existing = Transaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing is not None:
        log.info("post: %s already recorded as txn %s", idempotency_key, existing.pk)
        return existing

    if len(legs) < 2:
        raise Unbalanced("a movement needs at least two sides")
    if any(leg.amount == ZERO for leg in legs):
        raise Unbalanced("a leg of zero moves nothing")
    total = sum((leg.amount for leg in legs), start=ZERO)
    if total != ZERO:
        raise Unbalanced(f"legs sum to {total}, not zero")

    # Collapse repeated accounts, then lock in a stable order.
    delta_by_account: dict[int, Decimal] = {}
    for leg in legs:
        delta_by_account[leg.account.pk] = (
            delta_by_account.get(leg.account.pk, ZERO) + leg.amount
        )

    locked = {
        account.pk: account
        for account in Account.objects.select_for_update()
        .filter(pk__in=delta_by_account)
        .order_by("pk")
    }

    txn = Transaction.objects.create(
        kind=kind,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at or timezone.now(),
        memo=memo,
        created_by=created_by,
        reverses=reverses,
    )

    Entry.objects.bulk_create(
        [
            Entry(
                transaction=txn,
                account=locked[leg.account.pk],
                amount=leg.amount,
                owner_id=locked[leg.account.pk].owner_id,
            )
            for leg in legs
        ]
    )

    for pk, delta in delta_by_account.items():
        account = locked[pk]
        new_balance = account.balance + delta
        if new_balance < ZERO and account.kind in AccountKind.customer_owned():
            # Raised before the write so the operator sees a sentence, not an
            # IntegrityError. The database CHECK remains as the backstop.
            raise InsufficientFunds(account, -delta)
        account.balance = new_balance
        account.save(update_fields=["balance", "updated_at"])

    log.info("post: %s %s -> txn %s", kind, idempotency_key, txn.pk)
    return txn


@db_transaction.atomic
def reverse(txn: Transaction, *, reason: str, by=None) -> Transaction:
    """Undo a transaction by posting its mirror image.

    The original stays exactly as it was. Anyone reading the history later sees
    both what happened and that it was taken back, which is the only way an
    audit ever reconstructs a disputed balance.
    """
    if hasattr(txn, "reversed_by"):
        raise MoneyError(f"txn {txn.pk} was already reversed by {txn.reversed_by_id}")

    return post(
        kind=TransactionKind.REVERSAL,
        idempotency_key=f"reversal:{txn.uuid}",
        legs=[Leg(account=e.account, amount=-e.amount) for e in txn.entries.all()],
        memo=reason,
        created_by=by,
        reverses=txn,
    )


# ---------------------------------------------------------------------------
# Insurance — the deposit lifecycle
# ---------------------------------------------------------------------------


def deposit_insurance(
    *,
    user,
    amount: Decimal,
    source: str,
    reference: str,
    occurred_at=None,
    memo: str = "",
) -> Transaction:
    """Money arrived from a customer and became available insurance.

    ``reference`` is the payment's identity in the world it came from (an Odoo
    payment id, a Moyasar id). It becomes the idempotency key, so the same
    payment heard twice credits once.
    """
    external = {
        "cash": AccountKind.EXTERNAL_CASH,
        "card": AccountKind.EXTERNAL_CARD,
    }.get(source)
    if external is None:
        raise MoneyError(f"unknown funding source {source!r}")

    return post(
        kind=TransactionKind.INSURANCE_TOPUP,
        idempotency_key=f"{source}:{reference}",
        occurred_at=occurred_at,
        memo=memo,
        legs=[
            Leg(system_account(external), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_FREE), amount),
        ],
    )


@db_transaction.atomic
def hold_for_auction(*, user, auction, amount: Decimal | None = None) -> Hold:
    """Reserve a customer's insurance against one auction so they can bid.

    Idempotent per (customer, auction): a customer who bids twenty times in the
    same auction has exactly one hold, enforced by a unique constraint rather
    than by remembering to check.
    """
    existing = Hold.objects.filter(
        owner=user, auction=auction, state=HoldState.ACTIVE
    ).first()
    if existing is not None:
        return existing

    amount = amount or Decimal(settings.INSURANCE_DEPOSIT_AMOUNT)
    txn = post(
        kind=TransactionKind.INSURANCE_HOLD,
        idempotency_key=f"hold:{user.pk}:{auction.pk}",
        memo=f"حجز تأمين لمزاد {auction.pk}",
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_HELD), amount),
        ],
    )
    return Hold.objects.create(
        owner=user,
        auction=auction,
        amount=amount,
        reason=HoldReason.BIDDING,
        created_by_transaction=txn,
    )


@db_transaction.atomic
def release_hold(hold: Hold, *, memo: str = "") -> Hold:
    """Give a hold's money back to the customer's free insurance."""
    if hold.state != HoldState.ACTIVE:
        return hold

    bucket = (
        AccountKind.INSURANCE_HELD
        if hold.reason == HoldReason.BIDDING
        else AccountKind.INSURANCE_LOCKED
    )
    txn = post(
        kind=TransactionKind.INSURANCE_RELEASE,
        idempotency_key=f"release:{hold.pk}",
        memo=memo or f"فك حجز {hold.pk}",
        legs=[
            Leg(account_for(hold.owner, bucket), -hold.amount),
            Leg(account_for(hold.owner, AccountKind.INSURANCE_FREE), hold.amount),
        ],
    )
    hold.state = HoldState.RELEASED
    hold.ended_by_transaction = txn
    hold.ended_at = timezone.now()
    hold.save(update_fields=["state", "ended_by_transaction", "ended_at"])
    return hold


@db_transaction.atomic
def lock_for_invoice(*, user, invoice: Invoice, amount: Decimal | None = None) -> Hold:
    """Pin insurance against an unpaid invoice so it cannot be refunded away.

    A customer who owes us money keeps their deposit with us. v1 let a debtor's
    deposit look free because nothing recorded *which* debt it answered; here
    the hold names the invoice.
    """
    existing = Hold.objects.filter(
        owner=user, invoice=invoice, state=HoldState.ACTIVE
    ).first()
    if existing is not None:
        return existing

    amount = amount or min(
        invoice.outstanding,
        account_for(user, AccountKind.INSURANCE_FREE).balance,
    )
    if amount <= ZERO:
        raise MoneyError("nothing free to lock against this invoice")

    txn = post(
        kind=TransactionKind.INSURANCE_LOCK,
        idempotency_key=f"lock:{user.pk}:{invoice.pk}",
        memo=f"قفل تأمين على الفاتورة {invoice.number}",
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_LOCKED), amount),
        ],
    )
    return Hold.objects.create(
        owner=user,
        invoice=invoice,
        amount=amount,
        reason=HoldReason.DUES,
        created_by_transaction=txn,
    )


def refund_insurance(
    *, user, amount: Decimal, reference: str, occurred_at=None, memo: str = ""
) -> Transaction:
    """Pay insurance back out to the customer.

    Only free insurance can leave. Anything held for a live auction or locked
    against an unpaid invoice is, by construction, not in the free bucket — so
    the refund of a debtor's deposit fails on arithmetic rather than on a gate
    somebody has to remember to write.
    """
    return post(
        kind=TransactionKind.INSURANCE_REFUND,
        idempotency_key=f"refund:{reference}",
        occurred_at=occurred_at,
        memo=memo,
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -amount),
            Leg(system_account(AccountKind.EXTERNAL_REFUND), amount),
        ],
    )


def receive_unattributed(
    *, amount: Decimal, source: str, reference: str, occurred_at=None, memo: str = ""
) -> Transaction:
    """Money arrived that we cannot yet attribute to a customer.

    v1's instinct was to drop what it could not place, and money went missing in
    exactly that gap. Here it lands in ``suspense``: visible, counted, and
    waiting for someone to say whose it is.
    """
    external = (
        AccountKind.EXTERNAL_CARD if source == "card" else AccountKind.EXTERNAL_CASH
    )
    return post(
        kind=TransactionKind.UNATTRIBUTED_RECEIPT,
        idempotency_key=f"{source}:{reference}",
        occurred_at=occurred_at,
        memo=memo,
        legs=[
            Leg(system_account(external), -amount),
            Leg(system_account(AccountKind.SUSPENSE), amount),
        ],
    )


def attribute(
    *, user, amount: Decimal, reference: str, by=None, memo: str = ""
) -> Transaction:
    """Move a suspense amount to the customer it turned out to belong to."""
    return post(
        kind=TransactionKind.ATTRIBUTION,
        idempotency_key=f"attribute:{reference}",
        memo=memo,
        created_by=by,
        legs=[
            Leg(system_account(AccountKind.SUSPENSE), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_FREE), amount),
        ],
    )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    check: str
    subject: str
    detail: str


def verify_ledger() -> list[Finding]:
    """Recompute what the ledger claims and report every disagreement.

    This is deliberately independent of :func:`post`: it reads only entries and
    holds, so a bug in the posting path shows up here instead of being confirmed
    by it. Run it after every deploy and nightly.

    It cannot, and does not pretend to, prove the ledger agrees with Odoo — that
    is a separate comparison against the book of record.
    """
    findings: list[Finding] = []

    # 1. Every transaction sums to zero.
    for txn in (
        Transaction.objects.annotate(total=Sum("entries__amount"))
        .filter(total__isnull=False)
        .exclude(total=ZERO)
    ):
        findings.append(
            Finding(
                "balanced_transactions", f"txn {txn.pk}", f"entries sum to {txn.total}"
            )
        )

    # 2. Every cached balance equals the sum of its entries.
    sums = {
        row["account"]: row["total"]
        for row in Entry.objects.values("account").annotate(total=Sum("amount"))
    }
    for account in Account.objects.all():
        actual = sums.get(account.pk, ZERO)
        if account.balance != actual:
            findings.append(
                Finding(
                    "cached_balance",
                    str(account),
                    f"cached {account.balance}, entries say {actual}",
                )
            )

    # 3. Held and locked money is fully explained by active holds.
    for kind, reason in (
        (AccountKind.INSURANCE_HELD, HoldReason.BIDDING),
        (AccountKind.INSURANCE_LOCKED, HoldReason.DUES),
    ):
        for account in Account.objects.filter(kind=kind).exclude(balance=ZERO):
            claimed = (
                Hold.objects.filter(
                    owner_id=account.owner_id, reason=reason, state=HoldState.ACTIVE
                ).aggregate(total=Sum("amount"))["total"]
                or ZERO
            )
            if claimed != account.balance:
                findings.append(
                    Finding(
                        "holds_explain_bucket",
                        str(account),
                        f"bucket holds {account.balance}, active holds claim {claimed}",
                    )
                )

    # 4. Nobody's locked insurance exceeds what they actually owe.
    for account in Account.objects.filter(kind=AccountKind.INSURANCE_LOCKED).exclude(
        balance=ZERO
    ):
        owed = (
            Invoice.objects.filter(customer_id=account.owner_id)
            .exclude(state=InvoiceState.CANCELLED)
            .aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        paid = (
            Invoice.objects.filter(customer_id=account.owner_id)
            .exclude(state=InvoiceState.CANCELLED)
            .aggregate(total=Sum("amount_paid"))["total"]
            or ZERO
        )
        outstanding = max(owed - paid, ZERO)
        if account.balance > outstanding:
            findings.append(
                Finding(
                    "locked_not_above_dues",
                    str(account),
                    f"locked {account.balance} against {outstanding} outstanding",
                )
            )

    return findings
