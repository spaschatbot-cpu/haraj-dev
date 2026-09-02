"""E3 — the auction starts and ends on Saudi time, across a day change.

The interesting cases are not "an hour later". They are the ones where the
Riyadh date and the UTC date disagree: an auction an operator scheduled for
midnight Sunday starts at 21:00 UTC on Saturday, and any code that reasons
about "today" in the wrong zone is off by a day for three hours of every day.

Nothing here converts a timezone by hand — `apps.core.time.from_display` is
the only conversion, at the edge where a human's wall clock enters the system
(Article 3-1).
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from django.db import connections

from apps.auctions import services
from apps.auctions.models import Auction
from apps.auctions.states import AuctionState
from apps.auctions.tasks import LOCK_NAME, run_calendar
from apps.core.locks import single_instance
from apps.core.time import from_display, to_display

pytestmark = pytest.mark.django_db

#: Midnight in Riyadh, on a Sunday, typed by an operator into a form.
RIYADH_MIDNIGHT = datetime(2026, 9, 6, 0, 0)
MINUTE = timedelta(minutes=1)


def test_a_riyadh_midnight_is_stored_as_the_previous_utc_day():
    """The premise the rest of the file rests on, asserted rather than assumed."""
    stored = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)

    assert stored == datetime(2026, 9, 5, 21, 0, tzinfo=UTC)
    assert stored.date() != to_display(stored).date()  # the day change itself


def test_an_auction_starts_at_riyadh_midnight_not_utc_midnight(
    make_auction, make_vehicle
):
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    auction = make_auction(
        state=AuctionState.SCHEDULED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
    )
    make_vehicle(auction)

    run_calendar(now=starts_at - MINUTE)
    assert Auction.objects.get(pk=auction.pk).state == AuctionState.SCHEDULED

    run_calendar(now=starts_at)
    assert Auction.objects.get(pk=auction.pk).state == AuctionState.LIVE


def test_utc_midnight_of_the_saudi_day_does_not_start_it_early(
    make_auction, make_vehicle
):
    """03:00 Riyadh on the Saudi day is 00:00 UTC — three hours too early.

    This is the exact off-by-a-day that kept breaking v1: code that asked
    "is it the auction's day yet?" in the server's zone.
    """
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    auction = make_auction(
        state=AuctionState.SCHEDULED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
    )
    make_vehicle(auction)

    utc_midnight_of_the_saudi_day = datetime(2026, 9, 6, 0, 0, tzinfo=UTC)
    assert to_display(utc_midnight_of_the_saudi_day).date() == RIYADH_MIDNIGHT.date()

    run_calendar(now=starts_at - MINUTE)

    assert Auction.objects.get(pk=auction.pk).state == AuctionState.SCHEDULED


def test_an_auction_ends_across_the_day_change(make_auction, make_vehicle):
    """Starts 22:00 Riyadh Sunday, ends 02:00 Riyadh Monday — one UTC day."""
    starts_at = from_display(datetime(2026, 9, 6, 22, 0), assume_display_timezone=True)
    ends_at = from_display(datetime(2026, 9, 7, 2, 0), assume_display_timezone=True)
    assert starts_at.date() == ends_at.date()  # same UTC day, different Riyadh days
    assert to_display(starts_at).date() != to_display(ends_at).date()

    auction = make_auction(
        state=AuctionState.SCHEDULED, starts_at=starts_at, ends_at=ends_at
    )
    make_vehicle(auction)

    run_calendar(now=starts_at)
    assert Auction.objects.get(pk=auction.pk).state == AuctionState.LIVE

    run_calendar(now=ends_at - MINUTE)
    assert Auction.objects.get(pk=auction.pk).state == AuctionState.LIVE

    run_calendar(now=ends_at)
    assert Auction.objects.get(pk=auction.pk).state == AuctionState.ENDED


def test_a_window_that_passed_while_the_worker_was_down_is_caught_up(
    make_auction, make_vehicle
):
    """One tick takes it `scheduled → live → ended`.

    Leaving it live until the next tick would open a window in which a bid
    could be accepted on an auction that finished hours ago.
    """
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    auction = make_auction(
        state=AuctionState.SCHEDULED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
    )
    make_vehicle(auction)

    result = run_calendar(now=auction.ends_at + timedelta(days=1))

    assert Auction.objects.get(pk=auction.pk).state == AuctionState.ENDED
    assert result["started"] == [auction.pk]
    assert result["ended"] == [auction.pk]


def test_the_calendar_leaves_drafts_and_cancelled_auctions_alone(
    make_auction, make_vehicle
):
    """Only `scheduled` starts and only `live` ends — the table decides."""
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    untouched = {}
    for state in (AuctionState.DRAFT, AuctionState.CANCELLED, AuctionState.ENDED):
        auction = make_auction(
            state=state, starts_at=starts_at, ends_at=starts_at + timedelta(hours=4)
        )
        make_vehicle(auction)
        untouched[auction.pk] = state

    run_calendar(now=starts_at + timedelta(days=1))

    for pk, state in untouched.items():
        assert Auction.objects.get(pk=pk).state == state


def test_the_calendar_is_idempotent_within_a_tick(make_auction, make_vehicle):
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    auction = make_auction(
        state=AuctionState.SCHEDULED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
    )
    make_vehicle(auction)

    first = run_calendar(now=starts_at)
    second = run_calendar(now=starts_at)

    assert first["started"] == [auction.pk]
    assert second["started"] == []


@pytest.mark.django_db(transaction=True)
def test_the_calendar_stands_down_when_another_worker_holds_the_lock():
    """Article 5-1. The holder must be another connection: an advisory lock is
    session-scoped, so taking it again from this one would prove nothing."""
    holding = threading.Event()
    release = threading.Event()
    outcome = {}

    def holder():
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
        result = run_calendar()
    finally:
        release.set()
        thread.join(timeout=10)

    assert outcome["holder_got_it"] is True
    assert "skipped" in result


def test_the_calendar_is_not_on_a_schedule():
    """Article 5-2 — defined and tested, never scheduled without a decision.

    This assertion is the place where that decision has to be made out loud:
    adding a beat entry means deleting a test that says why you shouldn't.
    """
    beat = getattr(settings, "CELERY_BEAT_SCHEDULE", {})
    scheduled = [
        name
        for name, entry in beat.items()
        if "auction" in str(entry.get("task", "")).lower()
    ]
    assert scheduled == []


def test_due_queries_compare_utc_to_utc(make_auction, make_vehicle):
    """The comparison never touches the display zone.

    A converted column compared against an unconverted one is the single most
    expensive class of v1 bug; here the query gets `starts_at` as stored.
    """
    starts_at = from_display(RIYADH_MIDNIGHT, assume_display_timezone=True)
    auction = make_auction(
        state=AuctionState.SCHEDULED,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=4),
    )
    make_vehicle(auction)

    assert list(services.due_to_activate(starts_at)) == [auction]
    assert list(services.due_to_activate(starts_at - MINUTE)) == []
