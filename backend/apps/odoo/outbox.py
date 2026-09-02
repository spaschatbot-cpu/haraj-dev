"""Everything we owe Odoo, written down before we try to send it.

No caller reaches Odoo directly. A decision that needs to reach them becomes a
row here, and one worker drains the table. That indirection is what makes a
retry safe: the row carries a reference Odoo treats as unique, so sending it
twice cannot act twice.

v1's retry cron had no such reference and opened a second refund on a
customer's account — the same customer then saw three refund requests, two
theirs and one ours.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.money.models import Invoice, Transaction

from .client import OdooUnreachable, call
from .models import OutboxMessage, OutboxState

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
BACKOFF_MINUTES = [1, 5, 25, 125, 360, 720, 1440, 1440]


def enqueue(
    *,
    endpoint: str,
    payload: dict,
    reference: str,
    source_transaction: Transaction | None = None,
) -> OutboxMessage:
    """Record an intention to tell Odoo something.

    The reference is unique in this table, so queuing the same intention twice
    returns the existing row rather than creating a second one. Two callers
    racing to record the same decision is ordinary; two rows would mean two
    calls to Odoo.
    """
    try:
        with db_transaction.atomic():
            return OutboxMessage.objects.create(
                endpoint=endpoint,
                payload=payload,
                reference=reference,
                source_transaction=source_transaction,
            )
    except IntegrityError:
        existing = OutboxMessage.objects.filter(reference=reference).first()
        if existing is None:
            raise
        log.info("outbox: %s already queued as %s", reference, existing.pk)
        return existing


def payment_reference(invoice: Invoice, payment: Transaction) -> str:
    """The reference Odoo will see for one payment against one invoice.

    Distinct per payment is the whole point. Odoo rejects a second payment
    carrying a reference it has already seen, and in v1 every partial payment on
    an invoice reused the invoice's own memo — 223 attempts across 26 invoices
    were refused for exactly this, and the money sat unapplied while the log
    filled with retries that could never succeed.

    The distinguishing half is the *payment's own identity*, not a position in a
    sequence. A counted sequence was derived from ``COUNT(*)`` taken before the
    insert, so two payments recorded on one invoice at the same moment both read
    the same count, both built ``INV/1/P1``, and :func:`enqueue` — right to
    treat a repeated caller-supplied reference as already queued — handed the
    loser the winner's row and its payload. Our ledger held two payments, Odoo
    heard about one, and nothing was left to replay. Article 1-5 asks for a key
    derived from the event's identity, and ``txn.uuid`` is that identity.
    """
    return f"{invoice.number}/P{payment.uuid}"


def due(now=None) -> list[OutboxMessage]:
    """Queued or failed messages whose backoff has elapsed."""
    now = now or timezone.now()
    candidates = OutboxMessage.objects.filter(
        state__in=[OutboxState.PENDING, OutboxState.FAILED],
        attempts__lt=MAX_ATTEMPTS,
    ).order_by("created_at")

    ready = []
    for message in candidates:
        if message.attempts == 0:
            ready.append(message)
            continue
        index = min(message.attempts, len(BACKOFF_MINUTES) - 1)
        last = message.sent_at or message.created_at
        if last + timedelta(minutes=BACKOFF_MINUTES[index]) <= now:
            ready.append(message)
    return ready


def send(message: OutboxMessage) -> OutboxMessage:
    """Deliver one message, and record honestly what happened.

    The three outcomes are kept apart on purpose:

    * **confirmed** — Odoo took it.
    * **failed** — could not reach them, or they were broken. Retry: the
      unique reference means a second attempt cannot act twice, and *not
      reaching them proves nothing about whether they acted* (Article 2-4).
    * **abandoned** — Odoo considered it and said no. Retrying sends the same
      thing again and gets the same answer, so it stops and waits for a
      person.
    """
    message.attempts += 1
    message.sent_at = timezone.now()
    message.state = OutboxState.SENT
    message.save(update_fields=["attempts", "sent_at", "state"])

    try:
        response = call(message.endpoint, message.payload, reference=message.reference)
    except OdooUnreachable as exc:
        message.state = OutboxState.FAILED
        message.last_error = str(exc)
        message.save(update_fields=["state", "last_error"])
        log.warning("outbox: %s unreachable — %s", message.reference, exc)
        return message
    except Exception as exc:  # noqa: BLE001 — a refusal is data, not a crash
        message.state = (
            OutboxState.ABANDONED if isinstance(exc, ValueError) else OutboxState.FAILED
        )
        message.last_error = f"{type(exc).__name__}: {exc}"
        message.save(update_fields=["state", "last_error"])
        log.error("outbox: %s refused — %s", message.reference, exc)
        return message

    message.state = OutboxState.CONFIRMED
    message.response = response
    message.last_error = ""
    message.save(update_fields=["state", "response", "last_error"])
    log.info("outbox: %s confirmed", message.reference)
    return message


def queue_payment(
    invoice: Invoice, amount: Decimal, *, source_transaction: Transaction
):
    """Tell Odoo about a payment we recorded, with its own reference.

    ``source_transaction`` has no default on purpose: it is what the reference
    is built from, and without it two simultaneous payments on one invoice
    collapse into one message.
    """
    return enqueue(
        endpoint="payments",
        payload={
            "invoice": invoice.odoo_invoice_id or invoice.number,
            # A string, not a float. Article 3-2 does not stop at our boundary.
            "amount": str(amount),
        },
        reference=payment_reference(invoice, source_transaction),
        source_transaction=source_transaction,
    )
