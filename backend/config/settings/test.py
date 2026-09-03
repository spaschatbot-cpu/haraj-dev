"""Tests — deliberately inherits `prod`, never `dev`.

In v1 a money path passed in tests and failed in production because the local
database was configured more leniently than the real one. A test that runs
under gentler settings than production proves nothing (Article 4-2).

Only what genuinely cannot run inside CI is overridden here: real secrets,
outbound mail, and HTTPS-only transport. Everything else — the database
engine, the constraints, the password hashers — stays exactly as production
has it.
"""

from .prod import *  # noqa: F403

ENVIRONMENT_NAME = "test"

# A real value, so the production guard in prod.py is satisfied honestly
# rather than bypassed.
SECRET_KEY = "test-only-key-not-used-anywhere-else"  # noqa: S105

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

# Django's test client speaks plain HTTP; leaving the redirect on would turn
# every request in the suite into a 301 before it reached a view.
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Still PostgreSQL — the engine is never swapped (Article 4-2). Only the
# database name and the connection lifetime change.
DATABASES["default"] = env.db(  # noqa: F405
    "TEST_DATABASE_URL",
    default="postgres://haraj:haraj@127.0.0.1:5432/haraj2_test",
)
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405

# Rate limits are a production behaviour with its own tests (T602, T611);
# leaving them on globally would make every other test order-dependent.
REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {},
}

# The OTP limits are attached to their views rather than to DRF's defaults, so
# emptying the dict above does not reach them. Same reason, said again where it
# applies: 736 tests that each spend a shared hourly counter would start failing
# in the order they happen to run. `test_otp_rate_limit.py` switches each scope
# on for the one test that proves it, with `override_settings`.
OTP_THROTTLE_RATES: dict[str, str] = {}
BID_THROTTLE_RATES: dict[str, str] = {}

# Same reason a third time, for the limits that are not DRF's (T914): the Odoo
# webhook, the payment callback and staff sign-in. Hundreds of tests post to
# those boundaries, and a shared per-minute counter would make them fail in the
# order they happened to run. Each test that proves one of these limits switches
# its own scope on with `override_settings`.
EDGE_THROTTLE_RATES: dict[str, str] = {}

# Local memory, and only here. Redis is not a CI dependency, and every test that
# needs a counter overrides this with a `locmem` cache of its own so the count
# it asserts on cannot be a leftover from an earlier test.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "haraj-tests",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

ODOO_ENABLED = False
