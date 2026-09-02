"""E7 and T407 — one card, one field list, and no query per card.

Two failures from v1 are being prevented here, and they look unrelated until
you notice both come from the card being assembled in more than one place:

* a field added for one screen and missing on another, because three lists of
  permitted fields existed;
* a list page that issued a query per car, because the specification lived in
  a side table and each card fetched its own row.

So: the field set is asserted to be identical along every path that produces a
card, and the query count is asserted to be flat in the number of cards.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.auctions.cards import VEHICLE_CARD_FIELDS, card_queryset, vehicle_card
from apps.auctions.listing import vehicle_page
from apps.auctions.models import Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import ListingState

pytestmark = pytest.mark.django_db


@pytest.fixture
def live_auction(make_auction):
    return make_auction(state=AuctionState.LIVE)


def test_a_card_contains_exactly_the_declared_fields(live_auction, make_vehicle):
    card = vehicle_card(make_vehicle(live_auction, state=VehicleState.LISTED))

    assert tuple(card) == VEHICLE_CARD_FIELDS


def test_every_path_produces_the_same_field_set(live_auction, make_vehicle, staff):
    """The listing endpoint and a single card are the same function, and this
    is what says so — the comparison v1 never made."""
    vehicle = make_vehicle(live_auction, state=VehicleState.LISTED)

    direct = set(vehicle_card(vehicle))
    listed = set(vehicle_page(staff)["results"][0])

    assert direct == listed == set(VEHICLE_CARD_FIELDS)


def test_the_card_carries_the_one_price_as_text(live_auction, make_vehicle):
    vehicle = make_vehicle(
        live_auction, state=VehicleState.LISTED, reserve_price=Decimal("50000.10")
    )

    card = vehicle_card(vehicle)

    assert card["reserve_price"] == "50000.10"
    assert isinstance(card["reserve_price"], str)  # never a float, Article 3-2
    assert not [key for key in card if "price" in key and key != "reserve_price"]


def test_specifications_are_on_the_card_without_a_second_query(
    live_auction, make_vehicle, django_assert_num_queries
):
    """T407 — the specs are columns, so reading them costs nothing extra."""
    make_vehicle(
        live_auction,
        state=VehicleState.LISTED,
        odometer_km=120_000,
        transmission="automatic",
        fuel_type="petrol",
        condition="running",
    )

    with django_assert_num_queries(2):  # the vehicles, and the cover prefetch
        cards = [vehicle_card(v) for v in card_queryset(Vehicle.objects.all())]

    assert cards[0]["odometer_km"] == 120_000
    assert cards[0]["transmission_label"] == "أوتوماتيك"
    assert cards[0]["fuel_type_label"] == "بنزين"
    assert cards[0]["condition_label"] == "تسير"


def test_fifty_cards_cost_the_same_queries_as_one(
    live_auction, make_vehicle, django_assert_num_queries
):
    """T408's real acceptance: the page does not grow a query per car."""
    for _ in range(50):
        make_vehicle(live_auction, state=VehicleState.LISTED)

    with django_assert_num_queries(2):
        cards = [vehicle_card(v) for v in card_queryset(Vehicle.objects.all())]

    assert len(cards) == 50


def test_the_card_says_both_states_and_does_not_confuse_them(make_auction, make_vehicle):
    hidden = make_vehicle(
        make_auction(state=AuctionState.DRAFT), state=VehicleState.LISTED
    )

    card = vehicle_card(hidden)

    assert card["state"] == VehicleState.LISTED
    assert card["listing_state"] == ListingState.HIDDEN


def test_a_partner_owned_card_names_its_owner(live_auction, make_vehicle, partner):
    card = vehicle_card(
        make_vehicle(
            live_auction, state=VehicleState.LISTED, owner_company=partner.company
        )
    )

    assert card["owner_company_name"] == "شركة الشريك"


def test_a_card_with_no_cover_image_says_so_rather_than_guessing(
    live_auction, make_vehicle
):
    card = vehicle_card(make_vehicle(live_auction, state=VehicleState.LISTED))

    assert card["thumbnail_url"] is None
