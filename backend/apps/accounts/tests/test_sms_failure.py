"""T603 — "we could not send you a code" is not "your code is wrong".

In v1 both came out of the same generic failure, so an SMS balance running out
was diagnosed from scratch every time, and the first move was always asking
customers to try again. Four things have to be true for that to stop:

1. The client gets a **distinct code**, not a 500 with an incident id.
2. The status is **503, not 409** — the platform failed, the caller did not.
3. The failure **survives the rollback** that the failed send causes. This is
   the part that is easy to get wrong and invisible when it is wrong: the row
   would simply never be there.
4. It reaches a **health screen**, so a run of them has a start time.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import services
from apps.accounts.errors import VerificationCodeUndeliverable
from apps.accounts.models import PhoneVerification, SmsFailure
from apps.accounts.sms import SmsSendFailed

pytestmark = pytest.mark.django_db

PHONE = "966501234567"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def broken_provider(monkeypatch):
    """A provider that refuses everything, the way an empty balance does."""

    def refuse(*, phone: str, body: str) -> None:
        raise SmsSendFailed("insufficient balance", provider="unifonic")

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: refuse)


@pytest.fixture
def working_provider(monkeypatch) -> list[dict]:
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


def send(api: APIClient, phone: str = PHONE):
    return api.post(reverse("accounts_api:send-code"), {"phone": phone}, format="json")


# ---------------------------------------------------------------------------
# What the customer is told
# ---------------------------------------------------------------------------


def test_a_dead_provider_says_so_instead_of_saying_nothing(api, broken_provider):
    """The acceptance criterion: a clear code, never «حدث خطأ»."""
    response = send(api)

    assert response.status_code == 503
    assert response.data["error"]["code"] == "sms_undeliverable"
    # An incident id is what a 500 hands back — a token support has to look up.
    # This failure is understood, so it does not get one.
    assert "incident" not in response.data["error"]["detail"]
    assert (
        response.data["error"]["message"] == "تعذّر إرسال رمز التحقق الآن. جرّب بعد قليل."
    )


def test_the_outage_is_not_a_409_because_the_caller_did_nothing_wrong(
    api, broken_provider
):
    """Every other refusal in this app is a 409. This one must not be.

    A 409 tells the app the request was judged and refused, which invites it to
    show the sentence and stop. A 503 says "not now" and invites a retry — and
    keeps our provider's outage out of the customer's error budget.
    """
    assert send(api).status_code == 503


def test_a_wrong_code_and_a_dead_provider_are_different_answers(
    api, working_provider, broken_provider
):
    """The distinction the whole task is about, asserted side by side."""
    outage = send(api)

    assert outage.status_code == 503
    assert outage.data["error"]["code"] == "sms_undeliverable"

    wrong = api.post(
        reverse("accounts_api:verify-code"),
        {"phone": PHONE, "code": "000000", "full_name": "مجرِّب"},
        format="json",
    )

    assert wrong.status_code == 409
    assert wrong.data["error"]["code"] != "sms_undeliverable"


# ---------------------------------------------------------------------------
# The record — and the rollback it has to survive
# ---------------------------------------------------------------------------


def test_the_failure_is_written_even_though_the_send_rolled_back(broken_provider):
    """The heart of T603.

    `_send_verification_code` sends inside its atomic block on purpose, so the
    provider failing takes the unsent code's row with it. A failure record
    written inside that block would be taken with it too — and the evidence
    would be missing at exactly the moment it was worth having. Same shape as
    the bug T601 found in `check_verification_code`.
    """
    with pytest.raises(VerificationCodeUndeliverable):
        services.send_verification_code(phone=PHONE)

    failure = SmsFailure.objects.get()

    assert failure.phone == PHONE
    assert failure.provider == "unifonic"
    assert "insufficient balance" in failure.reason


def test_no_code_is_left_recorded_that_nobody_was_ever_told(broken_provider):
    """The rollback the record has to survive is a rollback we still want.

    A `PhoneVerification` row surviving a failed send would be a code the
    customer never received but the system would happily accept.
    """
    with pytest.raises(VerificationCodeUndeliverable):
        services.send_verification_code(phone=PHONE)

    assert not PhoneVerification.objects.filter(phone=PHONE).exists()
    assert SmsFailure.objects.count() == 1


def test_a_provider_that_names_no_backend_is_still_attributed(monkeypatch):
    """`SmsSendFailed` may carry no provider; the configured one is the answer.

    A failure row that says "" under provider is a row that answers nothing when
    two providers are being compared.
    """

    def refuse(*, phone: str, body: str) -> None:
        raise SmsSendFailed("gateway timeout")

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: refuse)

    with pytest.raises(VerificationCodeUndeliverable):
        services.send_verification_code(phone=PHONE)

    assert SmsFailure.objects.get().provider != ""


def test_a_successful_send_records_no_failure(working_provider):
    services.send_verification_code(phone=PHONE)

    assert SmsFailure.objects.count() == 0
    assert working_provider


# ---------------------------------------------------------------------------
# Reaching a health screen
# ---------------------------------------------------------------------------


def test_the_count_is_the_window_not_the_whole_table():
    """Forty failures last March is history; forty in the last hour is an outage."""
    SmsFailure.objects.create(provider="p", phone=PHONE, reason="old")
    SmsFailure.objects.filter(reason="old").update(
        created_at=timezone.now() - timedelta(days=2)
    )
    SmsFailure.objects.create(provider="p", phone=PHONE, reason="now")

    assert services.recent_sms_failures() == 1
    assert services.recent_sms_failures(within=timedelta(days=7)) == 2


def test_health_reports_the_provider_refusing(client, broken_provider, api):
    with pytest.raises(VerificationCodeUndeliverable):
        services.send_verification_code(phone=PHONE)

    body = client.get("/health").json()

    assert body["checks"]["sms"] == {
        "ok": False,
        "reason": "provider_refusing",
        "failures_last_hour": 1,
    }
    # Degraded, not down: an SMS outage is not a reason to pull the service out
    # of a load balancer, and the sign-in path already answers 503 by itself.
    assert body["status"] == "degraded"


def test_health_is_quiet_when_the_provider_is_carrying_messages(client):
    body = client.get("/health").json()

    assert body["checks"]["sms"]["ok"] is True
    assert body["checks"]["sms"]["failures_last_hour"] == 0
