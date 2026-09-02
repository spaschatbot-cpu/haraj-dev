"""The support screen. One page, read-only, guarded by a capability.

It translates a query string into a call to :mod:`apps.bidding.support` and
renders what comes back. No rule, no calculation, no write — a view's whole job
(Article 4-4).

The guard names the *page*, not a capability: `apps.console.navigation` holds
the one row that both shows this in the sidebar and admits a caller to it
(T802).
"""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import render

from apps.console.views import console_page

from .support import look_up


@console_page("console:why-no-bid")
def why_no_bid(request):
    """«ليه ما يقدرش يزايد؟» — a phone number in, the last refusals out.

    Support's most-asked question in v1 had no stored answer, so every case was
    reconstructed by hand from several tables after the balances had already
    moved. Here the answer is a lookup, and it is the same answer today as it
    will be next month.
    """
    return render(
        request,
        "bidding/why_no_bid.html",
        {
            "lookup": look_up(request.GET.get("phone", "")),
            # Article 5-6: every screen says which environment it is, so a
            # staging lookup is never mistaken for a production one.
            "environment": settings.ENVIRONMENT_NAME,
        },
    )
