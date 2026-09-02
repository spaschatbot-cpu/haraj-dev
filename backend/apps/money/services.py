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
from django.db import transaction as db_transaction
from django.db.models import Count, Sum
from django.utils import timezone

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
    Transaction,
    TransactionKind,
)

log = logging.getLogger(__name__)


class MoneyError(DomainError):
    """A refused money operation. Always safe to show to a customer.

    It carries its own Arabic sentence and a stable code; turning that into an
    HTTP response is :mod:`apps.core.exceptions`'s job and nobody else's.
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
    code = "insufficient_funds"

    def __init__(
        self,
        account: Account,
        needed: Decimal,
        *,
        user_message: str | None = None,
        detail: dict | None = None,
    ):
        self.account = account
        self.needed = needed
        super().__init__(
            f"{account.kind} for owner {account.owner_id} holds {account.balance}, "
            f"needs {needed}",
            user_message=user_message
            or (
                f"الرصيد المتاح لا يكفي: المتاح {account.balance} ريال "
                f"والمطلوب {needed} ريال."
            ),
            detail=detail
            or {
                "bucket": account.kind,
                "available": str(account.balance),
                "required": str(needed),
            },
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
        # ``reversed_by`` is the reverse side of a OneToOne, so it has no
        # ``_id`` shortcut — reading one raised AttributeError and turned a
        # deliberate refusal into a crash.
        raise MoneyError(
            f"txn {txn.pk} was already reversed by {txn.reversed_by.pk}",
            user_message="هذه الحركة معكوسة من قبل.",
        )

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
    existing = Hold.objects.filter(
        owner=user, auction=auction, state=HoldState.ACTIVE
    ).first()
    if existing is not None:
        return existing

    amount = amount or deposit_amount_for(auction=auction)
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

    txn = deposit_insurance(
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

    free = account_for(user, AccountKind.INSURANCE_FREE)
    if amount > free.balance:
        held = account_for(user, AccountKind.INSURANCE_HELD).balance
        locked = account_for(user, AccountKind.INSURANCE_LOCKED).balance
        raise InsufficientFunds(
            free,
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
def record_payment(
    *,
    user,
    invoice: Invoice,
    method: str = PaymentMethod.BALANCE,
    reference: str | None = None,
    occurred_at=None,
) -> Transaction:
    """Settle an invoice from the customer's own money.

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
    invoice.state = (
        InvoiceState.PAID
        if invoice.amount_paid >= invoice.amount
        else InvoiceState.PARTIAL
    )
    invoice.save(update_fields=["amount_paid", "state", "updated_at"])
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
