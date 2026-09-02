"""Listing pages — counted and paged by the database.

v1 fetched every vehicle of every open auction, de-duplicated the list in
Python and sliced it there too. It was fine at a hundred cars and took
`/api/v1/auctions` down at a few thousand, because the cost grew with the
table while the page size stayed at twenty.

So: `COUNT(*)` in SQL, `LIMIT/OFFSET` in SQL, the visibility rule as a `WHERE`
clause rather than a filter applied to a materialised list, and the card's
joins declared once in :func:`apps.auctions.cards.card_queryset`. Query count
here is constant in the page size — measured, not asserted in a comment.
"""

from __future__ import annotations

from django.db.models import Count, Q

from .cards import auction_card, card_queryset, vehicle_cards
from .models import Auction
from .states import VehicleState
from .visibility import PUBLIC_AUCTION_STATES, visible_vehicles

DEFAULT_PAGE_SIZE = 20

#: The largest page a caller may ask for. v1 took whatever `limit` arrived, so
#: `?limit=100000` was a full table scan any customer could request — and the
#: SQL paging below is only cheap because the slice is small.
MAX_PAGE_SIZE = 100


def auction_page(
    user, *, state: str = "", limit: int = DEFAULT_PAGE_SIZE, offset: int = 0
) -> dict:
    """Auctions with their vehicle counts, one query for the page.

    The count is a correlated aggregate, not a second round trip per auction —
    the shape that made the v1 list quadratic.

    ``state`` narrows the page in SQL, *after* the visibility rule and never
    instead of it: a caller who names a state they may not see gets an empty
    page. Filtering the rendered rows instead would also make ``total`` a lie —
    it would count the page, not the result.
    """
    auctions = Auction.objects.all()
    if not getattr(user, "is_staff", False):
        auctions = auctions.filter(state__in=list(PUBLIC_AUCTION_STATES))
    if state:
        auctions = auctions.filter(state=state)

    total = auctions.count()
    rows = list(
        with_vehicle_counts(auctions).order_by("-starts_at")[offset : offset + limit]
    )

    return {"total": total, "results": [auction_card(auction) for auction in rows]}


def with_vehicle_counts(auctions):
    """The two counts an auction card shows, as correlated aggregates.

    One function, so the list and the detail page cannot disagree about how many
    cars an auction holds — which they would the moment somebody wrote the
    annotation a second time and left one of the two `filter` clauses behind.
    """
    return auctions.annotate(
        vehicle_count=Count("vehicles", distinct=True),
        open_vehicle_count=Count(
            "vehicles",
            filter=Q(vehicles__state__in=[VehicleState.LISTED, VehicleState.BIDDING]),
            distinct=True,
        ),
    )


def vehicle_page(
    user,
    *,
    auction: Auction | None = None,
    search: str = "",
    state: str = "",
    make: str = "",
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict:
    """A page of vehicle cards, filtered by the one visibility rule.

    Every filter below is a ``WHERE`` clause added *before* the count and the
    slice, never a comprehension over a materialised list — the shape that made
    v1's list quadratic. So the cost of a filtered page is the cost of a page,
    whatever the table grew to.

    The visibility rule is applied first and cannot be filtered around: a caller
    who names a state they may not see gets an empty page rather than a leak.
    """
    queryset = visible_vehicles(user)
    if auction is not None:
        queryset = queryset.filter(auction=auction)
    if state:
        queryset = queryset.filter(state=state)
    if make:
        queryset = queryset.filter(make__iexact=make)
    if year_from is not None:
        queryset = queryset.filter(year__gte=year_from)
    if year_to is not None:
        queryset = queryset.filter(year__lte=year_to)

    search = (search or "").strip()
    if search:
        # One box, three columns. `icontains` and not a full-text index: at this
        # size it is honest, and a fake index would hide the day it stops being
        # enough. A numeric term is also tried as a lot number, because typing
        # "٤٧" into the search box means lot 47 to everybody who uses this.
        terms = Q(make__icontains=search) | Q(model__icontains=search)
        if search.isdigit():
            terms = terms | Q(lot_number=int(search))
        queryset = queryset.filter(terms)

    total = queryset.count()
    page = card_queryset(queryset).order_by("auction_id", "lot_number")[
        offset : offset + limit
    ]

    return {"total": total, "results": vehicle_cards(page)}


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "auction_page",
    "vehicle_page",
    "with_vehicle_counts",
]
