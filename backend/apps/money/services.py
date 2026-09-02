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
from django.db import IntegrityError
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
    """A refused money operation.

    The message is Arabic and finished: an operator reads it as-is, and the
    API returns it under a stable ``code`` (Article 1-6 — every number shown
    has an explanation, including the ones we refuse to produce).
    """


class Unbalanced(MoneyError):
    pass


class InsufficientFunds(MoneyError):
    """A customer bucket would have gone below zero.

    The message names all three quantities, because "الرصيد لا يكفي" alone
    sends support back to the database to find out by how much.
    """

    def __init__(self, account: Account, available: Decimal, needed: Decimal):
        self.account = account
        self.available = available
        self.needed = needed
        super().__init__(
            f"{AccountKind(account.kind).label}: المتاح {available} والمطلوب {needed}"
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

    Calling this twice with the same ``idempotency_key`` returns the
    transaction from the first call and moves nothing — which is what lets
    every webhook handler, retry cron and manual replay run without fear of
    double-crediting.

    The order of the steps below is the design, not an accident:

    1. a known key short-circuits before anything is validated or locked;
    2. the movement is validated while nothing has been written;
    3. repeated legs for one account are collapsed, so an account is locked
       once and its balance moves once;
    4. accounts are locked in ascending primary-key order — the single thing
       that keeps two concurrent postings from deadlocking against each other;
    5. every resulting balance is checked **before** the first write, so a
       refusal costs no rows and the caller gets a sentence instead of an
       IntegrityError;
    6. only then are the transaction, its entries, and the balances written.
    """
    existing = _find_by_key(idempotency_key)
    if existing is not None:
        log.info("post: %s already recorded as txn %s", idempotency_key, existing.pk)
        return existing

    _validate(legs)

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
    missing = set(delta_by_account) - set(locked)
    if missing:
        raise MoneyError(f"حسابات غير موجودة: {sorted(missing)}")

    # Check every bucket before writing anything. A refusal must leave no
    # trace, and the caller must learn which bucket was short and by how much.
    new_balances: dict[int, Decimal] = {}
    for pk, delta in delta_by_account.items():
        account = locked[pk]
        new_balance = account.balance + delta
        if new_balance < ZERO and account.kind in AccountKind.customer_owned():
            raise InsufficientFunds(account, available=account.balance, needed=-delta)
        new_balances[pk] = new_balance

    txn, is_ours = _create_transaction(
        kind=kind,
        idempotency_key=idempotency_key,
        occurred_at=occurred_at or timezone.now(),
        memo=memo,
        created_by=created_by,
        reverses=reverses,
    )
    if not is_ours:
        # Another thread won the unique key. Its transaction is the real one,
        # complete with its entries; ours was never written.
        log.info("post: %s was won by txn %s concurrently", idempotency_key, txn.pk)
        return txn

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

    for pk, new_balance in new_balances.items():
        account = locked[pk]
        account.balance = new_balance
        account.save(update_fields=["balance", "updated_at"])

    log.info("post: %s %s -> txn %s", kind, idempotency_key, txn.pk)
    return txn


def _validate(legs: list[Leg]) -> None:
    """Refuse a movement that cannot be a movement.

    Every message here is Arabic and complete, because these are the errors an
    operator sees when a manual correction is rejected.
    """
    if len(legs) < 2:
        raise Unbalanced("الحركة تحتاج طرفين على الأقل")
    if any(leg.amount == ZERO for leg in legs):
        raise Unbalanced("طرف بصفر لا يحرّك شيئاً")
    total = sum((leg.amount for leg in legs), start=ZERO)
    if total != ZERO:
        raise Unbalanced(f"مجموع الأطراف {total} وليس صفراً")


def _find_by_key(idempotency_key: str) -> Transaction | None:
    return Transaction.objects.filter(idempotency_key=idempotency_key).first()


def _create_transaction(**fields) -> tuple[Transaction, bool]:
    """Insert the transaction, letting the unique key settle any race.

    Returns the transaction and whether this call is the one that created it.

    Two threads can both pass the pre-check for the same key; the pre-check is
    a shortcut, never the guarantee. The unique index is the arbiter, and the
    thread that loses reads the winner's row instead of raising — an inbound
    webhook delivered twice at once must credit once and report success twice,
    not succeed once and error once.

    The loser only reaches the insert after the winner has committed, because
    it is still waiting on the account locks the winner holds. So the row it
    reads back is complete, entries and all.

    The savepoint matters: without it the IntegrityError would poison the
    surrounding atomic block and there would be nothing left to return into.
    """
    try:
        with db_transaction.atomic():
            return Transaction.objects.create(**fields), True
    except IntegrityError:
        winner = _find_by_key(fields["idempotency_key"])
        if winner is None:
            raise
        return winner, False


@db_transaction.atomic
def reverse(txn: Transaction, *, reason: str, by=None) -> Transaction:
    """Undo a transaction by posting its mirror image.

    The original stays exactly as it was. Anyone reading the history later
    sees both what happened and that it was taken back, which is the only way
    an audit ever reconstructs a disputed balance.
    """
    already = Transaction.objects.filter(reverses=txn).first()
    if already is not None:
        raise MoneyError(f"المعاملة {txn.pk} معكوسة بالفعل بالمعاملة {already.pk}")
    if txn.kind == TransactionKind.REVERSAL:
        raise MoneyError(f"المعاملة {txn.pk} هي نفسها عكس، ولا تُعكس مرة أخرى")

    entries = list(txn.entries.select_related("account"))
    if not entries:
        raise MoneyError(f"المعاملة {txn.pk} بلا قيود، فلا شيء يُعكس")

    return post(
        kind=TransactionKind.REVERSAL,
        idempotency_key=f"reversal:{txn.uuid}",
        legs=[Leg(account=e.account, amount=-e.amount) for e in entries],
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
        raise MoneyError(f"مصدر تمويل غير معروف: {source!r}")

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


def _active_hold(*, owner, auction=None, invoice=None) -> Hold | None:
    return Hold.objects.filter(
        owner=owner, auction=auction, invoice=invoice, state=HoldState.ACTIVE
    ).first()


def _episode(*, owner, auction=None, invoice=None) -> int:
    """How many times this customer has already been held against this subject.

    The number turns a hold's idempotency key from "this customer and this
    auction, forever" into "this customer's *n*-th hold on this auction",
    which is what the key has to mean.

    Getting this wrong is subtle and expensive. With a permanent key, a
    customer who bids, has the hold released at settlement, then bids again in
    a relisted round gets a `post` that recognises the old key, moves nothing,
    and still returns — leaving a fresh Hold row claiming money that never
    left `insurance_free`. The bucket and the holds disagree from then on.

    Counting every hold regardless of state keeps the number stable for
    concurrent callers inside one episode: they all read the same count and
    therefore build the same key, so twenty simultaneous bids move the deposit
    exactly once.
    """
    return Hold.objects.filter(owner=owner, auction=auction, invoice=invoice).count()


def _lock_free_insurance(user) -> Account:
    """Take the customer's `insurance_free` row lock before deciding anything.

    Every hold for one customer contends on this single row, so the decision
    (is there already a hold? which episode is this?) and the movement that
    follows from it happen under the same lock instead of straddling it.

    Without it, twenty simultaneous bids each read "no hold yet, episode 0",
    and the ones that lose the race then recompute a *different* episode
    number, build a fresh idempotency key, and try to move a deposit that the
    winner has already moved. The unique index still keeps the hold rows
    correct; it is the money that goes wrong.
    """
    return Account.objects.select_for_update().get(
        pk=account_for(user, AccountKind.INSURANCE_FREE).pk
    )


def _create_hold(**fields) -> Hold:
    """Create the hold, letting the partial unique index settle any race.

    Twenty bidders' worth of concurrent requests all pass `_active_hold`
    before any of them inserts. The pre-check is a shortcut; the index is the
    guarantee. The loser reads the winner's hold rather than raising, because
    a customer who clicked twice has one claim on their deposit, not an error.
    """
    try:
        with db_transaction.atomic():
            return Hold.objects.create(**fields)
    except IntegrityError:
        winner = _active_hold(
            owner=fields["owner"],
            auction=fields.get("auction"),
            invoice=fields.get("invoice"),
        )
        if winner is None:
            raise
        return winner


@db_transaction.atomic
def hold_for_auction(*, user, auction, amount: Decimal | None = None) -> Hold:
    """Reserve a customer's insurance against one auction so they can bid.

    Idempotent per (customer, auction): a customer who bids twenty times in the
    same auction has exactly one hold, enforced by a unique constraint rather
    than by remembering to check.
    """
    _lock_free_insurance(user)

    existing = _active_hold(owner=user, auction=auction)
    if existing is not None:
        return existing

    amount = amount or Decimal(settings.INSURANCE_DEPOSIT_AMOUNT)
    episode = _episode(owner=user, auction=auction)
    txn = post(
        kind=TransactionKind.INSURANCE_HOLD,
        idempotency_key=f"hold:{user.pk}:{auction.pk}:{episode}",
        memo=f"حجز تأمين لمزاد {auction.pk}",
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_HELD), amount),
        ],
    )
    return _create_hold(
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
    free_account = _lock_free_insurance(user)

    existing = _active_hold(owner=user, invoice=invoice)
    if existing is not None:
        return existing

    available = free_account.balance
    # Lock the smaller of what is owed and what is there. Locking more than
    # the debt would be a penalty, and this bucket is a guarantee.
    amount = amount or min(invoice.outstanding, available)
    if amount <= ZERO:
        raise MoneyError(
            f"لا يوجد تأمين متاح لقفله على الفاتورة {invoice.number}: "
            f"المتاح {available} والمستحق {invoice.outstanding}"
        )

    episode = _episode(owner=user, invoice=invoice)
    txn = post(
        kind=TransactionKind.INSURANCE_LOCK,
        idempotency_key=f"lock:{user.pk}:{invoice.pk}:{episode}",
        memo=f"قفل تأمين على الفاتورة {invoice.number}",
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -amount),
            Leg(account_for(user, AccountKind.INSURANCE_LOCKED), amount),
        ],
    )
    return _create_hold(
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
    suspense = system_account(AccountKind.SUSPENSE)
    if amount > suspense.balance:
        # Suspense is a platform bucket, so it carries no CHECK floor — an
        # over-attribution would quietly invent money instead of failing.
        # This is the one place that guard has to live.
        raise MoneyError(f"المعلّق فيه {suspense.balance} ولا يكفي لنسب {amount}")

    return post(
        kind=TransactionKind.ATTRIBUTION,
        idempotency_key=f"attribute:{reference}",
        memo=memo,
        created_by=by,
        legs=[
            Leg(suspense, -amount),
            Leg(account_for(user, AccountKind.INSURANCE_FREE), amount),
        ],
    )


# ---------------------------------------------------------------------------
# Confiscation — the only path that takes a customer's money for good
# ---------------------------------------------------------------------------


@db_transaction.atomic
def confiscate(hold: Hold, *, reason: str, by, memo: str = "") -> Transaction:
    """Take a held or locked deposit permanently, by a named decision.

    Both arguments are mandatory and neither has a default. Confiscation is
    the one movement that ends with a customer poorer and no service rendered,
    so it may never happen as a side effect of a cron, a retry, or a
    convenience default — someone put their name to it and wrote why.

    TODO(T008): also record this through `apps.core.audit.record` once that
    exists. Until then the transaction itself carries the two facts the audit
    needs — `created_by` and `memo` — and `Hold.ended_by_transaction` links
    the claim to the decision that ended it.
    """
    if not reason or not reason.strip():
        raise MoneyError("المصادرة تحتاج سبباً مكتوباً")
    if by is None:
        raise MoneyError("المصادرة تحتاج منفّذاً مسمّى")
    if hold.state != HoldState.ACTIVE:
        raise MoneyError(f"الحجز {hold.pk} ليس قائماً، فلا شيء يُصادَر")

    bucket = (
        AccountKind.INSURANCE_HELD
        if hold.reason == HoldReason.BIDDING
        else AccountKind.INSURANCE_LOCKED
    )
    txn = post(
        kind=TransactionKind.INSURANCE_CONFISCATE,
        idempotency_key=f"confiscate:{hold.pk}",
        memo=f"مصادرة حجز {hold.pk}: {reason.strip()}" + (f" — {memo}" if memo else ""),
        created_by=by,
        legs=[
            Leg(account_for(hold.owner, bucket), -hold.amount),
            Leg(system_account(AccountKind.CONFISCATED), hold.amount),
        ],
    )
    hold.state = HoldState.CONSUMED
    hold.ended_by_transaction = txn
    hold.ended_at = timezone.now()
    hold.save(update_fields=["state", "ended_by_transaction", "ended_at"])
    return txn


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
