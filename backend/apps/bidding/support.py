"""Reading refusals back — the answer to «ليه ما يقدرش يزايد؟».

Read-only, on purpose and by construction: nothing in this module writes a row,
and the screen built on it (T503) offers no button that could. Support looks
things up here; decisions are made by the services next door, with a name
attached.

Everything shown is a stored fact from the moment of the refusal. Nothing is
recomputed — recomputing would answer a question about *now*, and the question
support is being asked is always about *then*.
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.accounts.models import User
from apps.accounts.services import find_by_phone

from .models import BidRefusal

__all__ = ["Lookup", "look_up"]

#: Enough history to see a pattern, few enough to read on one screen.
DEFAULT_LIMIT = 20


@dataclass(frozen=True)
class Lookup:
    """What the support screen asked for and what came back."""

    query: str
    bidder: User | None
    refusals: list[BidRefusal]

    @property
    def searched(self) -> bool:
        return bool(self.query.strip())


def look_up(query: str, *, limit: int = DEFAULT_LIMIT) -> Lookup:
    """Find a bidder by whatever the support agent typed, and their refusals.

    The matching itself is `apps.accounts.services.find_by_phone`, not a rule
    written here: ``0551234567``, ``+966551234567`` and ``966551234567`` are one
    number, and every staff screen that takes a phone number has to agree about
    that. A support box that only accepts the stored format is a support box
    that gets used once — and a second copy of the normalisation is a second
    screen that stops agreeing the day one of them is edited.
    """
    bidder = find_by_phone(query)
    if bidder is None:
        return Lookup(query=query, bidder=None, refusals=[])

    refusals = list(
        BidRefusal.objects.filter(bidder=bidder).select_related(
            "vehicle", "vehicle__auction"
        )[:limit]
    )
    return Lookup(query=query, bidder=bidder, refusals=refusals)
