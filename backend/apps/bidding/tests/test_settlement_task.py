"""T512 — one settlement at a time, and nothing on a schedule.

Two things this file proves, and the second is as important as the first:

* **Contention stands down.** A second worker finding the lock held returns
  without settling anything. The holder must be on *another connection* — an
  advisory lock is session-scoped, so taking it again from this one would
  prove nothing at all.
* **Neither task is on a beat.** Article 5-2. In v1 one cron nobody decided to
  enable issued 38 unintended invoices, and this task moves more money than
  that one did.
"""

from __future__ import annotations

import threading
from decimal import Decimal

import pytest
from django.db import connections
from django.utils import timezone

from apps.auctions import services as auctions
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding.tasks import (
    LOCK_NAME,
    close_settled_auctions,
    settle_ended_auctions,
)
from apps.core.locks import single_instance
from apps.money import services as money
from apps.money.models import Hold, HoldReason, HoldState
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db(transaction=True)


def an_ended_auction(number: int = 700) -> Auction:
    """Created live and then ended, so the row got there the way real ones do."""
    now = timezone.now()
    auction = Auction.objects.create(
        number=number,
        title="مزاد منتهٍ",
        starts_at=now - timezone.timedelta(hours=3),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )
    return end_now(auction)


def a_live_auction(number: int = 701) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=number,
        title="مزاد جارٍ",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


def end_now(auction: Auction) -> Auction:
    """Close ``auction`` through the state machine, not around it.

    `ops/checks/auction_state_single_writer.py` fails the build on a test that
    writes `state` directly, and it is right to: a fixture that bypasses the
    transition is a fixture that stops proving the transition works. So the
    clock moves — which is a fact about time, not a state — and
    `services.end` does the rest.
    """
    Auction.objects.filter(pk=auction.pk).update(
        ends_at=timezone.now() - timezone.timedelta(minutes=1)
    )
    auction.refresh_from_db()
    return auctions.end(auction)


def a_car(auction: Auction, lot: int = 1, reserve: str = "40000.00") -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal(reserve),
    )


def a_bidder(django_user_model, phone: str):
    user = django_user_model.objects.create_user(
        phone=phone, full_name="مزايد", national_id=phone[-10:]
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(
        user=user, amount=Decimal("50000.00"), source="cash", reference=f"seed/{phone}"
    )
    return user


# ---------------------------------------------------------------------------
# The lock
# ---------------------------------------------------------------------------


def test_a_second_worker_stands_down_while_the_first_holds_the_lock(
    django_user_model,
):
    """The acceptance criterion: two concurrent runs, one does the work.

    The lock matters here beyond tidiness. `settle_auction` is idempotent, so
    two copies would not double-release — but they would *interleave*: one
    computes the competitor set, the other resolves a car, and the first then
    releases a deposit belonging to somebody who became a competitor a moment
    ago. That is v1's bug re-created by concurrency instead of by logic.
    """
    auction = a_live_auction()
    car = a_car(auction)
    loser = a_bidder(django_user_model, "966501111111")
    winner = a_bidder(django_user_model, "966502222222")

    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=loser, vehicle=car, amount=Decimal("50000.00"))
    end_now(auction)

    holding = threading.Event()
    release = threading.Event()
    outcome: dict = {}

    def holder() -> None:
        try:
            with single_instance(LOCK_NAME) as acquired:
                outcome["holder_got_it"] = acquired
                holding.set()
                release.wait(timeout=10)
        finally:
            connections.close_all()

    thread = threading.Thread(target=holder)
    thread.start()
    holding.wait(timeout=10)

    try:
        result = settle_ended_auctions()
    finally:
        release.set()
        thread.join(timeout=10)

    assert outcome["holder_got_it"] is True
    assert result == {"skipped": "another instance holds the lock"}

    # And nothing moved: the loser's deposit is exactly where it was.
    assert Hold.objects.filter(
        owner=loser, auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).exists()
    assert verify_ledger() == []


def test_the_task_settles_when_the_lock_is_free(django_user_model):
    auction = a_live_auction()
    car = a_car(auction)
    winner = a_bidder(django_user_model, "966501111111")
    loser = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=loser, vehicle=car, amount=Decimal("50000.00"))

    end_now(auction)

    result = settle_ended_auctions()

    assert result["settled"] == [auction.pk]
    assert result["failed"] == []
    assert not Hold.objects.filter(
        owner=loser, auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).exists()
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# What it picks up, and what it leaves alone
# ---------------------------------------------------------------------------


def test_a_live_auction_is_not_settled(django_user_model):
    """Settling an auction that is still accepting bids resolves it early."""
    auction = a_live_auction()
    car = a_car(auction)
    bidder = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("70000.00"))

    result = settle_ended_auctions()

    car.refresh_from_db()
    assert result["settled"] == []
    assert car.state == VehicleState.BIDDING


def test_a_failing_auction_does_not_stop_the_others(monkeypatch, django_user_model):
    """A task that reports success while skipping one is how money stays held."""
    first = an_ended_auction(number=710)
    second = an_ended_auction(number=711)

    from apps.bidding import tasks

    real = tasks.settlement.settle_auction

    def explode_on_the_first(auction, **kwargs):
        if auction.pk == first.pk:
            raise RuntimeError("boom")
        return real(auction, **kwargs)

    monkeypatch.setattr(tasks.settlement, "settle_auction", explode_on_the_first)

    result = settle_ended_auctions()

    assert result["failed"] == [first.pk]
    assert result["settled"] == [second.pk]


def test_running_the_task_twice_changes_nothing_the_second_time(django_user_model):
    auction = a_live_auction()
    car = a_car(auction)
    winner = a_bidder(django_user_model, "966501111111")
    loser = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=loser, vehicle=car, amount=Decimal("50000.00"))
    end_now(auction)

    settle_ended_auctions()
    free_after_first = money.account_for(loser, "insurance_free").balance

    settle_ended_auctions()

    assert money.account_for(loser, "insurance_free").balance == free_after_first
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# Closing
# ---------------------------------------------------------------------------


def test_an_auction_waiting_on_its_owner_is_reported_not_closed(django_user_model):
    """An owner deciding on a car takes as long as it takes. Not an error."""
    auction = a_live_auction()
    car = a_car(auction, reserve="90000.00")
    bidder = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("50000.00"))
    end_now(auction)
    settle_ended_auctions()

    result = close_settled_auctions()

    auction.refresh_from_db()
    assert result["closed"] == []
    assert result["waiting"] == [auction.pk]
    assert auction.state == AuctionState.ENDED


def test_an_auction_whose_cars_are_resolved_is_closed(django_user_model):
    auction = a_live_auction()
    car = a_car(auction)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    end_now(auction)
    settle_ended_auctions()

    result = close_settled_auctions()

    auction.refresh_from_db()
    assert result["closed"] == [auction.pk]
    assert auction.state == AuctionState.SETTLED


# ---------------------------------------------------------------------------
# Article 5-2 — defined, and deliberately not scheduled
# ---------------------------------------------------------------------------


def test_neither_settlement_task_is_on_a_schedule():
    """v1's one unplanned cron issued 38 invoices. This one moves more money.

    Enabling a beat is a per-environment decision somebody makes on purpose;
    this test is what makes "on purpose" mean editing a line that fails a test
    rather than adding one nobody notices.
    """
    from config.celery import app

    scheduled = {entry.get("task") for entry in (app.conf.beat_schedule or {}).values()}

    assert LOCK_NAME not in scheduled
    assert "bidding.close_settled_auctions" not in scheduled
