"""T718 — the message that actually leaves carries the environment's name.

`apps/core/tests/test_environment.py` proves the decision. This file proves the
decision is *wired into the real path*: a customer asks for a code through the
API, and what the provider is handed is stamped. The two are separate on
purpose — a correct stamping function that nothing calls is exactly the shape
the v1 bug had.

Article 5-6, and the incident behind it: a test message reached a real customer,
who read it and acted on it.
"""

from __future__ import annotations

import pytest
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.sms import send_sms

pytestmark = pytest.mark.django_db

PHONE = "966501234567"


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture what the provider was handed — after the seam, not before it."""
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


def request_a_code(api: APIClient) -> None:
    api.post(reverse("accounts_api:send-code"), {"phone": PHONE}, format="json")


def test_the_otp_a_customer_receives_here_says_which_environment_sent_it(api, sent):
    """The suite runs as `test`, so the code that goes out must say so.

    This is the assertion that fails if somebody routes a new message around
    :func:`apps.accounts.sms.send_sms`.
    """
    request_a_code(api)

    assert sent, "no message reached the provider at all"
    assert sent[0]["body"].startswith("[اختبار] ")


def test_the_same_send_from_production_carries_no_stamp(api, sent):
    """A real customer gets his code and nothing else in front of it."""
    with override_settings(ENVIRONMENT_NAME="production"):
        request_a_code(api)

    assert sent[0]["body"].startswith("رمز التحقق:")


def test_a_customer_on_staging_can_still_read_his_code(api, sent):
    """The stamp warns; it must not cost the tester the thing he asked for."""
    with override_settings(ENVIRONMENT_NAME="staging"):
        request_a_code(api)

    first_line = sent[0]["body"].split("\n")[0]
    assert len("".join(ch for ch in first_line if ch.isdigit())) == 6


def test_any_message_at_all_is_stamped_not_only_the_otp(sent):
    """The guarantee is the seam's, not the OTP wording's.

    Notifications (`apps.notifications`) have no sender yet. When one is
    written, it inherits this by sending through the same function — which is
    the reason the stamp lives there and not next to `OTP_MESSAGE`.
    """
    send_sms(phone=PHONE, body="مزايدتك على السيارة تجاوزها غيرك.")

    assert sent[0]["body"] == "[اختبار] مزايدتك على السيارة تجاوزها غيرك."
