"""Interpreting what the payment gateway said, separately from receiving it.

The sibling of `apps.odoo.processing`, and deliberately shaped like it. The two
boundaries share one table (`odoo.InboundMessage`) and nothing else: they read
different field names, they trust different secrets, and neither may interpret
the other's bodies — that last one is T913's third finding, and it is checked
here as it is checked there.

Why this is a module and not a method on `PaymentCallbackView`
--------------------------------------------------------------
Because a stored message has to be interpretable **again**. When it lived on the
view there was exactly one caller — the HTTP request that first delivered the
body — so a gateway message that failed had no way back at all: the retry cron
filters on Odoo's source, and the console's only button called Odoo's
interpreter, which answers a foreign source with `ignored`. `ignored` is
terminal. A real payment could reach the gateway, fail here on a lock timeout,
and then be *ended* by the one button support was given.

So interpretation is a function anything may call on a stored row, and the three
callers — the callback, the console button, and `tasks.retry_failed_gateway` —
all call this one. Same rule as the Odoo boundary: not a copy, not a variant
that skips a check because a human asked this time.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone

from apps.odoo.models import InboundMessage, InboundState

from . import services

log = logging.getLogger(__name__)

#: The only source whose messages this module may interpret. See the module
#: docstring, and `apps.odoo.processing.INTERPRETED_SOURCE` for the mirror.
INTERPRETED_SOURCE = "payment_gateway"

#: The states a message can be interpreted *from*. `received` is the first
#: delivery; `failed` is the retry queue. Everything else is either terminal or
#: evidence nobody vouched for.
INTERPRETABLE = (InboundState.RECEIVED, InboundState.FAILED)


def interpret(message: InboundMessage) -> InboundMessage:
    """Read one stored gateway notification and record what came of it.

    Safe to call again on anything, and safe to call on a row that is not ours.
    Two refusals, and both leave the row **exactly as it was**:

    * a message from any other source. Marking it would be the very bug this
      module exists to fix, in the other direction: an Odoo row ended here is an
      Odoo row `apps.odoo.tasks.due_messages` never offers again.
    * a message whose signature did not verify. It is stored (Article 2-2) and
      interpreted by nothing — T913. A replay button is not an exemption.

    A row that already reached `processed` or `ignored` is returned untouched,
    which is what lets the callback, the console button and the retry task share
    this call.
    """
    if message.source != INTERPRETED_SOURCE:
        log.warning(
            "gateway interpret: refused message %s from source %r",
            message.pk,
            message.source,
        )
        return message

    if message.state == InboundState.REJECTED_SIGNATURE:
        log.warning("gateway interpret: refused unsigned message %s", message.pk)
        return message

    if message.state not in INTERPRETABLE:
        log.info("gateway interpret: message %s already %s", message.pk, message.state)
        return message

    # The stored payload, not the caller's copy of it. The row is the record —
    # on a duplicate delivery the caller holds a body that never became this
    # message, and interpreting that instead would credit against evidence
    # nobody can read back.
    payload = message.payload or {}

    try:
        amount = Decimal(str(payload.get("amount", "0")))
    except (InvalidOperation, ValueError):
        amount = None

    reference = str((payload.get("metadata") or {}).get("reference", ""))
    status_raw = str(payload.get("status", ""))

    if amount is None or amount <= 0:
        message.state = InboundState.FAILED
        message.note = f"مبلغ غير مفهوم في الرسالة: {payload.get('amount')!r}"
    else:
        try:
            outcome = services.apply_gateway_payment(
                reference=reference,
                payment_id=str(payload.get("id", "")),
                amount=amount,
                status_raw=status_raw,
                succeeded=status_raw in settings.PAYMENT_SUCCESS_STATUSES,
            )
        except Exception as exc:  # noqa: BLE001 — a failure here is data
            # Article 2-2: a raise that escapes leaves the row with an empty
            # note and nothing looking at it. `failed` is now a queue rather
            # than a grave, which is the whole point of this module.
            log.exception("gateway interpret: message %s raised", message.pk)
            message.state = InboundState.FAILED
            message.note = f"{type(exc).__name__}: {exc}"
        else:
            message.state = {
                "credited": InboundState.PROCESSED,
                "suspense": InboundState.PROCESSED,
                "ignored": InboundState.IGNORED,
            }.get(outcome.disposition, InboundState.FAILED)
            message.note = outcome.note
            message.resulting_transaction = outcome.transaction

    message.attempts += 1
    message.processed_at = timezone.now()
    message.save(
        update_fields=[
            "state",
            "note",
            "resulting_transaction",
            "attempts",
            "processed_at",
        ]
    )
    log.info("gateway interpret: message %s -> %s", message.pk, message.state)
    return message


__all__ = ["INTERPRETED_SOURCE", "interpret"]
