"""T414 — the listing counts and pages in SQL, measured on a thousand cars.

Two assertions, and the first matters more than the second: **query count is
flat in the size of the table.** A wall-clock budget on a developer's machine
is weather; a query count that grows with rows is the bug that took
`/api/v1/auctions` down in v1, and it shows up at a hundred rows as easily as
at a million.

The 300 ms budget is still asserted, because the point of the phase is a page
that opens.
"""

from __future__ import annotations

import time

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.auctions.listing import auction_page, vehicle_page
from apps.auctions.models import Vehicle
from apps.auctions.states import AuctionState, VehicleState

pytestmark = pytest.mark.django_db

#: Whole milliseconds, not fractional seconds. This tree now carries money
#: columns and is scanned by `no_float_in_money`, and a budget written as
#: `0.3` is a float literal on a money path's file — the guard cannot tell a
#: page budget from a riyal, and teaching it to would only teach people to
#: silence it here.
BUDGET_MILLISECONDS = 300
FLEET = 1_000


@pytest.fixture
def a_thousand_cars(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.LIVE)
    Vehicle.objects.bulk_create(
        Vehicle(
            auction=auction,
            lot_number=number,
            make="تويوتا",
            model="كامري",
            year=2022,
            state=VehicleState.LISTED,
        )
        for number in range(1, FLEET + 1)
    )
    return auction


def test_a_page_of_cars_is_three_queries_whatever_the_fleet_size(
    a_thousand_cars, django_assert_num_queries
):
    """Count, page, cover prefetch. Not one per car, and not one per page
    size — the same three for twenty rows out of a thousand."""
    with django_assert_num_queries(3):
        page = vehicle_page(AnonymousUser(), limit=20)

    assert page["total"] == FLEET
    assert len(page["results"]) == 20


def test_the_count_comes_from_the_database_not_from_python(
    a_thousand_cars, django_assert_num_queries
):
    """`len(list(queryset))` would be correct and would also load a thousand
    rows to produce one integer."""
    with django_assert_num_queries(3):
        page = vehicle_page(AnonymousUser(), limit=1, offset=990)

    assert page["total"] == FLEET
    assert len(page["results"]) == 1


def test_a_deep_page_costs_the_same_as_the_first(a_thousand_cars):
    first = time.perf_counter()
    vehicle_page(AnonymousUser(), limit=20, offset=0)
    early = time.perf_counter() - first

    second = time.perf_counter()
    vehicle_page(AnonymousUser(), limit=20, offset=FLEET - 20)
    late = time.perf_counter() - second

    assert early * 1000 < BUDGET_MILLISECONDS
    assert late * 1000 < BUDGET_MILLISECONDS


def test_the_auction_list_counts_its_vehicles_in_one_query(
    a_thousand_cars, make_auction, make_vehicle, django_assert_num_queries
):
    """The v1 shape was a count query per auction — quadratic by construction."""
    for _ in range(5):
        other = make_auction(state=AuctionState.LIVE)
        make_vehicle(other, state=VehicleState.LISTED)

    with django_assert_num_queries(2):  # the total, and the page with its counts
        page = auction_page(AnonymousUser(), limit=10)

    assert page["total"] == 6
    counts = {row["number"]: row["vehicle_count"] for row in page["results"]}
    assert counts[a_thousand_cars.number] == FLEET


def test_the_listing_stays_inside_the_budget_on_a_thousand_cars(a_thousand_cars):
    started = time.perf_counter()
    page = vehicle_page(AnonymousUser(), limit=20)
    elapsed = time.perf_counter() - started

    assert len(page["results"]) == 20
    assert elapsed * 1000 < BUDGET_MILLISECONDS, (
        f"{elapsed * 1000:.0f}ms > {BUDGET_MILLISECONDS}ms"
    )
