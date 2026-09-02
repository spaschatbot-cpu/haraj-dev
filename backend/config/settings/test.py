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

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

ODOO_ENABLED = False
