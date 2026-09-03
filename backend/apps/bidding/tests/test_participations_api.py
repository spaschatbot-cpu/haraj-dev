"""`GET /api/v1/participations/` — the auctions I am in, and my deposit in each.

Why the endpoint exists, written down because the alternative is what the
Flutter app was about to do. The «مشاركاتي» screen needs, per auction, how many
bids I still have standing and what my insurance for that auction is doing. Both
facts exist — `Bid` and `money.Hold` — and neither list carries the other, so
building the answer on the client means matching bids against wallet holds in a
screen. A rule that lives in a screen is a second copy of a rule (Article 4-5):
the app's idea of «محجوز» drifts from the ledger's the first time a hold is
released or consumed without a bid changing.

The app had already been generated against this path and the server served no
route for it, so «مشاركاتي» would have shown an error page against a real
backend. This is the route it was calling.

Everything here is the caller's own rows. A sealed auction's property is that
bidders cannot see each other, and a list of *participants* is exactly the shape
that leaks it.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import tokens as token_service
from apps.auctions.models import Auction
from apps.auctions.states import AuctionState
from apps.bidding import services as bidding
from apps.money import services as money
from apps.money.models import Hold, HoldState

from .conftest import TEN_K, make_vehicle

pytestmark = pytest.mark.django_db

URL = "bidding_api:my-participations"


def signed_in(user) -> APIClient:
    api = APIClient()
    pair = token_service.issue_pair(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return api


def rows(response) -> list[dict]:
    return response.data["results"]


def test_an_auction_i_bid_in_appears_with_my_bid_count(bidder, vehicle, live_auction):
    bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))
    second = make_vehicle(live_auction, lot=2)
    bidding.place_bid(user=bidder, vehicle=second, amount=Decimal("60000.00"))

    response = signed_in(bidder).get(reverse(URL))

    assert response.status_code == 200
    assert response.data["total"] == 1, "المزاد الواحد صفٌّ واحد مهما كثرت مزايداته"
    row = rows(response)[0]
    assert row["auction"]["id"] == live_auction.pk
    assert row["auction"]["title"] == "مزاد المزايدة"
    assert row["bids_count"] == 2


def test_the_auction_state_arrives_named_not_only_coded(bidder, vehicle):
    """A screen must not carry a second copy of the state vocabulary.

    `state_label` is the auction's own Arabic word for itself; an app that maps
    `live` → «جارٍ» owns a table that drifts the day a state is added.
    """
    bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))

    row = rows(signed_in(bidder).get(reverse(URL)))[0]

    assert row["auction"]["state"] == AuctionState.LIVE
    assert row["auction"]["state_label"] == AuctionState(AuctionState.LIVE).label


def test_a_standing_bid_holds_the_deposit_and_the_row_says_so(bidder, vehicle):
    bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))

    row = rows(signed_in(bidder).get(reverse(URL)))[0]

    assert row["insurance"]["state"] == HoldState.ACTIVE
    assert row["insurance"]["state_label"] == HoldState(HoldState.ACTIVE).label
    assert row["insurance"]["amount"] == str(TEN_K)
    assert isinstance(row["insurance"]["amount"], str), "المادة ٣-٢"
    assert row["insurance"]["currency"]


def test_the_insurance_state_is_the_ledgers_and_not_derived_from_the_bids(
    bidder, vehicle, live_auction
):
    """The one thing a client could never have worked out for itself.

    The deposit is released while every bid row stays exactly as it was. An app
    matching «مزايداتي» against «المحفظة» would still be showing «محجوز» — the
    hold is the only thing that knows, and it is what this field reads.
    """
    bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))
    money.release_hold(
        Hold.objects.get(owner=bidder, auction=live_auction, state=HoldState.ACTIVE)
    )

    row = rows(signed_in(bidder).get(reverse(URL)))[0]

    assert row["bids_count"] == 1
    assert row["insurance"]["state"] == HoldState.RELEASED
    assert row["insurance"]["amount"] is None, "المفكوك ليس محجوزاً، فلا يُعرض مبلغه"


def test_holding_a_deposit_without_bidding_is_still_a_participation(
    bidder, live_auction
):
    """Money pinned to an auction is being *in* it, bid or no bid.

    A row omitted here is a customer looking at a wallet that says 10,000
    محجوز and a list that shows nothing holding it.
    """
    money.hold_for_auction(user=bidder, auction=live_auction)

    response = signed_in(bidder).get(reverse(URL))

    assert response.data["total"] == 1
    assert rows(response)[0]["bids_count"] == 0
    assert rows(response)[0]["insurance"]["state"] == HoldState.ACTIVE


def test_a_withdrawn_bid_leaves_the_participation_and_stops_counting(
    bidder, vehicle, live_auction
):
    bid = bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))
    bidding.withdraw_bid(user=bidder, bid=bid)

    row = rows(signed_in(bidder).get(reverse(URL)))[0]

    assert row["auction"]["id"] == live_auction.pk
    assert row["bids_count"] == 0, "المسحوبة لا تُعدّ، والمشاركة لا تُمحى"


def test_i_see_only_my_own_participations(bidder, outsider, vehicle):
    money.deposit_insurance(
        user=outsider, amount=TEN_K, source="cash", reference="dep/outsider"
    )
    bidding.place_bid(user=outsider, vehicle=vehicle, amount=Decimal("70000.00"))

    response = signed_in(bidder).get(reverse(URL))

    assert response.data["total"] == 0, "قائمة المشاركين تكسر ختم المزاد"


def test_the_endpoint_needs_a_caller(client):
    assert client.get(reverse(URL)).status_code == 401


def test_an_auction_i_never_touched_is_absent(bidder, vehicle):
    now = timezone.now()
    Auction.objects.create(
        number=999,
        title="مزاد لم أدخله",
        starts_at=now,
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )
    bidding.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("55000.00"))

    assert signed_in(bidder).get(reverse(URL)).data["total"] == 1


def test_the_page_is_bounded(bidder, live_auction):
    money.hold_for_auction(user=bidder, auction=live_auction)

    response = signed_in(bidder).get(reverse(URL), {"limit": 1, "offset": 1})

    assert response.data["total"] == 1
    assert rows(response) == []
