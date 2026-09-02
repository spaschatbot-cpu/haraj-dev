"""T602 — every path that sends a code is metered, and the meter is shared.

Three things have to be true, and each is a separate way this task fails:

1. **The limits work.** A sixth message to one number inside the hour is
   refused, and so is a script asking for one message each across many numbers.
2. **They cannot be forgotten.** `ops/checks/one_otp_rate_limit.py` fails the
   build when a send path appears without them — proved here by writing a path
   that lacks them and watching the check speak.
3. **They are real where it counts.** `check --deploy` refuses an environment
   whose rates are unset, and one whose cache each worker holds privately.

The limits are off in `settings/test.py` on purpose (736 tests sharing one
hourly counter would fail by running order), so every test below switches on
exactly the scope it is about, with a cache of its own so the count it asserts
cannot be a leftover.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.checks import (
    otp_rate_limits_are_real_in_a_deployed_environment as deploy_check,
)

pytestmark = pytest.mark.django_db

PHONE = "966501234567"

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]
SCANNED = [BACKEND / "apps", BACKEND / "config"]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    assert spec is not None and spec.loader is not None, f"{name}.py غير موجود"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def a_cache(location: str) -> dict:
    """A cache nobody else is counting in.

    Each test gets its own LOCATION: a rate limit reads a counter, and a counter
    shared with the previous test is the order-dependence this whole design is
    trying to avoid.
    """
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": location,
        }
    }


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _empty_cache():
    """Start every test with no counts, and leave none behind."""
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """Capture what the SMS seam was handed, instead of logging it."""
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


def send(api: APIClient, phone: str = PHONE):
    return api.post(reverse("accounts_api:send-code"), {"phone": phone}, format="json")


# ---------------------------------------------------------------------------
# The limits themselves
# ---------------------------------------------------------------------------


@override_settings(
    OTP_THROTTLE_RATES={"otp_send_phone": "3/hour"},
    OTP_RESEND_COOLDOWN_SECONDS=0,
    CACHES=a_cache("per-phone"),
)
def test_one_number_cannot_be_made_to_ring_all_afternoon(api, sent):
    """The cooldown expires with the code; this limit does not."""
    for _ in range(3):
        assert send(api).status_code == 200

    refused = send(api)

    assert refused.status_code == 429
    assert refused.data["error"]["code"] == "throttled"
    # The fourth message was never handed to the provider — the point of the
    # limit is the message not being paid for, not the customer seeing a 429.
    assert len(sent) == 3


@override_settings(
    OTP_THROTTLE_RATES={"otp_send_caller": "3/hour"},
    OTP_RESEND_COOLDOWN_SECONDS=0,
    CACHES=a_cache("per-caller"),
)
def test_walking_the_numbering_plan_trips_the_caller_limit(api, sent):
    """A different number each time defeats a per-number limit, and only that."""
    numbers = ["96650000000" + str(n) for n in range(4)]

    assert send(api, numbers[0]).status_code == 200
    assert send(api, numbers[1]).status_code == 200
    assert send(api, numbers[2]).status_code == 200

    assert send(api, numbers[3]).status_code == 429
    assert len(sent) == 3


@override_settings(
    OTP_THROTTLE_RATES={"otp_send_phone": "2/hour"},
    OTP_RESEND_COOLDOWN_SECONDS=0,
    CACHES=a_cache("two-numbers"),
)
def test_one_numbers_exhausted_budget_does_not_refuse_another(api, sent):
    """The per-number counter is per number, not one bucket for everybody."""
    assert send(api, "966500000001").status_code == 200
    assert send(api, "966500000001").status_code == 200
    assert send(api, "966500000001").status_code == 429

    assert send(api, "966500000002").status_code == 200


@override_settings(
    OTP_THROTTLE_RATES={"otp_verify_caller": "3/hour"},
    CACHES=a_cache("verify"),
)
def test_a_list_of_numbers_cannot_be_worked_through_five_guesses_at_a_time(api):
    """The attempt cap is per code; this is the limit that sees the list."""
    url = reverse("accounts_api:verify-code")
    body = {"phone": PHONE, "code": "000000", "full_name": "مجرِّب"}

    for _ in range(3):
        assert api.post(url, body, format="json").status_code != 429

    assert api.post(url, body, format="json").status_code == 429


@override_settings(
    OTP_THROTTLE_RATES={"otp_send_phone": "1/hour"},
    CACHES=a_cache("no-phone"),
)
def test_a_body_with_no_number_is_refused_without_spending_anyones_budget(api, sent):
    """A throttle must not crash, and must not meter a bucket it cannot name."""
    for _ in range(3):
        malformed = api.post(
            reverse("accounts_api:send-code"), {"purpose": "login"}, format="json"
        )
        assert malformed.status_code == 400

    # The real number still has its whole budget: nothing was charged to a
    # shared `None` bucket by requests that never named a number.
    assert send(api).status_code == 200


def test_the_suite_runs_with_the_limits_off(settings):
    """The decision in `settings/test.py`, asserted where it can be seen.

    If this ever fails, tests elsewhere have started sharing an hourly counter
    and will begin failing by the order they ran in.
    """
    assert settings.OTP_THROTTLE_RATES == {}


@override_settings(OTP_THROTTLE_RATES={}, CACHES=a_cache("off"))
def test_an_unconfigured_scope_means_off_not_a_crash(api, sent):
    """Missing rate → allow. The loud half of that decision is the deploy check."""
    with override_settings(OTP_RESEND_COOLDOWN_SECONDS=0):
        for _ in range(8):
            assert send(api).status_code == 200


# ---------------------------------------------------------------------------
# The check that stops a fourth path being added unmetered
# ---------------------------------------------------------------------------


def test_no_otp_path_in_the_tree_is_unmetered():
    assert load("one_otp_rate_limit").violations(SCANNED) == []


UNMETERED_VIEW = """
from rest_framework.views import APIView
from apps.accounts import services


class RecoverAccountView(APIView):
    def post(self, request):
        services.send_verification_code(phone=request.data["phone"])
"""

HAND_WRITTEN_LIMITS = """
from rest_framework.views import APIView
from apps.accounts import services
from apps.accounts.throttling import OtpSendPerPhoneThrottle


class RecoverAccountView(APIView):
    throttle_classes = [OtpSendPerPhoneThrottle]

    def post(self, request):
        services.send_verification_code(phone=request.data["phone"])
"""

EMPTY_LIMITS = """
from rest_framework.views import APIView
from apps.accounts import services


class RecoverAccountView(APIView):
    throttle_classes = []

    def post(self, request):
        services.send_verification_code(phone=request.data["phone"])
"""

VERIFY_UNMETERED = """
from rest_framework.views import APIView
from apps.accounts import services


class SecondVerifyView(APIView):
    def post(self, request):
        services.sign_in_with_code(phone="966500000000", code="1")
"""

SENDING_FROM_NOWHERE = """
from apps.accounts import services


def resend_everything(numbers):
    for number in numbers:
        services.send_verification_code(phone=number)
"""


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(UNMETERED_VIEW, id="a send path with no limits at all"),
        pytest.param(HAND_WRITTEN_LIMITS, id="limits written out by hand"),
        pytest.param(EMPTY_LIMITS, id="throttle_classes emptied"),
        pytest.param(VERIFY_UNMETERED, id="a second unmetered verify path"),
        pytest.param(SENDING_FROM_NOWHERE, id="sending outside any view"),
    ],
)
def test_the_check_speaks_when_a_path_goes_unmetered(tmp_path: Path, source: str):
    (tmp_path / "recovery.py").write_text(source, encoding="utf-8")

    found = load("one_otp_rate_limit").violations([tmp_path])

    assert found, "الفحص سكت عن مسار بلا حدّ"


def test_the_service_layer_itself_is_not_a_violation():
    """`services.py` defines these functions and calls them from each other.

    Excluding it is the one exemption in the check, and an exemption nobody
    tests is an exemption that quietly widens.
    """
    check = load("one_otp_rate_limit")
    services_file = BACKEND / "apps" / "accounts" / "services.py"

    assert check.violations([services_file.parent], service_layer=services_file) == []


# ---------------------------------------------------------------------------
# The deploy checks — a limit that is off, or counted per worker, is not a limit
# ---------------------------------------------------------------------------


@override_settings(
    OTP_THROTTLE_RATES={"otp_send_phone": "5/hour"},
    CACHES={"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": "x"}},
)
def test_a_deployed_environment_missing_a_limit_is_refused():
    ids = [finding.id for finding in deploy_check(None)]

    assert "accounts.E002" in ids


@override_settings(
    OTP_THROTTLE_RATES={
        "otp_send_phone": "5/hour",
        "otp_send_caller": "20/hour",
        "otp_verify_caller": "30/hour",
    },
    CACHES=a_cache("locmem-in-production"),
)
def test_a_per_worker_cache_makes_the_limit_a_lie_and_is_refused():
    ids = [finding.id for finding in deploy_check(None)]

    assert "accounts.E003" in ids


@override_settings(
    OTP_THROTTLE_RATES={
        "otp_send_phone": "5/hour",
        "otp_send_caller": "20/hour",
        "otp_verify_caller": "30/hour",
    },
    CACHES={"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": "x"}},
)
def test_a_properly_configured_environment_passes():
    assert deploy_check(None) == []
