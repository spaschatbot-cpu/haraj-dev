"""Every state an auction or a vehicle can hold, and every move between them.

The table below **is** the rule. A pair that is not in it is refused — not
logged, not warned about, refused — because the alternative is what v1 did:
each screen decided for itself whether a move made sense, and the answers
drifted apart until an auction could be "ended" twice and a car could be
awarded after it had been withdrawn.

Two kinds of refusal, deliberately distinct:

* :class:`InvalidTransition` — this move does not exist. A bug, or a screen
  offering a button it should not have.
* :class:`TransitionNotReady` — the move exists but its precondition is not
  met yet (the auction has no cars, its start time has not arrived). Normal,
  and the message says what is missing.

Collapsing the two into one error would make "you cannot do that ever" and
"not yet" indistinguishable to the caller, and the caller is the one deciding
whether to retry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .models import Auction, Vehicle


class AuctionState(models.TextChoices):
    DRAFT = "draft", "مسودة"
    SCHEDULED = "scheduled", "مجدول"
    LIVE = "live", "جارٍ"
    ENDED = "ended", "منتهٍ"
    SETTLED = "settled", "مُسوّى"
    CANCELLED = "cancelled", "ملغى"


class VehicleState(models.TextChoices):
    """Where a car stands.

    Deliberately wide (Article 3-5). v1 squashed this enum into four values
    once and lost the distinction between a car nobody bid on and a car whose
    owner refused the highest bid — two situations with opposite next steps.
    """

    DRAFT = "draft", "مسودة"
    LISTED = "listed", "معروضة"
    BIDDING = "bidding", "تحت المزايدة"
    AWAITING_DECISION = "awaiting_decision", "بانتظار قرار المالك"
    AWARDED = "awarded", "مرسّاة"
    REJECTED = "rejected", "مرفوضة"
    INVOICED = "invoiced", "مفوترة"
    PAID = "paid", "مسدَّدة"
    RELEASED = "released", "خرجت"
    WITHDRAWN = "withdrawn", "مسحوبة"
    RELISTED = "relisted", "معادة للعرض"


#: The v1 vocabulary, mapped onto the enum above (T404).
#:
#: Reconstructed from the documented v1 lifecycle in `docs/system-handbook.md`
#: and `specs/004-data-migration`, **not** read out of a v1 database — nobody
#: on this branch has access to one. When the migration phase opens the real
#: table, this map is the thing to check against it, and any v1 value missing
#: from here is a finding, not a silent default.
V1_VEHICLE_STATE_MAP: dict[str, str] = {
    "new": VehicleState.DRAFT,
    "draft": VehicleState.DRAFT,
    "available": VehicleState.LISTED,
    "in_auction": VehicleState.LISTED,
    "bidding": VehicleState.BIDDING,
    "pending_approval": VehicleState.AWAITING_DECISION,
    "owner_review": VehicleState.AWAITING_DECISION,
    "sold": VehicleState.AWARDED,
    "won": VehicleState.AWARDED,
    "not_sold": VehicleState.REJECTED,
    "cancelled_sale": VehicleState.REJECTED,
    "invoiced": VehicleState.INVOICED,
    "paid": VehicleState.PAID,
    "delivered": VehicleState.RELEASED,
    "released": VehicleState.RELEASED,
    "withdrawn": VehicleState.WITHDRAWN,
    "removed": VehicleState.WITHDRAWN,
    "relisted": VehicleState.RELISTED,
}


class AuctionError(Exception):
    """A refused auction operation, with a message an operator can read."""


class InvalidTransition(AuctionError):
    """This move is not in the table, so it does not exist."""


class TransitionNotReady(AuctionError):
    """The move exists, but its precondition is not met yet."""


#: A guard returns an Arabic reason when the move must wait, or None when it
#: may proceed. Returning a reason rather than raising keeps every refusal
#: message next to the rule that produced it.
Guard = Callable[..., str | None]


@dataclass(frozen=True)
class Move:
    source: str
    target: str
    why: str
    guard: Guard | None = None


def _auction_ready_to_schedule(auction: Auction, now: datetime) -> str | None:
    if not auction.vehicles.exists():
        return "لا يمكن جدولة مزاد بلا مركبات"
    if auction.ends_at <= now:
        return "وقت انتهاء المزاد مضى بالفعل"
    return None


def _auction_start_time_reached(auction: Auction, now: datetime) -> str | None:
    if auction.starts_at > now:
        return "لم يحن وقت بدء المزاد بعد"
    return None


def _auction_end_time_reached(auction: Auction, now: datetime) -> str | None:
    if auction.ends_at > now:
        return "المزاد لم ينته بعد"
    return None


#: Auction moves. Anything absent is refused.
#:
#: There is no `live → cancelled`: by the time an auction is live, bidders'
#: deposits are held against it, and releasing them is settlement's job
#: (phase 006), not a state flip. Cancelling a running auction therefore goes
#: `live → ended → settled`, which is the path that returns the money.
AUCTION_MOVES: tuple[Move, ...] = (
    Move(
        AuctionState.DRAFT,
        AuctionState.SCHEDULED,
        "المزاد اكتمل إعداده وصار له موعد",
        _auction_ready_to_schedule,
    ),
    Move(
        AuctionState.SCHEDULED,
        AuctionState.DRAFT,
        "سُحب من الجدول قبل أن يبدأ — لا فلوس تحرّكت بعد",
    ),
    Move(
        AuctionState.SCHEDULED,
        AuctionState.LIVE,
        "حان وقت البدء",
        _auction_start_time_reached,
    ),
    Move(
        AuctionState.LIVE,
        AuctionState.ENDED,
        "انتهى وقت المزاد؛ لا مزايدة بعد الآن",
        _auction_end_time_reached,
    ),
    Move(
        AuctionState.ENDED,
        AuctionState.SETTLED,
        "التسوية المالية تمّت (الفيز 006)",
    ),
    Move(AuctionState.DRAFT, AuctionState.CANCELLED, "أُلغي وهو مسودة"),
    Move(AuctionState.SCHEDULED, AuctionState.CANCELLED, "أُلغي قبل أن يبدأ"),
)


def _vehicle_has_a_named_winner(vehicle: Vehicle) -> str | None:
    if vehicle.awarded_to_id is None:
        return "الترسية تحتاج اسم الفائز"
    if vehicle.awarded_price is None:
        return "الترسية تحتاج سعر الرسو"
    return None


#: Vehicle moves. Same rule: absent means refused.
#:
#: `relisted` is a way-station, not a resting place — a car that came back
#: from a withdrawal, a rejection, or an unpaid invoice sits there until
#: someone lists it again, and the distinct state is what makes "why is this
#: car here twice?" answerable.
VEHICLE_MOVES: tuple[Move, ...] = (
    Move(VehicleState.DRAFT, VehicleState.LISTED, "اكتملت بياناتها وعُرضت"),
    Move(VehicleState.DRAFT, VehicleState.WITHDRAWN, "سُحبت قبل العرض"),
    Move(VehicleState.LISTED, VehicleState.BIDDING, "بدأت المزايدة عليها"),
    Move(VehicleState.LISTED, VehicleState.WITHDRAWN, "سُحبت قبل المزايدة"),
    # A car that was offered and nobody bid on. Without this move it has no exit
    # at all when the auction ends: `listed` leads only to `bidding` and to
    # `withdrawn`, and withdrawn means somebody pulled it — which is a different
    # fact and the wrong one to record. It would also leave the auction with an
    # unresolved car forever, so settlement could never close it (T511).
    Move(
        VehicleState.LISTED,
        VehicleState.REJECTED,
        "انتهى المزاد ولم تُقدَّم عليها أي مزايدة",
    ),
    Move(
        VehicleState.BIDDING,
        VehicleState.AWAITING_DECISION,
        "أعلى مزايدة دون سعر الوقوف — القرار للمالك",
    ),
    Move(
        VehicleState.BIDDING,
        VehicleState.AWARDED,
        "رست على أعلى مزايد",
        _vehicle_has_a_named_winner,
    ),
    Move(VehicleState.BIDDING, VehicleState.REJECTED, "لم تُقبل أي مزايدة"),
    Move(VehicleState.BIDDING, VehicleState.WITHDRAWN, "سُحبت أثناء المزايدة"),
    Move(
        VehicleState.AWAITING_DECISION,
        VehicleState.AWARDED,
        "المالك قبل المزايدة",
        _vehicle_has_a_named_winner,
    ),
    Move(VehicleState.AWAITING_DECISION, VehicleState.REJECTED, "المالك رفض المزايدة"),
    Move(VehicleState.AWARDED, VehicleState.INVOICED, "صدرت فاتورة الفوز"),
    Move(
        VehicleState.AWARDED,
        VehicleState.RELISTED,
        "أُلغيت الترسية قبل الفوترة — تعود للعرض",
    ),
    Move(VehicleState.INVOICED, VehicleState.PAID, "سُدّدت الفاتورة"),
    Move(VehicleState.INVOICED, VehicleState.RELISTED, "لم تُسدَّد الفاتورة فاستُرجعت"),
    Move(VehicleState.PAID, VehicleState.RELEASED, "استلمها المشتري"),
    Move(VehicleState.REJECTED, VehicleState.RELISTED, "تعود للعرض في مزاد لاحق"),
    Move(VehicleState.WITHDRAWN, VehicleState.RELISTED, "رجعت بعد السحب"),
    Move(VehicleState.RELISTED, VehicleState.LISTED, "أُدرجت من جديد"),
)


def _index(moves: tuple[Move, ...]) -> dict[tuple[str, str], Move]:
    return {(move.source, move.target): move for move in moves}


AUCTION_MOVE_INDEX = _index(AUCTION_MOVES)
VEHICLE_MOVE_INDEX = _index(VEHICLE_MOVES)


def _label(choices: type[models.TextChoices], value: str) -> str:
    try:
        return choices(value).label
    except ValueError:
        return value


def check_auction_move(auction: Auction, target: str, now: datetime) -> Move:
    """Return the move, or raise. Never mutates anything.

    Kept separate from the service functions so a screen can ask "may I?"
    without a write, and so the answer it gets is produced by the same table
    the write would consult.
    """
    move = AUCTION_MOVE_INDEX.get((auction.state, target))
    if move is None:
        raise InvalidTransition(
            f"لا يمكن نقل المزاد من «{_label(AuctionState, auction.state)}» "
            f"إلى «{_label(AuctionState, target)}»"
        )
    if move.guard is not None:
        reason = move.guard(auction, now)
        if reason:
            raise TransitionNotReady(reason)
    return move


def check_vehicle_move(vehicle: Vehicle, target: str) -> Move:
    """Return the move, or raise. Never mutates anything."""
    move = VEHICLE_MOVE_INDEX.get((vehicle.state, target))
    if move is None:
        raise InvalidTransition(
            f"لا يمكن نقل المركبة من «{_label(VehicleState, vehicle.state)}» "
            f"إلى «{_label(VehicleState, target)}»"
        )
    if move.guard is not None:
        reason = move.guard(vehicle)
        if reason:
            raise TransitionNotReady(reason)
    return move
