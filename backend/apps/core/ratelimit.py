"""A counter in the shared cache, for the paths DRF's throttles cannot reach.

The customer API is metered by DRF (`apps.accounts.throttling`,
`apps.bidding.throttling`). Three paths are not DRF views and would otherwise
have no limit at all, which is what T914 is about:

* the **Odoo webhook**, a plain Django view;
* the **payment callback**, which had no limit and stores a row per request
  from anyone who can reach it;
* **staff sign-in**, which is Django's admin login and holds the passwords that
  open `money.act` and `money.exception`.

One implementation, so "5 an hour" means one thing (Article 4-5). A fixed
window rather than a sliding one on purpose: it is one `incr` per request
instead of a read-modify-write of a timestamp list, and at these ceilings the
difference a fixed window allows — up to twice the rate across a window
boundary — is a rounding error against limits whose job is to bound a runaway
loop and a guessing script.

**The cache is the limit.** Under gunicorn each worker holds its own local
memory, so a per-process cache turns "5 an hour" into "5N an hour" with nothing
in the settings saying so. `apps.accounts.checks` already refuses a deployed
environment on local memory; that check is what makes this module honest.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class Verdict:
    """What the counter concluded, and how long the caller should wait."""

    allowed: bool
    count: int
    limit: int
    retry_after: int


#: The window each period letter means, in seconds. Keyed on the first letter,
#: which is DRF's own reading of a rate string — so `5/h`, `5/hour` and
#: `5/hourly` all mean the same thing here as they do there.
PERIODS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_rate(rate: str) -> tuple[int, int]:
    """``"600/minute"`` → ``(600, 60)``. Raises on anything it cannot read.

    Raising rather than defaulting: a typo in a rate must be a loud failure,
    never a limit that silently became "unlimited" because the string did not
    parse.
    """
    count, separator, period = rate.partition("/")
    period = period.strip().lower()
    if not separator or not period or period[0] not in PERIODS:
        raise ValueError(f"unreadable rate {rate!r}")
    return int(count), PERIODS[period[0]]


def rate_for(scope: str) -> str | None:
    """The configured rate for ``scope``, or ``None`` meaning *off here*.

    Off is a real answer and it is deliberate: `settings/test.py` empties these
    so 1,200 tests do not share one hourly counter, and each test that proves a
    limit switches its own scope on with `override_settings`. The half that
    keeps that honest is `apps.core.checks`, which refuses a deployed
    environment with any of them missing.
    """
    rates: dict[str, str] = getattr(settings, "EDGE_THROTTLE_RATES", {})
    return rates.get(scope)


def consume(scope: str, ident: str) -> Verdict:
    """Count one request from ``ident`` against ``scope``.

    ``allowed`` is True when the limit is off, so a caller can always be
    written as ``if not consume(...).allowed: refuse()`` with no second branch
    asking whether limiting is enabled.
    """
    rate = rate_for(scope)
    if not rate:
        return Verdict(allowed=True, count=0, limit=0, retry_after=0)

    limit, window = parse_rate(rate)
    key = f"edge-rate:{scope}:{ident}"

    try:
        # `add` writes only when the key is absent, so it starts the window
        # exactly once however many requests race here. `incr` then counts.
        cache.add(key, 0, timeout=window)
        count = cache.incr(key)
    except ValueError:
        # The key expired between `add` and `incr`. That is the first request
        # of a new window, not a violation.
        cache.set(key, 1, timeout=window)
        count = 1

    return Verdict(allowed=count <= limit, count=count, limit=limit, retry_after=window)


__all__ = ["Verdict", "consume", "parse_rate", "rate_for"]
