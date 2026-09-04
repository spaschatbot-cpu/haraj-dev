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

# Redis is optional on a developer's machine, but the base default points the
# cache at it — so with no server running, every cache touch is a 500, starting
# with staff sign-in's own throttle. Dev therefore counts in local memory
# unless CACHE_URL points elsewhere. runserver is a single process, so
# "5/hour" still means 5/hour here; and the `--deploy` gate (accounts.E003)
# refuses local memory the moment anything deployed uses it, so this default
# cannot leak into production the way a silent fallback would.
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}  # noqa: F405
