"""E1 — a test for every permitted move, and one for every refused one.

The forbidden half is generated from the table: every pair of states that is
*not* in it must raise, including a state to itself. Written by hand it would
be twenty-odd cases nobody would keep current; generated, it fails the moment
someone widens the table without meaning to.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from apps.auctions import services
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import (
    AUCTION_MOVE_INDEX,
    AUCTION_MOVES,
    VEHICLE_MOVE_INDEX,
    VEHICLE_MOVES,
    AuctionState,
    InvalidTransition,
    TransitionNotReady,
    VehicleState,
)

MINUTE = timedelta(minutes=1)


def _now_for(auction: Auction, target: str):
    """A moment at which the move's own guard is satisfied."""
    if target == AuctionState.SCHEDULED:
        return auction.starts_at - timedelta(hours=1)
    if target == AuctionState.LIVE:
        return auction.starts_at
    if target == AuctionState.ENDED:
        return auction.ends_at
    return auction.starts_at + MINUTE


# ---------------------------------------------------------------------------
# Auction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "move", AUCTION_MOVES, ids=[f"{m.source}->{m.target}" for m in AUCTION_MOVES]
)
def test_every_permitted_auction_move_is_taken(move, make_auction, make_vehicle):
    auction = make_auction(state=move.source)
    make_vehicle(auction)  # scheduling refuses an empty auction

    services.move_auction(auction, move.target, now=_now_for(auction, move.target))

    assert auction.state == move.target
    assert Auction.objects.get(pk=auction.pk).state == move.target


FORBIDDEN_AUCTION_MOVES = [
    (source, target)
    for source in AuctionState.values
    for target in AuctionState.values
    if (source, target) not in AUCTION_MOVE_INDEX
]


@pytest.mark.parametrize(
    ("source", "target"),
    FORBIDDEN_AUCTION_MOVES,
    ids=[f"{s}->{t}" for s, t in FORBIDDEN_AUCTION_MOVES],
)
def test_every_other_auction_move_is_refused(source, target, make_auction, make_vehicle):
    auction = make_auction(state=source)
    make_vehicle(auction)

    with pytest.raises(InvalidTransition):
        services.move_auction(auction, target, now=_now_for(auction, target))

    assert Auction.objects.get(pk=auction.pk).state == source


def test_a_settled_auction_is_the_end_of_the_line(make_auction, make_vehicle):
    """No move leaves `settled`. Stated on its own because it is the promise
    the money side leans on: settlement happens once."""
    assert not [m for m in AUCTION_MOVES if m.source == AuctionState.SETTLED]


def test_a_live_auction_cannot_be_cancelled(make_auction, make_vehicle):
    """Deposits are held against a live auction; releasing them is
    settlement's job, so cancelling goes through ending."""
    auction = make_auction(state=AuctionState.LIVE)
    make_vehicle(auction)

    with pytest.raises(InvalidTransition):
        services.cancel(auction)


# -- guards -----------------------------------------------------------------


def test_an_empty_auction_cannot_be_scheduled(make_auction):
    auction = make_auction(state=AuctionState.DRAFT)

    with pytest.raises(TransitionNotReady, match="بلا مركبات"):
        services.schedule(auction, now=auction.starts_at - MINUTE)


def test_an_auction_does_not_start_before_its_time(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.SCHEDULED)
    make_vehicle(auction)

    with pytest.raises(TransitionNotReady, match="لم يحن وقت"):
        services.activate(auction, now=auction.starts_at - MINUTE)


def test_an_auction_does_not_end_before_its_time(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.LIVE)
    make_vehicle(auction)

    with pytest.raises(TransitionNotReady, match="لم ينته"):
        services.end(auction, now=auction.ends_at - MINUTE)


def test_an_auction_whose_end_has_passed_cannot_be_scheduled(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.DRAFT)
    make_vehicle(auction)

    with pytest.raises(TransitionNotReady, match="مضى"):
        services.schedule(auction, now=auction.ends_at + MINUTE)


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


def _extra_for(target: str, customer):
    if target == VehicleState.AWARDED:
        return {"awarded_to": customer, "awarded_price": Decimal("61000.00")}
    return None


@pytest.mark.parametrize(
    "move", VEHICLE_MOVES, ids=[f"{m.source}->{m.target}" for m in VEHICLE_MOVES]
)
def test_every_permitted_vehicle_move_is_taken(
    move, make_auction, make_vehicle, customer
):
    vehicle = make_vehicle(make_auction(), state=move.source)

    services.move_vehicle(vehicle, move.target, extra=_extra_for(move.target, customer))

    assert vehicle.state == move.target
    assert Vehicle.objects.get(pk=vehicle.pk).state == move.target


FORBIDDEN_VEHICLE_MOVES = [
    (source, target)
    for source in VehicleState.values
    for target in VehicleState.values
    if (source, target) not in VEHICLE_MOVE_INDEX
]


@pytest.mark.parametrize(
    ("source", "target"),
    FORBIDDEN_VEHICLE_MOVES,
    ids=[f"{s}->{t}" for s, t in FORBIDDEN_VEHICLE_MOVES],
)
def test_every_other_vehicle_move_is_refused(
    source, target, make_auction, make_vehicle, customer
):
    vehicle = make_vehicle(make_auction(), state=source)

    with pytest.raises(InvalidTransition):
        services.move_vehicle(vehicle, target, extra=_extra_for(target, customer))

    assert Vehicle.objects.get(pk=vehicle.pk).state == source


def test_an_award_needs_a_named_winner(make_auction, make_vehicle):
    vehicle = make_vehicle(make_auction(), state=VehicleState.BIDDING)

    with pytest.raises(TransitionNotReady, match="اسم الفائز"):
        services.move_vehicle(vehicle, VehicleState.AWARDED)

    assert Vehicle.objects.get(pk=vehicle.pk).state == VehicleState.BIDDING


def test_an_award_needs_a_price(make_auction, make_vehicle, customer):
    vehicle = make_vehicle(make_auction(), state=VehicleState.BIDDING)

    with pytest.raises(TransitionNotReady, match="سعر الرسو"):
        services.move_vehicle(
            vehicle, VehicleState.AWARDED, extra={"awarded_to": customer}
        )


def test_award_records_winner_price_and_moment(make_auction, make_vehicle, customer):
    vehicle = make_vehicle(make_auction(), state=VehicleState.BIDDING)

    services.award(vehicle, customer, Decimal("61000.00"))

    stored = Vehicle.objects.get(pk=vehicle.pk)
    assert stored.state == VehicleState.AWARDED
    assert stored.awarded_to_id == customer.pk
    assert stored.awarded_price == Decimal("61000.00")
    assert stored.awarded_at is not None


def test_refusal_messages_are_arabic(make_auction, make_vehicle):
    """An operator reads the message as-is; it is not a developer string."""
    vehicle = make_vehicle(make_auction(), state=VehicleState.DRAFT)

    with pytest.raises(InvalidTransition) as raised:
        services.move_vehicle(vehicle, VehicleState.PAID)

    assert "مسودة" in str(raised.value)
    assert "مسدَّدة" in str(raised.value)
