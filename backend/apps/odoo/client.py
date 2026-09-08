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
from pathlib import Path

import requests
from django.conf import settings

from apps.core import jsonio

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


def _bearer() -> str:
    """ترويسةُ المصادقة كما يبنيها v1: التوكن مسبوقاً بـ«Bearer ».

    التوكنُ في `settings.ODOO_API_KEY` (يضعه المشغّل في `.env`، سرٌّ لا يُودَع
    في الكود). إن حمل «Bearer » أصلاً تُركت، وإلا أُضيفت — فيقبل الإعدادُ
    الصيغتين كما يفعل v1.
    """
    token = (settings.ODOO_API_KEY or "").strip()
    if token and not token.lower().startswith("bearer "):
        token = f"Bearer {token}"
    return token


def _tls_verify():
    """كيف يُتحقَّق من TLS: شهادةُ `tools/cacert.pem` إن وُجدت، أو إطفاءٌ صريح
    في التطوير عبر `ODOO_INSECURE_TLS` (كـ v1 — الشهادةُ على أجهزة التطوير قديمة
    غالباً). في الإنتاج يبقى التحقّقُ قائماً."""
    if getattr(settings, "ODOO_INSECURE_TLS", False):
        return False
    ca = Path(settings.BASE_DIR) / "tools" / "cacert.pem"
    return str(ca) if ca.is_file() else True


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
            headers={
                "Content-Type": "application/json",
                # عقدُ أودو الحقيقيّ (كما في v1): مصادقةُ Bearer لا `X-Api-Key`.
                # يُضاف «Bearer » إن لم يكن التوكن يحملها أصلاً.
                "Authorization": _bearer(),
            },
            # مهلتان كـ v1: اتصالٌ ٥ث، قراءةٌ ١٢ث — فأودو المعلَّق لا يُجمّد طلباً
            # للمستخدم طويلاً حتى يبدو «خطأ اتصال».
            timeout=(5, 12),
            verify=_tls_verify(),
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
        # Not `response.json()`: their reply carries their amounts —
        # `amount_total` is read straight out of it during reconciliation — and
        # requests' decoder would make each one a float before we saw it.
        # Article 3-2 says «ولو في تقرير», and a reconciliation report is
        # precisely a report (a halala lost here either invents a discrepancy
        # or rounds a real one away).
        return jsonio.loads(response.content)
    except ValueError:
        return {"raw": response.text[:1000]}
