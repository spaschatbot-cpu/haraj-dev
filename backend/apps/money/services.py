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

import hashlib
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.db.models import Count
from django.utils import timezone

from apps.core import audit
from apps.core.errors import DomainError

from .models import (
    MONEY,
    ZERO,
    Account,
    AccountKind,
    Entry,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceState,
    PaymentIntent,
    PaymentIntentState,
    PaymentMethod,
    PaymentPurpose,
    RefundRequest,
    RefundRequestState,
    Transaction,
    TransactionKind,
)

log = logging.getLogger(__name__)


class MoneyError(DomainError):
    """A refused money operation. Always safe to show to a customer.

    It carries its own Arabic sentence and a stable code; turning that into an
    HTTP response is :mod:`apps.core.exceptions`'s job and nobody else's
    (Article 1-6 — every number shown has an explanation, including the ones
    we refuse to produce).
    """

    code = "money_error"
    default_message = "تعذّر تنفيذ العملية المالية."


class Unbalanced(MoneyError):
    code = "unbalanced_transaction"
    default_message = "الحركة غير متوازنة ولم تُسجَّل."


class InvalidAmount(MoneyError):
    code = "invalid_amount"
    default_message = "المبلغ غير صالح."


class InsufficientFunds(MoneyError):
    """A customer bucket would have gone below zero.

    ``available`` is stated by the caller rather than read back off
    ``account.balance``: what a customer may actually take out of a bucket is
    not always the whole of it, and the refusal has to name the number the
    rule used.

    A caller with a fuller explanation — "10000.00 مقفولة على مستحقات" — passes
    its own ``user_message`` and ``detail``. Without one, the code alone picks
    the wording, and the two quantities go in ``detail``. The bucket's internal
    name deliberately does not: ``insurance_free`` is our word, not the
    customer's.
    """

    code = "insufficient_funds"

    def __init__(
        self,
        account: Account,
        available: Decimal,
        needed: Decimal,
        *,
        user_message: str | None = None,
        detail: dict | None = None,
    ):
        self.account = account
        self.available = available
        self.needed = needed
        super().__init__(
            f"{AccountKind(account.kind).label}: المتاح {available} والمطلوب {needed}",
            user_message=user_message,
            detail=detail or {"available": str(available), "required": str(needed)},
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
    # Each refusal carries two texts: the one phase 002 wrote, which names the
    # rows and reaches the log and str(exc), and the sentence a customer reads.
    # Primary keys are useful in the first and meaningless in the second.
    already = Transaction.objects.filter(reverses=txn).first()
    if already is not None:
        raise MoneyError(
            f"المعاملة {txn.pk} معكوسة بالفعل بالمعاملة {already.pk}",
            user_message="هذه الحركة معكوسة من قبل.",
        )
    if txn.kind == TransactionKind.REVERSAL:
        raise MoneyError(
            f"المعاملة {txn.pk} هي نفسها عكس، ولا تُعكس مرة أخرى",
            user_message="هذه الحركة هي نفسها عكس، ولا تُعكس مرة أخرى.",
        )

    entries = list(txn.entries.select_related("account"))
    if not entries:
        raise MoneyError(
            f"المعاملة {txn.pk} بلا قيود، فلا شيء يُعكس",
            user_message="لا توجد قيود في هذه الحركة، فلا شيء يُعكس.",
        )

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


def deposit_key(source: str, reference: str) -> str:
    """The idempotency key a deposit will use.

    Public because callers need to ask "has this payment already been
    recorded?" before deciding anything else, and a caller that rebuilds the
    string itself is a second definition of the same rule (Article 4-5) —
    which then drifts, silently, the first time the format changes.
    """
    return f"{source}:{reference}"


def suspense_key(source: str, reference: str) -> str:
    """The idempotency key an *unattributed* receipt will use.

    Deliberately a different namespace from :func:`deposit_key`. The two used
    to be the same string, and that collision was silent and expensive: a
    payment that landed in suspense made the later attributed deposit for that
    very payment a no-op — ``post`` recognised the key, moved nothing, and
    handed back the suspense transaction, so the caller marked the intent
    ``succeeded`` and told the customer they were topped up while their wallet
    was empty and the money still sat in suspense.
    """
    return f"suspense:{source}:{reference}"


def find_transaction(idempotency_key: str) -> Transaction | None:
    """The transaction recorded under this key, if any."""
    return _find_by_key(idempotency_key)


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
        idempotency_key=deposit_key(source, reference),
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


def deposit_amount_for(*, auction=None) -> Decimal:
    """How much insurance the platform requires — the server's number, always.

    The single place this figure is decided. Every path that needs it (holding
    for a bid, starting a card top-up) reads it from here, so raising an
    auction's requirement changes one row and not four screens. A request never
    supplies it: in v1 the amount travelled in the payload and a pen test moved
    it.
    """
    if auction is not None:
        return auction.deposit_required
    return Decimal(settings.INSURANCE_DEPOSIT_AMOUNT).quantize(
        Decimal(1).scaleb(-MONEY["decimal_places"])
    )


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

    amount = amount or deposit_amount_for(auction=auction)
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

    # A bidding hold is *released*; a dues lock is *unlocked*. Both words exist
    # in the enum, and the statement a customer reads should use the right one.
    bucket, kind = (
        (AccountKind.INSURANCE_HELD, TransactionKind.INSURANCE_RELEASE)
        if hold.reason == HoldReason.BIDDING
        else (AccountKind.INSURANCE_LOCKED, TransactionKind.INSURANCE_UNLOCK)
    )
    txn = post(
        kind=kind,
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
        return _top_up_hold(existing, invoice=invoice, free_account=free_account)

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


def _top_up_hold(hold: Hold, *, invoice: Invoice, free_account: Account) -> Hold:
    """Relock whatever a partly-spent hold no longer covers.

    A lock is created for what the customer could cover at the time, and paying
    part of the debt out of it shrinks it. A hold that merely *exists* is
    therefore not a hold that still answers the debt: returning it unchanged
    locked nothing more, and the insurance payment that followed then failed on
    an empty bucket — and kept failing on every retry, so the invoice could
    never be settled from insurance at all.

    Runs under the ``insurance_free`` row lock its caller already took, so the
    figure it locks is the one that was there when it decided to lock it. The
    key names the total the hold is being brought up to, so replaying the same
    top-up moves nothing.
    """
    short = min(invoice.outstanding - hold.amount, free_account.balance)
    if short <= ZERO:
        return hold

    new_amount = hold.amount + short
    post(
        kind=TransactionKind.INSURANCE_LOCK,
        idempotency_key=f"lock:{hold.pk}:up-to:{new_amount}",
        memo=f"زيادة القفل على الفاتورة {invoice.number}",
        legs=[
            Leg(account_for(hold.owner, AccountKind.INSURANCE_FREE), -short),
            Leg(account_for(hold.owner, AccountKind.INSURANCE_LOCKED), short),
        ],
    )
    hold.amount = new_amount
    hold.save(update_fields=["amount"])
    return hold


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
        idempotency_key=suspense_key(source, reference),
        occurred_at=occurred_at,
        memo=memo,
        legs=[
            Leg(system_account(external), -amount),
            Leg(system_account(AccountKind.SUSPENSE), amount),
        ],
    )


@db_transaction.atomic
def attribute(
    *, user, amount: Decimal, reference: str, by=None, memo: str = ""
) -> Transaction:
    """Move a suspense amount to the customer it turned out to belong to.

    The suspense row is locked before the balance is read, not after. Without
    the lock this was a check-then-write across two operators: both read
    10,000, both passed the guard, both posted, and suspense finished at
    -10,000 with 20,000 of insurance credited against 10,000 that had actually
    arrived. ``post`` could not stop it either — its negative-balance refusal
    covers customer buckets only, and suspense belongs to the platform.
    """
    suspense = Account.objects.select_for_update().get(
        pk=system_account(AccountKind.SUSPENSE).pk
    )
    if amount > suspense.balance:
        # The database now carries this floor as well (Article 3-3), but a
        # CHECK can only produce an IntegrityError. This is what produces a
        # sentence, and it is decided under the lock that makes it true.
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


@db_transaction.atomic
def credit_payment(
    *,
    user,
    amount: Decimal,
    source: str,
    reference: str,
    occurred_at=None,
    memo: str = "",
) -> Transaction:
    """Credit one real-world payment to a customer, exactly once.

    A payment can reach us before we know whose it is — the gateway retries
    faster than our own row becomes visible, or Odoo names a customer we have
    not linked yet — land in suspense, and then be heard about a second time
    once the link exists. Both tellings are the *same* money, so the second one
    has to move it out of suspense. Posting a fresh deposit instead would take
    the amount off the external account twice for a payment that arrived once,
    and leave an orphan in suspense that nobody would ever claim.

    Every caller that turns an inbound payment into a credit goes through here,
    so "has this payment already been credited, and where is it sitting?" is
    answered in one place rather than restated at each boundary (Article 4-5).
    """
    already = find_transaction(deposit_key(source, reference))
    if already is not None:
        return already

    in_suspense = find_transaction(suspense_key(source, reference))
    if in_suspense is None:
        return deposit_insurance(
            user=user,
            amount=amount,
            source=source,
            reference=reference,
            occurred_at=occurred_at,
            memo=memo,
        )

    if in_suspense.total != amount:
        # Two different numbers for one payment. Guessing which is right is how
        # a discrepancy becomes a loss nobody notices; the money stays whole in
        # suspense and a human decides.
        raise MoneyError(
            f"الدفعة {reference} محفوظة في المعلّق بمبلغ {in_suspense.total} "
            f"والمطلوب نسبه {amount} — الفرق يحتاج قراراً بشرياً"
        )

    return attribute(
        user=user,
        amount=amount,
        reference=deposit_key(source, reference),
        memo=memo or f"نسب دفعة {reference} بعد أن عُرف صاحبها",
    )


# ---------------------------------------------------------------------------
# What the wallet screen reads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Bucket:
    """One named pot of a customer's money, and the entries that explain it."""

    kind: str
    label: str
    amount: Decimal
    entry_count: int


@dataclass(frozen=True)
class WalletSnapshot:
    buckets: list[Bucket]
    total: Decimal
    holds: list[Hold]
    as_of: object


def wallet_snapshot(user) -> WalletSnapshot:
    """Every bucket a customer owns, itemised, with its reason attached.

    v1 showed one number. A customer read "رصيدك 10,000", assumed it was his to
    withdraw, and discovered it was pinned to a bid. Here each pot is named, its
    total is the sum of its own entries, and every held riyal points at the
    auction or invoice holding it.
    """
    balances = {
        row["kind"]: row["balance"]
        for row in Account.objects.filter(
            owner=user, kind__in=AccountKind.customer_owned()
        ).values("kind", "balance")
    }
    counts = {
        row["account__kind"]: row["n"]
        for row in Entry.objects.filter(owner=user)
        .values("account__kind")
        .annotate(n=Count("id"))
    }

    buckets = [
        Bucket(
            kind=kind,
            label=AccountKind(kind).label,
            amount=balances.get(kind, ZERO),
            entry_count=counts.get(kind, 0),
        )
        for kind in AccountKind.customer_owned()
    ]
    holds = list(
        Hold.objects.filter(owner=user, state=HoldState.ACTIVE)
        .select_related("auction", "invoice")
        .order_by("-created_at")
    )
    return WalletSnapshot(
        buckets=buckets,
        total=sum((b.amount for b in buckets), start=ZERO),
        holds=holds,
        as_of=timezone.now(),
    )


def statement_entries(user, *, bucket: str | None = None):
    """The customer's own ledger lines, newest first.

    Read straight from :class:`~apps.money.models.Entry` — the numbers on the
    statement are the postings themselves, not a summary computed beside them.
    """
    if bucket is not None and bucket not in AccountKind.customer_owned():
        raise InvalidAmount(
            f"unknown bucket {bucket!r}",
            user_message="نوع الرصيد المطلوب غير معروف.",
            detail={"allowed": list(AccountKind.customer_owned())},
        )

    entries = Entry.objects.filter(owner=user).select_related("transaction", "account")
    if bucket is not None:
        entries = entries.filter(account__kind=bucket)
    return entries.order_by("-transaction__occurred_at", "-id")


# ---------------------------------------------------------------------------
# Card top-up — intent, then return, then attribution
# ---------------------------------------------------------------------------


@db_transaction.atomic
def start_topup(
    *,
    user,
    auction=None,
    purpose: str = PaymentPurpose.INSURANCE_DEPOSIT,
    client_key: str | None = None,
) -> PaymentIntent:
    """Write down what this customer is about to pay, before they pay it.

    Two things are decided here and nowhere else: **how much** (from
    :func:`deposit_amount_for`) and **whose** the payment is. The gateway never
    learns our user id and cannot be trusted with it; when the money comes back,
    attribution is a lookup on this row.

    ``client_key`` makes a double-tapped button idempotent. It is namespaced by
    the user, so one customer's key can never address another's intent.
    """
    reference = (
        f"topup-{user.pk}-{hashlib.sha256(client_key.encode()).hexdigest()[:32]}"
        if client_key
        else f"topup-{uuid.uuid4().hex}"
    )

    existing = PaymentIntent.objects.filter(reference=reference).first()
    if existing is not None:
        return existing

    return PaymentIntent.objects.create(
        reference=reference,
        user=user,
        amount=deposit_amount_for(auction=auction),
        currency=settings.CURRENCY,
        purpose=purpose,
        auction=auction,
        gateway=settings.PAYMENT_GATEWAY,
    )


@dataclass(frozen=True)
class GatewayOutcome:
    """What became of a payment the gateway told us about.

    ``disposition`` is deliberately explicit — ``credited``, ``suspense``,
    ``failed`` or ``ignored`` — because Article 2-2 forbids a silent return: the
    caller writes this word, and the reason, onto the stored message.
    """

    disposition: str
    note: str
    transaction: Transaction | None = None
    intent: PaymentIntent | None = None


@db_transaction.atomic
def apply_gateway_payment(
    *,
    reference: str,
    payment_id: str,
    amount: Decimal,
    status_raw: str,
    succeeded: bool,
    gateway: str | None = None,
    occurred_at=None,
) -> GatewayOutcome:
    """Turn one gateway notification into ledger movement, or into suspense.

    The customer is read from the stored intent named by ``reference``. Nothing
    in the caller's payload — no user id, no email, no amount — is allowed to
    decide whose money this is or how much of it there was.

    Three endings, and no fourth:

    * the intent is known and the gateway's amount matches ours → credited;
    * we cannot place it, or the amounts disagree → ``suspense``, kept and
      visible, waiting for a human;
    * the gateway says it did not succeed → recorded, no movement.
    """
    gateway = gateway or settings.PAYMENT_GATEWAY
    intent = PaymentIntent.objects.select_for_update().filter(reference=reference).first()

    if not succeeded:
        if intent is not None:
            intent.state = PaymentIntentState.FAILED
            intent.gateway_payment_id = payment_id or intent.gateway_payment_id
            intent.gateway_status_raw = status_raw
            intent.note = f"البوابة أبلغت بحالة {status_raw!r}"
            intent.save(
                update_fields=[
                    "state",
                    "gateway_payment_id",
                    "gateway_status_raw",
                    "note",
                    "updated_at",
                ]
            )
        return GatewayOutcome(
            disposition="ignored",
            note=f"دفعة غير ناجحة بحالة {status_raw!r}؛ لم تتحرك أي فلوس.",
            intent=intent,
        )

    if intent is None:
        # Money we cannot place. It is kept, not dropped — v1's instinct to
        # discard the unrecognised is exactly how payments went missing.
        txn = receive_unattributed(
            amount=amount,
            source="card",
            reference=payment_id or reference,
            occurred_at=occurred_at,
            memo=f"دفعة بلا نية مسجَّلة (مرجع {reference})",
        )
        return GatewayOutcome(
            disposition="suspense",
            note=(
                f"لا توجد نية دفع بالمرجع {reference}؛ المبلغ {amount} محفوظ في "
                "حساب المعلّق بانتظار إسناده."
            ),
            transaction=txn,
        )

    if amount != intent.amount:
        # We will not guess which number is right. The money is kept whole in
        # suspense and a human decides; crediting either figure silently is how
        # a discrepancy becomes a loss nobody notices.
        txn = receive_unattributed(
            amount=amount,
            source="card",
            reference=payment_id or reference,
            occurred_at=occurred_at,
            memo=f"مبلغ مختلف عن النية {intent.reference}",
        )
        intent.state = PaymentIntentState.DISPUTED
        intent.gateway_payment_id = payment_id or intent.gateway_payment_id
        intent.gateway_status_raw = status_raw
        intent.note = f"البوابة أبلغت {amount} والنية {intent.amount}"
        intent.save(
            update_fields=[
                "state",
                "gateway_payment_id",
                "gateway_status_raw",
                "note",
                "updated_at",
            ]
        )
        return GatewayOutcome(
            disposition="suspense",
            note=(
                f"المبلغ العائد {amount} لا يطابق النية {intent.amount}؛ حُفظ في "
                "حساب المعلّق ولم يُنسب."
            ),
            transaction=txn,
            intent=intent,
        )

    # `credit_payment`, not `deposit_insurance`: this very payment may already
    # be sitting in suspense from an earlier delivery that arrived before the
    # intent was visible, and the customer must be credited once either way.
    txn = credit_payment(
        user=intent.user,
        amount=intent.amount,
        source="card",
        reference=payment_id or reference,
        occurred_at=occurred_at,
        memo=f"شحن تأمين بالبطاقة ({intent.reference})",
    )
    intent.state = PaymentIntentState.SUCCEEDED
    intent.gateway_payment_id = payment_id or intent.gateway_payment_id
    intent.gateway_status_raw = status_raw
    intent.resulting_transaction = txn
    intent.save(
        update_fields=[
            "state",
            "gateway_payment_id",
            "gateway_status_raw",
            "resulting_transaction",
            "updated_at",
        ]
    )
    return GatewayOutcome(
        disposition="credited",
        note=f"نُسبت {intent.amount} إلى صاحب النية {intent.reference}.",
        transaction=txn,
        intent=intent,
    )


# ---------------------------------------------------------------------------
# Refunds — asking, not paying
# ---------------------------------------------------------------------------


@db_transaction.atomic
def request_refund(
    *, user, amount: Decimal, client_key: str | None = None
) -> RefundRequest:
    """Queue a refund of the customer's *free* insurance.

    Only ``insurance_free`` can leave. Money held for a live auction or locked
    against an unpaid invoice is not in that bucket, so a debtor's request fails
    on the same arithmetic every other withdrawal fails on. There is no "is this
    customer a debtor?" gate here on purpose: a gate is a rule someone can
    forget to call, and in v1 somebody did.

    Nothing is posted. The ledger moves when the payout is confirmed through the
    inbound path, never on our own optimism.

    Because nothing is posted, the balance this checks against does not move
    either — so *checking* it was never enough. Ten requests with ten different
    idempotency keys each passed the same check against the same untouched
    10,000 and instructed accounting to pay out 100,000 against one deposit,
    which is the shape of the v1 duplicate-refund incident the outbox exists to
    prevent. One open request at a time is the answer, and
    ``one_open_refund_request_per_customer`` — not this function — is what
    enforces it (Article 3-3).
    """
    if amount is None or amount <= ZERO:
        raise InvalidAmount(
            f"refund amount {amount!r}",
            user_message="مبلغ الاسترداد لازم يكون أكبر من صفر.",
        )

    reference = (
        f"refund-{user.pk}-{hashlib.sha256(client_key.encode()).hexdigest()[:32]}"
        if client_key
        else f"refund-{uuid.uuid4().hex}"
    )
    existing = RefundRequest.objects.filter(reference=reference).first()
    if existing is not None:
        return existing

    # The `insurance_free` row lock, taken for the reason every other
    # withdrawal takes it: the decision below and the row it writes must not
    # straddle another request reading the same balance.
    _lock_free_insurance(user)

    open_request = RefundRequest.objects.filter(
        user=user, state__in=RefundRequestState.open_states()
    ).first()
    if open_request is not None:
        raise MoneyError(
            f"user {user.pk} already has refund request {open_request.pk} open",
            user_message=(
                f"لديك طلب استرداد قائم بمبلغ {open_request.amount} ريال. "
                "انتظر تنفيذه أو ألغه قبل طلب استرداد آخر."
            ),
            detail={
                "open_request": open_request.reference,
                "open_amount": str(open_request.amount),
                "open_state": open_request.state,
            },
        )

    free = account_for(user, AccountKind.INSURANCE_FREE)
    if amount > free.balance:
        held = account_for(user, AccountKind.INSURANCE_HELD).balance
        locked = account_for(user, AccountKind.INSURANCE_LOCKED).balance
        raise InsufficientFunds(
            free,
            free.balance,
            amount,
            user_message=(
                f"لا يمكن استرداد {amount} ريال. المتاح للاسترداد {free.balance} ريال "
                f"فقط؛ لديك {locked} ريال مقفولة على مستحقات و{held} ريال محجوزة "
                "لمزادات."
            ),
            detail={
                "requested": str(amount),
                "available": str(free.balance),
                "locked_for_dues": str(locked),
                "held_for_auctions": str(held),
            },
        )

    from apps.odoo.models import OutboxMessage

    outbox = OutboxMessage.objects.create(
        endpoint="refund.request",
        reference=f"refund:{reference}",
        payload={
            "reference": reference,
            "user": user.pk,
            "amount": str(amount),
            "currency": settings.CURRENCY,
        },
    )
    return RefundRequest.objects.create(
        user=user, amount=amount, reference=reference, outbox_message=outbox
    )


# ---------------------------------------------------------------------------
# Paying for what you bought
# ---------------------------------------------------------------------------


class InvoiceNotPayable(MoneyError):
    code = "invoice_not_payable"
    default_message = "هذه الفاتورة غير قابلة للسداد الآن."


class UnsupportedPaymentMethod(MoneyError):
    code = "unsupported_payment_method"
    default_message = "طريقة السداد هذه غير مدعومة."


@db_transaction.atomic
def pay_invoice_from_balance(
    *,
    user,
    invoice: Invoice,
    method: str = PaymentMethod.BALANCE,
    reference: str | None = None,
    occurred_at=None,
) -> Transaction:
    """Settle an invoice from the customer's own money.

    Named apart from :func:`record_payment` because they are different acts.
    This one is a customer pressing "pay" and is the whole transaction: it
    decides, moves, and settles. ``record_payment`` books money that has
    already arrived from somewhere else — cash at the counter, a card, the
    accounting system telling us a bank transfer cleared — and takes the
    amount and the source as facts. Both existed under one name after the
    merge, and Python kept whichever was defined last.

    The invoice's own lock is spent first — that is what it was locked for — and
    the remainder comes from free insurance. Both steps are ordinary postings:
    the lock is released back to ``insurance_free``, then one
    ``invoice_payment`` moves the whole outstanding amount to revenue. Splitting
    it this way keeps every hold whole, so ``verify_ledger`` still recognises
    every locked riyal between the two steps.

    A bank transfer is settled by the accounting system when the bank confirms
    it, not here; and a card never settles a purchase at all.
    """
    if invoice.customer_id != user.pk:
        raise InvoiceNotPayable(
            f"invoice {invoice.pk} does not belong to user {user.pk}",
            user_message="هذه الفاتورة ليست فاتورتك.",
        )
    if method != PaymentMethod.BALANCE:
        raise UnsupportedPaymentMethod(
            f"method {method!r} is not settled by this endpoint",
            user_message=(
                "السداد من هنا يتم من الرصيد فقط. التحويل البنكي يُسجَّل عند تأكيده "
                "من الحساب البنكي."
            ),
            detail={"method": method},
        )

    # The row the caller handed us was read when the request arrived, and an
    # Odoo webhook may have settled the invoice since. Take the same lock
    # `record_payment` takes and decide from the row under it: without this,
    # `outstanding` was computed from a stale `amount_paid`, a second full
    # payment went to revenue, and the write-back overwrote the webhook's —
    # 20,000 taken for a 10,000 invoice that then read exactly 10,000 paid.
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)

    reference = reference or f"balance:{invoice.pk}"
    key = f"invoice-payment:{invoice.number}:{reference}"
    already = Transaction.objects.filter(idempotency_key=key).first()
    if already is not None:
        return already

    outstanding = invoice.outstanding
    if invoice.state == InvoiceState.CANCELLED or outstanding <= ZERO:
        raise InvoiceNotPayable(
            f"invoice {invoice.number} has nothing outstanding",
            user_message="لا يوجد مبلغ مستحق على هذه الفاتورة.",
            detail={"invoice": invoice.number, "outstanding": str(outstanding)},
        )

    holds = list(
        Hold.objects.filter(
            owner=user, invoice=invoice, state=HoldState.ACTIVE
        ).select_for_update()
    )
    locked = sum((h.amount for h in holds), start=ZERO)
    free = account_for(user, AccountKind.INSURANCE_FREE)

    if free.balance + locked < outstanding:
        raise InsufficientFunds(
            free,
            # What can actually go to this invoice is the free balance plus the
            # lock already standing against it — not the free balance alone.
            free.balance + locked,
            outstanding,
            user_message=(
                f"رصيدك لا يكفي لسداد {outstanding} ريال. المتاح {free.balance} ريال "
                f"والمقفول على هذه الفاتورة {locked} ريال."
            ),
            detail={
                "invoice": invoice.number,
                "outstanding": str(outstanding),
                "available": str(free.balance),
                "locked_for_this_invoice": str(locked),
            },
        )

    for hold in holds:
        release_hold(hold, memo=f"فك القفل لسداد الفاتورة {invoice.number}")

    txn = post(
        kind=TransactionKind.INVOICE_PAYMENT,
        idempotency_key=key,
        occurred_at=occurred_at,
        memo=f"سداد الفاتورة {invoice.number} من الرصيد",
        legs=[
            Leg(account_for(user, AccountKind.INSURANCE_FREE), -outstanding),
            Leg(system_account(AccountKind.REVENUE), outstanding),
        ],
    )

    invoice.amount_paid = invoice.amount_paid + outstanding
    # `derive_invoice_state` and nothing else. The branch that stood here
    # agreed with it only by luck — it knew neither CANCELLED nor DRAFT — and
    # two ways of deriving one column is exactly how v1 made an invoice read
    # one state when the customer paid it and another when Odoo did.
    invoice.state = derive_invoice_state(invoice)
    invoice.save(update_fields=["amount_paid", "state", "updated_at"])
    return txn


# ---------------------------------------------------------------------------
# Invoices — the state is derived, and the payment is what derives it
# ---------------------------------------------------------------------------


def derive_invoice_state(invoice: Invoice) -> str:
    """What this invoice's state *is*, computed from its own numbers.

    One function, called after every payment, and the only thing allowed to
    decide this field. In v1 the column was written once at insert and never
    again, so every mirrored invoice read `draft` forever and nothing could
    safely branch on it — including the refund gate that was supposed to stop
    a debtor withdrawing their deposit.

    Odoo's own word lives in `odoo_state_raw` and is never consulted here. It
    is evidence about what they think, not a fact about what we are owed.
    """
    if invoice.state == InvoiceState.CANCELLED:
        return InvoiceState.CANCELLED
    if invoice.amount_paid <= ZERO:
        # Nothing paid yet. A draft stays a draft until someone issues it;
        # anything already issued is simply outstanding.
        return (
            InvoiceState.DRAFT
            if invoice.state == InvoiceState.DRAFT
            else InvoiceState.OPEN
        )
    if invoice.amount_paid >= invoice.amount:
        return InvoiceState.PAID
    return InvoiceState.PARTIAL


@db_transaction.atomic
def record_payment(
    *,
    invoice: Invoice,
    amount: Decimal,
    source: str,
    reference: str,
    occurred_at=None,
    by=None,
) -> Transaction:
    """Record money paid against an invoice, and re-derive what that leaves.

    The movement, the new `amount_paid`, the new state, and the release of any
    insurance the debt was holding all happen inside one atomic block. Half of
    that landing without the other half is how a paid customer keeps a locked
    deposit, or an unpaid one gets it back.

    `source` is where the money comes from:

    * ``insurance`` — the deposit we are already holding for this debt
    * ``cash`` / ``card`` — a fresh payment from outside the platform
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    key = f"payment:{invoice.pk}:{reference}"

    # `post` is idempotent, but `amount_paid` is not: without this the replay
    # of a webhook would move no money and still add to the paid total, so the
    # invoice would read `paid` while the ledger showed nothing paid. The
    # cached column has to be as replay-proof as the movement it summarises.
    already = _find_by_key(key)
    if already is not None:
        log.info("record_payment: %s already recorded as txn %s", key, already.pk)
        return already

    if invoice.state == InvoiceState.CANCELLED:
        raise MoneyError(f"الفاتورة {invoice.number} ملغاة، فلا تُسدَّد")
    if amount <= ZERO:
        raise MoneyError("مبلغ السداد يجب أن يكون أكبر من صفر")
    if amount > invoice.outstanding:
        raise MoneyError(f"المطلوب سداده {invoice.outstanding} والمبلغ {amount} أكبر منه")

    revenue = system_account(AccountKind.REVENUE)
    if source == "insurance":
        from_account = account_for(invoice.customer, AccountKind.INSURANCE_LOCKED)
    elif source in ("cash", "card"):
        from_account = system_account(
            AccountKind.EXTERNAL_CASH if source == "cash" else AccountKind.EXTERNAL_CARD
        )
    else:
        raise MoneyError(f"مصدر سداد غير معروف: {source!r}")

    txn = post(
        kind=TransactionKind.INVOICE_PAYMENT,
        idempotency_key=key,
        occurred_at=occurred_at,
        memo=f"سداد على الفاتورة {invoice.number}",
        created_by=by,
        legs=[Leg(from_account, -amount), Leg(revenue, amount)],
    )

    if source == "insurance":
        _consume_locked_claim(invoice, amount, txn)

    invoice.amount_paid = invoice.amount_paid + amount
    invoice.state = derive_invoice_state(invoice)
    invoice.save(update_fields=["amount_paid", "state", "updated_at"])

    if invoice.state == InvoiceState.PAID:
        _release_holds_on(invoice)

    return txn


def _consume_locked_claim(invoice: Invoice, amount: Decimal, txn: Transaction) -> None:
    """Shrink the locks by what this payment just took out of ``insurance_locked``.

    A hold is a claim on money that is *there*. Spending the locked bucket
    without shrinking the claim leaves a hold asserting more than the bucket
    holds, and every consequence of that gap is a real refusal:

    * ``verify_ledger`` reports the drift as an unexplained bucket;
    * ``_release_holds_on`` later releases the hold's original figure out of a
      bucket that now holds less, ``post`` refuses, and the whole settling
      payment — a legitimate one — rolls back;
    * ``lock_for_invoice`` finds the exhausted hold still ACTIVE and hands it
      back having locked nothing.

    A fully spent hold keeps its ``amount`` — ``hold_is_positive`` forbids zero,
    and the figure is the record of what the claim was worth — and says it is
    over in its state, naming the transaction that ended it.
    """
    remaining = amount
    holds = (
        Hold.objects.select_for_update()
        .filter(invoice=invoice, state=HoldState.ACTIVE, reason=HoldReason.DUES)
        .order_by("pk")
    )
    for hold in holds:
        if remaining <= ZERO:
            break
        taken = min(hold.amount, remaining)
        remaining -= taken
        if taken >= hold.amount:
            hold.state = HoldState.CONSUMED
            hold.ended_by_transaction = txn
            hold.ended_at = timezone.now()
            hold.save(update_fields=["state", "ended_by_transaction", "ended_at"])
        else:
            hold.amount = hold.amount - taken
            hold.save(update_fields=["amount"])


def _release_holds_on(invoice: Invoice) -> None:
    """The debt is settled, so whatever it was holding is the customer's again.

    Paying from the locked bucket has already emptied it; releasing then moves
    nothing and the hold is simply marked consumed. Paying from outside leaves
    the deposit intact and this is what hands it back. Either way the customer
    is never left owing nothing while we still hold their money.
    """
    for hold in Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE):
        remaining = account_for(hold.owner, AccountKind.INSURANCE_LOCKED).balance
        if remaining <= ZERO:
            hold.state = HoldState.CONSUMED
            hold.ended_at = timezone.now()
            hold.save(update_fields=["state", "ended_at"])
            continue
        release_hold(hold, memo=f"سُدِّدت الفاتورة {invoice.number}")


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

    It is also the one movement that writes an :class:`~apps.core.models.AuditLog`
    row. The transaction already carries `created_by` and `memo`, but a dispute
    asks what the hold *was* before it was taken, and that is the before/after
    the audit row holds. The `TODO` that stood here said "once
    `apps.core.audit.record` exists"; it existed from the day core merged, and a
    TODO in a docstring fails no CI step, so the condition came due and nothing
    said so.
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
    audited = ("state", "amount", "reason", "auction_id", "invoice_id")
    before = audit.snapshot(hold, audited)

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

    audit.record(
        action="money.confiscate",
        entity=hold,
        actor=by,
        before=before,
        after=audit.snapshot(hold, audited),
        note=f"{reason.strip()}" + (f" — {memo}" if memo else ""),
    )
    return txn
