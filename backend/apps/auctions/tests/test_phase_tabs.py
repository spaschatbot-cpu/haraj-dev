"""The browse page's three tabs: one request, one filter, three counters.

The owner asked for tabs by auction phase over a flat grid of cars, and one
auction a week means the tab is in practice «which auction am I looking at».
Three things have to hold for that to work, and each has failed somewhere
before:

* **the phase is the auction's**, not the car's — a withdrawn car in a finished
  auction belongs to «منتهي», and v1 put it in «قريباً» by reading the vehicle's
  own column;
* **all three counters come back on every request**, because all three tabs are
  drawn at all times. v1 asked for them one tab at a time, twice over, so the
  three numbers were three different moments and stopped summing to anything;
* **the counters obey the filters and the visibility rule.** A counter that
  ignored the search box says «١٢ في المنتهي» and opens on three, which is worse
  than no counter at all; one that ignored visibility would leak the existence
  of a draft auction to anybody who could count.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auctions.listing import vehicle_page
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import (
    PHASE_AUCTION_STATES,
    PUBLIC_AUCTION_STATES,
    Phase,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def world(make_auction, make_vehicle):
    """One car in each phase, plus one nobody outside staff may see.

    Deliberately uneven counts — 1 / 2 / 3 — so a counter that returned the
    wrong tab's number, or the same number three times, cannot pass.
    """
    soon = make_auction(state=AuctionState.SCHEDULED)
    live = make_auction(state=AuctionState.LIVE)
    over = make_auction(state=AuctionState.ENDED)
    settled = make_auction(state=AuctionState.SETTLED)
    draft = make_auction(state=AuctionState.DRAFT)

    cars = {
        "soon": [make_vehicle(soon, state=VehicleState.LISTED)],
        "active": [make_vehicle(live, state=VehicleState.BIDDING) for _ in range(2)],
        "ended": [
            make_vehicle(over, state=VehicleState.REJECTED),
            make_vehicle(over, state=VehicleState.WITHDRAWN),  # invisible: withdrawn
            make_vehicle(settled, state=VehicleState.PAID),
            make_vehicle(settled, state=VehicleState.RELEASED),
        ],
        "hidden": [make_vehicle(draft, state=VehicleState.LISTED)],
    }
    return cars


def browse(api: APIClient, **params) -> dict:
    return api.get(reverse("auctions_api:vehicle-list"), params).data


# ---------------------------------------------------------------------------
# The map itself — written once, and it has to add up
# ---------------------------------------------------------------------------


def test_the_three_tabs_partition_the_public_auction_states():
    """No public state without a tab, and no state in two tabs.

    This is the assertion that keeps the tabs meaningful as an interface: a
    state missing from the map is a car a customer can reach by URL and never
    by tapping, and a state in two tabs is a car counted twice in a header that
    claims to describe the whole.
    """
    covered = [state for states in PHASE_AUCTION_STATES.values() for state in states]

    assert set(covered) == set(PUBLIC_AUCTION_STATES)
    assert len(covered) == len(set(covered)), "حالة مزاد في تبويبين"
    assert set(PHASE_AUCTION_STATES) == set(Phase.values)


def test_no_tab_covers_a_state_the_public_may_not_see():
    """`draft` and `cancelled` have no tab, and must never acquire one.

    A tab is a filter over what a caller may already see; naming a hidden state
    in the map would be the one edit that turns the filter into a way around
    the visibility rule.
    """
    covered = {state for states in PHASE_AUCTION_STATES.values() for state in states}

    assert AuctionState.DRAFT not in covered
    assert AuctionState.CANCELLED not in covered


# ---------------------------------------------------------------------------
# The filter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("phase", "states"),
    [
        (Phase.SOON, {AuctionState.SCHEDULED}),
        (Phase.ACTIVE, {AuctionState.LIVE}),
        (Phase.ENDED, {AuctionState.ENDED, AuctionState.SETTLED}),
    ],
)
def test_a_tab_shows_only_the_auction_states_it_names(api, world, phase, states):
    page = browse(api, phase=phase)

    assert page["results"], f"التبويب «{phase}» فارغ"
    assert {row["auction_state"] for row in page["results"]} <= states


def test_the_ended_tab_holds_settled_auctions_too(api, world):
    """«منتهي» is the customer's word; settlement is our bookkeeping step."""
    page = browse(api, phase=Phase.ENDED)

    assert AuctionState.SETTLED in {row["auction_state"] for row in page["results"]}


def test_leaving_the_tab_out_is_exactly_what_the_endpoint_did_before(api, world):
    """The parameter is optional, so no existing consumer breaks by ignoring it."""
    everything = browse(api)
    tabs = [browse(api, phase=name)["results"] for name in Phase.values]

    assert {row["id"] for row in everything["results"]} == {
        row["id"] for page in tabs for row in page
    }


def test_a_tab_nobody_defined_is_refused_by_name(api, world):
    """Not silently ignored — a typo that returns the whole table is a tab that
    lies about what it is showing."""
    response = api.get(reverse("auctions_api:vehicle-list"), {"phase": "finished"})

    assert response.status_code == 400
    assert "phase" in response.data["error"]["detail"]


def test_a_tab_cannot_reach_around_the_visibility_rule(api, world):
    """The draft auction's car is in no tab, and in no total, for the public."""
    ids = {
        row["id"] for name in Phase.values for row in browse(api, phase=name)["results"]
    }

    assert world["hidden"][0].pk not in ids
    assert browse(api)["total"] == 6


def test_the_withdrawn_car_is_hidden_even_inside_its_own_tab(api, world):
    """The phase narrows the visible set; it never widens it. A withdrawn car
    sits in a public auction and is still not on offer."""
    page = browse(api, phase=Phase.ENDED)

    assert world["ended"][1].pk not in {row["id"] for row in page["results"]}
    assert page["total"] == 3


# ---------------------------------------------------------------------------
# The counters
# ---------------------------------------------------------------------------


def test_every_response_carries_all_three_counters_whatever_the_tab(api, world):
    """The three tabs are on screen at all times, so the numbers are needed at
    all times — and they must be the *same* three however the page was asked
    for, because they were read in one moment."""
    expected = {"soon": 1, "active": 2, "ended": 3}

    assert browse(api)["counts"] == expected
    for name in Phase.values:
        assert browse(api, phase=name)["counts"] == expected


def test_the_total_of_a_tab_is_that_tabs_counter(api, world):
    """Read out of the same aggregate row, so the header and the tab cannot
    disagree by a car that moved between two queries."""
    for name in Phase.values:
        page = browse(api, phase=name)
        assert page["total"] == page["counts"][name]


def test_the_counters_obey_the_search_box(api, world, make_auction, make_vehicle):
    """«١٢ في المنتهي» that opens on three is worse than no counter."""
    live = make_auction(state=AuctionState.LIVE)
    make_vehicle(live, state=VehicleState.LISTED, make="نيسان", model="التيما")

    page = browse(api, search="التيما")

    assert page["counts"] == {"soon": 0, "active": 1, "ended": 0}
    assert page["total"] == 1


def test_the_counters_obey_the_other_filters_too(api, world, make_auction, make_vehicle):
    over = make_auction(state=AuctionState.ENDED)
    make_vehicle(over, state=VehicleState.REJECTED, year=1998)

    assert browse(api, year_to=2000)["counts"] == {"soon": 0, "active": 0, "ended": 1}
    assert browse(api, make="لا-أحد")["counts"] == {"soon": 0, "active": 0, "ended": 0}


def test_the_counters_count_only_what_the_caller_may_see(api, world, staff):
    """Two callers, two sets of numbers, one rule producing both.

    The anonymous visitor does not count the withdrawn car; staff do, because
    staff may see it — the counters are an aggregate over `visible_vehicles`,
    not a second answer to who-sees-what.

    And a staff caller's three tabs do **not** sum to their total: the draft
    auction's car belongs to no tab at all. That gap is the honest answer. The
    tabs are three named subsets of what you may see, never a partition of it,
    and a counter forced to add up would have to invent a fourth tab for a
    state the public has no business hearing about.
    """
    anonymous = browse(api)

    api.force_authenticate(user=staff)
    privileged = browse(api)

    assert anonymous["counts"] == {"soon": 1, "active": 2, "ended": 3}
    assert privileged["counts"] == {"soon": 1, "active": 2, "ended": 4}
    assert privileged["total"] == 8  # every car, the draft auction's included
    assert sum(privileged["counts"].values()) == 7


def test_the_favourites_page_answers_in_the_same_shape(api, world, customer):
    """One page shape for every list of cars. A screen that had to branch on
    which endpoint it called is the drift `cards.py` exists to prevent, wearing
    the envelope instead of the card."""
    api.force_authenticate(user=customer)

    page = api.get(reverse("auctions_api:favourite-list")).data

    assert set(page) == {"total", "counts", "results"}
    assert page["counts"] == {"soon": 0, "active": 0, "ended": 0}


# ---------------------------------------------------------------------------
# The cost — the whole reason the counters live in this response
# ---------------------------------------------------------------------------


def test_the_page_costs_the_same_queries_whichever_tab_and_however_many(
    api, world, django_assert_num_queries
):
    """The counter that costs a query per tab is exactly what is being avoided.

    v1 spent six requests on three numbers. Here the number of queries is the
    same with no tab selected as with any of the three — and it does not grow
    when a fourth phase is added, because the three counts are one conditional
    aggregate and not three `COUNT`s.
    """
    with django_assert_num_queries(3) as baseline:
        browse(api)

    for name in Phase.values:
        with django_assert_num_queries(len(baseline.captured_queries)):
            browse(api, phase=name)


def test_the_counters_are_one_query_not_one_per_phase(world, django_assert_num_queries):
    """Stated against the function rather than the endpoint, so the assertion
    survives a change in how the view is wired: the aggregate, the page and the
    cover prefetch. Three, for three counters plus a total."""
    with django_assert_num_queries(3):
        page = vehicle_page(AnonymousUser(), limit=20)

    assert page["counts"] == {"soon": 1, "active": 2, "ended": 3}


# ---------------------------------------------------------------------------
# What the countdown on the card needs
# ---------------------------------------------------------------------------


def test_the_card_carries_the_auction_the_countdown_needs(api, world):
    """Without these the card cannot show a clock without a second request per
    car — twenty-one connections to draw twenty countdowns."""
    card = browse(api, phase=Phase.ACTIVE)["results"][0]
    auction = world["active"][0].auction

    assert card["auction_id"] == auction.pk
    assert card["auction_title"] == auction.title
    assert card["auction_starts_at"] == auction.starts_at.isoformat().replace(
        "+00:00", "Z"
    )
    assert card["auction_ends_at"] == auction.ends_at.isoformat().replace("+00:00", "Z")


def test_the_times_on_the_card_are_utc_on_the_wire(api, world):
    """Article 3-1. Each channel converts once, at its own display edge; a card
    that arrived in Riyadh time would make the app convert a converted value."""
    card = browse(api, phase=Phase.ACTIVE)["results"][0]

    assert card["auction_starts_at"].endswith("Z")
    assert card["auction_ends_at"].endswith("Z")


def test_the_auction_fields_cost_no_extra_query(api, world, django_assert_num_queries):
    """`card_queryset` already joins the auction, so four more of its columns
    are free — that is why they belong on the card rather than behind a second
    endpoint."""
    with django_assert_num_queries(3):
        page = browse(api, limit=20)

    assert all(row["auction_ends_at"] for row in page["results"])


def test_the_detail_page_carries_them_too(api, world):
    """T609: the list card and the detail card are the same set of keys. A
    field added to one and not the other is the v1 failure this project has a
    CI check for."""
    vehicle = world["active"][0]

    listed = next(
        row
        for row in browse(api, phase=Phase.ACTIVE)["results"]
        if row["id"] == vehicle.pk
    )
    detail = api.get(reverse("auctions_api:vehicle-detail", args=[vehicle.pk])).data

    assert detail == listed
    for field in ("auction_id", "auction_title", "auction_starts_at", "auction_ends_at"):
        assert field in detail
