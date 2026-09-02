"""Deployment checks this app owns.

A system check rather than a `raise` at import: `settings/test.py` inherits from
`prod.py` on purpose, so a guard at import time there would stop the test
settings loading at all — a rule about production breaking CI. `check --deploy`
is already a blocking CI step, so a finding here reaches the same gate.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Tags, Warning, register


@register(Tags.security, deploy=True)
def bidding_is_metered_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """The half that keeps T611's "off when unset" honest.

    A `Warning` rather than an `Error`, and the difference from the OTP checks
    is deliberate: an unmetered send path is somebody else's bill charged to us,
    while an unmetered bid path is a busy last minute and an oracle that takes
    real effort to read. Serious, not "refuse to deploy".
    """
    rates = getattr(settings, "BID_THROTTLE_RATES", {})
    if rates.get("bid_caller"):
        return []

    return [
        Warning(
            "BID_THROTTLE_RATES has no rate for 'bid_caller', so bidding is "
            "unmetered in this environment.",
            hint="A script racing the close makes fifty transactions the rest "
            "of the auction queues behind, and every refusal names the "
            "bidder's own numbers — unmetered, that is an oracle.",
            id="bidding.W001",
        )
    ]
