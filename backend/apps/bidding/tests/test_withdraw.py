"""T507 — withdrawing a bid, and who still keeps their deposit afterwards.

The second test here is the one that matters. In v1 `settleAuction` released
the deposit of a bidder who was still in the running on a car nobody had
decided yet; the money left and had to be asked for again. A withdrawal is the
same question asked earlier, and it has to give the same answer.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.auctions import services as auctions
from apps.bidding import services
from apps.bidding.models import Bid
from apps.money import services as money
from apps.money.models import AccountKind, Hold, HoldState
from apps.money.verification import verify_ledger

from .conftest import TEN_K, make_vehicle

pytestmark = pytest.mark.django_db

BID = Decimal("30000.00")


def held(user) -> Decimal:
    return money.account_for(user, AccountKind.INSURANCE_HELD).balance


def free(user) -> Decimal:
    return money.account_for(user, AccountKind.INSURANCE_FREE).balance


def test_a_withdrawn_bid_is_marked_not_deleted(bidder, vehicle):
    bid = services.place_bid(user=bidder, vehicle=vehicle, amount=BID)

    services.withdraw_bid(user=bidder, bid=bid)

    bid.refresh_from_db()
    assert bid.is_withdrawn
    assert bid.withdrawn_at is not None
    assert Bid.objects.filter(pk=bid.pk).exists(), "history is never deleted"
    assert not Bid.objects.live().filter(vehicle=vehicle).exists()


def test_the_last_withdrawal_in_an_auction_frees_the_deposit(bidder, vehicle):
    bid = services.place_bid(user=bidder, vehicle=vehicle, amount=BID)
    assert held(bidder) == TEN_K

    services.withdraw_bid(user=bidder, bid=bid)

    assert held(bidder) == Decimal("0.00")
    assert free(bidder) == TEN_K
    assert not Hold.objects.filter(owner=bidder, state=HoldState.ACTIVE).exists()
    assert verify_ledger() == []


def test_a_competitor_on_an_undecided_car_keeps_their_deposit(bidder, live_auction):
    """Two cars, one withdrawal. The other car is still open, so the deposit
    stays — this is the v1 incident in miniature."""
    first = make_vehicle(live_auction, lot=1)
    second = make_vehicle(live_auction, lot=2)

    withdrawn = services.place_bid(user=bidder, vehicle=first, amount=BID)
    services.place_bid(user=bidder, vehicle=second, amount=BID)

    services.withdraw_bid(user=bidder, bid=withdrawn)

    assert held(bidder) == TEN_K, "a live competitor's deposit must not be released"
    assert Hold.objects.filter(owner=bidder, state=HoldState.ACTIVE).count() == 1
    assert verify_ledger() == []


def test_a_winner_keeps_their_deposit_after_withdrawing_elsewhere(bidder, live_auction):
    """Winning one car ties the deposit even after every other bid is pulled."""
    won = make_vehicle(live_auction, lot=1)
    other = make_vehicle(live_auction, lot=2)

    services.place_bid(user=bidder, vehicle=won, amount=BID)
    pulled = services.place_bid(user=bidder, vehicle=other, amount=BID)

    auctions.award(won, bidder, BID)
    services.withdraw_bid(user=bidder, bid=pulled)

    assert held(bidder) == TEN_K
    assert verify_ledger() == []


def test_withdrawing_twice_changes_nothing(bidder, vehicle):
    bid = services.place_bid(user=bidder, vehicle=vehicle, amount=BID)

    services.withdraw_bid(user=bidder, bid=bid)
    services.withdraw_bid(user=bidder, bid=bid)

    assert free(bidder) == TEN_K
    assert verify_ledger() == []


def test_only_the_bidder_may_withdraw_their_bid(bidder, outsider, vehicle):
    bid = services.place_bid(user=bidder, vehicle=vehicle, amount=BID)

    with pytest.raises(services.NotYourBid):
        services.withdraw_bid(user=outsider, bid=bid)

    bid.refresh_from_db()
    assert not bid.is_withdrawn
