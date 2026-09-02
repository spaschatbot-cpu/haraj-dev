"""Deployment checks this app owns.

A system check, not a `raise` at import time. The one-time-code settings are
wrong only in a *deployed* environment, and `settings/test.py` inherits from
`prod.py` on purpose — an import-time guard there would refuse to let the test
settings load at all, which is how a rule about production ends up breaking CI.

`manage.py check --deploy` is already a blocking CI step against `prod`, so
these findings reach the same gate as Django's own.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

CONSOLE_BACKEND = "apps.accounts.sms.console_backend"


@register(Tags.security, deploy=True)
def one_time_codes_are_safe_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """The code must go to the customer's phone and nowhere else."""
    findings: list = []

    if settings.SMS_BACKEND == CONSOLE_BACKEND:
        findings.append(
            Error(
                "SMS_BACKEND is the console backend, which writes one-time codes "
                "into the application log.",
                hint="Point SMS_BACKEND at a real provider before deploying.",
                id="accounts.E001",
            )
        )

    # Six digits with an unbounded number of guesses is not a secret, it is a
    # countdown. The cap is what makes the length sufficient.
    if settings.OTP_MAX_ATTEMPTS > 10:
        findings.append(
            Warning(
                f"OTP_MAX_ATTEMPTS is {settings.OTP_MAX_ATTEMPTS}; a "
                f"{settings.OTP_CODE_DIGITS}-digit code stops being a secret "
                "once guessing is cheap.",
                hint="Five is the default, and is already generous.",
                id="accounts.W001",
            )
        )

    # An access token that outlives the working day cannot be revoked by
    # expiry, which is the only thing that limits a token stolen off a device
    # that never comes back to us.
    if settings.ACCESS_TOKEN_TTL_SECONDS > 60 * 60 * 24:
        findings.append(
            Warning(
                "ACCESS_TOKEN_TTL_SECONDS is longer than a day.",
                hint="Short access, long refresh — the refresh token is the "
                "one designed to be rotated and revoked.",
                id="accounts.W002",
            )
        )

    return findings


#: Every scope `apps.accounts.throttling` can read. Listed here rather than
#: derived from the classes so that deleting a limit is a deliberate edit in two
#: files, not a limit that quietly stops being required.
REQUIRED_THROTTLE_SCOPES = ("otp_send_phone", "otp_send_caller", "otp_verify_caller")

LOCAL_MEMORY_CACHE = "django.core.cache.backends.locmem.LocMemCache"
DUMMY_CACHE = "django.core.cache.backends.dummy.DummyCache"


@register(Tags.security, deploy=True)
def otp_rate_limits_are_real_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """A limit that is off, or that each worker counts on its own, is not a limit.

    Both findings here are `Error`, not `Warning`: an unmetered send path is a
    third party's SMS bill charged to us, and the whole reason T602 exists.
    """
    findings: list = []

    rates = getattr(settings, "OTP_THROTTLE_RATES", {})
    missing = [scope for scope in REQUIRED_THROTTLE_SCOPES if not rates.get(scope)]
    if missing:
        findings.append(
            Error(
                "OTP rate limits are not configured for: " + ", ".join(missing) + ".",
                hint="Set them in OTP_THROTTLE_RATES. An unmetered send path is "
                "a free SMS gateway for whoever finds it.",
                id="accounts.E002",
            )
        )

    # A per-process cache under N workers turns "5/hour" into "5N/hour", and
    # nothing in the settings says so. This is the difference between a limit
    # and the appearance of one.
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if backend in (LOCAL_MEMORY_CACHE, DUMMY_CACHE):
        findings.append(
            Error(
                f"The default cache is {backend}, which every worker process "
                "holds separately — so the OTP rate limits count per worker.",
                hint="Point CACHE_URL at Redis; the limits are only shared if "
                "the counter is.",
                id="accounts.E003",
            )
        )

    return findings
