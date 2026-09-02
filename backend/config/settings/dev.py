"""Local development.

The only settings module that relaxes anything. Nothing here may be imported
by `test` — a test that runs under gentler settings than production proves
nothing (Article 4-2).
"""

from .base import *  # noqa: F403

ENVIRONMENT_NAME = "development"

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Every connection is fresh, so a schema change is picked up without a restart.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
