"""T601 — a code goes out, a correct one comes back, two tokens are issued.

The four endings phase 007 names for this task each have a test below: a correct
code, an expired one, one guessed too many times, and one used twice. The rest
guard the rule that is easiest to break by accident and worst to break at all —
that the code never appears in a response.
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
from apps.accounts.errors import OtpIncorrect
from apps.accounts.models import AuthToken, PhoneVerification, TokenKind, User

pytestmark = pytest.mark.django_db

PHONE = "966501234567"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture what the SMS seam was handed, instead of logging it."""
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


def code_from(message: str) -> str:
    """Pull the digits out of the SMS the way a customer reads them off a screen."""
    return "".join(ch for ch in message.split("\n")[0] if ch.isdigit())


def send(api: APIClient, phone: str = PHONE):
    return api.post(reverse("accounts_api:send-code"), {"phone": phone}, format="json")


NAME = "إبراهيم المحي"


def verify(api: APIClient, code: str, phone: str = PHONE, **extra):
    """Sign in. Carries a name by default: every path that opens a *new* account
    must, and passing it on a sign-in to an existing one is ignored."""
    body = {"phone": phone, "code": code, "full_name": NAME}
    body.update(extra)
    return api.post(reverse("accounts_api:verify-code"), body, format="json")


def refresh(api: APIClient, token: str):
    return api.post(reverse("accounts_api:refresh"), {"refresh": token}, format="json")


# --------------------------------------------------------------------------
# The four endings T601 names
# --------------------------------------------------------------------------


def test_a_correct_code_returns_an_access_and_a_refresh_token(api, sent):
    send(api)
    response = verify(api, code_from(sent[0]["body"]))

    assert response.status_code == 200
    assert response.data["access"]
    assert response.data["refresh"]
    assert response.data["expires_in"] == 900
    assert response.data["user"]["phone"] == PHONE
    assert response.data["user"]["is_new"] is True

    assert AuthToken.objects.filter(kind=TokenKind.ACCESS).count() == 1
    assert AuthToken.objects.filter(kind=TokenKind.REFRESH).count() == 1


def test_an_expired_code_is_refused(api, sent):
    send(api)
    code = code_from(sent[0]["body"])

    # Shift the whole row into the past, not just its expiry: the table refuses
    # a code that expires before it was created, and that constraint is right.
    verification = PhoneVerification.objects.get()
    verification.created_at = timezone.now() - timedelta(hours=1)
    verification.expires_at = timezone.now() - timedelta(seconds=1)
    verification.save(update_fields=["created_at", "expires_at"])

    response = verify(api, code)

    assert response.status_code == 409
    assert response.data["error"]["code"] == "otp_expired"
    assert not User.objects.filter(phone=PHONE).exists()


def test_too_many_wrong_guesses_burn_the_code(api, sent, settings):
    send(api)
    code = code_from(sent[0]["body"])
    wrong = "000000" if code != "000000" else "111111"

    for attempt in range(settings.OTP_MAX_ATTEMPTS - 1):
        refused = verify(api, wrong)
        assert refused.data["error"]["code"] == "otp_incorrect", attempt

    spent = verify(api, wrong)
    assert spent.data["error"]["code"] == "otp_too_many_attempts"

    # And the real code is dead too — the budget belongs to the code, not to the
    # guess. Otherwise an attacker spends the budget and the customer's own
    # correct code still opens the account for whoever asks next.
    after = verify(api, code)
    assert after.status_code == 409
    assert after.data["error"]["code"] in {"otp_expired", "otp_too_many_attempts"}


def test_a_code_cannot_be_used_twice(api, sent):
    send(api)
    code = code_from(sent[0]["body"])

    assert verify(api, code).status_code == 200

    second = verify(api, code)
    assert second.status_code == 409
    assert second.data["error"]["code"] == "otp_already_used"


# --------------------------------------------------------------------------
# The code never comes back
# --------------------------------------------------------------------------


def test_the_response_never_carries_the_code(api, sent):
    response = send(api)
    code = code_from(sent[0]["body"])

    assert response.status_code == 200
    assert code not in str(response.data)
    assert code not in response.content.decode()
    assert set(response.data) == {"sent", "expires_at", "resend_after"}


def test_the_stored_row_holds_a_digest_not_the_code(api, sent):
    send(api)
    code = code_from(sent[0]["body"])

    verification = PhoneVerification.objects.get()
    assert verification.code_hash != code
    assert verification.code_hash == otp_module.hash_code(code)


def test_an_unknown_number_is_refused_without_a_row(api):
    response = verify(api, "123456", phone="966509999999")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "otp_not_found"


# --------------------------------------------------------------------------
# Sending twice
# --------------------------------------------------------------------------


def test_a_resend_is_refused_while_the_first_code_is_young(api, sent):
    send(api)
    again = send(api)

    assert again.status_code == 409
    assert again.data["error"]["code"] == "otp_resend_too_soon"
    assert len(sent) == 1


def test_a_resend_after_the_cooldown_voids_the_first_code(api, sent, settings):
    send(api)
    first_code = code_from(sent[0]["body"])

    stale = PhoneVerification.objects.get()
    stale.created_at = timezone.now() - timedelta(
        seconds=settings.OTP_RESEND_COOLDOWN_SECONDS + 1
    )
    stale.save(update_fields=["created_at"])

    send(api)
    assert len(sent) == 2

    # The old code is now simply the wrong digits for the code that is live —
    # which is what the customer is told. Saying "expired" would mean keeping
    # the dead row addressable, and two rows a guess can be checked against.
    refused = verify(api, first_code)
    assert refused.status_code == 409
    assert refused.data["error"]["code"] == "otp_incorrect"
    assert PhoneVerification.objects.filter(voided_at__isnull=False).count() == 1


def test_a_badly_shaped_number_never_reaches_the_provider(api, sent):
    response = send(api, phone="0501234567")
    assert response.status_code == 400
    assert sent == []


# --------------------------------------------------------------------------
# The tokens
# --------------------------------------------------------------------------


def signed_in(api, sent) -> dict:
    send(api)
    response = verify(api, code_from(sent[-1]["body"]))
    assert response.status_code == 200
    return dict(response.data)


def test_the_access_token_authenticates_a_request(api, sent):
    pair = signed_in(api, sent)

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    assert api.get("/api/v1/wallet/").status_code == 200


def test_an_unknown_bearer_token_is_refused(api):
    api.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    assert api.get("/api/v1/wallet/").status_code == 401


def test_an_expired_access_token_is_refused(api, sent):
    pair = signed_in(api, sent)

    AuthToken.objects.filter(kind=TokenKind.ACCESS).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    assert api.get("/api/v1/wallet/").status_code == 401


def test_a_refresh_token_is_exchanged_for_a_new_pair(api, sent):
    first = signed_in(api, sent)
    second = refresh(api, first["refresh"])

    assert second.status_code == 200
    assert second.data["access"] != first["access"]
    assert second.data["refresh"] != first["refresh"]


def test_a_reused_refresh_token_logs_the_whole_chain_out(api, sent):
    first = signed_in(api, sent)
    second = refresh(api, first["refresh"]).data

    replayed = refresh(api, first["refresh"])
    assert replayed.status_code == 409
    assert replayed.data["error"]["code"] == "refresh_token_reused"

    # Both parties are out, not only the one that replayed.
    assert refresh(api, second["refresh"]).status_code == 409
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {second['access']}")
    assert api.get("/api/v1/wallet/").status_code == 401


def test_an_unknown_refresh_token_is_refused(api):
    response = refresh(api, "nonsense")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "invalid_refresh_token"


def test_a_second_sign_in_reuses_the_account(api, sent, settings):
    settings.OTP_RESEND_COOLDOWN_SECONDS = 0

    for _ in range(2):
        signed_in(api, sent)

    assert User.objects.filter(phone=PHONE).count() == 1


def test_tokens_are_stored_as_digests_not_as_themselves():
    user = User.objects.create_user(phone=PHONE, full_name="إبراهيم")
    pair = token_service.issue_pair(user)

    stored = set(AuthToken.objects.values_list("token_hash", flat=True))
    assert pair["access"] not in stored
    assert pair["refresh"] not in stored
    assert len(stored) == 2


def test_a_deactivated_user_cannot_use_a_live_token():
    user = User.objects.create_user(phone=PHONE, full_name="إبراهيم")
    pair = token_service.issue_pair(user)

    user.is_active = False
    user.save(update_fields=["is_active"])

    assert token_service.resolve_access(pair["access"]) is None


def test_the_service_refuses_a_wrong_code_without_a_view(settings, sent):
    services.send_verification_code(phone=PHONE)

    with pytest.raises(OtpIncorrect) as refused:
        services.check_verification_code(phone=PHONE, code="999999")

    assert refused.value.detail["attempts_left"] == settings.OTP_MAX_ATTEMPTS - 1


# --------------------------------------------------------------------------
# Opening an account needs a name — and asking for one must not cost a code
# --------------------------------------------------------------------------


def test_a_new_number_without_a_name_is_refused(api, sent):
    send(api)
    response = verify(api, code_from(sent[0]["body"]), full_name="")

    assert response.status_code == 409
    assert response.data["error"]["code"] == "registration_needs_name"
    assert not User.objects.filter(phone=PHONE).exists()


def test_being_asked_for_a_name_does_not_burn_the_code(api, sent):
    send(api)
    code = code_from(sent[0]["body"])

    verify(api, code, full_name="")
    second = verify(api, code)

    assert second.status_code == 200
    assert second.data["user"]["is_new"] is True


def test_an_existing_account_signs_in_without_sending_a_name(api, sent, settings):
    settings.OTP_RESEND_COOLDOWN_SECONDS = 0
    User.objects.create_user(phone=PHONE, full_name=NAME)

    send(api)
    response = verify(api, code_from(sent[-1]["body"]), full_name="")

    assert response.status_code == 200
    assert response.data["user"]["is_new"] is False
    assert response.data["user"]["display_name"] == NAME
