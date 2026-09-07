"""T007 — the two conversions, and the guess that is refused.

Saudi Arabia is UTC+3 all year with no daylight saving, so every expectation
here is a fixed three-hour shift. The cases that matter are the ones where
that shift moves the calendar date, because a date that silently moves is how
an auction appears to close on the wrong day.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from apps.core.time import from_display, to_display

RIYADH = ZoneInfo("Asia/Riyadh")


def test_utc_becomes_saudi_time():
    stored = datetime(2026, 3, 14, 9, 30, tzinfo=UTC)

    shown = to_display(stored)

    assert shown.hour == 12
    assert shown.minute == 30
    assert shown.utcoffset() == timedelta(hours=3)


def test_saudi_midnight_is_the_previous_day_in_storage():
    """Midnight in Riyadh is 21:00 UTC the day before.

    An auction scheduled to open at 00:00 on the 15th is stored under the
    14th. Any code that compares that stored value against a Saudi date
    without converting is off by a day — which is the whole reason this
    module exists.
    """
    entered = datetime(2026, 3, 15, 0, 0, tzinfo=RIYADH)

    stored = from_display(entered)

    assert stored.astimezone(UTC) == datetime(2026, 3, 14, 21, 0, tzinfo=UTC)
    assert stored.date() == datetime(2026, 3, 14).date()


def test_late_utc_evening_is_already_tomorrow_for_the_customer():
    stored = datetime(2026, 3, 14, 22, 15, tzinfo=UTC)

    shown = to_display(stored)

    assert shown.date() == datetime(2026, 3, 15).date()
    assert shown.hour == 1


def test_round_trip_returns_the_same_moment():
    stored = datetime(2026, 7, 1, 18, 45, tzinfo=UTC)

    assert from_display(to_display(stored)) == stored


def test_to_display_refuses_a_naive_value():
    with pytest.raises(ValueError, match="aware datetime"):
        to_display(datetime(2026, 3, 15, 0, 0))


def test_from_display_refuses_a_naive_value_by_default():
    """Silence here would be a guess, and a wrong guess is invisible."""
    with pytest.raises(ValueError, match="aware datetime"):
        from_display(datetime(2026, 3, 15, 0, 0))


def test_from_display_accepts_a_naive_value_only_when_told_to():
    entered = datetime(2026, 3, 15, 0, 0)

    stored = from_display(entered, assume_display_timezone=True)

    assert stored == datetime(2026, 3, 14, 21, 0, tzinfo=UTC)


def test_a_value_in_a_third_timezone_is_converted_not_relabelled():
    cairo = datetime(2026, 3, 15, 0, 0, tzinfo=ZoneInfo("Africa/Cairo"))

    stored = from_display(cairo)

    assert stored == datetime(2026, 3, 14, 22, 0, tzinfo=UTC)


def test_display_timezone_is_read_from_settings(settings):
    settings.DISPLAY_TIME_ZONE = "UTC"

    shown = to_display(datetime(2026, 3, 14, 9, 30, tzinfo=UTC))

    assert shown.utcoffset() == timedelta(0)
