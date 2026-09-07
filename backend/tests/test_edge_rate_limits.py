"""T914 — the limits at the edge, and the header that used to lift all of them.

Behaviour, never infrastructure. Redis is not a CI dependency and never becomes
one here: every test below uses a `locmem` cache of its own, because what is
being proved is *what the limit does*, and "the counter is shared between
workers" is `apps.accounts.checks`'s job — it refuses a deployed environment on
a per-process cache, and `test_the_deploy_audit...` below holds it to that.

Each test switches on the one scope it is about. `settings/test.py` empties
`EDGE_THROTTLE_RATES` so 1,200 tests do not share an hourly counter.
"""

from __future__ import annotations

import json
import time

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse

from apps.core import ratelimit
from apps.core.net import client_ip
from apps.odoo.signing import expected_signature

pytestmark = pytest.mark.django_db

SECRET = "test-webhook-secret"


@pytest.fixture(autouse=True)
def _own_counter(settings):
    """A cache nobody else wrote to, so a count asserted on is this test's."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "edge-rate-limits",
        }
    }
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# Who is calling — the number every per-address limit rests on
# ---------------------------------------------------------------------------


class TestWhoIsCalling:
    """The finding: with no trusted proxy configured, the forwarded header was
    read anyway, so a caller rotating it got a fresh budget on every request.

    DRF's default made it worse than the hand-written version: unset
    `NUM_PROXIES` keys the throttle on the *whole* header, so
    `X-Forwarded-For: 1.1.1.1, 2.2.2.2` and `X-Forwarded-For: 1.1.1.1,2.2.2.3`
    are two different callers. One header and a loop, and the metered OTP send
    path is unmetered again — the exact v1 hole T602 closed.
    """

    def request_from(self, remote: str, forwarded: str | None = None):
        extra = {"REMOTE_ADDR": remote}
        if forwarded is not None:
            extra["HTTP_X_FORWARDED_FOR"] = forwarded
        return RequestFactory().get("/", **extra)

    def test_with_no_proxy_the_header_is_ignored(self, settings):
        settings.TRUSTED_PROXY_HOPS = 0

        assert client_ip(self.request_from("10.0.0.9", "1.2.3.4")) == "10.0.0.9"

    def test_rotating_the_header_does_not_change_who_is_counted(self, settings):
        settings.TRUSTED_PROXY_HOPS = 0

        seen = {client_ip(self.request_from("10.0.0.9", f"9.9.9.{n}")) for n in range(50)}

        assert seen == {"10.0.0.9"}

    def test_behind_one_proxy_the_last_entry_is_read(self, settings):
        """Everything left of the last hop was written by the caller."""
        settings.TRUSTED_PROXY_HOPS = 1

        who = client_ip(self.request_from("10.0.0.1", "1.1.1.1, 203.0.113.7"))

        assert who == "203.0.113.7"

    def test_drf_reads_the_same_number(self, settings):
        """Two answers to "who is calling" would be two different rate limits."""
        assert settings.REST_FRAMEWORK["NUM_PROXIES"] == settings.TRUSTED_PROXY_HOPS


class TestTheOtpLimitSurvivesTheHeader:
    """The exploit that made the header finding worth fixing.

    Five messages an hour to one number is the courtesy limit; twenty an hour
    from one caller is the one that stops somebody walking the numbering plan,
    and it is the one that pays the SMS bill. Rotating a header must not buy a
    fresh twenty.
    """

    def send(self, client, phone: str, forwarded: str):
        return client.post(
            reverse("accounts_api:send-code"),
            data={"phone": phone},
            content_type="application/json",
            HTTP_X_FORWARDED_FOR=forwarded,
            REMOTE_ADDR="10.0.0.9",
        )

    def test_a_rotating_forwarded_header_does_not_buy_more_messages(
        self, client, settings
    ):
        settings.TRUSTED_PROXY_HOPS = 0
        settings.OTP_THROTTLE_RATES = {"otp_send_caller": "3/hour"}

        # Each request claims to come from somewhere new, and walks a different
        # number so the per-phone limit is not what refuses it.
        codes = [
            self.send(client, f"96650000{n:04d}", f"9.9.9.{n}").status_code
            for n in range(5)
        ]

        assert 429 in codes


# ---------------------------------------------------------------------------
# The webhook boundaries
# ---------------------------------------------------------------------------


class TestThePaymentCallbackIsMetered:
    """It stores a row per request and needs no credential to be reached.

    Until T914 there was no ceiling on it at all: a stranger could write rows
    until the disk filled, and every one of them cost us a database round trip
    at whatever rate they could manage.
    """

    def post(self, client):
        return client.post(
            reverse("money:payment-callback"),
            data=json.dumps({"id": "x", "status": "paid"}),
            content_type="application/json",
            HTTP_X_SIGNATURE="0" * 64,
        )

    def test_over_the_ceiling_it_answers_429(self, client, settings):
        settings.PAYMENT_WEBHOOK_SECRET = "gateway-secret"
        settings.EDGE_THROTTLE_RATES = {"payment_callback": "2/minute"}

        first = [self.post(client).status_code for _ in range(2)]
        over = self.post(client)

        assert first == [401, 401]  # stored and refused, as before
        assert over.status_code == 429

    def test_under_the_ceiling_nothing_changes(self, client, settings):
        settings.PAYMENT_WEBHOOK_SECRET = "gateway-secret"
        settings.EDGE_THROTTLE_RATES = {"payment_callback": "10/minute"}

        assert self.post(client).status_code == 401


class TestTheOdooWebhookCeilingIsASetting:
    def test_it_can_be_turned_without_editing_code(self, client, settings):
        settings.ODOO_WEBHOOK_SECRET = SECRET
        settings.ODOO_DB = "haraj_prod"
        settings.EDGE_THROTTLE_RATES = {"odoo_webhook": "1/minute"}

        assert _signed_post(client, {"delivery_id": "A"}).status_code == 200
        assert _signed_post(client, {"delivery_id": "B"}).status_code == 429


# ---------------------------------------------------------------------------
# Staff sign-in
# ---------------------------------------------------------------------------


class TestStaffSignInIsMetered:
    """A password path, and the passwords behind it open `money.act`."""

    def attempt(self, client, phone="966500000099", password="wrong"):
        return client.post(
            "/admin/login/",
            data={"username": phone, "password": password, "next": "/admin/"},
            REMOTE_ADDR="10.0.0.9",
        )

    def test_guessing_one_account_runs_out(self, client, settings, staff):
        settings.EDGE_THROTTLE_RATES = {"staff_login_account": "3/hour"}

        codes = [self.attempt(client).status_code for _ in range(4)]

        assert codes[-1] == 429
        assert 429 not in codes[:3]

    def test_spraying_one_password_across_accounts_runs_out_too(
        self, client, settings, staff
    ):
        """The per-account limit alone does not see this: every attempt names a
        different account, so no account's budget is ever spent twice."""
        settings.EDGE_THROTTLE_RATES = {"staff_login_ip": "3/hour"}

        codes = [
            self.attempt(client, phone=f"96650000{n:04d}").status_code for n in range(4)
        ]

        assert codes[-1] == 429

    def test_the_refusal_does_not_say_whether_the_account_exists(
        self, client, settings, staff
    ):
        settings.EDGE_THROTTLE_RATES = {"staff_login_ip": "1/hour"}

        self.attempt(client)
        known = self.attempt(client, phone=staff.phone)
        unknown = self.attempt(client, phone="966500000000")

        assert known.status_code == unknown.status_code == 429
        assert known.content == unknown.content

    def test_the_form_itself_is_never_refused(self, client, settings, staff):
        """Metering GET would let anyone lock the sign-in page for an office."""
        settings.EDGE_THROTTLE_RATES = {"staff_login_ip": "1/hour"}

        self.attempt(client)
        self.attempt(client)

        assert client.get("/admin/login/").status_code == 200


# ---------------------------------------------------------------------------
# The counter itself
# ---------------------------------------------------------------------------


class TestTheCounter:
    def test_an_unset_scope_is_off_rather_than_an_error(self, settings):
        settings.EDGE_THROTTLE_RATES = {}

        assert ratelimit.consume("odoo_webhook", "1.1.1.1").allowed

    def test_an_unreadable_rate_raises_rather_than_meaning_unlimited(self):
        with pytest.raises(ValueError):
            ratelimit.parse_rate("600 per minute")

    def test_two_callers_do_not_share_a_budget(self, settings):
        settings.EDGE_THROTTLE_RATES = {"odoo_webhook": "1/minute"}

        assert ratelimit.consume("odoo_webhook", "a").allowed
        assert ratelimit.consume("odoo_webhook", "b").allowed
        assert not ratelimit.consume("odoo_webhook", "a").allowed


class TestTheDeployAuditHoldsTheseToBeReal:
    """ "Off by default" is only safe because it is loud."""

    def test_a_deployed_environment_with_no_edge_limits_is_refused(self, settings):
        from apps.core.checks import the_edge_is_metered_in_a_deployed_environment

        settings.EDGE_THROTTLE_RATES = {}

        findings = the_edge_is_metered_in_a_deployed_environment(None)

        assert [f.id for f in findings] == ["core.E004"]

    def test_a_deployed_environment_whose_two_proxy_numbers_disagree_is_refused(
        self, settings
    ):
        from apps.core.checks import the_edge_is_metered_in_a_deployed_environment

        settings.TRUSTED_PROXY_HOPS = 1
        settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": None}
        settings.EDGE_THROTTLE_RATES = {
            "odoo_webhook": "1/minute",
            "payment_callback": "1/minute",
            "staff_login_ip": "1/hour",
            "staff_login_account": "1/hour",
        }

        findings = the_edge_is_metered_in_a_deployed_environment(None)

        assert [f.id for f in findings] == ["core.E006"]

    def test_a_per_process_cache_is_refused(self, settings):
        """A limit each worker counts on its own is 'five an hour' times N."""
        from apps.accounts.checks import (
            otp_rate_limits_are_real_in_a_deployed_environment,
        )

        settings.OTP_THROTTLE_RATES = {
            "otp_send_phone": "5/hour",
            "otp_send_caller": "20/hour",
            "otp_verify_caller": "30/hour",
        }

        findings = otp_rate_limits_are_real_in_a_deployed_environment(None)

        assert [f.id for f in findings] == ["accounts.E003"]


def _signed_post(client, payload: dict):
    body = json.dumps(payload).encode()
    stamp = str(time.time())
    return client.post(
        "/webhooks/odoo/",
        data=body,
        content_type="application/json",
        HTTP_X_ODOO_SIGNATURE=expected_signature(body, stamp, SECRET),
        HTTP_X_ODOO_TIMESTAMP=stamp,
    )
