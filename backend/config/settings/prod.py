"""Production.

This module is the reference environment: `test` inherits from it so that a
green test suite means something about production, not about a friendlier
local machine.
"""

from .base import *  # noqa: F403

ENVIRONMENT_NAME = env("ENVIRONMENT_NAME", default="production")  # noqa: F405

DEBUG = False

# An unset host list in production means every Host header is accepted, which
# is how host-header poisoning gets in. Fail at boot instead.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set in production")

if SECRET_KEY == INSECURE_SECRET_KEY:  # noqa: F405
    raise RuntimeError("SECRET_KEY must be set outside DEBUG")

# --------------------------------------------------------------------------
# Transport and cookies
# --------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

# Reusing connections matters here: the money engine opens a transaction per
# posting, and reconnecting on each one shows up immediately under load.
DATABASES["default"]["CONN_MAX_AGE"] = env.int(  # noqa: F405
    "CONN_MAX_AGE", default=60
)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 5)  # noqa: F405

# --------------------------------------------------------------------------
# Mail
# --------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = True

LOGGING["root"]["level"] = env("LOG_LEVEL", default="INFO")  # noqa: F405
