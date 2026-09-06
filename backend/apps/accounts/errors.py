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


class AccountStopped(DomainError):
    """حسابٌ أوقفه موظّفٌ يطلب رمزاً جديداً ويدخل به.

    `is_active` كان يُفحَص في `tokens.verify` و`tokens.rotate` وحدهما — أي أنه
    يقطع الرمز **القائم** ولا يمنع رمزاً جديداً. فالموقوف يطلب رمزاً بجوّاله،
    يدخل، ويأخذ زوجاً جديداً: الإيقاف يصمد حتى أوّل رسالةٍ نصّية.

    والرفض **بعد** فحص الرمز لا قبله، وذلك مقصود: رفضٌ يسبق الفحص يجعل هذه
    النقطة تُجيب «هل هذا الرقم موقوف؟» لمن يجرّب أرقاماً، وهو سؤالٌ لا يحقّ
    لمجهولٍ أن يعرف جوابه. ومن يعرف رمزاً صحيحاً يملك الجوّال فعلاً.
    """

    code = "account_stopped"
    default_message = "هذا الحساب موقوف. تواصل مع خدمة العملاء."


class VerificationCodeUndeliverable(DomainError):
    """We decided to send a code and the provider would not carry it.

    The one refusal in this file that is **not** about something the customer
    did. Every other class here answers "your code was wrong / late / spent";
    this one answers "our provider is down, and no code exists for you to type".
    Collapsing the two — which is what a bare 500 does — is why v1's support
    started every SMS outage by asking customers to try again.

    Hence ``status_code``: 503, not the 409 the rest of this file carries. A 409
    tells the client the request was refused on its merits and invites the app
    to show the sentence and stop; a 503 says the platform is temporarily unable
    and this is worth retrying. And it keeps our outage out of the customer's
    error budget, where it does not belong.
    """

    code = "sms_undeliverable"
    status_code = 503
    default_message = "تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل."


class PhoneChangeNeedsBothCodes(DomainError):
    """One of the two codes was wrong, and one right code changes nothing.

    The refusal deliberately does **not** say *which* one. Telling a caller
    "the code sent to the old number was correct, the new one was not" hands an
    attacker holding one of the two phones a way to test the other half of the
    pair one guess at a time. Both halves fail together or neither does.
    """

    code = "phone_change_needs_both_codes"
    default_message = "لازم الرمزين الصحيحين — المرسَل للرقم القديم والمرسَل للجديد."


class PhoneAlreadyRegistered(DomainError):
    """The number being moved to already opens somebody else's account.

    Refused before a single code is sent. Sending one would ring a stranger's
    phone with a code for a change they never asked about, which is a way to
    harass a number and a way to phish its owner.
    """

    code = "phone_already_registered"
    default_message = "هذا الرقم مسجَّل على حساب آخر."


class PhoneUnchanged(DomainError):
    """A change to the number the account already has."""

    code = "phone_unchanged"
    default_message = "هذا هو رقمك الحالي."


class NationalIdAlreadyVerified(DomainError):
    """The id on this account is valid, and a valid id is set once.

    The asymmetry is the rule (T606). A customer who mistyped a digit must be
    able to fix themselves — v1 made them ask support, who edited the database.
    But a *correct* id cannot be swapped for somebody else's, because the
    account carries obligations that belong to the person that number names.
    """

    code = "national_id_already_verified"
    default_message = "رقم الهوية مثبَّت ولا يمكن تغييره. راجع الدعم لو فيه خطأ."


class NationalIdInvalid(DomainError):
    """Ten digits, starting with 1 or 2, and a checksum that holds."""

    code = "national_id_invalid"
    default_message = "رقم الهوية غير صحيح."


class CompanyProfileIncomplete(DomainError):
    """A company account missing what an invoice must carry.

    ZATCA requires the commercial register, the VAT number and the national
    address on a tax invoice. A company that bids without them wins a car we
    cannot legally invoice — so the profile is refused at the point it is saved
    rather than at the point an invoice fails to issue.
    """

    code = "company_profile_incomplete"
    default_message = "بيانات الشركة ناقصة: السجل والرقم الضريبي والعنوان الوطني."
