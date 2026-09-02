"""The single translator from an exception to an HTTP body.

Every error the API returns has the same envelope::

    {"error": {"code": "insufficient_funds", "message": "…", "detail": {}}}

``code`` is stable and machine-readable; ``message`` is Arabic and ready to
display. A :class:`~apps.core.errors.DomainError` becomes **409**, because a
refused-by-design operation is an answer, not a fault — returning 500 for it (as
v1 did) trained the app to treat every refusal as an outage.

Anything genuinely unexpected becomes 500 with an incident id: the id is logged
next to the traceback and returned to the client, so a customer can quote it and
support can find the exact request, without leaking the traceback itself.

.. note::
   This is the handler described in `specs/001-foundation/plan.md` (T009). It is
   written here because the wallet endpoints cannot be tested without it; if the
   foundation task lands a richer version, this one is meant to be replaced, not
   duplicated.
"""

from __future__ import annotations

import logging
import uuid

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.core.errors import DomainError

log = logging.getLogger(__name__)

#: A readable Arabic sentence for each refusal DRF raises on our behalf. Keyed
#: by DRF's own ``default_code`` so a new exception class inherits the right
#: wording instead of needing a new branch.
ARABIC_BY_CODE = {
    "not_found": "لم نجد ما طلبته.",
    "permission_denied": "ليس لديك صلاحية لهذا الإجراء.",
    "not_authenticated": "يلزم تسجيل الدخول أولاً.",
    "authentication_failed": "بيانات الدخول غير صحيحة.",
    "invalid": "بيانات الطلب غير صحيحة.",
    "parse_error": "تعذّرت قراءة الطلب.",
    "method_not_allowed": "هذه الطريقة غير مدعومة لهذه النقطة.",
    "not_acceptable": "الصيغة المطلوبة غير مدعومة.",
    "unsupported_media_type": "نوع المحتوى غير مدعوم.",
    "throttled": "تجاوزت الحد المسموح، حاول بعد قليل.",
    "error": "تعذّر تنفيذ الطلب.",
}

UNEXPECTED_MESSAGE = "حدث خطأ غير متوقّع. أعد المحاولة، وإن تكرر أبلغ الدعم بالرقم أدناه."


def _envelope(code: str, message: str, detail: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "detail": detail or {}}}


def _first_sentence(detail) -> str | None:
    """The first human sentence buried in a DRF validation detail tree.

    A serializer that took the trouble to write an Arabic message should have it
    reach the screen, rather than be flattened into a generic "invalid input".
    """
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        for value in detail.values():
            found = _first_sentence(value)
            if found:
                return found
    if isinstance(detail, list):
        for item in detail:
            found = _first_sentence(item)
            if found:
                return found
    return None


def unified_exception_handler(exc, context):
    """Return every error in the one envelope, with an Arabic message."""
    if isinstance(exc, DomainError):
        log.info("refused: %s — %s", exc.code, exc)
        return Response(
            _envelope(exc.code, exc.user_message, exc.detail),
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, Http404):
        return Response(
            _envelope("not_found", ARABIC_BY_CODE["not_found"]),
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, APIException):
        code = str(getattr(exc, "default_code", "error"))
        message = ARABIC_BY_CODE.get(code, ARABIC_BY_CODE["error"])
        detail: dict = {}

        if isinstance(exc, ValidationError):
            detail = (
                exc.detail if isinstance(exc.detail, dict) else {"errors": exc.detail}
            )
            message = _first_sentence(exc.detail) or message
        elif isinstance(exc, PermissionDenied):
            message = ARABIC_BY_CODE["permission_denied"]

        response = drf_exception_handler(exc, context)
        code_out = "validation_error" if isinstance(exc, ValidationError) else code
        return Response(
            _envelope(code_out, message, detail),
            status=response.status_code if response else exc.status_code,
            headers={"Retry-After": str(exc.wait)}
            if getattr(exc, "wait", None)
            else None,
        )

    # Genuinely unexpected. The traceback goes to the log with an id; the client
    # gets the id and nothing else.
    incident = uuid.uuid4().hex[:12]
    log.exception("unhandled exception, incident %s", incident)
    return Response(
        _envelope("internal_error", UNEXPECTED_MESSAGE, {"incident": incident}),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
