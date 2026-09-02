"""Business rules about accounts.

Two of them so far: what an account is called when a human looks at it, and how
a person proves they hold a phone number. Both live here because rules live in
the service layer, and they live *only* here because a rule written twice
eventually disagrees with itself.

No view in this app decides anything. A view reads a request, calls one function
below, and renders what comes back.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts import otp as otp_module
from apps.accounts.errors import (
    OtpAlreadyUsed,
    OtpExpired,
    OtpIncorrect,
    OtpNotFound,
    OtpResendTooSoon,
    OtpTooManyAttempts,
    RegistrationNeedsName,
    VerificationCodeUndeliverable,
)
from apps.accounts.models import (
    Company,
    OtpPurpose,
    PhoneVerification,
    SmsFailure,
    User,
)
from apps.accounts.sms import SmsSendFailed, send_sms

log = logging.getLogger(__name__)


def display_name(user: User) -> str:
    """The one name any screen, report, export or message may show for ``user``.

    A company bids under the company's name, never under the name of whoever
    happens to represent it. In v1 some screens showed the representative and
    others the company, so support could not tell which account had placed a
    bid. Every caller asks this function; nobody assembles a name themselves.

    An account marked as a company but with no company row yet falls back to the
    person's own name — half-finished registration must not render blank.
    """
    try:
        company: Company = user.company
    except Company.DoesNotExist:
        return user.full_name
    return company.name


# --------------------------------------------------------------------------
# Proving a phone number
# --------------------------------------------------------------------------

#: The sentence the customer receives. One place, so the wording is the same
#: whichever path sent it (Article 4-5).
OTP_MESSAGE = "رمز التحقق: {code}\nينتهي خلال {minutes} دقائق. لا تشاركه مع أحد."


def send_verification_code(
    *, phone: str, purpose: str = OtpPurpose.LOGIN
) -> PhoneVerification:
    """Send a fresh code to ``phone``, or say plainly that we could not.

    The whole of this function is the difference between the two endings, and
    it is a difference v1 never made: "your code is wrong" is the customer's
    problem, "the provider would not carry it" is ours. Both looked the same
    from the outside, so every SMS balance running out was diagnosed from
    scratch — and the first move was always asking customers to try again.

    **The failure is recorded outside the transaction, and that placement is
    the task.** :func:`_send_verification_code` sends inside its atomic block on
    purpose, so a provider failure takes the unsent code's row down with it. A
    failure record written in that block would be rolled back by the very same
    exception — the evidence would disappear at exactly the moment it was worth
    keeping. So the block runs, fails, and rolls back; only then do we write.

    This is the same shape as the bug T601 found in `check_verification_code`,
    where a refusal raised inside the atomic block took the attempt count it had
    just written with it. Once is an accident; writing it down here is how it
    stops being a pattern.
    """
    try:
        return _send_verification_code(phone=phone, purpose=purpose)
    except SmsSendFailed as failure:
        SmsFailure.objects.create(
            provider=failure.provider or settings.SMS_BACKEND,
            phone=phone,
            purpose=purpose,
            reason=str(failure),
        )
        # `error`, not `warning`: nobody can sign in while this is happening,
        # and the row above is what turns a run of these into a start time.
        log.error(
            "sms provider refused a code for %s via %s: %s",
            phone,
            failure.provider or settings.SMS_BACKEND,
            failure,
        )
        raise VerificationCodeUndeliverable(
            f"provider refused the code for {phone}"
        ) from failure


def recent_sms_failures(*, within: timedelta | None = None) -> int:
    """How many codes the provider has refused lately.

    The number a health screen shows (T220, T813) and the reason this table
    exists: one failure is a bad minute, forty in an hour is a balance that ran
    out at a knowable time.
    """
    window = within or timedelta(hours=1)
    return SmsFailure.objects.filter(created_at__gte=timezone.now() - window).count()


@transaction.atomic
def _send_verification_code(
    *, phone: str, purpose: str = OtpPurpose.LOGIN
) -> PhoneVerification:
    """Send a fresh code to ``phone`` and record that we did.

    Sending voids whatever code was outstanding for the same phone and purpose.
    Two live codes would double the number of guesses that work at once, and
    would make "the code I got" ambiguous for a customer holding two messages.

    Refuses with :class:`OtpResendTooSoon` while the previous code is younger
    than the cooldown. That is a courtesy limit on this one number; the account-
    wide rate limit that protects the SMS bill is T602, and is a separate thing.
    """
    now = timezone.now()
    outstanding = _latest_for(phone, purpose)

    if outstanding is not None and outstanding.is_live:
        cooldown = timedelta(seconds=settings.OTP_RESEND_COOLDOWN_SECONDS)
        if outstanding.created_at + cooldown > now:
            raise OtpResendTooSoon(
                f"resend for {phone} while the previous code is still live",
                detail={
                    "retry_after": int(
                        (outstanding.created_at + cooldown - now).total_seconds()
                    )
                },
            )
        outstanding.voided_at = now
        outstanding.save(update_fields=["voided_at"])

    code = otp_module.generate_code()
    ttl = timedelta(seconds=settings.OTP_TTL_SECONDS)
    verification = PhoneVerification.objects.create(
        phone=phone,
        purpose=purpose,
        code_hash=otp_module.hash_code(code),
        created_at=now,
        expires_at=now + ttl,
    )

    # Sending last, inside the transaction: a provider failure must not leave a
    # code recorded that nobody was ever told. `SmsSendFailed` propagates to the
    # wrapper above, which records the failure *after* this block has rolled
    # back and turns it into `VerificationCodeUndeliverable`.
    send_sms(
        phone=phone,
        body=OTP_MESSAGE.format(code=code, minutes=settings.OTP_TTL_SECONDS // 60),
    )
    return verification


def check_verification_code(
    *, phone: str, code: str, purpose: str = OtpPurpose.LOGIN
) -> PhoneVerification:
    """Consume the outstanding code for ``phone`` if ``code`` matches it.

    Every ending is named. There is no branch here that returns quietly, and no
    caller that has to guess why a code did not work — the refusal carries the
    reason, in Arabic, ready to put on a screen.

    **The refusal is raised after the transaction closes, never inside it.** A
    wrong guess has to be *counted*, and an exception thrown inside the atomic
    block that counted it takes the count down with it — leaving a five-guess
    budget that never runs out, which is the same as no budget at all. So the
    block decides and writes; the raise happens once the write is committed.
    """
    refusal: Exception | None = None

    with transaction.atomic():
        verification = _latest_for(phone, purpose, for_update=True)

        if verification is None:
            raise OtpNotFound(f"no code was ever sent to {phone} for {purpose}")

        if verification.consumed_at is not None:
            raise OtpAlreadyUsed(
                f"code for {phone} was consumed at {verification.consumed_at}"
            )

        if verification.voided_at is not None:
            raise OtpExpired(f"code for {phone} was voided at {verification.voided_at}")

        if verification.expires_at <= timezone.now():
            raise OtpExpired(f"code for {phone} expired at {verification.expires_at}")

        if verification.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise OtpTooManyAttempts(f"code for {phone} has no attempts left")

        # Counted before the comparison, and saved whether or not it matched —
        # a guess that costs nothing is not a guess an attacker minds making.
        verification.attempts += 1

        if otp_module.codes_match(code, verification.code_hash):
            verification.consumed_at = timezone.now()
            verification.save(update_fields=["attempts", "consumed_at"])
        else:
            spent = verification.attempts >= settings.OTP_MAX_ATTEMPTS
            if spent:
                verification.voided_at = timezone.now()
                refusal = OtpTooManyAttempts(f"code for {phone} exhausted its attempts")
            else:
                refusal = OtpIncorrect(
                    f"wrong code for {phone}",
                    detail={
                        "attempts_left": settings.OTP_MAX_ATTEMPTS - verification.attempts
                    },
                )
            verification.save(update_fields=["attempts", "voided_at"])

    if refusal is not None:
        raise refusal
    return verification


def _latest_for(
    phone: str, purpose: str, *, for_update: bool = False
) -> PhoneVerification | None:
    rows = PhoneVerification.objects.filter(phone=phone, purpose=purpose)
    if for_update:
        rows = rows.select_for_update()
    return rows.order_by("-created_at").first()


def user_for_verified_phone(*, phone: str, full_name: str = "") -> tuple[User, bool]:
    """The account that owns ``phone``, creating it on first sign-in.

    Returns ``(user, created)``. A Saudi mobile that has just been proven is
    identity enough to open an account — asking for a password as well would
    only add a thing to forget, and v1's customers overwhelmingly had no email
    to recover one with.
    """
    user = User.objects.filter(phone=phone).first()
    now = timezone.now()

    if user is None:
        user = User.objects.create_user(phone=phone, full_name=full_name)
        user.phone_verified_at = now
        user.save(update_fields=["phone_verified_at"])
        return user, True

    if user.phone_verified_at is None:
        user.phone_verified_at = now
        user.save(update_fields=["phone_verified_at"])
    return user, False


def sign_in_with_code(*, phone: str, code: str, full_name: str = "") -> tuple[User, bool]:
    """The whole of signing in: check the code, then hand back the account.

    Returns ``(user, created)``. This exists so the view has exactly one call to
    make and no ordering to get right — and the ordering matters. The name is
    demanded *before* the code is consumed, because a good code spent on a
    missing form field costs the customer another SMS and another minute for a
    mistake they can still fix on the screen in front of them.

    **Not atomic, deliberately.** Each step below already is. Wrapping them
    together would roll back the attempt `check_verification_code` just counted
    whenever it refuses — and an attempt that is not counted is a five-guess
    budget that never empties. The two steps are also not one unit of meaning:
    a code is spent the moment it is typed correctly, whatever happens next.
    """
    full_name = full_name.strip()
    existing = User.objects.filter(phone=phone).first()

    if existing is None and not full_name:
        raise RegistrationNeedsName(f"{phone} has no account and no name was given")

    check_verification_code(phone=phone, code=code)
    return user_for_verified_phone(phone=phone, full_name=full_name)
