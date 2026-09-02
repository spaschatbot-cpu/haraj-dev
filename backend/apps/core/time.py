"""The only place a timestamp changes timezone.

Everything is stored in UTC. Auction times are entered and read in Saudi time.
The conversion happens here and nowhere else — not in a view, not in a
serializer, and never inside a query (Article 3-1).

Two functions, one direction each. The costliest v1 outages came from
comparing a converted column against an unconverted one, and a single pair of
named conversions makes that mistake visible in review instead of at
settlement time.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from django.conf import settings


def to_display(value: datetime) -> datetime:
    """A stored moment → the display timezone.

    Call at the presentation edge only: rendering a template, building a
    response, formatting a message.
    """
    _reject_naive(value, caller="to_display")
    return value.astimezone(_display_timezone())


def from_display(value: datetime, *, assume_display_timezone: bool = False) -> datetime:
    """A time a human entered → UTC, ready to store.

    An aware value is converted from whatever zone it carries. A naive one is
    refused unless the caller states, with `assume_display_timezone=True`,
    that it really is a display-local wall clock — a form field, an imported
    spreadsheet cell. That is a claim the caller has to make out loud; this
    module will not infer it.
    """
    if value.tzinfo is None:
        if not assume_display_timezone:
            _reject_naive(value, caller="from_display")
        value = value.replace(tzinfo=_display_timezone())
    return value.astimezone(UTC)


def _display_timezone() -> ZoneInfo:
    return ZoneInfo(settings.DISPLAY_TIME_ZONE)


def _reject_naive(value: datetime, *, caller: str) -> None:
    """Refuse to guess what zone a naive timestamp was in.

    Guessing is how a converted value ends up compared against an unconverted
    one. The mismatch is silent and surfaces hours later as money in the wrong
    place, so it is better to fail at the call site.
    """
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(
            f"{caller}() needs an aware datetime; got a naive one ({value!r}). "
            f"Attach a timezone where the value enters the system."
        )
