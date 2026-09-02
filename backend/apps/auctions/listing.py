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


def auction_page(user, *, limit: int = DEFAULT_PAGE_SIZE, offset: int = 0) -> dict:
    """Auctions with their vehicle counts, one query for the page.

    The count is a correlated aggregate, not a second round trip per auction —
    the shape that made the v1 list quadratic.
    """
    auctions = Auction.objects.all()
    if not getattr(user, "is_staff", False):
        auctions = auctions.filter(state__in=list(PUBLIC_AUCTION_STATES))

    total = auctions.count()

    rows = list(
        auctions.annotate(
            vehicle_count=Count("vehicles", distinct=True),
            open_vehicle_count=Count(
                "vehicles",
                filter=Q(vehicles__state__in=[VehicleState.LISTED, VehicleState.BIDDING]),
                distinct=True,
            ),
        ).order_by("-starts_at")[offset : offset + limit]
    )

    return {"total": total, "results": [auction_card(auction) for auction in rows]}


def vehicle_page(
    user,
    *,
    auction: Auction | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict:
    """A page of vehicle cards, filtered by the one visibility rule."""
    queryset = visible_vehicles(user)
    if auction is not None:
        queryset = queryset.filter(auction=auction)

    total = queryset.count()
    page = card_queryset(queryset).order_by("auction_id", "lot_number")[
        offset : offset + limit
    ]

    return {"total": total, "results": vehicle_cards(page)}


__all__ = ["auction_page", "vehicle_page"]
