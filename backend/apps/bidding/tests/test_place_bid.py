"""T504 / T505 / T506 — placing a bid, under load and under revision.

The concurrency here is real threads on real PostgreSQL connections. A mocked
race proves nothing about `SELECT ... FOR UPDATE`, and the two findings this
module exists to prevent (F-003 and F-004 in `specs/002-money-engine`) were both
invisible to sequential tests.
"""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from django.db import IntegrityError, connections
from django.utils import timezone

from apps.auctions.states import VehicleState
from apps.bidding import services
from apps.bidding.models import Bid, BidRefusal
from apps.money import services as money
from apps.money.models import AccountKind, Hold, HoldState
from apps.money.verification import verify_ledger

from .conftest import TEN_K, make_user, make_vehicle

pytestmark = pytest.mark.django_db(transaction=True)

BIDDERS = 50


def run_in_threads(target, count):
    """Run `target(index)` in `count` real threads and collect the outcomes.

    The same shape as `apps/money/tests/test_posting.py::run_in_threads`, kept
    as a copy rather than shared: a test helper that spans two apps becomes a
    thing to keep working, and this one is five lines of `threading`. Each
    thread closes its own connection, without which the next test hangs on a
    lock instead of failing.
    """
    results: list = [None] * count
    errors: list = [None] * count

    def wrapped(i):
        try:
            results[i] = target(i)
        except Exception as exc:  # noqa: BLE001 — the test inspects the type
            errors[i] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=wrapped, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)

    return results, errors


def funded_crowd(django_user_model, size: int) -> list:
    people = []
    for index in range(size):
        person = make_user(
            django_user_model,
            phone=f"9665020{index:05d}",
            national_id=f"2{index:09d}",
            full_name=f"مزايد {index}",
            phone_verified_at=timezone.now(),
        )
        money.deposit_insurance(
            user=person, amount=TEN_K, source="cash", reference=f"dep/crowd/{index}"
        )
        people.append(person)
    return people


# ---------------------------------------------------------------------------
# T504 / F1 — fifty at once on one car
# ---------------------------------------------------------------------------


def test_fifty_concurrent_bids_on_one_car_neither_lose_nor_duplicate(
    django_user_model, vehicle
):
    crowd = funded_crowd(django_user_model, BIDDERS)
    amounts = [Decimal("20000.00") + index * 100 for index in range(BIDDERS)]

    def bid(index):
        return services.place_bid(
            user=crowd[index], vehicle=vehicle, amount=amounts[index]
        )

    results, errors = run_in_threads(bid, BIDDERS)

    assert [error for error in errors if error is not None] == []
    assert all(result is not None for result in results)
    assert BidRefusal.objects.count() == 0

    live = list(Bid.objects.live().filter(vehicle=vehicle))
    assert len(live) == BIDDERS, "a bid was lost"
    assert Bid.objects.filter(vehicle=vehicle).count() == BIDDERS, "a bid was doubled"
    assert {bid.bidder_id for bid in live} == {person.pk for person in crowd}
    assert sorted(bid.amount for bid in live) == sorted(amounts)

    # Consistent order: the ranking the model promises is a strict one, and the
    # car's top bid is the largest number anybody sent.
    ranked = list(Bid.objects.live().filter(vehicle=vehicle).order_by("-amount", "id"))
    assert [bid.amount for bid in ranked] == sorted(amounts, reverse=True)
    assert ranked[0].amount == max(amounts)

    assert Hold.objects.filter(state=HoldState.ACTIVE).count() == BIDDERS
    assert verify_ledger() == []

    vehicle.refresh_from_db()
    assert vehicle.state == VehicleState.BIDDING


# ---------------------------------------------------------------------------
# T505 — the deposit is taken once per auction
# ---------------------------------------------------------------------------


def test_twenty_bids_in_one_auction_hold_once(bidder, live_auction):
    cars = [make_vehicle(live_auction, lot=lot) for lot in range(1, 21)]

    for index, car in enumerate(cars):
        services.place_bid(user=bidder, vehicle=car, amount=Decimal("30000.00") + index)

    holds = Hold.objects.filter(owner=bidder, state=HoldState.ACTIVE)
    assert holds.count() == 1
    assert holds.first().amount == TEN_K
    assert money.account_for(bidder, AccountKind.INSURANCE_HELD).balance == TEN_K
    assert money.account_for(bidder, AccountKind.INSURANCE_FREE).balance == Decimal(
        "0.00"
    )
    assert verify_ledger() == []


def test_twenty_concurrent_bids_by_one_person_hold_once(bidder, live_auction):
    """The same customer on twenty cars at the same instant.

    Every one of them contends for one `insurance_free` row inside
    `hold_for_auction`, and each holds a different vehicle row on the way in —
    which is the lock order this module promises, tested rather than asserted.
    """
    cars = [make_vehicle(live_auction, lot=lot) for lot in range(1, 21)]

    def bid(index):
        return services.place_bid(
            user=bidder, vehicle=cars[index], amount=Decimal("30000.00") + index
        )

    results, errors = run_in_threads(bid, len(cars))

    assert [error for error in errors if error is not None] == []
    assert all(result is not None for result in results)
    assert Hold.objects.filter(owner=bidder, state=HoldState.ACTIVE).count() == 1
    assert money.account_for(bidder, AccountKind.INSURANCE_HELD).balance == TEN_K
    assert verify_ledger() == []


def test_the_first_bid_opens_the_car(bidder, vehicle):
    assert vehicle.state == VehicleState.LISTED

    services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("30000.00"))

    vehicle.refresh_from_db()
    assert vehicle.state == VehicleState.BIDDING


# ---------------------------------------------------------------------------
# T506 / F3 — lowering is allowed, but never by accident
# ---------------------------------------------------------------------------


def test_a_lower_bid_is_refused_until_it_is_confirmed(bidder, vehicle):
    standing = services.place_bid(
        user=bidder, vehicle=vehicle, amount=Decimal("30000.00")
    )

    with pytest.raises(services.LowerBidNeedsConfirmation) as raised:
        services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("25000.00"))

    assert raised.value.code == "lower_needs_confirm"
    assert raised.value.detail["standing"] == "30000.00"

    standing.refresh_from_db()
    assert not standing.is_superseded
    assert Bid.objects.filter(vehicle=vehicle).count() == 1


def test_a_confirmed_lower_bid_replaces_the_standing_one(bidder, vehicle):
    standing = services.place_bid(
        user=bidder, vehicle=vehicle, amount=Decimal("30000.00")
    )

    revised = services.place_bid(
        user=bidder,
        vehicle=vehicle,
        amount=Decimal("25000.00"),
        confirm_lower=True,
    )

    standing.refresh_from_db()
    assert standing.is_superseded
    assert revised.supersedes_id == standing.pk
    assert list(Bid.objects.live().filter(vehicle=vehicle)) == [revised]
    assert Bid.objects.filter(vehicle=vehicle).count() == 2, "history stays whole"


def test_raising_needs_no_confirmation(bidder, vehicle):
    standing = services.place_bid(
        user=bidder, vehicle=vehicle, amount=Decimal("30000.00")
    )

    raised = services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("35000.00"))

    standing.refresh_from_db()
    assert standing.is_superseded
    assert list(Bid.objects.live().filter(vehicle=vehicle)) == [raised]


def test_the_same_amount_twice_is_one_bid(bidder, vehicle):
    first = services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("30000.00"))
    again = services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("30000.00"))

    assert again.pk == first.pk
    assert Bid.objects.filter(vehicle=vehicle).count() == 1


def test_a_second_live_bid_is_impossible_even_without_the_service(bidder, vehicle):
    """The rule lives in the schema, not only in the code (Article 3-3)."""
    services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("30000.00"))

    with pytest.raises(IntegrityError):
        Bid.objects.create(vehicle=vehicle, bidder=bidder, amount=Decimal("31000.00"))


def test_a_bid_of_zero_is_not_a_bid(bidder, vehicle):
    with pytest.raises(services.BiddingError):
        services.place_bid(user=bidder, vehicle=vehicle, amount=Decimal("0.00"))
