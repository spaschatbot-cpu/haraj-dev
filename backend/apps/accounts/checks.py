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
