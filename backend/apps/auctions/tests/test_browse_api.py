"""T608 and T609 — browsing, and the one card shape both endpoints render.

Two requirements, and the second is the one that decays quietly:

* **T608** pages, filters and searches *in SQL*, with a ceiling on every
  parameter. v1 fetched every vehicle of every open auction and sliced the list
  in Python, so the cost grew with the table while the page stayed at twenty.
* **T609** returns, for one car, exactly the fields the list returns. Not
  "roughly the same" — the same set, compared here key by key. A detail page
  that grew a field the list never had is how v1 ended up with two answers to
  "what is this car".
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auctions.cards import VEHICLE_CARD_FIELDS
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState

pytestmark = pytest.mark.django_db


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def auction() -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=101,
        title="مزاد الرياض",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


@pytest.fixture
def hidden_auction() -> Auction:
    """A draft. Nobody outside the staff may know it exists."""
    now = timezone.now()
    return Auction.objects.create(
        number=999,
        title="مسودّة",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.DRAFT,
        deposit_required=Decimal("10000.00"),
    )


def a_car(auction: Auction, lot: int, **overrides) -> Vehicle:
    fields = {
        "auction": auction,
        "lot_number": lot,
        "make": "تويوتا",
        "model": "كامري",
        "year": 2020,
        "state": VehicleState.LISTED,
        "reserve_price": Decimal("55000.00"),
    }
    fields.update(overrides)
    return Vehicle.objects.create(**fields)


# ---------------------------------------------------------------------------
# T609 — one card shape, two endpoints
# ---------------------------------------------------------------------------


def test_the_detail_page_returns_exactly_the_fields_the_list_returns(api, auction):
    """The acceptance criterion, compared as sets rather than trusted."""
    vehicle = a_car(auction, 1)

    listed = api.get(reverse("auctions_api:vehicle-list")).data["results"][0]
    detail = api.get(reverse("auctions_api:vehicle-detail", args=[vehicle.pk])).data

    assert set(detail) == set(listed)
    assert set(detail) == set(VEHICLE_CARD_FIELDS)
    assert detail == listed


def test_a_car_nobody_may_see_is_a_404_not_a_403(api, hidden_auction):
    """A 403 confirms the row exists — enough to enumerate an auction early."""
    vehicle = a_car(hidden_auction, 1)

    response = api.get(reverse("auctions_api:vehicle-detail", args=[vehicle.pk]))

    assert response.status_code == 404


def test_the_listing_sends_no_price_at_all(api, auction):
    """‏v1 لا يعرض سعراً في القائمة، وطلب المالك «بدون زيادة» (2026-09-06).

    وليست مسألةَ عرض: هذه نقطةٌ **عامّة** لا تطلب دخولاً، فسعرٌ فيها يُخبر كلَّ
    من يفتحها بأقلّ ما يقبله البائع على كل مركبة. والسعر يصل من يحتاجه عبر
    `check_eligibility` بعد أن يُعرَف من هو.

    وقاعدة المادة ٣-٢ (المبلغ نصٌّ لا رقم) باقيةٌ حيث يبقى مبلغ — في المحفظة
    والفواتير وردّ الأهلية — ولها اختباراتها هناك.
    """
    a_car(auction, 1)

    card = api.get(reverse("auctions_api:vehicle-list")).data["results"][0]

    assert not [key for key in card if "price" in key], sorted(card)


# ---------------------------------------------------------------------------
# T608 — paging, filtering, searching, and the ceiling on each
# ---------------------------------------------------------------------------


def test_the_page_is_sliced_and_counted_by_the_database(api, auction):
    for lot in range(1, 26):
        a_car(auction, lot)

    page = api.get(reverse("auctions_api:vehicle-list"), {"limit": 5}).data

    assert page["total"] == 25
    assert len(page["results"]) == 5


def test_offset_walks_the_list_without_repeating_a_car(api, auction):
    for lot in range(1, 11):
        a_car(auction, lot)

    first = api.get(reverse("auctions_api:vehicle-list"), {"limit": 4}).data
    second = api.get(reverse("auctions_api:vehicle-list"), {"limit": 4, "offset": 4}).data

    assert {row["id"] for row in first["results"]} & {
        row["id"] for row in second["results"]
    } == set()


def test_a_limit_beyond_the_ceiling_is_refused(api, auction):
    """`?limit=100000` was a table scan any customer could ask v1 for."""
    response = api.get(reverse("auctions_api:vehicle-list"), {"limit": 100000})

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_search_matches_make_and_model(api, auction):
    a_car(auction, 1, make="تويوتا", model="كامري")
    a_car(auction, 2, make="نيسان", model="التيما")

    found = api.get(reverse("auctions_api:vehicle-list"), {"search": "التيما"}).data

    assert found["total"] == 1
    assert found["results"][0]["model"] == "التيما"


def test_a_number_in_the_search_box_finds_the_lot(api, auction):
    """Typing "47" into the box means lot 47 to everybody who uses this."""
    a_car(auction, 47, make="هوندا")
    a_car(auction, 48, make="هوندا")

    found = api.get(reverse("auctions_api:vehicle-list"), {"search": "47"}).data

    assert found["total"] == 1
    assert found["results"][0]["lot_number"] == 47


def test_the_year_range_filters_in_sql(api, auction):
    a_car(auction, 1, year=2015)
    a_car(auction, 2, year=2020)
    a_car(auction, 3, year=2023)

    found = api.get(
        reverse("auctions_api:vehicle-list"), {"year_from": 2018, "year_to": 2021}
    ).data

    assert found["total"] == 1
    assert found["results"][0]["year"] == 2020


def test_a_backwards_year_range_is_named_not_silently_empty(api, auction):
    response = api.get(
        reverse("auctions_api:vehicle-list"), {"year_from": 2023, "year_to": 2010}
    )

    assert response.status_code == 400


def test_filtering_cannot_reach_around_the_visibility_rule(api, hidden_auction):
    """A state a caller may not see returns an empty page, not a leak."""
    a_car(hidden_auction, 1, state=VehicleState.DRAFT)

    found = api.get(
        reverse("auctions_api:vehicle-list"), {"state": VehicleState.DRAFT}
    ).data

    assert found["total"] == 0


def test_the_filtered_total_counts_the_result_not_the_page(api, auction):
    """A total computed after slicing is a total that lies on page two."""
    for lot in range(1, 16):
        a_car(auction, lot, make="تويوتا")
    a_car(auction, 99, make="فورد")

    found = api.get(
        reverse("auctions_api:vehicle-list"), {"make": "تويوتا", "limit": 5}
    ).data

    assert found["total"] == 15
    assert len(found["results"]) == 5


# ---------------------------------------------------------------------------
# The auction list
# ---------------------------------------------------------------------------


def test_the_auction_list_hides_what_is_not_public(api, auction, hidden_auction):
    page = api.get(reverse("auctions_api:auction-list")).data

    assert page["total"] == 1
    assert page["results"][0]["number"] == 101


def test_the_auction_detail_agrees_with_its_row_in_the_list(api, auction):
    """Both read `cards.auction_card` over the same annotations."""
    a_car(auction, 1)
    # Withdrawn, not awarded: an awarded car must name its winner (a CHECK
    # constraint says so), and this test is about counting, not settlement.
    a_car(auction, 2, state=VehicleState.WITHDRAWN)

    listed = api.get(reverse("auctions_api:auction-list")).data["results"][0]
    detail = api.get(reverse("auctions_api:auction-detail", args=[auction.pk])).data

    assert detail == listed
    assert detail["vehicle_count"] == 2
    assert detail["open_vehicle_count"] == 1


def test_a_draft_auction_is_a_404(api, hidden_auction):
    response = api.get(reverse("auctions_api:auction-detail", args=[hidden_auction.pk]))

    assert response.status_code == 404


def test_one_auctions_cars_are_the_only_ones_listed(api, auction):
    other = Auction.objects.create(
        number=202,
        title="مزاد جدة",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )
    a_car(auction, 1)
    a_car(other, 1)

    page = api.get(reverse("auctions_api:auction-vehicles", args=[auction.pk])).data

    assert page["total"] == 1
    assert page["results"][0]["auction_number"] == 101


# ---------------------------------------------------------------------------
# The cost, measured
# ---------------------------------------------------------------------------


def test_a_page_costs_the_same_number_of_queries_whatever_its_size(
    api, auction, django_assert_num_queries
):
    """The v1 failure was O(n) queries in the page size. This is the check.

    Not a comment claiming the joins are declared — a count. `card_queryset`
    promises three queries for any page (T407, T408) and the two paging queries
    sit on top of it; if a card ever starts reaching for a row of its own, this
    fails at five cars rather than at five thousand.
    """
    for lot in range(1, 21):
        a_car(auction, lot)

    with django_assert_num_queries(3) as small:
        api.get(reverse("auctions_api:vehicle-list"), {"limit": 1})

    # The same count for twenty cars as for one. That equality is the whole
    # assertion — the absolute number is whatever `card_queryset` needs today,
    # but a card that starts fetching a row of its own breaks the equality at
    # five cars instead of at five thousand.
    with django_assert_num_queries(len(small.captured_queries)):
        api.get(reverse("auctions_api:vehicle-list"), {"limit": 20})
