"""T604 — moving an account onto a new number takes both numbers.

The acceptance criterion is stated as two negatives: the old code alone does not
do it, and neither does the new. That is because v1's takeover path needed only
one. Proving the *new* number was enough, so somebody who reached a signed-in
session — a shared laptop, a phone handed over unlocked — moved the account onto
a number they controlled, and the owner's number stopped working without the
owner ever being asked a question.

The tests below are in the order the risk runs: what it refuses first, then what
it costs a customer who mistypes, then what it does when it works.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import otp as otp_module
from apps.accounts import services
from apps.accounts import tokens as token_service
from apps.accounts.errors import (
    PhoneAlreadyRegistered,
    PhoneChangeNeedsBothCodes,
    PhoneUnchanged,
)
from apps.accounts.models import AuthToken, OtpPurpose, PhoneVerification, User
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db

OLD = "966501111111"
NEW = "966502222222"


@pytest.fixture(autouse=True)
def _no_cooldown(settings):
    """Two codes go out back to back here; the courtesy cooldown is not the subject."""
    settings.OTP_RESEND_COOLDOWN_SECONDS = 0


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Every message the provider was handed, in order."""
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


@pytest.fixture
def user() -> User:
    return User.objects.create_user(phone=OLD, full_name="صاحب الحساب")


def codes_for(phone: str) -> str:
    """The digits actually sent to ``phone``, recovered by brute force.

    Six digits, one hash, and this is a test — the alternative is a fixture that
    plants a known hash, which would stop exercising `generate_code`.
    """
    row = PhoneVerification.objects.filter(
        phone=phone, purpose=OtpPurpose.CHANGE_PHONE
    ).latest("created_at")
    for candidate in range(1_000_000):
        digits = f"{candidate:06d}"
        if otp_module.codes_match(digits, row.code_hash):
            return digits
    raise AssertionError(f"no code matched the hash stored for {phone}")


def start(user: User, new_phone: str = NEW) -> dict:
    return services.start_phone_change(user=user, new_phone=new_phone)


# ---------------------------------------------------------------------------
# The acceptance criterion: one code is never enough
# ---------------------------------------------------------------------------


def test_the_old_code_alone_does_not_move_the_account(user, sent):
    start(user)
    right = codes_for(OLD)

    with pytest.raises(PhoneChangeNeedsBothCodes):
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code=right, new_code="000000"
        )

    user.refresh_from_db()
    assert user.phone == OLD


def test_the_new_code_alone_does_not_move_the_account(user, sent):
    start(user)
    right = codes_for(NEW)

    with pytest.raises(PhoneChangeNeedsBothCodes):
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code="000000", new_code=right
        )

    user.refresh_from_db()
    assert user.phone == OLD


def test_the_refusal_does_not_say_which_half_was_right(user, sent):
    """Otherwise whoever holds one phone can test the other, one guess at a time."""
    start(user)

    with pytest.raises(PhoneChangeNeedsBothCodes) as old_half:
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code=codes_for(OLD), new_code="000000"
        )

    start(user)

    with pytest.raises(PhoneChangeNeedsBothCodes) as new_half:
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code="000000", new_code=codes_for(NEW)
        )

    assert old_half.value.user_message == new_half.value.user_message
    assert old_half.value.code == new_half.value.code


# ---------------------------------------------------------------------------
# What a mistyped code costs
# ---------------------------------------------------------------------------


def test_a_typo_in_one_code_does_not_spend_the_other(user, sent):
    """The reason both codes are judged before either is consumed.

    Calling the single-code check twice would consume the right one, and the
    customer would need two fresh messages — which T602's five-an-hour limit
    then meters, so a couple of fumbles lock them out for an hour.
    """
    start(user)
    right_old, right_new = codes_for(OLD), codes_for(NEW)

    with pytest.raises(PhoneChangeNeedsBothCodes):
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code=right_old, new_code="000000"
        )

    # The same pair of codes, typed correctly this time, still works.
    services.confirm_phone_change(
        user=user, new_phone=NEW, current_code=right_old, new_code=right_new
    )

    user.refresh_from_db()
    assert user.phone == NEW


def test_the_attempt_is_counted_against_the_wrong_code_only(user, sent):
    """A correct code must not lose an attempt because its partner was mistyped."""
    start(user)
    right_old = codes_for(OLD)

    with pytest.raises(PhoneChangeNeedsBothCodes):
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code=right_old, new_code="000000"
        )

    old_row = PhoneVerification.objects.filter(phone=OLD).latest("created_at")
    new_row = PhoneVerification.objects.filter(phone=NEW).latest("created_at")

    assert old_row.attempts == 0
    assert new_row.attempts == 1


def test_the_attempt_budget_actually_empties(user, sent, settings):
    """T601's bug, checked on this path too: a count rolled back is no budget."""
    start(user)
    right_old = codes_for(OLD)

    for _ in range(settings.OTP_MAX_ATTEMPTS):
        with pytest.raises(PhoneChangeNeedsBothCodes):
            services.confirm_phone_change(
                user=user, new_phone=NEW, current_code=right_old, new_code="000000"
            )

    new_row = PhoneVerification.objects.filter(phone=NEW).latest("created_at")

    assert new_row.attempts == settings.OTP_MAX_ATTEMPTS
    assert new_row.voided_at is not None


# ---------------------------------------------------------------------------
# What it refuses before a message ever goes out
# ---------------------------------------------------------------------------


def test_a_number_that_opens_another_account_is_refused_before_any_code(user, sent):
    """Sending there would ring a stranger's phone about a change they never asked for."""
    User.objects.create_user(phone=NEW, full_name="شخص آخر")

    with pytest.raises(PhoneAlreadyRegistered):
        start(user)

    assert sent == []


def test_changing_to_the_number_you_already_have_is_refused(user, sent):
    with pytest.raises(PhoneUnchanged):
        start(user, new_phone=OLD)

    assert sent == []


def test_a_number_registered_between_the_two_steps_is_still_refused(user, sent):
    """The check is re-read inside the lock, not trusted from step one."""
    start(user)
    right_old, right_new = codes_for(OLD), codes_for(NEW)

    User.objects.create_user(phone=NEW, full_name="سبقه غيره")

    with pytest.raises(PhoneAlreadyRegistered):
        services.confirm_phone_change(
            user=user, new_phone=NEW, current_code=right_old, new_code=right_new
        )

    user.refresh_from_db()
    assert user.phone == OLD


def test_both_numbers_are_sent_a_code(user, sent):
    result = start(user)

    assert [message["phone"] for message in sent] == [OLD, NEW]
    assert result["sent_to_current"] and result["sent_to_new"]


def test_no_code_comes_back_in_the_response(user, sent):
    """T601's hardest rule, on this path too."""
    result = start(user)
    digits = codes_for(NEW)

    assert digits not in str(result)


# ---------------------------------------------------------------------------
# What it does when it works
# ---------------------------------------------------------------------------


def test_both_codes_move_the_account_and_spend_the_codes(user, sent):
    start(user)
    right_old, right_new = codes_for(OLD), codes_for(NEW)

    services.confirm_phone_change(
        user=user, new_phone=NEW, current_code=right_old, new_code=right_new
    )

    user.refresh_from_db()
    assert user.phone == NEW
    assert user.phone_verified_at is not None

    for phone in (OLD, NEW):
        row = PhoneVerification.objects.filter(phone=phone).latest("created_at")
        assert row.consumed_at is not None, f"the code for {phone} was not spent"


def test_a_spent_pair_cannot_be_replayed(user, sent):
    start(user)
    right_old, right_new = codes_for(OLD), codes_for(NEW)
    services.confirm_phone_change(
        user=user, new_phone=NEW, current_code=right_old, new_code=right_new
    )

    third = "966503333333"
    with pytest.raises(Exception) as replay:
        services.confirm_phone_change(
            user=user, new_phone=third, current_code=right_old, new_code=right_new
        )

    assert not User.objects.filter(phone=third).exists()
    assert replay.value.__class__.__name__ != "PhoneUnchanged"


def test_every_session_is_revoked_because_the_number_changed(user, sent):
    """If the change was a takeover, this is what ends it."""
    token_service.issue_pair(user)
    token_service.issue_pair(user)
    assert AuthToken.objects.filter(user=user, revoked_at__isnull=True).exists()

    start(user)
    services.confirm_phone_change(
        user=user,
        new_phone=NEW,
        current_code=codes_for(OLD),
        new_code=codes_for(NEW),
    )

    assert not AuthToken.objects.filter(user=user, revoked_at__isnull=True).exists()


def test_the_change_is_audited_with_both_numbers(user, sent):
    start(user)
    services.confirm_phone_change(
        user=user,
        new_phone=NEW,
        current_code=codes_for(OLD),
        new_code=codes_for(NEW),
    )

    entry = AuditLog.objects.get(action="accounts.change_phone")

    assert entry.before["phone"] == OLD
    assert entry.after["phone"] == NEW
    assert entry.actor_id == user.pk


def test_an_expired_code_is_named_as_expired_not_as_a_wrong_pair(user, sent, settings):
    """A stale code and a mistyped one are different problems for the customer."""
    start(user)
    # Both timestamps move, not just one: the table refuses a row that expires
    # before it was created (`otp_expires_after_creation`), so ageing a code
    # means ageing the whole row the way real time would have.
    aged = timezone.now() - timedelta(hours=1)
    PhoneVerification.objects.filter(phone=NEW).update(
        created_at=aged, expires_at=aged + timedelta(seconds=1)
    )

    with pytest.raises(Exception) as refusal:
        services.confirm_phone_change(
            user=user,
            new_phone=NEW,
            current_code=codes_for(OLD),
            new_code="000000",
        )

    assert refusal.value.code == "otp_expired"


# ---------------------------------------------------------------------------
# The endpoints
# ---------------------------------------------------------------------------


@pytest.fixture
def signed_in(user) -> tuple[APIClient, User]:
    api = APIClient()
    pair = token_service.issue_pair(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return api, user


def test_the_endpoints_refuse_a_caller_who_is_not_signed_in():
    api = APIClient()

    assert api.post(
        reverse("accounts_api:start-phone-change"), {"new_phone": NEW}, format="json"
    ).status_code in (401, 403)


def test_the_number_being_left_is_read_off_the_token_not_the_body(signed_in, sent):
    """A body that could name the current number would move somebody else's account."""
    api, user = signed_in
    victim = User.objects.create_user(phone="966509999999", full_name="ضحية")

    api.post(
        reverse("accounts_api:start-phone-change"),
        {"new_phone": NEW, "phone": victim.phone, "user": victim.pk},
        format="json",
    )

    assert [message["phone"] for message in sent] == [OLD, NEW]
    victim.refresh_from_db()
    assert victim.phone == "966509999999"


def test_the_whole_flow_over_http(signed_in, sent):
    api, user = signed_in

    started = api.post(
        reverse("accounts_api:start-phone-change"), {"new_phone": NEW}, format="json"
    )
    assert started.status_code == 200

    confirmed = api.post(
        reverse("accounts_api:confirm-phone-change"),
        {
            "new_phone": NEW,
            "current_code": codes_for(OLD),
            "new_code": codes_for(NEW),
        },
        format="json",
    )

    assert confirmed.status_code == 200
    assert confirmed.data["phone"] == NEW

    user.refresh_from_db()
    assert user.phone == NEW


def test_one_wrong_code_over_http_is_a_409_with_the_shared_code(signed_in, sent):
    api, user = signed_in
    api.post(
        reverse("accounts_api:start-phone-change"), {"new_phone": NEW}, format="json"
    )

    response = api.post(
        reverse("accounts_api:confirm-phone-change"),
        {"new_phone": NEW, "current_code": codes_for(OLD), "new_code": "000000"},
        format="json",
    )

    assert response.status_code == 409
    assert response.data["error"]["code"] == "phone_change_needs_both_codes"
