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

from apps.accounts import identity
from apps.accounts import otp as otp_module
from apps.accounts import tokens as token_service
from apps.accounts.errors import (
    CompanyProfileIncomplete,
    NationalIdAlreadyVerified,
    NationalIdInvalid,
    OtpAlreadyUsed,
    OtpExpired,
    OtpIncorrect,
    OtpNotFound,
    OtpResendTooSoon,
    OtpTooManyAttempts,
    PhoneAlreadyRegistered,
    PhoneChangeNeedsBothCodes,
    PhoneUnchanged,
    RegistrationNeedsName,
    VerificationCodeUndeliverable,
)
from apps.accounts.models import (
    AccountType,
    Company,
    OtpPurpose,
    PhoneVerification,
    SmsFailure,
    User,
)
from apps.accounts.sms import SmsSendFailed, send_sms
from apps.core import audit

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


# --------------------------------------------------------------------------
# Changing the number the account is opened with
# --------------------------------------------------------------------------


def start_phone_change(*, user: User, new_phone: str) -> dict:
    """Send a code to the number being left **and** the number being moved to.

    Two codes, because v1's account-takeover path needed only one. There,
    proving the new number was enough: someone who got at a signed-in session —
    a shared laptop, a phone handed over unlocked — moved the account onto a
    number they controlled, and the owner's number stopped working without the
    owner ever being asked. Requiring the old number too means the theft has to
    survive the real owner's phone ringing.

    Refused before either message goes out when the new number already opens
    another account: sending a code there would ring a stranger's phone about a
    change they never asked for.
    """
    new_phone = new_phone.strip()

    if new_phone == user.phone:
        raise PhoneUnchanged(f"{user.pk} asked to change to the number it has")

    if User.objects.filter(phone=new_phone).exclude(pk=user.pk).exists():
        raise PhoneAlreadyRegistered(f"{new_phone} already opens another account")

    # The old number first. If the provider is down, `send_verification_code`
    # raises before the new number is ever contacted — so a failure leaves the
    # stranger's phone silent rather than half-way through the flow.
    current = send_verification_code(phone=user.phone, purpose=OtpPurpose.CHANGE_PHONE)
    send_verification_code(phone=new_phone, purpose=OtpPurpose.CHANGE_PHONE)

    return {
        "sent_to_current": True,
        "sent_to_new": True,
        "expires_at": current.expires_at,
        "resend_after": settings.OTP_RESEND_COOLDOWN_SECONDS,
    }


def confirm_phone_change(
    *, user: User, new_phone: str, current_code: str, new_code: str
) -> User:
    """Move the account onto ``new_phone`` once **both** codes check out.

    The acceptance criterion is a negative one — the old code alone does not do
    it, and neither does the new — so the interesting part of this function is
    what it refuses, and in particular *how*.

    **Both codes are judged before either is spent.** The obvious implementation
    calls the existing single-code check twice, and it is wrong in a way that
    only shows up in a customer's hands: a right first code plus a typo in the
    second consumes the right one, and the customer starts over needing two
    fresh messages — which T602's five-an-hour limit then meters, so a couple of
    fumbles lock them out for an hour. Here both rows are locked and compared,
    an attempt is counted against whichever code was wrong, and neither is
    consumed unless both matched.

    **The refusal never says which code was wrong.** A caller holding one of the
    two phones could otherwise test the other half one guess at a time; the pair
    fails together or not at all.

    **The raise happens after the transaction closes**, for the reason T601
    wrote down in `check_verification_code`: an exception thrown inside the block
    that counted a wrong attempt takes the count with it, and an attempt budget
    that never empties is not a budget.
    """
    new_phone = new_phone.strip()

    if new_phone == user.phone:
        raise PhoneUnchanged(f"{user.pk} asked to change to the number it has")

    refusal: Exception | None = None
    before: dict | None = None

    with transaction.atomic():
        # Locked in a fixed order — by the number itself, not "old then new".
        #
        # Two rows are locked here, and the obvious order is the order the
        # caller thinks in: the number being left, then the number being moved
        # to. That is a deadlock waiting for two customers swapping numbers with
        # each other: A locks (X, Y) while B locks (Y, X), and each holds what
        # the other needs. Sorting the pair means every caller takes the two
        # locks in the same order, so one of them simply waits.
        #
        # `place_bid` writes the same rule down for the same reason (T504); it
        # is a property of taking more than one lock, not of bidding.
        first, second = sorted((user.phone, new_phone))
        gated = {
            phone: _gate(phone, OtpPurpose.CHANGE_PHONE) for phone in (first, second)
        }
        current, incoming = gated[user.phone], gated[new_phone]

        # Re-read inside the lock: between `start_phone_change` and this call
        # somebody else may have finished registering the same number.
        if User.objects.filter(phone=new_phone).exclude(pk=user.pk).exists():
            raise PhoneAlreadyRegistered(f"{new_phone} already opens another account")

        current_ok = otp_module.codes_match(current_code, current.code_hash)
        incoming_ok = otp_module.codes_match(new_code, incoming.code_hash)

        # Counted per code, and only against the one that was actually wrong: a
        # correct code must not lose an attempt because its partner was mistyped.
        for verification, matched in ((current, current_ok), (incoming, incoming_ok)):
            if matched:
                continue
            verification.attempts += 1
            if verification.attempts >= settings.OTP_MAX_ATTEMPTS:
                verification.voided_at = timezone.now()
            verification.save(update_fields=["attempts", "voided_at"])

        if not (current_ok and incoming_ok):
            refusal = PhoneChangeNeedsBothCodes(
                f"phone change for {user.pk} had "
                f"current_ok={current_ok} incoming_ok={incoming_ok}"
            )
        else:
            spent = timezone.now()
            for verification in (current, incoming):
                verification.consumed_at = spent
                verification.save(update_fields=["consumed_at"])

            before = audit.snapshot(user, ["phone", "phone_verified_at"])
            user.phone = new_phone
            user.phone_verified_at = spent
            user.save(update_fields=["phone", "phone_verified_at"])

    if refusal is not None:
        raise refusal

    # Outside the transaction, after the change: every other session is signed
    # in under a number this account no longer answers on. If the change *was* a
    # takeover, this is what ends it; if it was the owner, it costs them one
    # sign-in on their other devices. The trade is not close.
    revoked = token_service.revoke_all_for(user)

    audit.record(
        action="accounts.change_phone",
        entity=user,
        actor=user,
        before=before,
        after=audit.snapshot(user, ["phone", "phone_verified_at"]),
        note=f"{revoked} sessions revoked",
    )
    return user


# --------------------------------------------------------------------------
# The profile — what a customer may change about themselves
# --------------------------------------------------------------------------

#: The only fields on `User` a customer may edit about themselves. Named here
#: rather than derived from the model, and that is the point: a field added to
#: the table tomorrow — a flag, a balance, a staff note — must not become
#: editable by everybody just by existing. `phone` is absent because changing it
#: is T604 and needs two codes; `account_type` is absent because becoming a
#: company is a profile with obligations, handled below.
EDITABLE_PROFILE_FIELDS = frozenset({"full_name", "email"})


def update_profile(*, user: User, changes: dict) -> User:
    """Apply ``changes`` to ``user``, refusing anything not in the allowlist.

    The refusal is a *validation* refusal, raised before anything is written —
    T605's acceptance criterion is that an unknown field is a clear 400 and
    never a 500. In v1 the profile endpoint passed the request body into
    `Model.objects.filter(...).update(**body)`, so a typo was a database error
    and a well-chosen key was a privilege escalation.
    """
    unknown = set(changes) - EDITABLE_PROFILE_FIELDS
    if unknown:
        raise ValueError(f"unknown profile fields: {sorted(unknown)}")

    before = audit.snapshot(user, sorted(EDITABLE_PROFILE_FIELDS))
    for field, value in changes.items():
        setattr(user, field, value)
    user.save(update_fields=list(changes) or None)

    audit.record(
        action="accounts.update_profile",
        entity=user,
        actor=user,
        before=before,
        after=audit.snapshot(user, sorted(EDITABLE_PROFILE_FIELDS)),
    )
    return user


def set_national_id(*, user: User, national_id: str) -> User:
    """Record the customer's identity number — once it is right, forever.

    The rule reads oddly until you see both halves (T606):

    * A **valid** id already on the account cannot be changed. The account
      carries obligations — deposits, invoices, a bidding history — and those
      belong to the person that number names.
    * An **invalid** one can. Somebody who mistyped a digit must be able to fix
      themselves. In v1 they could not: the first value written was final, so
      correcting a typo meant asking support to edit the database, and support
      editing identity columns is its own problem.

    The new value must itself be valid, so the exit from the correctable state
    is one-way.
    """
    national_id = (national_id or "").strip()

    if user.national_id and identity.is_valid(user.national_id):
        raise NationalIdAlreadyVerified(f"{user.pk} already carries a valid national id")

    if not identity.is_valid(national_id):
        raise NationalIdInvalid(f"{national_id!r} is not a well-formed identity")

    before = audit.snapshot(user, ["national_id"])
    user.national_id = national_id
    user.save(update_fields=["national_id"])

    audit.record(
        action="accounts.set_national_id",
        entity=user,
        actor=user,
        before=before,
        after=audit.snapshot(user, ["national_id"]),
    )
    return user


#: What ZATCA requires on a tax invoice, and therefore what a company must have
#: before it can win one. Listed once; the serializer and the refusal below both
#: read it, so "required" cannot mean two different things.
REQUIRED_COMPANY_FIELDS = (
    "name",
    "commercial_register",
    "vat_number",
    "building_number",
    "street",
    "district",
    "city",
    "postal_code",
)


def save_company_profile(*, user: User, fields: dict) -> Company:
    """Create or update the company profile, complete or not at all.

    **New companies must be complete; existing ones are exempt.** That is not
    leniency, it is the only migration path that works: v1's companies were
    entered before ZATCA required a national address, and roughly a third have
    no postal code. Refusing to let them save their phone number until they
    produce a district would lock working accounts out of their own profile.
    The cutoff is `COMPANY_PROFILE_REQUIRED_FROM`, a setting rather than a
    literal, because the day the exemption ends is an owner's decision.

    A company that is exempt today still cannot be *invoiced* without the
    fields — that refusal belongs to the invoice, not to this form.
    """
    existing = Company.objects.filter(user=user).first()
    is_new = existing is None

    if is_new:
        missing = [
            field for field in REQUIRED_COMPANY_FIELDS if not (fields.get(field) or "")
        ]
        if missing:
            raise CompanyProfileIncomplete(
                f"new company for {user.pk} missing {missing}",
                detail={"missing": missing},
            )

    before = None if is_new else audit.snapshot(existing, REQUIRED_COMPANY_FIELDS)
    company = existing or Company(user=user)
    for field, value in fields.items():
        setattr(company, field, value)
    company.save()

    # The account becomes a company account by having one. Deriving it here
    # rather than trusting a flag in the request body means nobody bids under a
    # company name they simply claimed.
    if user.account_type != AccountType.COMPANY:
        user.account_type = AccountType.COMPANY
        user.save(update_fields=["account_type"])

    audit.record(
        action="accounts.save_company_profile",
        entity=company,
        actor=user,
        before=before,
        after=audit.snapshot(company, REQUIRED_COMPANY_FIELDS),
        note="created" if is_new else "updated",
    )
    return company


def company_profile_is_complete(company: Company | None) -> bool:
    """Whether ``company`` carries everything a tax invoice needs.

    Read by screens that want to warn an exempt company before it bids, and by
    T607's tests. Not a permission — a company missing a field may still browse
    and still bid; what it cannot do is be invoiced.
    """
    if company is None:
        return False
    return all(getattr(company, field, "") for field in REQUIRED_COMPANY_FIELDS)


def _gate(phone: str, purpose: str) -> PhoneVerification:
    """The outstanding code for ``phone``, or the named reason there is none.

    Everything here refuses *without writing*, so it is safe to call for both
    numbers before either code has been compared. The writes — counting a wrong
    attempt, consuming a right one — belong to the caller, which is the only
    place that knows whether the pair as a whole succeeded.
    """
    verification = _latest_for(phone, purpose, for_update=True)

    if verification is None:
        raise OtpNotFound(f"no code was ever sent to {phone} for {purpose}")
    if verification.consumed_at is not None:
        raise OtpAlreadyUsed(f"code for {phone} was consumed")
    if verification.voided_at is not None:
        raise OtpExpired(f"code for {phone} was voided")
    if verification.expires_at <= timezone.now():
        raise OtpExpired(f"code for {phone} expired at {verification.expires_at}")
    if verification.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OtpTooManyAttempts(f"code for {phone} has no attempts left")

    return verification
