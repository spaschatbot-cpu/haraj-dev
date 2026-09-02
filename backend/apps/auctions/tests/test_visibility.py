"""E6 — one visibility rule, and every path gives the same answer.

The strong test here is not any single case; it is the matrix. `can_view` and
`visible_vehicles` are two implementations of one rule — Python and SQL — and
the moment they disagree for any user over any vehicle, this fails. v1's hole
was exactly that shape: the panel that checked partner ownership was not the
panel that listed the cars, and closing it took 22 edits.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import (
    ListingState,
    can_view,
    listing_state,
    visible_vehicles,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(make_auction, make_vehicle, partner, other_partner):
    """One vehicle in every combination that matters."""
    vehicles = {}
    for auction_state in AuctionState.values:
        auction = make_auction(state=auction_state)
        for vehicle_state in VehicleState.values:
            vehicles[f"{auction_state}/{vehicle_state}"] = make_vehicle(
                auction, state=vehicle_state
            )
            vehicles[f"{auction_state}/{vehicle_state}/partner"] = make_vehicle(
                auction, state=vehicle_state, owner_company=partner.company
            )
            vehicles[f"{auction_state}/{vehicle_state}/other"] = make_vehicle(
                auction, state=vehicle_state, owner_company=other_partner.company
            )
    return vehicles


@pytest.mark.parametrize(
    "who", ["anonymous", "customer", "partner", "other_partner", "staff"]
)
def test_the_two_paths_agree_on_every_vehicle(
    who, world, request, customer, partner, other_partner, staff
):
    user = AnonymousUser() if who == "anonymous" else request.getfixturevalue(who)

    by_predicate = {v.pk for v in world.values() if can_view(user, v)}
    by_queryset = set(visible_vehicles(user).values_list("pk", flat=True))

    assert by_predicate == by_queryset


def test_staff_see_everything(world, staff):
    assert visible_vehicles(staff).count() == len(world)


def test_a_partner_sees_their_own_hidden_vehicle(make_auction, make_vehicle, partner):
    """A draft car in a draft auction: invisible to the public, visible to the
    partner who owns it — the same rule, not an exception bolted on."""
    auction = make_auction(state=AuctionState.DRAFT)
    mine = make_vehicle(auction, state=VehicleState.DRAFT, owner_company=partner.company)

    assert can_view(partner, mine) is True
    assert list(visible_vehicles(partner)) == [mine]


def test_a_partner_does_not_see_another_partners_hidden_vehicle(
    make_auction, make_vehicle, partner, other_partner
):
    auction = make_auction(state=AuctionState.DRAFT)
    theirs = make_vehicle(
        auction, state=VehicleState.DRAFT, owner_company=other_partner.company
    )

    assert can_view(partner, theirs) is False
    assert list(visible_vehicles(partner)) == []


def test_the_public_sees_a_listed_car_in_a_live_auction(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.LIVE)
    car = make_vehicle(auction, state=VehicleState.LISTED)

    assert can_view(AnonymousUser(), car) is True
    assert list(visible_vehicles(AnonymousUser())) == [car]


def test_the_public_never_sees_a_draft_auction(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.DRAFT)
    car = make_vehicle(auction, state=VehicleState.LISTED)

    assert can_view(AnonymousUser(), car) is False


def test_the_public_never_sees_a_withdrawn_car(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.LIVE)
    car = make_vehicle(auction, state=VehicleState.WITHDRAWN)

    assert can_view(AnonymousUser(), car) is False


def test_listing_state_is_the_display_answer_of_the_same_rule(
    make_auction, make_vehicle, partner
):
    """«حالة العرض» is not «حالة المركبة»: a car can be `listed` and still
    hidden, because its auction has not been announced."""
    hidden = make_vehicle(
        make_auction(state=AuctionState.DRAFT), state=VehicleState.LISTED
    )
    shown = make_vehicle(make_auction(state=AuctionState.LIVE), state=VehicleState.LISTED)

    assert listing_state(hidden) == ListingState.HIDDEN
    assert listing_state(shown) == ListingState.PUBLISHED
    assert hidden.state == shown.state == VehicleState.LISTED
