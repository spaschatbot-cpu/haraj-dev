"""How often one bidder may act. T611.

The limit here is not about cost the way T602's is — a bid sends no SMS. It is
about the two things a bidding endpoint invites:

* **A script racing the close.** `place_bid` already serialises on the vehicle
  row (T504), so a flood is correct rather than corrupting — but fifty threads
  queueing on one row is fifty transactions the rest of the auction waits
  behind. The limit keeps one caller from making the last minute of an auction
  everybody else's problem.
* **Probing the eligibility gate.** Every refusal names its reason and its
  numbers (`available`, `required`, `outstanding_dues`) because a customer is
  entitled to know why. Unmetered, that same honesty is an oracle: bid a riyal
  at a time and read somebody's deposit balance off the refusals.

Per **caller**, not per vehicle. A limit per car would let one script hold a
hundred cars at the same rate, which is the shape of the problem rather than
the fix.

The rate lives in `settings.BID_THROTTLE_RATES` and is off when unset, for the
reason `apps.accounts.throttling` sets out at length: `settings/test.py` empties
DRF's throttle configuration so the suite is not order-dependent, and a limit
attached to the views has to survive that with an off switch of its own. The
half that keeps "off by default" honest is `apps.bidding.checks`, which refuses
a deployed environment where it is off.
"""

from __future__ import annotations

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class BidPerCallerThrottle(SimpleRateThrottle):
    """How many bidding actions one signed-in account may take an hour.

    Keyed on the account, not the address: bidders share offices and share NAT,
    and metering the address would make one company's second bidder wait on the
    first. The endpoint requires authentication, so there is always an account
    to key on.
    """

    scope = "bid_caller"

    def get_rate(self) -> str | None:
        rates: dict[str, str] = getattr(settings, "BID_THROTTLE_RATES", {})
        return rates.get(self.scope)

    def get_cache_key(self, request, view) -> str | None:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            # Unauthenticated callers are refused by the permission class before
            # they can bid. Metering them would put every anonymous request into
            # one shared bucket, which is a way to lock the endpoint for
            # everybody by hammering it while signed out.
            return None
        return str(self.cache_format % {"scope": self.scope, "ident": user.pk})


#: What every bidding path must carry, named so a third limit later reaches all
#: of them at once rather than the ones somebody remembered.
BID_THROTTLES: list[type[SimpleRateThrottle]] = [BidPerCallerThrottle]
