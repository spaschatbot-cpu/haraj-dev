"""Interpreting what Odoo said, separately from receiving it.

This runs after the message is safely stored, and it can run again. Every path
through it ends in one of exactly three states, each with a written reason:

* ``processed`` — we understood it and acted
* ``ignored``   — we understood it and deliberately did nothing
* ``failed``    — we did not understand it, or acting raised

There is no fourth ending and no silent ``return``. Article 2-2 exists because
in v1 a branch that fell off the end left a message looking untouched, and
nobody could tell "we decided not to" from "we never got there".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db import transaction as db_transaction
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    AccountKind,
    Invoice,
    InvoiceSource,
    InvoiceState,
    RefundRequest,
    RefundRequestState,
    Transaction,
    TransactionKind,
)

from .models import CustomerLink, InboundMessage, InboundState, RefundShortfall

log = logging.getLogger(__name__)

#: How long after a payment a refund of the same amount makes replaying that
#: payment suspect. Generous on purpose: the v1 case was same-day, but a
#: refund three days later says just as clearly that the money went back.
REFUND_LOOKBACK_DAYS = 30


@dataclass(frozen=True)
class Outcome:
    """What interpreting a message concluded. Never constructed without a note."""

    state: str
    note: str
    transaction: Transaction | None = None

    def __post_init__(self):
        if not self.note.strip():
            raise ValueError("every outcome states its reason")


#: The only source whose messages this module may interpret.
#:
#: `InboundMessage` is a shared table — the payment gateway writes to it too —
#: and every handler below reads `payload` as though Odoo wrote it. Nothing
#: stops a *different* sender's body from carrying `event: "payment.posted"`
#: and a `customer_id`, so the source is checked here rather than assumed.
INTERPRETED_SOURCE = "odoo"


def process(message: InboundMessage) -> InboundMessage:
    """Interpret one stored message and record what came of it.

    Safe to call again on anything. A message that already reached a terminal
    state is returned untouched, which is what lets the retry task, the admin
    replay button, and a manual shell call all use this same function.

    **Two things it refuses to interpret at all**, and both refusals are the
    fix for one exploitable path found in T913's sweep:

    * a message whose **signature did not verify**. It is stored — Article 2-2
      — but a body nobody vouched for must never reach a handler that moves
      money. In v1's shape of this bug the forged body was parked in `failed`,
      which is the retry queue, so the retry cron interpreted it a minute later
      as though it had been signed.
    * a message from **any source but Odoo**. The table is shared, the handlers
      below read Odoo's field names, and a payment-gateway body that happens to
      carry `event: "payment.posted"` would otherwise be routed straight into
      :func:`_handle_payment`.

    Neither refusal is silent (Article 2-2), and neither leaves the message in
    a state the retry queue picks up — so a forged body is not re-offered every
    minute forever. They differ in *where* the reason is written: the unsigned
    one already carries the boundary's note and its own state, and re-saving it
    here would only spend an attempt on a message no attempt can help; the
    foreign-source one is being judged for the first time, so it is written
    down here.
    """
    if message.state in (InboundState.PROCESSED, InboundState.IGNORED):
        log.info("process: message %s already %s", message.pk, message.state)
        return message

    if message.state == InboundState.REJECTED_SIGNATURE:
        log.warning("process: refused to interpret unsigned message %s", message.pk)
        return message

    if message.source != INTERPRETED_SOURCE:
        return _finish(
            message,
            Outcome(
                InboundState.IGNORED,
                f"رسالة من مصدر {message.source!r} لا يفسّرها مسار أودو",
            ),
        )

    try:
        outcome = _interpret(message)
    except Exception as exc:  # noqa: BLE001 — a failure here is data, not a crash
        log.exception("process: message %s raised", message.pk)
        outcome = Outcome(InboundState.FAILED, f"{type(exc).__name__}: {exc}")

    return _finish(message, outcome)


def _finish(message: InboundMessage, outcome: Outcome) -> InboundMessage:
    """The single place a message's state is written."""
    message.state = outcome.state
    message.note = outcome.note
    message.attempts += 1
    message.resulting_transaction = outcome.transaction
    if outcome.state in (InboundState.PROCESSED, InboundState.IGNORED):
        message.processed_at = timezone.now()
    message.save(
        update_fields=[
            "state",
            "note",
            "attempts",
            "resulting_transaction",
            "processed_at",
        ]
    )
    log.info("process: message %s -> %s (%s)", message.pk, outcome.state, outcome.note)
    return message


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


def _interpret(message: InboundMessage) -> Outcome:
    """Route by event, and refuse to guess at anything unrecognised.

    An unknown event is `ignored` with its name written down, not `failed`:
    failing would put it in the retry queue forever, and retrying will not
    teach us what `sale.order.confirmed` means. Someone reads the inbox,
    decides, and adds a branch.
    """
    handlers = {
        "payment.posted": _handle_payment,
        "payment.updated": _handle_payment,
        "invoice.posted": _handle_invoice,
        "invoice.updated": _handle_invoice,
        "refund.confirmed": _handle_refund,
    }
    handler = handlers.get(message.event)
    if handler is None:
        return Outcome(
            InboundState.IGNORED,
            f"حدث غير معروف: {message.event!r} — لا يوجد فرع يعالجه",
        )
    return handler(message)


@db_transaction.atomic
def _handle_payment(message: InboundMessage) -> Outcome:
    """A customer paid Odoo. It becomes insurance, and may settle an invoice.

    Odoo sends this twice for one payment: `posted` carries no invoice link,
    and `updated` carries it later. Both arrive here; the idempotency key is
    the payment's own id, so the second one credits nothing and only does the
    linking work that the first could not.
    """
    payload = message.payload
    payment_id = str(payload.get("payment_id") or payload.get("id") or "")
    if not payment_id:
        return Outcome(InboundState.FAILED, "رسالة دفعة بلا معرّف دفعة")

    amount, error = _amount(payload)
    if amount is None:
        return Outcome(InboundState.FAILED, error)

    odoo_customer = str(payload.get("customer_id") or payload.get("partner_id") or "")
    user, link_note = _resolve_customer(odoo_customer)

    # Built by the money layer, not restated here: a caller that spells the
    # key out itself is a second definition that drifts the day the format
    # changes (Article 4-5).
    reference = f"odoo:{payment_id}"
    already = services.find_transaction(services.deposit_key("cash", reference))

    if user is None:
        # A suspense receipt lives in its own key namespace, so this asks about
        # the receipt itself and not about a deposit that was never made.
        in_suspense = services.find_transaction(services.suspense_key("cash", reference))
        if in_suspense is not None:
            return Outcome(
                InboundState.PROCESSED,
                f"دفعة {payment_id} مسجَّلة سابقاً في المعلّق — {link_note}",
                in_suspense,
            )
        if already is not None:
            return Outcome(
                InboundState.PROCESSED,
                f"دفعة {payment_id} مقيَّدة سابقاً — {link_note}",
                already,
            )
        # Article 2-2 and the suspense rule: money we cannot place is kept,
        # never dropped and never attributed to a guess.
        txn = services.receive_unattributed(
            amount=amount,
            source="cash",
            reference=reference,
            memo=f"دفعة أودو {payment_id} بلا عميل معروف",
        )
        return Outcome(
            InboundState.PROCESSED,
            f"وصلت إلى المعلّق — {link_note}",
            txn,
        )

    if already is None:
        blocked = _refunded_since(user, amount, message)
        if blocked is not None:
            return Outcome(InboundState.IGNORED, blocked)

        # `credit_payment`, not `deposit_insurance`: `posted` may have arrived
        # before the customer was linked and put this very payment in suspense,
        # and `updated` must move that money to them rather than post a second
        # deposit for one payment.
        txn = services.credit_payment(
            user=user,
            amount=amount,
            source="cash",
            reference=reference,
            memo=f"دفعة أودو {payment_id}",
        )
    else:
        txn = already

    invoice_ref = payload.get("invoice_id")
    if not invoice_ref:
        return Outcome(
            InboundState.PROCESSED,
            f"دفعة {payment_id} قُيّدت كتأمين؛ لا فاتورة مرفقة بعد",
            txn,
        )

    settled = _settle_invoice_from_deposit(user, str(invoice_ref), amount, payment_id)
    return Outcome(InboundState.PROCESSED, settled, txn)


def _settle_invoice_from_deposit(
    user, invoice_ref: str, amount: Decimal, payment_id: str
) -> str:
    """The invoice link arrived. Apply the deposit we are already holding.

    This is the third message in the v1 sequence — the one a deduplication
    rule swallowed, leaving a settled deposit showing as refundable for
    weeks. Here it is what closes the loop: lock what the debt claims, pay it
    from the lock, and let `record_payment` release whatever is left over.
    """
    invoice = Invoice.objects.filter(odoo_invoice_id=invoice_ref).first()
    if invoice is None:
        # Not a failure: the invoice message may simply not have arrived yet,
        # and this one is already recorded as insurance. Saying so plainly is
        # better than retrying against an invoice that does not exist.
        return (
            f"دفعة {payment_id} قُيّدت كتأمين؛ الفاتورة {invoice_ref} لم تصلنا بعد فلم تُسوَّ"
        )
    if invoice.state == InvoiceState.CANCELLED:
        return f"دفعة {payment_id} قُيّدت كتأمين؛ الفاتورة {invoice_ref} ملغاة"
    if invoice.outstanding <= Decimal("0.00"):
        return f"دفعة {payment_id} قُيّدت كتأمين؛ الفاتورة {invoice_ref} مسدَّدة"

    services.lock_for_invoice(user=user, invoice=invoice)
    payable = min(amount, invoice.outstanding)
    services.record_payment(
        invoice=invoice,
        amount=payable,
        source="insurance",
        reference=f"odoo:{payment_id}",
    )
    return f"دفعة {payment_id} سدَّدت {payable} على الفاتورة {invoice_ref}"


def _handle_invoice(message: InboundMessage) -> Outcome:
    """Mirror an invoice, keeping Odoo's own word beside our derived state.

    `odoo_state_raw` takes whatever string they send, including one we have
    never seen. Nothing branches on it. In v1 an enum column rejected an
    unfamiliar value and rolled back the entire insert, so the webhook looked
    stopped while it was working perfectly (Article 2-3).
    """
    payload = message.payload
    invoice_ref = str(payload.get("invoice_id") or payload.get("id") or "")
    if not invoice_ref:
        return Outcome(InboundState.FAILED, "رسالة فاتورة بلا معرّف فاتورة")

    amount, error = _amount(payload)
    if amount is None:
        return Outcome(InboundState.FAILED, error)

    odoo_customer = str(payload.get("customer_id") or payload.get("partner_id") or "")
    user, link_note = _resolve_customer(odoo_customer)
    if user is None:
        return Outcome(
            InboundState.FAILED,
            f"فاتورة {invoice_ref} لعميل غير مربوط — {link_note}",
        )

    raw_state = str(payload.get("state", ""))[:64]
    invoice = Invoice.objects.filter(odoo_invoice_id=invoice_ref).first()
    if invoice is None:
        invoice = Invoice.objects.create(
            customer=user,
            number=str(payload.get("number") or f"ODOO/{invoice_ref}")[:64],
            amount=amount,
            odoo_invoice_id=invoice_ref,
            odoo_state_raw=raw_state,
            state=InvoiceState.OPEN,
            # Theirs, so the amount already carries the tax. Saying so here is
            # what stops it being taxed a second time (HR-05).
            source=InvoiceSource.ODOO_SYNC,
            issued_at=timezone.now(),
        )
        return Outcome(
            InboundState.PROCESSED,
            f"أُنشئت الفاتورة {invoice.number} بمبلغ {amount} "
            f"(حالة أودو المحفوظة: {raw_state!r})",
        )

    if amount < invoice.amount_paid:
        # Odoo lowering an invoice below what has already been paid against it
        # would erase real dues without a reversing entry: `outstanding` clamps
        # at zero, `derive_invoice_state` reads PAID, and the difference simply
        # disappears from every report. The schema refuses it too
        # (`invoice_paid_not_above_amount`); this is what makes the refusal a
        # sentence a person can act on rather than an IntegrityError.
        return Outcome(
            InboundState.FAILED,
            f"الفاتورة {invoice.number}: أودو تقول {amount} والمسدَّد عندنا "
            f"{invoice.amount_paid} — تخفيضها تحت المسدَّد يحتاج قيداً عاكساً "
            "وقراراً بشرياً",
        )

    invoice.odoo_state_raw = raw_state
    invoice.amount = amount
    invoice.state = services.derive_invoice_state(invoice)
    invoice.save(update_fields=["odoo_state_raw", "amount", "state", "updated_at"])
    return Outcome(
        InboundState.PROCESSED,
        f"حُدّثت الفاتورة {invoice.number} (حالة أودو المحفوظة: {raw_state!r})",
    )


@db_transaction.atomic
def _handle_refund(message: InboundMessage) -> Outcome:
    """Odoo confirmed a refund. Only a confirmed one moves our ledger.

    Atomic like its payment sibling: the posting and the closing of the request
    that asked for it are one fact, and half of it landing would leave a
    customer poorer with a request still reading «مُقدَّم» — and, because one
    open request is all a customer may have, unable to ask for anything else.
    """
    payload = message.payload
    refund_id = str(payload.get("refund_id") or payload.get("id") or "")
    if not refund_id:
        return Outcome(InboundState.FAILED, "رسالة استرداد بلا معرّف")

    amount, error = _amount(payload)
    if amount is None:
        return Outcome(InboundState.FAILED, error)

    odoo_customer = str(payload.get("customer_id") or payload.get("partner_id") or "")
    user, link_note = _resolve_customer(odoo_customer)
    if user is None:
        return Outcome(
            InboundState.FAILED, f"استرداد {refund_id} لعميل غير مربوط — {link_note}"
        )

    shortfall = _shortfall_if_pledged(message, user, amount, refund_id)
    if shortfall is not None:
        return shortfall

    txn = services.refund_insurance(
        user=user,
        amount=amount,
        reference=f"odoo:{refund_id}",
        memo=f"استرداد أودو {refund_id}",
    )
    closed = _close_refund_request(user, payload, txn)
    return Outcome(
        InboundState.PROCESSED, f"استُرد {amount} للعميل {user.pk}{closed}", txn
    )


def _shortfall_if_pledged(
    message: InboundMessage, user, amount: Decimal, refund_id: str
) -> Outcome | None:
    """Refuse a payout the free bucket cannot answer, and open a case for it.

    ``PHASE_02`` §4-3, and the incident behind it: v1 paid back a deposit that
    was securing a car the customer had already won **and collected**, "مما ترك
    الشركة دون أي غطاء قانوني أو مالي".

    The ledger would refuse this on its own — the free bucket is empty and the
    CHECK stops the posting. That refusal is not enough. It arrives as one more
    `failed` message carrying an arithmetic sentence, and nothing says a car may
    be uncovered. Article 2-2 draws the line this sits on: a message refused
    **on purpose** is `ignored` with a written reason, and this writes the reason
    into a row somebody reviews rather than into a log line somebody greps.

    Returns ``None`` when the money is genuinely free, and the caller pays out.
    """
    free = services.account_for(user, AccountKind.INSURANCE_FREE).balance
    if free >= amount:
        return None

    held = services.account_for(user, AccountKind.INSURANCE_HELD).balance
    locked = services.account_for(user, AccountKind.INSURANCE_LOCKED).balance
    short = amount - free

    case, created = RefundShortfall.objects.get_or_create(
        refund_ref=f"odoo:{refund_id}",
        defaults={
            "message": message,
            "user": user,
            "requested": amount,
            "free": free,
            "held": held,
            "locked": locked,
            "shortfall": short,
            "note": (
                f"طلب أودو استرداد {amount} والمتاح {free}. "
                f"المحجوز {held} والمرهون {locked} — لا يُسحب المرهون آلياً."
            ),
        },
    )
    again = "" if created else " (طلبٌ مكرَّر — القضية مفتوحة أصلاً)"
    log.info(
        "refund %s short by %s for user %s — case %s%s",
        refund_id,
        short,
        user.pk,
        case.pk,
        again,
    )
    return Outcome(
        InboundState.IGNORED,
        f"استرداد {refund_id}: المتاح {free} والمطلوب {amount} — "
        f"فُتحت قضية عجز #{case.pk} ولم يُنفَّذ شيء{again}",
    )


def _close_refund_request(user, payload: dict, txn: Transaction) -> str:
    """Mark the request this payout answers as executed, and say which one.

    Nothing else in the tree ever advanced a `RefundRequest` past `requested`,
    so a customer's request read «مُقدَّم» forever after the money had already
    left — and the `a_confirmed_refund_names_its_transaction` CHECK, the
    schema's expression of Article 1-6, was unreachable.

    Odoo echoes our own reference back; matching on it rather than on the
    amount is deliberate, because two requests for the same figure are
    indistinguishable by amount and guessing between them is how v1 closed the
    wrong one.
    """
    reference = str(payload.get("reference") or "")
    if not reference:
        return " — بلا مرجع طلب، فلم يُغلق أي طلب"

    request = (
        RefundRequest.objects.select_for_update()
        .filter(user=user, reference=reference)
        .first()
    )
    if request is None:
        return f" — لا يوجد طلب بالمرجع {reference!r}"
    if request.state == RefundRequestState.CONFIRMED:
        return f" — الطلب {reference} كان منفَّذاً بالفعل"

    request.state = RefundRequestState.CONFIRMED
    request.resulting_transaction = txn
    request.save(update_fields=["state", "resulting_transaction", "updated_at"])
    return f" — أُغلق الطلب {reference}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _amount(payload: dict) -> tuple[Decimal | None, str]:
    """Read a money field as Decimal, never as float (Article 3-2)."""
    raw = payload.get("amount")
    if raw is None:
        return None, "الرسالة بلا مبلغ"
    try:
        amount = Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return None, f"مبلغ غير صالح: {raw!r}"
    if amount <= Decimal("0.00"):
        return None, f"مبلغ غير موجب: {amount}"
    return amount, ""


def _resolve_customer(odoo_customer_id: str):
    """Find whose money this is — by an explicit link, or not at all.

    No fallback to matching on phone or name. In v1 one placeholder row with
    an empty phone matched everybody, and a unique index on phone meant the
    whole safety net keyed off it went down with it (T218).
    """
    if not odoo_customer_id:
        return None, "الرسالة بلا معرّف عميل أودو"

    link = (
        CustomerLink.objects.filter(odoo_customer_id=odoo_customer_id, is_primary=True)
        .select_related("user")
        .first()
    )
    if link is not None:
        return link.user, f"عميل أودو {odoo_customer_id} مربوط بالحساب {link.user_id}"

    if CustomerLink.objects.filter(odoo_customer_id=odoo_customer_id).exists():
        # Links exist but none is primary. Choosing one is a human decision:
        # picking the newest, or the first, is exactly the guess that debited
        # 20,000 twice.
        return None, (
            f"عميل أودو {odoo_customer_id} له روابط بلا حساب أساسي — يحتاج قراراً بشرياً"
        )

    return None, f"عميل أودو {odoo_customer_id} غير مربوط بأي حساب"


def _refunded_since(user, amount: Decimal, message: InboundMessage) -> str | None:
    """Refuse to replay a payment the customer has since been refunded.

    A payment that failed to record is not automatically still owed. In v1 a
    replay recreated a 10,000 charge on a customer who had already had that
    exact amount returned, turning a fixed bug into a fresh debt.

    Returns the reason to ignore, or None when replaying is safe.
    """
    since = message.received_at or timezone.now()
    refunded = Transaction.objects.filter(
        kind=TransactionKind.INSURANCE_REFUND,
        entries__owner=user,
        occurred_at__gte=since,
        occurred_at__lte=since + timezone.timedelta(days=REFUND_LOOKBACK_DAYS),
    ).distinct()

    for candidate in refunded:
        if candidate.total == amount:
            return (
                f"لم تُعَد المحاولة: العميل استُرد له {amount} بالمعاملة "
                f"{candidate.pk} بعد وصول هذه الرسالة — "
                f"إعادة التقييد كانت ستصنع ديناً جديداً"
            )
    return None
