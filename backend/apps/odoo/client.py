"""The only place that talks to Odoo over the network.

Two rules hold this module together:

* **`ODOO_ENABLED=False` is the default in every environment** (Article 2-6).
  A disabled client does not quietly succeed — it raises, loudly, because a
  no-op that looks like a success is how a staging deploy convinces you a
  real invoice was issued.
* **Nothing outside the sending worker calls this.** Anything we owe Odoo is
  written to the outbox first. That is what makes a retry safe, and it is
  enforced by a text check in CI.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20


class OdooDisabled(RuntimeError):
    """The integration is off for this environment, on purpose."""


class OdooUnreachable(RuntimeError):
    """The call did not complete.

    Deliberately distinct from a rejection. Article 2-4: not reaching them is
    not evidence that nothing happened on their side — a five-second timeout
    read as "no money moved" is what pulled 10,000 from a real customer in v1.
    A caller seeing this must retry, never compensate.
    """


def call(endpoint: str, payload: dict, *, reference: str) -> dict:
    """POST to Odoo, carrying a reference they treat as unique."""
    if not settings.ODOO_ENABLED:
        raise OdooDisabled(
            f"تكامل أودو مطفأ في هذه البيئة؛ لم يُرسل {reference} إلى {endpoint}"
        )

    url = f"{settings.ODOO_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
    try:
        response = requests.post(
            url,
            json={**payload, "reference": reference},
            headers={"X-Api-Key": settings.ODOO_API_KEY},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OdooUnreachable(f"تعذّر الوصول إلى أودو: {exc}") from exc

    if response.status_code >= 500:
        # Their fault and probably temporary: retry.
        raise OdooUnreachable(f"أودو ردّت {response.status_code}")
    if response.status_code >= 400:
        # Their considered "no". Retrying sends it again unchanged.
        raise ValueError(
            f"أودو رفضت {reference}: {response.status_code} {response.text[:200]}"
        )

    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:1000]}
