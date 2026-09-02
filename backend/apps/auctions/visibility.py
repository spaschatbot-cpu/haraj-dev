"""Who may see which vehicle — decided once, here.

In v1 the answer was re-derived in every panel that listed cars, and the panel
that checked partner ownership was not the panel that hid them; closing that
hole touched 22 places. So there is one predicate, and everything else is
built from it:

* :func:`can_view` answers for a single vehicle already in memory.
* :func:`visible_vehicles` answers for a whole table, in SQL.

They must agree for every user and every vehicle, and a test proves that over
the full matrix rather than trusting that the two were written from the same
idea (E6).
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from .models import Vehicle
from .states import AuctionState, VehicleState

#: An auction the public may know about at all. A draft is not an
#: announcement, and a cancelled auction is not history the public needs.
PUBLIC_AUCTION_STATES = frozenset(
    {
        AuctionState.SCHEDULED,
        AuctionState.LIVE,
        AuctionState.ENDED,
        AuctionState.SETTLED,
    }
)

#: A vehicle actually being offered or already resolved in public view.
#: `draft` is unfinished, `withdrawn` was pulled, and `relisted` is waiting to
#: be placed in a new auction — none of the three is on offer right now.
PUBLIC_VEHICLE_STATES = frozenset(
    {
        VehicleState.LISTED,
        VehicleState.BIDDING,
        VehicleState.AWAITING_DECISION,
        VehicleState.AWARDED,
        VehicleState.REJECTED,
        VehicleState.INVOICED,
        VehicleState.PAID,
        VehicleState.RELEASED,
    }
)


class ListingState(models.TextChoices):
    """Whether the public can see the car — **not** where the car stands.

    Two different questions that v1 answered with one column, which is why an
    exported sheet could say "sold" for a car no customer had ever been shown.
    """

    PUBLISHED = "published", "معروضة للعموم"
    HIDDEN = "hidden", "غير معروضة"


def is_public(vehicle: Vehicle) -> bool:
    """The single predicate. Everything else in this module defers to it."""
    return (
        vehicle.auction.state in PUBLIC_AUCTION_STATES
        and vehicle.state in PUBLIC_VEHICLE_STATES
    )


def public_q() -> Q:
    """:func:`is_public`, expressed for the database.

    Written as its own function so the SQL form and the Python form sit next
    to each other in review; the equality test is what actually holds them
    together.
    """
    return Q(auction__state__in=list(PUBLIC_AUCTION_STATES)) & Q(
        state__in=list(PUBLIC_VEHICLE_STATES)
    )


def listing_state(vehicle: Vehicle) -> str:
    return ListingState.PUBLISHED if is_public(vehicle) else ListingState.HIDDEN


def _company_id(user) -> int | None:
    """The partner company this user represents, or None.

    Tolerates a user with no company row rather than requiring every caller to
    remember the `RelatedObjectDoesNotExist` dance.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    company = getattr(user, "company", None)
    return getattr(company, "id", None)


def can_view(user, vehicle: Vehicle) -> bool:
    """May this user see this vehicle? The only answer in the system."""
    if user is not None and getattr(user, "is_staff", False):
        return True

    owner_id = vehicle.owner_company_id
    if owner_id is not None and owner_id == _company_id(user):
        return True

    return is_public(vehicle)


def visible_vehicles(user, queryset=None):
    """The same rule as a queryset, so listing never re-derives it."""
    queryset = Vehicle.objects.all() if queryset is None else queryset

    if user is not None and getattr(user, "is_staff", False):
        return queryset

    rule = public_q()
    company_id = _company_id(user)
    if company_id is not None:
        rule = rule | Q(owner_company_id=company_id)

    return queryset.filter(rule)
