"""/health says which environment and build this is, and never leaks a secret."""

from __future__ import annotations

import json
from unittest import mock

import pytest
from django.test import override_settings

from apps.core import views

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _forget_the_cached_commit():
    """The commit is cached for the process; each test starts from a clean read."""
    views.commit_hash.cache_clear()
    yield
    views.commit_hash.cache_clear()


class TestHealthy:
    def test_it_answers_200_without_a_login(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_it_names_the_environment_and_the_build(self, client):
        with override_settings(ENVIRONMENT_NAME="staging", GIT_COMMIT="deadbeef" * 5):
            body = client.get("/health").json()
        assert body["environment"] == "staging"
        assert body["commit"] == ("deadbeef" * 5)[:40]

    def test_it_reports_a_real_database_round_trip(self, client):
        body = client.get("/health").json()
        assert body["checks"]["database"] == {"ok": True, "reason": "ok"}

    def test_the_commit_falls_back_to_the_checkout_when_unstamped(self, client):
        """A developer's machine stamps nothing, and the answer is still useful."""
        with override_settings(GIT_COMMIT=""):
            commit = client.get("/health").json()["commit"]
        assert commit and commit != "unknown"
        assert len(commit) == 40


class TestRedisIsOffAndSaysSo:
    """Redis is deliberately not running here. Reporting that is the job."""

    def test_an_unreachable_redis_is_reported_not_raised(self, client):
        with mock.patch.object(
            views, "_check_redis", return_value=(False, "unreachable")
        ):
            response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["redis"] == {"ok": False, "reason": "unreachable"}

    def test_the_real_check_never_raises(self):
        """Whatever Redis is doing, this returns a pair rather than an exception."""
        ok, reason = views._check_redis()
        assert isinstance(ok, bool)
        assert reason in {"ok", "unreachable", "not_configured"}

    def test_a_broker_that_is_not_redis_is_reported_as_unconfigured(self):
        with override_settings(CELERY_BROKER_URL="memory://"):
            assert views._check_redis() == (False, "not_configured")


class TestUnhealthy:
    def test_a_dead_database_is_503(self, client):
        with mock.patch.object(
            views, "_check_database", return_value=(False, "unreachable")
        ):
            response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "down"
        assert body["checks"]["database"] == {"ok": False, "reason": "unreachable"}
        # Still identifies itself: knowing *which* environment is down is the
        # first thing anyone asks.
        assert body["environment"]

    def test_the_check_itself_swallows_a_broken_connection(self):
        from django.db.utils import OperationalError

        with mock.patch.object(
            views.connection, "cursor", side_effect=OperationalError("server closed")
        ):
            assert views._check_database() == (False, "unreachable")


class TestNoSecrets:
    def test_the_body_carries_nothing_that_should_stay_inside(self, client, settings):
        raw = client.get("/health").content.decode()
        for secret in (
            settings.SECRET_KEY,
            settings.DATABASES["default"].get("PASSWORD") or "haraj",
            settings.CELERY_BROKER_URL,
            settings.DATABASES["default"].get("HOST") or "127.0.0.1",
        ):
            assert secret not in raw

    def test_a_database_failure_reports_a_fixed_word_not_the_driver_message(self):
        """Connection errors from psycopg can contain the whole DSN."""
        from django.db.utils import OperationalError

        leaky = OperationalError(
            "connection failed: dbname=haraj2 user=haraj password=haraj host=db"
        )
        with mock.patch.object(views.connection, "cursor", side_effect=leaky):
            ok, reason = views._check_database()
        assert (ok, reason) == (False, "unreachable")
        assert "password" not in reason

    def test_the_response_shape_is_exactly_what_we_publish(self, client):
        body = json.loads(client.get("/health").content)
        assert set(body) == {"status", "environment", "commit", "checks"}
        assert set(body["checks"]) == {"database", "redis"}
