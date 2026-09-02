"""The inbound boundary. It stores, and it answers. Nothing else.

Article 2-1: receive before you understand. This view must be able to succeed
while every interpreter behind it is broken, because the alternative — Odoo
retrying, giving up, and us never learning what it tried to say — is how v1
lost the webhook that carried the invoice link.

So there is no branch here on what the message *means*, no lookup of the
customer it concerns, and no synchronous call into processing. One insert, one
response.
"""

from __future__ import annotations

import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.core import jsonio

from .models import InboundMessage, InboundState
from .signing import verify

log = logging.getLogger(__name__)

#: Odoo bursts when an operator posts a batch, so the ceiling is generous. It
#: exists to bound a runaway loop, not to shape normal traffic.
RATE_LIMIT_PER_MINUTE = 600


@csrf_exempt
@require_POST
def odoo_webhook(request: HttpRequest) -> JsonResponse:
    """Store an inbound message and acknowledge it.

    The response codes are deliberate:

    * **200** — stored. Includes messages we have decided to ignore, and
      messages we could not parse. Odoo has done its part; the problem, if
      any, is ours and retrying will not help it.
    * **401** — signature failed. The message is *still stored*, under
      `rejected_signature`, because a burst of these is the only evidence
      that a secret was rotated on one side or that someone is probing.
    * **429** — over the rate ceiling. Nothing is stored; the sender should
      slow down and retry.
    """
    if _over_rate_limit(request):
        log.warning("odoo webhook: rate limited %s", _client_ip(request))
        return JsonResponse({"detail": "معدّل الطلبات تجاوز الحدّ"}, status=429)

    raw_body = request.body
    headers = _safe_headers(request)

    signature = verify(raw_body, request.META)
    if not signature.ok:
        _store(
            raw_body=raw_body,
            headers=headers,
            state=InboundState.REJECTED_SIGNATURE,
            note=signature.reason,
        )
        log.warning("odoo webhook: rejected signature — %s", signature.reason)
        return JsonResponse({"detail": "توقيع غير صالح"}, status=401)

    try:
        # Decoded through the shared money-safe decoder: a plain json.loads
        # here turned an amount into a float before the interpreter — which
        # reads `payload`, not `raw_body` — ever saw it, so a halala was already
        # gone by the time anything of ours could refuse it (Article 3-2).
        payload = jsonio.loads(raw_body or b"{}")
        if not isinstance(payload, dict):
            raise ValueError("الجذر ليس كائناً")
    except (json.JSONDecodeError, ValueError) as exc:
        # Signed by someone who holds our secret, so it is ours to explain.
        # Stored as `failed`, never dropped: a parser bug is fixable and the
        # message can be replayed afterwards.
        _store(
            raw_body=raw_body,
            headers=headers,
            state=InboundState.FAILED,
            note=f"جسم غير قابل للقراءة كـJSON: {exc}",
        )
        log.error("odoo webhook: unparseable body — %s", exc)
        return JsonResponse({"detail": "تم الاستلام"}, status=200)

    database = str(payload.get("db") or payload.get("database") or "")
    expected_database = settings.ODOO_DB
    if expected_database and database and database != expected_database:
        # A staging message reaching production. Recorded so the misdirection
        # is visible, and ignored so it can never move a riyal.
        _store(
            raw_body=raw_body,
            headers=headers,
            payload=payload,
            state=InboundState.IGNORED,
            note=(
                f"قاعدة أودو {database!r} ليست قاعدة هذه البيئة ({expected_database!r})"
            ),
        )
        log.warning("odoo webhook: message from foreign database %s", database)
        return JsonResponse({"detail": "تم الاستلام"}, status=200)

    message = _store(
        raw_body=raw_body,
        headers=headers,
        payload=payload,
        state=InboundState.RECEIVED,
    )
    return JsonResponse({"detail": "تم الاستلام", "id": message.pk}, status=200)


def _store(
    *,
    raw_body: bytes,
    headers: dict,
    state: str,
    note: str = "",
    payload: dict | None = None,
) -> InboundMessage:
    """Insert the message, treating a repeated delivery as already-stored.

    Odoo retries when our acknowledgement is slow, so the same delivery
    arriving twice is ordinary traffic, not an error. The unique index settles
    it and we hand back the row we already have.
    """
    payload = payload if payload is not None else {}
    fields = {
        "source": "odoo",
        "event": str(payload.get("event", ""))[:64],
        "delivery_id": _delivery_id(payload, headers),
        "subject_ref": _subject_ref(payload),
        "odoo_database": str(payload.get("db") or payload.get("database") or "")[:64],
        "payload": payload,
        "raw_body": raw_body.decode("utf-8", errors="replace"),
        "headers": headers,
        "state": state,
        "note": note,
    }
    try:
        # The savepoint is load-bearing: without it the IntegrityError leaves
        # the surrounding transaction unusable and the recovery query below
        # cannot run at all.
        with transaction.atomic():
            return InboundMessage.objects.create(**fields)
    except IntegrityError:
        existing = InboundMessage.objects.filter(
            source="odoo", delivery_id=fields["delivery_id"]
        ).first()
        if existing is None:
            raise
        log.info("odoo webhook: delivery %s already stored", fields["delivery_id"])
        return existing


def _delivery_id(payload: dict, headers: dict) -> str:
    """This delivery's identity — never the subject's.

    Three messages about one invoice are three messages. In v1 they were
    deduplicated by subject, and the third one, the only one carrying the
    invoice link, was silently discarded.

    When Odoo sends no delivery id we derive one from the delivery-shaped
    fields (event plus timestamp plus subject), documented here rather than
    invented at each call site. If even that is empty the field stays blank,
    which the partial unique index tolerates: better a duplicate row than a
    collapsed one.
    """
    for key in ("delivery_id", "message_id", "id"):
        value = payload.get(key)
        if value:
            return str(value)[:128]

    header_id = headers.get("X-Odoo-Delivery-Id") or headers.get("X-Request-Id")
    if header_id:
        return str(header_id)[:128]

    event = payload.get("event", "")
    timestamp = payload.get("timestamp", "") or payload.get("write_date", "")
    subject = _subject_ref(payload)
    derived = f"{event}:{subject}:{timestamp}".strip(":")
    return derived[:128] if derived.strip(":") else ""


def _subject_ref(payload: dict) -> str:
    """What the message is about, for reading one object's whole conversation."""
    for key in ("invoice_id", "invoice", "payment_id", "subject_ref", "ref"):
        value = payload.get(key)
        if value:
            return str(value)[:128]
    return ""


def _safe_headers(request: HttpRequest) -> dict:
    """The headers worth keeping, without the signature material.

    The signature is a keyed digest of the body; storing it next to the body
    hands an attacker who reads the table a verified sample to work from.
    """
    skipped = {"X-Odoo-Signature", "Cookie", "Authorization"}
    return {name: value for name, value in request.headers.items() if name not in skipped}


def _over_rate_limit(request: HttpRequest) -> bool:
    """A per-minute ceiling per sender, in the shared cache.

    Deliberately coarse. Its job is to bound a runaway retry loop, not to
    police legitimate bursts — a limiter that drops real messages would break
    the one rule this whole module exists to keep.
    """
    key = f"odoo-webhook-rate:{_client_ip(request)}"
    try:
        count = cache.get_or_set(key, 0, timeout=60)
        count = cache.incr(key)
    except ValueError:
        # The key expired between get_or_set and incr. Treat as the first
        # request of a new window rather than as a violation.
        cache.set(key, 1, timeout=60)
        return False
    return count > RATE_LIMIT_PER_MINUTE


def _client_ip(request: HttpRequest) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")
