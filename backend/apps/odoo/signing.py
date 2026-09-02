"""Verifying that a message really came from Odoo.

Two independent things are checked, and both must hold:

* the HMAC over the raw body matches the shared secret;
* the timestamp is inside a five-minute window.

The second is what stops a valid, correctly-signed message being captured and
replayed a week later. The signature alone proves origin, not freshness.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings

SIGNATURE_HEADER = "HTTP_X_ODOO_SIGNATURE"
TIMESTAMP_HEADER = "HTTP_X_ODOO_TIMESTAMP"

#: How old a signed message may be. Long enough to survive a slow network and
#: a few seconds of clock drift, short enough that a captured request is not
#: useful tomorrow.
MAX_AGE_SECONDS = 300


@dataclass(frozen=True)
class SignatureResult:
    ok: bool
    reason: str = ""


def expected_signature(raw_body: bytes, timestamp: str, secret: str) -> str:
    """The HMAC we expect, over timestamp and body together.

    The timestamp is inside the signed material on purpose. Signing the body
    alone would let someone replay a real message with a fresh timestamp, and
    the freshness check would pass on a value nobody vouched for.
    """
    message = timestamp.encode() + b"." + raw_body
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def verify(raw_body: bytes, meta: dict, *, now=None) -> SignatureResult:
    """Check a request's signature and freshness.

    Returns a result rather than raising: the caller has to store the message
    either way, and an exception would make "reject" the easy path and
    "reject and record" the one someone forgets.
    """
    secret = settings.ODOO_WEBHOOK_SECRET
    if not secret:
        # Refusing everything is the safe failure. A boundary with no secret
        # configured that accepts anything is worse than one that is down.
        return SignatureResult(False, "لا يوجد سرّ ويبهوك مضبوط في هذه البيئة")

    provided = meta.get(SIGNATURE_HEADER, "")
    timestamp = meta.get(TIMESTAMP_HEADER, "")
    if not provided or not timestamp:
        return SignatureResult(False, "الطلب بلا توقيع أو بلا طابع زمني")

    # Decimal, not float — even though this is a timestamp and not money.
    # The float ban is worth more as an absolute than as a rule with an
    # exception list, because the list is where a money module eventually
    # gets added "just this once".
    try:
        sent_at = Decimal(timestamp)
    except (InvalidOperation, ValueError):
        return SignatureResult(False, f"طابع زمني غير صالح: {timestamp!r}")

    current = Decimal(str(now)) if now is not None else Decimal(str(time.time()))
    age = current - sent_at
    if abs(age) > MAX_AGE_SECONDS:
        return SignatureResult(False, f"طابع زمني خارج النافذة: عمره {age:.0f} ثانية")

    # compare_digest, not ==: a plain comparison leaks how many leading bytes
    # were right through its own timing.
    if not hmac.compare_digest(provided, expected_signature(raw_body, timestamp, secret)):
        return SignatureResult(False, "التوقيع لا يطابق")

    return SignatureResult(True)
