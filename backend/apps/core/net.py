"""Who is calling. One answer, and every rate limit reads it. T914.

Every limit keyed "per address" is only as good as this function, and getting
it wrong is silent in both directions:

* **Trust the header when nothing sets it** and the limit stops existing. A
  caller writes `X-Forwarded-For: 10.0.0.1`, then `10.0.0.2`, and each value is
  a different bucket with a full budget. That is not a theoretical bypass — it
  is one header and a loop, and it reopens the free-SMS gateway T602 closed.
* **Ignore the header when a proxy does set it** and every caller shares one
  bucket: the proxy's own address. The first customer to sign in spends the
  hour for everybody behind it.

So the number of proxies is a *setting*, not a guess. `TRUSTED_PROXY_HOPS` is
0 by default — the application is directly reachable and `REMOTE_ADDR` is the
truth — and the environment that puts nginx in front raises it to 1. Only the
last N entries of the header were written by infrastructure we control; every
entry to the left of them was written by whoever felt like it.

DRF's `BaseThrottle.get_ident` implements the same rule from
`REST_FRAMEWORK["NUM_PROXIES"]`, which `settings.base` sets from this same
number, so the two cannot drift. `apps.core.checks` fails a deployed
environment where they have.
"""

from __future__ import annotations

from django.conf import settings

#: What a caller with no discoverable address is counted as. A shared bucket,
#: deliberately: an unaddressable caller is either a misconfiguration or a
#: probe, and neither deserves a budget of its own.
UNKNOWN = "unknown"


def trusted_proxy_hops() -> int:
    return max(0, int(getattr(settings, "TRUSTED_PROXY_HOPS", 0)))


def client_ip(request) -> str:
    """The address to meter this request against.

    With no trusted proxies the forwarded header is ignored entirely — it is a
    header, and headers are written by the caller. With N of them, the N-th
    entry from the right is the last one a machine of ours wrote, and anything
    further left is the caller's own text.
    """
    hops = trusted_proxy_hops()
    remote = request.META.get("REMOTE_ADDR") or UNKNOWN

    if hops == 0:
        return remote

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded:
        return remote

    addresses = [part.strip() for part in forwarded.split(",") if part.strip()]
    if not addresses:
        return remote

    # `-min(hops, len)`: with fewer entries than hops the leftmost is the best
    # we have. It is still ours to read, because a short header means the
    # request did not come through every proxy we expected — which is worth
    # metering conservatively rather than trusting.
    return addresses[-min(hops, len(addresses))]


__all__ = ["UNKNOWN", "client_ip", "trusted_proxy_hops"]
