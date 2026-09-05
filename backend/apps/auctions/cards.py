"""The one definition of what a vehicle card shows.

v1's home page alone drew this card four different ways behind three different
lists of permitted fields, so a field added for the app appeared on the web
and vanished in the admin — silently, because nothing compared the lists.

Here there is exactly one mapping, :data:`_BUILDERS`. The field list is
derived from it, every caller renders through :func:`vehicle_card`, and a CI
check refuses a second card builder elsewhere in the tree. Adding a field is
one line and it appears everywhere at once; that is the whole point.

Money is a decimal string, never a float and never a locale-formatted number
(Article 3-2 and the API contract in `docs/system-handbook.md` §10).
"""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.db.models import Prefetch

from .models import (
    FuelType,
    PlateType,
    Transmission,
    Vehicle,
    VehicleCondition,
    VehicleImage,
    VehicleState,
)
from .states import AuctionState
from .visibility import listing_state, phase_of


def _label(choices, value: str) -> str:
    try:
        return choices(value).label
    except ValueError:
        return value


def _amount(value) -> str | None:
    """A money value as it should cross a wire: fixed-point text.

    Serialising a `Decimal` as a JSON number invites the client to parse it
    into a float, and 10000.10 stops being 10000.10 somewhere in Dart.
    """
    return None if value is None else f"{value:.2f}"


def _cover(vehicle: Vehicle) -> VehicleImage | None:
    """The cover image, from the prefetch when there is one.

    `cover_images` is populated by :func:`card_queryset`. The fallback query
    exists for a vehicle fetched some other way; a list that lands on it is a
    list that forgot `card_queryset`, and the query-count test is what catches
    that rather than a comment asking people to remember.
    """
    prefetched = getattr(vehicle, "cover_images", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return vehicle.images.filter(is_cover=True).first()


def _thumbnail_url(vehicle: Vehicle) -> str | None:
    """The cover thumbnail, addressed from wherever the caller happens to be.

    `FieldFile.url` is a path, and a path only works while the server that
    rendered the page is the server that holds the file. Neither client is
    that server: the web is a separate Next app (Vercel in production) and the
    mobile app is not a server at all. So the browser asked **its own** origin
    for `/media/...` and every card image came back 404 — cards complete,
    pictures broken.

    `MEDIA_BASE_URL` empty keeps the old relative path, which is right for the
    console: same server, same origin.
    """
    cover = _cover(vehicle)
    if cover is None or not cover.thumbnail:
        return None
    return f"{settings.MEDIA_BASE_URL}{cover.thumbnail.url}"


#: key → how to read it off a vehicle. The single source of the card's shape.
_BUILDERS: dict[str, Callable[[Vehicle], object]] = {
    "id": lambda v: v.pk,
    # The auction, on the card. A card that counts down to the close needs the
    # closing moment, and a tab that says «نشط» needs to name which auction it
    # is showing — v1 sent both with every vehicle for exactly this reason, and
    # that part of v1 was right. Without them a countdown costs a second request
    # per car. They are free here: `card_queryset` already joins the auction, so
    # reading four more of its columns adds no query at all.
    #
    # Both times are UTC on the wire (Article 3-1); each channel converts once,
    # at its own display edge.
    "auction_id": lambda v: v.auction_id,
    "auction_number": lambda v: v.auction.number,
    "auction_title": lambda v: v.auction.title,
    "auction_state": lambda v: v.auction.state,
    # The tab this car sits in, decided here and not in either client. Both
    # channels ask the same question of a card — «هل انتهى؟ ومتى العدّ؟» — and
    # before this field the web answered it from `auction_ends_at` against the
    # browser clock while the app answered it from a field the contract did not
    # send. One name, one answer, derived from `PHASE_AUCTION_STATES`.
    "phase": lambda v: phase_of(v.auction.state),
    "auction_starts_at": lambda v: v.auction.starts_at,
    "auction_ends_at": lambda v: v.auction.ends_at,
    "lot_number": lambda v: v.lot_number,
    "title": lambda v: f"{v.make} {v.model} {v.year}",
    "make": lambda v: v.make,
    "model": lambda v: v.model,
    "year": lambda v: v.year,
    "odometer_km": lambda v: v.odometer_km,
    "transmission": lambda v: v.transmission,
    "transmission_label": lambda v: _label(Transmission, v.transmission),
    "fuel_type": lambda v: v.fuel_type,
    "fuel_type_label": lambda v: _label(FuelType, v.fuel_type),
    "condition": lambda v: v.condition,
    "condition_label": lambda v: _label(VehicleCondition, v.condition),
    "plate_type": lambda v: v.plate_type,
    "plate_type_label": lambda v: _label(PlateType, v.plate_type),
    # The one price. There is no "starting price", no "estimated value" and no
    # screen-local calculation — T406, enforced by a CI check.
    "reserve_price": lambda v: _amount(v.reserve_price),
    "state": lambda v: v.state,
    "state_label": lambda v: _label(VehicleState, v.state),
    "listing_state": lambda v: listing_state(v),
    "owner_company_name": lambda v: v.owner_company.name if v.owner_company_id else None,
    "thumbnail_url": _thumbnail_url,
}

#: What a card contains. Derived, so it cannot drift from what is built.
VEHICLE_CARD_FIELDS: tuple[str, ...] = tuple(_BUILDERS)


#: The auction's own card, defined the same way and in the same file. Two
#: cards, one module: "where is a card built?" has a single answer, and the
#: auction list cannot start drifting the way the vehicle list once did.
_AUCTION_BUILDERS: dict[str, Callable[[object], object]] = {
    "id": lambda a: a.pk,
    "number": lambda a: a.number,
    "title": lambda a: a.title,
    "state": lambda a: a.state,
    "state_label": lambda a: _label(AuctionState, a.state),
    "starts_at": lambda a: a.starts_at,
    "ends_at": lambda a: a.ends_at,
    "vehicle_count": lambda a: getattr(a, "vehicle_count", None),
    "open_vehicle_count": lambda a: getattr(a, "open_vehicle_count", None),
}

AUCTION_CARD_FIELDS: tuple[str, ...] = tuple(_AUCTION_BUILDERS)


def auction_card(auction) -> dict:
    """One auction row. The counts come from the queryset's annotations, so
    reading them here costs nothing — and returns None if a caller forgot to
    annotate, rather than quietly issuing a count query per row."""
    return {key: build(auction) for key, build in _AUCTION_BUILDERS.items()}


def vehicle_card(vehicle: Vehicle) -> dict:
    """One card. Every screen and every endpoint renders through this."""
    return {key: build(vehicle) for key, build in _BUILDERS.items()}


def vehicle_cards(vehicles) -> list[dict]:
    """Many cards — the same function, applied. Not a second code path."""
    return [vehicle_card(vehicle) for vehicle in vehicles]


def card_queryset(queryset=None):
    """A queryset shaped so a card costs no query of its own (T407, T408).

    Three queries for any page size: the vehicles with their auction and owner
    joined, and one prefetch for the cover images. Fifty cars cost the same
    three as one.
    """
    queryset = Vehicle.objects.all() if queryset is None else queryset
    return queryset.select_related("auction", "owner_company").prefetch_related(
        Prefetch(
            "images",
            queryset=VehicleImage.objects.filter(is_cover=True),
            to_attr="cover_images",
        )
    )
