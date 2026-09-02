"""One shape for every error the API returns.

    {"error": {"code": "insufficient_funds",
               "message": "الرصيد المتاح لا يكفي",
               "detail": {}}}

``code`` is the stable string the Flutter app branches on; ``message`` is Arabic
and ready to put on a screen; ``detail`` carries per-field information when
there is any, and is ``{}`` otherwise so the client never has to check whether
the key exists.

Three rules decide the status code
----------------------------------
* A **refused money operation** (:class:`apps.money.services.MoneyError` and its
  subclasses) is ``409``. It is an expected answer — "you do not have enough
  free insurance" is the system working, not failing — and a ``500`` there both
  lies to the client and buries the case in the error budget.
* A DRF exception keeps the status DRF already chose: ``NotFound`` stays ``404``,
  ``PermissionDenied`` ``403``, and so on.
* Anything else is a ``500`` carrying an incident id. The exception's own text
  never reaches the client; it goes to the log next to that id, so support can
  ask for the id and find the traceback without the client ever being told what
  broke.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from django.http import Http404
from django.utils.module_loading import import_string
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

log = logging.getLogger(__name__)

#: Exceptions that mean "refused, and the caller can do something about it".
#: They are named as strings and resolved on first use so that `apps.core` — the
#: layer everything else sits on — never imports a domain app at module load and
#: cannot become half of an import cycle. Adding a domain's refusal base here is
#: the whole of the work needed to give it 409s.
#: `DomainError` lives in this package, so `apps.money.services.MoneyError` —
#: which subclasses it — is covered without being named. It stays listed anyway:
#: the tuple is the readable answer to "what returns 409 here?", and a domain
#: that grows its own refusal base outside DomainError adds one line.
EXPECTED_REFUSALS: tuple[str, ...] = (
    "apps.core.errors.DomainError",
    "apps.money.services.MoneyError",
)

#: The Arabic the user actually reads, by code. This is the single place a
#: wording lives (Article 4-5); a screen that wants different words changes it
#: here, for every screen at once.
MESSAGES: dict[str, str] = {
    # money
    "insufficient_funds": "الرصيد المتاح لا يكفي",
    "unbalanced": "الحركة المالية غير متوازنة",
    "money_error": "لا يمكن تنفيذ هذه العملية على الفلوس",
    # DRF
    "not_found": "غير موجود",
    "permission_denied": "ليس لديك صلاحية لهذا الإجراء",
    "not_authenticated": "يلزم تسجيل الدخول",
    "authentication_failed": "تعذّر التحقق من هويتك",
    "invalid": "البيانات المرسلة غير صحيحة",
    "validation_error": "البيانات المرسلة غير صحيحة",
    "parse_error": "تعذّرت قراءة الطلب",
    "method_not_allowed": "هذه الطريقة غير مسموحة على هذا المسار",
    "not_acceptable": "الصيغة المطلوبة غير مدعومة",
    "unsupported_media_type": "نوع المحتوى غير مدعوم",
    "throttled": "عدد المحاولات كبير، حاول بعد قليل",
    # last resort
    "internal_error": "حدث خطأ غير متوقّع. أرفق رقم الحادثة عند التواصل مع الدعم.",
}

FALLBACK_MESSAGE = "تعذّر تنفيذ الطلب"

_camel_boundary = re.compile(r"(?<!^)(?=[A-Z])")


def code_for(exc: Exception) -> str:
    """``InsufficientFunds`` → ``insufficient_funds``.

    Derived rather than declared so a new refusal class gets a client-visible
    code by existing, and cannot ship with the code of the class above it —
    which is the way a hand-maintained mapping goes wrong.
    """
    return _camel_boundary.sub("_", type(exc).__name__).lower()


def _refusal_classes() -> tuple[type[Exception], ...]:
    """Resolve :data:`EXPECTED_REFUSALS`, tolerating an app that is not installed."""
    resolved: list[type[Exception]] = []
    for path in EXPECTED_REFUSALS:
        try:
            resolved.append(import_string(path))
        except ImportError:  # pragma: no cover - only when an app is removed
            log.warning("expected-refusal class %s could not be imported", path)
    return tuple(resolved)


def envelope(code: str, message: str = "", detail: Any = None) -> dict[str, Any]:
    """The response body, built in one place so no view can invent a variant."""
    return {
        "error": {
            "code": code,
            "message": message or MESSAGES.get(code, FALLBACK_MESSAGE),
            "detail": detail if detail is not None else {},
        }
    }


def first_sentence(detail: Any) -> str | None:
    """The first human sentence buried in a DRF validation detail tree.

    A serializer that took the trouble to write "المبلغ يحدده النظام" should
    have it reach the screen. Flattening it to a generic "البيانات المرسلة غير
    صحيحة" and burying the real reason in ``detail`` leaves the customer with a
    form that says no and will not say why.
    """
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        for value in detail.values():
            found = first_sentence(value)
            if found:
                return found
    if isinstance(detail, list):
        for item in detail:
            found = first_sentence(item)
            if found:
                return found
    return None


def api_exception_handler(exc: Exception, context: dict) -> Response:
    """DRF's ``EXCEPTION_HANDLER``. Returns a response for *every* exception."""
    view = context.get("view")

    if isinstance(exc, _refusal_classes()):
        # A refusal may declare its own stable code; otherwise the class name
        # gives it one, so a new refusal cannot ship wearing its parent's.
        code = getattr(exc, "code", None) or code_for(exc)

        # Three sources of wording, in order. An explicit `user_message` wins
        # because only the raiser can say "10000.00 مقفولة على مستحقات" — a
        # static table cannot hold a sentence with this customer's numbers in
        # it. Otherwise MESSAGES owns the wording (Article 4-5), and a code it
        # has never heard of falls back to the class's own default.
        message = getattr(exc, "explicit_message", "")
        if not message:
            message = MESSAGES.get(code) or getattr(exc, "user_message", "")

        # The exception's own text is diagnostic English ("insurance_free for
        # owner 7 holds 0.00, needs 10000") — useful to an operator reading
        # logs, wrong to put in front of a customer. It stays here.
        log.warning("refused: %s: %s (view=%s)", code, exc, view)
        set_rollback()
        return Response(
            envelope(code, message, getattr(exc, "detail", None)),
            status=status.HTTP_409_CONFLICT,
        )

    # Django's own 404, which `get_object_or_404` raises. DRF turns it into a
    # 404 response but leaves the exception as `Http404`, so it has no
    # `default_code` and `code_for` would name it after its class — a client
    # would see "http404" for a missing invoice and "not_found" for a missing
    # payment, for the same reason.
    if isinstance(exc, Http404):
        return Response(envelope("not_found"), status=status.HTTP_404_NOT_FOUND)

    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = getattr(exc, "detail", None)
        code = getattr(exc, "default_code", None) or code_for(exc)
        if isinstance(detail, dict | list):
            # A validation error. `validation_error` rather than DRF's own
            # `invalid`, because the client branches on this string and
            # "invalid" says nothing about which of the four hundred things
            # were invalid. The per-field errors stay in `detail`; the first
            # Arabic sentence among them becomes the message.
            return Response(
                envelope("validation_error", first_sentence(detail) or "", detail),
                status=response.status_code,
            )
        return Response(envelope(code), status=response.status_code)

    # Unexpected. The client gets a random token and nothing else; the token is
    # in the log line beside the traceback, which is the only thing support
    # needs to find it.
    incident = uuid.uuid4().hex[:12]
    log.exception("incident %s (view=%s): %s", incident, view, exc)
    set_rollback()
    return Response(
        envelope("internal_error", detail={"incident": incident}),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
