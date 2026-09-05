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

:class:`Phase` lives here for the same reason: the browse page's three tabs are
a partition of :data:`PUBLIC_AUCTION_STATES`, so the names and the states they
cover belong beside the rule they partition — not in a view, and certainly not
in each of the two clients.
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


class Phase(models.TextChoices):
    """The three tabs a browsing customer chooses between.

    A phase is a property of the **auction**, never of the car: "قريباً" is a
    car whose auction has not opened yet, not a car in some pending state of
    its own. v1 answered this from the vehicle's own column and a car withdrawn
    from a finished auction landed in "قريباً".

    One auction a week is the shape the owner asked for, so in practice the tab
    *is* «which auction am I looking at» — which is exactly why the three names
    must partition the public auction states with nothing left over and nothing
    counted twice.
    """

    SOON = "soon", "قريباً"
    ACTIVE = "active", "نشط"
    ENDED = "ended", "منتهي"


#: phase → the auction states it covers. The one place this mapping is written.
#:
#: `ended` holds two states because "منتهي" is a customer's word and settlement
#: is ours: a settled auction is over as far as anybody browsing is concerned,
#: and giving it a fourth tab would ask a bidder to care which of our internal
#: steps has run.
PHASE_AUCTION_STATES: dict[str, frozenset[str]] = {
    Phase.SOON: frozenset({AuctionState.SCHEDULED}),
    Phase.ACTIVE: frozenset({AuctionState.LIVE}),
    Phase.ENDED: frozenset({AuctionState.ENDED, AuctionState.SETTLED}),
}


#: auction state → the tab it sits in. **Inverted** from the mapping above and
#: never written a second time: two tables would be two answers to "is this over
#: yet?", which is the duplicate decision point Article 4-5 forbids.
_PHASE_OF_STATE: dict[str, str] = {
    state: str(phase)
    for phase, states in PHASE_AUCTION_STATES.items()
    for state in states
}


def phase_of(auction_state: str) -> str:
    """Which tab an auction in this state belongs to — the server's answer.

    On the card because otherwise each client derives it, and a client that
    derives it owns a second definition of "منتهي": the web would compare
    `auction_ends_at` to the browser's clock and the app would compare it to the
    phone's, and v1 proved where that ends — a customer two minutes fast read
    «انتهى» on an auction still taking bids and did not put one in.

    A state outside the three tabs (`draft`, `cancelled`) has no tab and gets
    the empty string rather than being folded into `ended`. Staff can see such a
    vehicle, and telling them it is over is a claim nobody made; the clients
    read the blank as "unknown" and show the car without a verdict (Article
    2-3 — an unrecognised value is kept, not resolved by guessing).
    """
    return _PHASE_OF_STATE.get(auction_state, "")


def phase_q(phase: str) -> Q:
    """The phase as a ``WHERE`` clause, to be **added** to the visibility rule.

    Never a replacement for it. A tab narrows what a caller may already see; a
    car hidden from an anonymous visitor today does not become visible because
    somebody named the tab it would sit in. Every caller therefore builds this
    on top of :func:`visible_vehicles`, and a test says so.
    """
    return Q(auction__state__in=sorted(PHASE_AUCTION_STATES[phase]))


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
