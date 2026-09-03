"""التحديث الحي — وما لا يجوز أن يمرّ فيه أبداً.

The task asked for live updates and the obvious reading is wrong. «مزايدة تظهر
خلال ثانيتين» sounds like a price ticker: other people's bids arriving on the
screen as they are placed. **This platform cannot have one**, and the reason is
not a limitation — it is the product:

    apps/bidding/api/views.py, first paragraph:
    «No endpoint that lists the bids on a car. A sealed auction's whole property
     is that bidders cannot see each other's numbers.»

A live feed of competitors' amounts would demolish in one endpoint the property
the whole bidding phase was built to hold, and it would do it while looking like
a feature request being satisfied.

So what is live here
--------------------
Two things, and neither is anybody else's number:

1. **The caller's own bids.** They bid on their phone; the website they left
   open shows it seconds later. That is J6 read literally — *مزايدة من التطبيق
   تظهر في الويب* — and it is the thing customers actually notice, because a
   second device showing a stale «لا مزايدات» is what makes people bid twice.
2. **Public facts about what they are bidding on.** An auction closing, a car
   moving to `awarded` or being withdrawn. Every one of these is already
   readable by anybody browsing; sending it sooner tells nobody anything new.

The rule, stated once so it can be tested: **an event may carry a number only if
it is the caller's own, and a state only if it is already public.**
`test_live_updates.py` places a competing bid and asserts nothing about it
reaches the stream — not the amount, not that it happened.

Why a digest and not a change log
---------------------------------
There is no event table and this does not add one. Each poll builds a *digest*
of what the caller may see, and emits only when it differs from the last one.
That has a property a log does not: it cannot be wrong for long. A missed
notification in a log is a client that stays stale until something else nudges
it; a digest re-derives from the rows every time, so the worst case is one
interval of lateness rather than an inconsistency nobody detects.

It also means no writer anywhere has to remember to publish. `place_bid` was
written before this file existed and did not change for it — a rule that
requires every writer to announce itself is a rule the next writer forgets.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from apps.auctions.models import Vehicle

from .models import Bid

__all__ = ["Snapshot", "snapshot_for"]

#: How often the stream re-derives. Two seconds because J6 asks for two, and a
#: shorter interval buys nothing a person can perceive while costing a query per
#: connection per tick.
INTERVAL_SECONDS = 2

#: How long a connection is held before the client is asked to reconnect.
#: Finite on purpose: a stream that lives forever survives a deploy that has
#: already replaced the code it is running, and the client that reconnects gets
#: the current answer from the current version.
MAX_STREAM_SECONDS = 15 * 60


@dataclass(frozen=True)
class Snapshot:
    """What one customer may be told, right now, in one object.

    `digest` is what the stream compares between ticks. It is derived from the
    payload rather than from a timestamp so that a change *back* to a previous
    value still registers — a withdrawal followed by an identical re-bid is two
    events to a customer and would be one to a `max(updated_at)` cursor.
    """

    bids: list[dict]
    vehicles: list[dict]
    digest: str

    def as_event(self) -> str:
        """The SSE frame for this snapshot.

        `id:` carries the digest so a reconnecting client can tell the server
        what it last saw, and be sent nothing when nothing moved.
        """
        payload = json.dumps(
            {"bids": self.bids, "vehicles": self.vehicles},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"id: {self.digest}\nevent: state\ndata: {payload}\n\n"


def _bid_row(bid: Bid) -> dict:
    """One of the caller's own bids.

    The amount is theirs, so it crosses — as the decimal string the ledger
    stores, never a float (Article 3-2). Nothing here is about anybody else.
    """
    return {
        "id": bid.pk,
        "vehicle_id": bid.vehicle_id,
        "amount": str(bid.amount),
        "is_withdrawn": bid.is_withdrawn,
        "is_superseded": bid.is_superseded,
    }


def _vehicle_row(vehicle: Vehicle) -> dict:
    """A car the caller has a live bid on, in facts that are already public.

    `state` and its label, and nothing else. No price, no bid count, no "you are
    winning" — the last of those is the sealed auction's secret wearing a
    friendly name, and it is the exact field a well-meaning ticket would ask for.
    """
    return {
        "id": vehicle.pk,
        "state": vehicle.state,
        "state_label": vehicle.get_state_display(),
        "auction_state": vehicle.auction.state,
    }


def snapshot_for(user) -> Snapshot:
    """Everything this customer may be told, derived from the rows.

    Two queries, whatever the customer has bid on: their live bids, and the cars
    those bids are against with the auction joined.
    """
    bids = list(
        Bid.objects.live().filter(bidder=user).order_by("vehicle_id", "-placed_at")
    )
    vehicles = list(
        Vehicle.objects.filter(pk__in={bid.vehicle_id for bid in bids})
        .select_related("auction")
        .order_by("pk")
    )

    bid_rows = [_bid_row(bid) for bid in bids]
    vehicle_rows = [_vehicle_row(vehicle) for vehicle in vehicles]

    material = json.dumps(
        [bid_rows, vehicle_rows], ensure_ascii=False, separators=(",", ":")
    )
    return Snapshot(
        bids=bid_rows,
        vehicles=vehicle_rows,
        digest=hashlib.sha256(material.encode()).hexdigest()[:16],
    )
