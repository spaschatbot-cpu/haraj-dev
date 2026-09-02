"""Refusals the authentication paths can hand a customer.

Every one of these is an answer, not a crash: the person typed a code that had
expired, or asked for a new one three seconds after the last. They subclass
:class:`apps.core.errors.DomainError`, so `apps.core.exceptions` turns them into
the one error envelope with an Arabic sentence and a 409 — no view here formats
an error body of its own.

The codes are stable strings; the Flutter app and the web client both branch on
them, and neither reads the Arabic to decide anything.
"""

from __future__ import annotations

from apps.core.errors import DomainError


class OtpNotFound(DomainError):
    """No code was ever sent to this number for this purpose."""

    code = "otp_not_found"
    default_message = "ما فيش رمز مُرسَل لهذا الرقم. اطلب رمزاً جديداً."


class OtpExpired(DomainError):
    """The code was right once. It is not right now."""

    code = "otp_expired"
    default_message = "انتهت صلاحية الرمز. اطلب رمزاً جديداً."


class OtpAlreadyUsed(DomainError):
    """A code opens one door, once.

    Without this, a code read over someone's shoulder — or left in an SMS log —
    stays a working key for as long as it has not expired.
    """

    code = "otp_already_used"
    default_message = "هذا الرمز استُعمل من قبل. اطلب رمزاً جديداً."


class OtpTooManyAttempts(DomainError):
    """The attempt budget for this code is spent.

    Six digits is a million possibilities, which is only a wall if the number of
    guesses is capped. It is capped per code, not per request, so burning the
    budget forces a new send — which T602's rate limit then meters.
    """

    code = "otp_too_many_attempts"
    default_message = "حاولت كثيراً بهذا الرمز. اطلب رمزاً جديداً."


class OtpIncorrect(DomainError):
    """Wrong digits, and the budget still has room."""

    code = "otp_incorrect"
    default_message = "الرمز غير صحيح."


class OtpResendTooSoon(DomainError):
    """A second send while the first code is still young and still valid."""

    code = "otp_resend_too_soon"
    default_message = "انتظر قليلاً قبل طلب رمز جديد."


class InvalidRefreshToken(DomainError):
    """Unknown, expired, or already revoked."""

    code = "invalid_refresh_token"
    default_message = "انتهت الجلسة. سجّل الدخول من جديد."


class RefreshTokenReused(DomainError):
    """A refresh token presented after it was already exchanged.

    Rotation means each refresh token is spent the moment it is used. Seeing a
    spent one again means two parties hold the same token, and only one of them
    is the customer — so the whole chain is revoked and both are logged out.
    """

    code = "refresh_token_reused"
    default_message = "تم إنهاء الجلسة لأسباب أمنية. سجّل الدخول من جديد."


class RegistrationNeedsName(DomainError):
    """First sign-in from a number nobody owns yet, with no name to open it under.

    Raised *before* the code is checked, deliberately. Consuming a good code and
    then refusing for a missing field would cost the customer a whole new SMS to
    fix a form they can still edit on screen.
    """

    code = "registration_needs_name"
    default_message = "أدخل الاسم لإنشاء الحساب."
