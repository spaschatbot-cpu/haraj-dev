"""Placing and revising a bid — and writing down every refusal.

Everything in here obeys three rules that came out of v1's incident reviews:

1. **One decision point.** No function here asks an eligibility question of its
   own; they all call :func:`~apps.bidding.eligibility.check_eligibility`.
2. **The row lock comes first.** The vehicle row is locked before anything is
   read that a decision will be made on. Finding F-004 in
   `specs/002-money-engine/findings.md` is what a read-then-decide costs: a
   deposit moved twice because the decision was taken outside the lock that was
   supposed to protect it.
3. **Nothing here writes to the ledger.** Money moves only through
   `apps.money.services`, which is idempotent per (customer, auction), so the
   deposit is taken on the first bid of an auction and never again (T505).

Lock order, everywhere in this module: **vehicle row, then money.** Money's own
locks are taken in ascending account id inside `post`, so two bidders on two
cars can never wait on each other in a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.auctions import services as auctions
from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core.errors import DomainError
from apps.money import services as money
from apps.money.models import MONEY, ZERO

from .eligibility import Eligibility, check_eligibility
from .models import Bid, BidRefusal

__all__ = [
    "BidRefused",
    "BiddingError",
    "LowerBidNeedsConfirmation",
    "place_bid",
    "record_refusal",
]

_CENT = Decimal(1).scaleb(-MONEY["decimal_places"])


class BiddingError(DomainError):
    """A refused bidding operation, safe to show to the customer."""

    code = "bidding_error"
    default_message = "تعذّر تنفيذ العملية على المزايدة."


class BidRefused(BiddingError):
    """The bid was refused by :func:`check_eligibility`, and it was written down.

    The client branches on :attr:`code`, which is the enumerated reason itself
    rather than a generic "refused" — the reasons are a closed set precisely so
    that a screen can say something specific about each one.
    """

    default_message = "لا يمكنك المزايدة على هذه المركبة الآن."

    def __init__(self, decision: Eligibility, refusal: BidRefusal | None = None):
        self.decision = decision
        self.refusal = refusal
        self.code = decision.reason
        super().__init__(
            f"bid refused: {decision.reason}",
            user_message=decision.detail,
            detail={
                "reason": decision.reason,
                "reason_label": decision.reason_label,
                "available": str(decision.money.insurance_free),
                "required": str(decision.required_deposit),
                "outstanding_dues": str(decision.money.outstanding_dues),
                "refusal": refusal.pk if refusal is not None else None,
            },
        )


class LowerBidNeedsConfirmation(BiddingError):
    """Lower than the bid already standing — allowed, but not by accident.

    Lowering is a deliberate feature of a sealed auction, not a mistake to be
    blocked. It is also the kind of thing a fat finger does, so the first
    attempt is refused with this and the caller must come back saying it meant
    it (F3).
    """

    code = "lower_needs_confirm"
    default_message = "المبلغ أقل من مزايدتك الحالية. أكّد الخفض إن كنت متأكداً."


# ---------------------------------------------------------------------------
# T502 — the refusal record
# ---------------------------------------------------------------------------


def record_refusal(
    *, user, vehicle, amount: Decimal, decision: Eligibility
) -> BidRefusal:
    """Write down one refusal with the money as it stood at that instant.

    The snapshot is copied, not referenced. Support's most common question in
    v1 was «ليه ما يقدرش يزايد؟» and the only way to answer it was to rebuild
    the moment by hand from several tables — after the balances had moved on,
    which meant the reconstruction was of a different moment.
    """
    return BidRefusal.objects.create(
        vehicle=vehicle,
        bidder=user,
        amount=amount,
        reason=decision.reason,
        detail=decision.detail[:500],
        insurance_free=decision.money.insurance_free,
        insurance_held=decision.money.insurance_held,
        insurance_locked=decision.money.insurance_locked,
        outstanding_dues=decision.money.outstanding_dues,
    )


# ---------------------------------------------------------------------------
# T504 / T505 / T506 — placing a bid
# ---------------------------------------------------------------------------


def _clean(amount) -> Decimal:
    """A bid amount as money, or a refusal — never a float (Article 3-2)."""
    try:
        value = Decimal(str(amount)).quantize(_CENT)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise BiddingError(
            f"bid amount {amount!r} is not a number",
            user_message="المبلغ غير صالح.",
        ) from exc
    if value <= ZERO:
        raise BiddingError(
            f"bid amount {value} is not positive",
            user_message="المبلغ لازم يكون أكبر من صفر.",
        )
    return value


@dataclass
class _Attempt:
    decision: Eligibility
    bid: Bid | None


def place_bid(
    *,
    user,
    vehicle: Vehicle,
    amount,
    confirm_lower: bool = False,
    now: datetime | None = None,
) -> Bid:
    """Place or revise one bid, or refuse and say why.

    The refusal record is written **after** the attempt's transaction has
    closed, and that is deliberate: raising inside the atomic block would roll
    back the very row whose whole purpose is to survive the refusal. The
    attempt itself writes nothing when it refuses, so there is nothing to
    undo — the two-step costs one extra statement and buys a record that
    cannot be rolled back by the thing it records.
    """
    amount = _clean(amount)
    attempt = _place(
        user=user, vehicle=vehicle, amount=amount, confirm_lower=confirm_lower, now=now
    )
    if attempt.bid is not None:
        return attempt.bid

    refusal = record_refusal(
        user=user, vehicle=vehicle, amount=amount, decision=attempt.decision
    )
    raise BidRefused(attempt.decision, refusal)


@transaction.atomic
def _place(
    *, user, vehicle: Vehicle, amount: Decimal, confirm_lower: bool, now
) -> _Attempt:
    """Lock, decide, hold, write — all of it inside one transaction.

    Fifty threads on one car all queue on the same vehicle row, so each of them
    reads a world in which the previous forty-nine have already finished. That
    is what makes the ordering consistent and the count exact; without the lock
    they would each read the same "no bid yet" and the deposit rule would be
    decided on a state that no longer existed by the time it was written.
    """
    # `of=("self",)` locks the car and nothing else. Without it postgres locks
    # every joined row too, so all fifty bidders on fifty cars in one auction
    # would queue behind a single auction row instead of behind their own car.
    locked = (
        Vehicle.objects.select_for_update(of=("self",))
        .select_related("auction")
        .get(pk=vehicle.pk)
    )

    decision = check_eligibility(user, locked, amount=amount, now=now)
    if not decision.allowed:
        # Return rather than raise: the caller records the refusal outside this
        # transaction, and an exception here would take that record with it.
        return _Attempt(decision=decision, bid=None)

    standing = Bid.objects.live().filter(vehicle=locked, bidder=user).first()
    if standing is not None:
        if amount == standing.amount:
            # The same number twice is a double tap, not a revision. Superseding
            # a bid with its own value would churn the history for nothing.
            return _Attempt(decision=decision, bid=standing)
        if amount < standing.amount and not confirm_lower:
            raise LowerBidNeedsConfirmation(
                f"{amount} is below the standing bid {standing.amount}",
                detail={
                    "standing": str(standing.amount),
                    "requested": str(amount),
                    "bid": standing.pk,
                },
            )

    # The deposit is per auction, and `hold_for_auction` is idempotent per
    # (customer, auction) under its own row lock — so this is called on every
    # bid and moves money on the first one only (T505).
    money.hold_for_auction(user=user, auction=locked.auction)

    if standing is not None:
        standing.is_superseded = True
        standing.save(update_fields=["is_superseded"])

    bid = Bid.objects.create(
        vehicle=locked, bidder=user, amount=amount, supersedes=standing
    )

    if locked.state == VehicleState.LISTED:
        # The first bid is what opens the car. The move goes through the
        # auctions service because that module is the only writer of this
        # column — a rule `ops/checks/auction_state_single_writer.py` enforces.
        auctions.open_bidding(locked)

    return _Attempt(decision=decision, bid=bid)
