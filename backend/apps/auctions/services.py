"""The only place an auction's or a vehicle's state changes.

Every move goes through :func:`move_auction` or :func:`move_vehicle`, which
consult the table in :mod:`apps.auctions.states` and write the column under a
row lock. No view, serializer, task, admin action or management command
assigns `.state` itself — `ops/checks/auction_state_single_writer.py` fails CI
if one does.

Why one writer, when a state column looks harmless next to the ledger: in v1
six paths could end an auction and each had grown its own idea of what "end"
meant, so a car could be awarded twice and a deposit released against an
auction that was still taking bids. The money engine has one writer for the
same reason; this is the same discipline applied to the thing that tells the
money engine what happened.

Nothing here touches `apps.money`. Settlement — releasing holds, issuing the
winner's invoice — belongs to phase 006 and calls in from outside.
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Auction, Vehicle, VehicleImage
from .states import (
    AuctionState,
    VehicleState,
    check_auction_move,
    check_vehicle_move,
)
from .visibility import can_view, visible_vehicles  # noqa: F401  (re-exported)

log = logging.getLogger(__name__)

__all__ = [
    "activate",
    "activate_due",
    "add_image",
    "award",
    "can_view",
    "cancel",
    "due_to_activate",
    "due_to_end",
    "end",
    "end_due",
    "invoice",
    "list_for_sale",
    "mark_paid",
    "move_auction",
    "move_vehicle",
    "open_bidding",
    "reject",
    "release",
    "relist",
    "schedule",
    "send_to_owner",
    "settle",
    "unschedule",
    "visible_vehicles",
    "withdraw",
]


# ---------------------------------------------------------------------------
# Auction
# ---------------------------------------------------------------------------


def move_auction(
    auction: Auction, target: str, *, now: datetime | None = None
) -> Auction:
    """Move one auction, or refuse.

    The row is re-read under `SELECT ... FOR UPDATE` before the table is
    consulted, so two workers reaching the same auction in the same second
    cannot both see `scheduled` and both activate it. The caller's instance is
    updated to match, because a caller holding a stale object is how the
    second write in v1 got made.
    """
    now = now or timezone.now()

    with transaction.atomic():
        locked = Auction.objects.select_for_update().get(pk=auction.pk)
        move = check_auction_move(locked, target, now)

        locked.state = target
        locked.save(update_fields=["state", "updated_at"])

    auction.state = locked.state
    auction.updated_at = locked.updated_at
    log.info("auction %s: %s → %s (%s)", auction.pk, move.source, move.target, move.why)
    return auction


def schedule(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.SCHEDULED, now=now)


def unschedule(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.DRAFT, now=now)


def activate(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.LIVE, now=now)


def end(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.ENDED, now=now)


def settle(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.SETTLED, now=now)


def cancel(auction: Auction, *, now: datetime | None = None) -> Auction:
    return move_auction(auction, AuctionState.CANCELLED, now=now)


# ---------------------------------------------------------------------------
# The calendar
# ---------------------------------------------------------------------------


def due_to_activate(now: datetime | None = None):
    """Scheduled auctions whose start moment has passed.

    The comparison is UTC on both sides — `starts_at` as stored against
    `timezone.now()`. Saudi time exists at the edges only: an operator types
    a Riyadh wall clock, `apps.core.time.from_display` turns it into UTC once,
    and no query ever converts anything (Article 3-1).
    """
    now = now or timezone.now()
    return Auction.objects.filter(
        state=AuctionState.SCHEDULED, starts_at__lte=now
    ).order_by("starts_at")


def due_to_end(now: datetime | None = None):
    """Live auctions whose end moment has passed."""
    now = now or timezone.now()
    return Auction.objects.filter(state=AuctionState.LIVE, ends_at__lte=now).order_by(
        "ends_at"
    )


def activate_due(now: datetime | None = None) -> list[int]:
    now = now or timezone.now()
    started: list[int] = []
    for auction in due_to_activate(now):
        activate(auction, now=now)
        started.append(auction.pk)
    return started


def end_due(now: datetime | None = None) -> list[int]:
    now = now or timezone.now()
    ended: list[int] = []
    for auction in due_to_end(now):
        end(auction, now=now)
        ended.append(auction.pk)
    return ended


# ---------------------------------------------------------------------------
# Vehicle
# ---------------------------------------------------------------------------


def move_vehicle(vehicle: Vehicle, target: str, *, extra: dict | None = None) -> Vehicle:
    """Move one vehicle, or refuse.

    `extra` carries the fields a move needs alongside the state — the winner
    and price of an award, say. They are written in the same transaction as
    the state, because a car recorded as `awarded` with no winner is a row the
    database check constraint would refuse anyway, and two statements would
    leave a window where it existed.
    """
    with transaction.atomic():
        locked = Vehicle.objects.select_for_update().get(pk=vehicle.pk)

        fields = ["state", "updated_at"]
        for name, value in (extra or {}).items():
            setattr(locked, name, value)
            fields.append(name)

        move = check_vehicle_move(locked, target)

        locked.state = target
        locked.save(update_fields=fields)

    for name, value in (extra or {}).items():
        setattr(vehicle, name, value)
    vehicle.state = locked.state
    vehicle.updated_at = locked.updated_at
    log.info("vehicle %s: %s → %s (%s)", vehicle.pk, move.source, move.target, move.why)
    return vehicle


def list_for_sale(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.LISTED)


def open_bidding(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.BIDDING)


def send_to_owner(vehicle: Vehicle) -> Vehicle:
    """Highest bid is below the reserve — the owner decides, not the system."""
    return move_vehicle(vehicle, VehicleState.AWAITING_DECISION)


def award(
    vehicle: Vehicle,
    winner,
    price: Decimal,
    *,
    now: datetime | None = None,
) -> Vehicle:
    """Record who won and for how much.

    The money side of winning — locking the winner's deposit against the
    invoice — is phase 006's, and calling it from here would put a second
    writer in front of the ledger.
    """
    return move_vehicle(
        vehicle,
        VehicleState.AWARDED,
        extra={
            "awarded_to": winner,
            "awarded_price": price,
            "awarded_at": now or timezone.now(),
        },
    )


def reject(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.REJECTED)


def invoice(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.INVOICED)


def mark_paid(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.PAID)


def release(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.RELEASED)


def withdraw(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.WITHDRAWN)


def relist(vehicle: Vehicle) -> Vehicle:
    return move_vehicle(vehicle, VehicleState.RELISTED)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def add_image(vehicle: Vehicle, file, *, position: int = 0, cover: bool = False):
    """Attach an image and generate its thumbnail in the same call.

    Generation is explicit rather than a `post_save` signal (T008 forbids
    signals project-wide): a row saved by a fixture, a migration or a shell
    should not silently start resizing files, and a reader of this function
    can see everything that happens on upload.
    """
    from .images import build_thumbnail

    with transaction.atomic():
        if cover:
            VehicleImage.objects.filter(vehicle=vehicle, is_cover=True).update(
                is_cover=False
            )

        image = VehicleImage(
            vehicle=vehicle, image=file, position=position, is_cover=cover
        )
        image.save()
        image.thumbnail = build_thumbnail(image.image)
        image.save(update_fields=["thumbnail"])

    return image
