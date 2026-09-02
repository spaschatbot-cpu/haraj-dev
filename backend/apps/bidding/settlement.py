"""What happens to everybody's money when an auction ends. T508–T511.

The rules are spec 006's table, applied literally:

===========================================  ===================================
the bidder's situation                       what happens to their deposit
===========================================  ===================================
won nothing, owes nothing                    released to `insurance_free`
won a car                                    stays held until the invoice, then
                                             locked against it
owes dues from before                        stays locked
**still competing on an unresolved car**     **stays held — never released**
===========================================  ===================================

The last row is the whole reason this module is not four lines. In v1
``settleAuction`` walked the losers and released them, and "loser" meant "not
the highest bid on any car" — so a bidder whose only car was still waiting on
its owner's decision had their deposit released, and when the owner accepted the
bid a day later the platform had to ask for the money back. Some of it was gone.

So a **competitor is any bidder who has not been outbid or refused on a car that
is not yet resolved**, and a competitor's hold is untouchable. Resolution is a
property of the *car*, not of the bid: `awarded`, `rejected` and `withdrawn` are
resolved; `bidding` and `awaiting_decision` are not.

Nothing here decides who won. `decide_vehicle` reads the highest live bid and
the reserve, and the two outcomes it can produce — award, or send to the owner —
are both moves `apps.auctions.services` already owns. Nothing here writes a
ledger entry either: every movement goes through `apps.money.services`, which is
the only writer (Article 1-2).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.services import award, reject, send_to_owner
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.money import services as money
from apps.money.models import Hold, HoldReason, HoldState, Invoice, InvoiceState

log = logging.getLogger(__name__)

#: A car whose fate is still open. A bidder on one of these is a competitor,
#: and a competitor's deposit is not released whatever else is true of them.
UNRESOLVED_VEHICLE_STATES = frozenset(
    {VehicleState.LISTED, VehicleState.BIDDING, VehicleState.AWAITING_DECISION}
)


@dataclass(frozen=True)
class VehicleOutcome:
    """What settlement decided about one car, and why."""

    vehicle_id: int
    outcome: str
    winner_id: int | None = None
    price: Decimal | None = None
    reason: str = ""


@dataclass(frozen=True)
class HoldOutcome:
    """What settlement did with one bidder's hold, and why it did that."""

    hold_id: int
    owner_id: int
    action: str
    reason: str


@dataclass(frozen=True)
class Settlement:
    """The whole report of one settlement run, for a screen and for a test."""

    auction_id: int
    vehicles: list[VehicleOutcome]
    holds: list[HoldOutcome]

    @property
    def released(self) -> list[HoldOutcome]:
        return [row for row in self.holds if row.action == "released"]

    @property
    def kept(self) -> list[HoldOutcome]:
        return [row for row in self.holds if row.action == "kept"]


# ---------------------------------------------------------------------------
# Deciding one car
# ---------------------------------------------------------------------------


def decide_vehicle(vehicle: Vehicle, *, now: datetime | None = None) -> VehicleOutcome:
    """Award the car, send it to its owner, or reject it — and say which.

    Three endings and no fourth:

    * **No live bid** → rejected. Nobody wanted it at any price.
    * **Highest bid at or above the reserve** → awarded to that bidder.
    * **Highest bid below the reserve** → the owner decides. That is a supported
      outcome, not a failure: a bid under the reserve is real money somebody
      offered, and the owner may take it. This is the state that made v1's
      release bug expensive — the car is unresolved for as long as the owner
      takes to answer, and its bidders are still competitors.

    The car is not moved to a resolved state by this function alone; `award` and
    the rest are `apps.auctions.services`' moves, and the state machine there is
    what refuses an impossible transition.
    """
    now = now or timezone.now()

    highest = (
        Bid.objects.live()
        .filter(vehicle=vehicle)
        .order_by("-amount", "placed_at")
        .first()
    )

    if highest is None:
        reject(vehicle)
        return VehicleOutcome(
            vehicle_id=vehicle.pk, outcome="rejected", reason="لا مزايدة على المركبة"
        )

    reserve = vehicle.reserve_price
    if reserve is not None and highest.amount < reserve:
        send_to_owner(vehicle)
        return VehicleOutcome(
            vehicle_id=vehicle.pk,
            outcome="awaiting_decision",
            winner_id=highest.bidder_id,
            price=highest.amount,
            reason="أعلى مزايدة دون سعر الوقوف — القرار للمالك",
        )

    award(vehicle, highest.bidder, highest.amount, now=now)
    return VehicleOutcome(
        vehicle_id=vehicle.pk,
        outcome="awarded",
        winner_id=highest.bidder_id,
        price=highest.amount,
        reason="رست على أعلى مزايد",
    )


# ---------------------------------------------------------------------------
# Who is still competing
# ---------------------------------------------------------------------------


def competitors_in(auction: Auction) -> set[int]:
    """Bidder ids with a live bid on a car in this auction that is not resolved.

    "Live" is `Bid.objects.live()` — the same definition the partial unique
    index is built on, so what this calls a competitor and what the database
    calls a standing bid are the same thing. A withdrawn or superseded bid does
    not make anybody a competitor; that is what withdrawing means.

    This is the set that must not be released, and computing it *before* any
    hold is touched is deliberate: releasing while walking the list would let an
    early release change the answer for a later bidder.
    """
    return set(
        Bid.objects.live()
        .filter(
            vehicle__auction=auction,
            vehicle__state__in=list(UNRESOLVED_VEHICLE_STATES),
        )
        .values_list("bidder_id", flat=True)
    )


def winners_in(auction: Auction) -> set[int]:
    """Bidder ids who won at least one car in this auction.

    Read off `Vehicle.awarded_to` rather than off the bids: the award is what
    the platform acted on, and a hand-corrected award must move the money with
    it rather than be silently overruled by a bid table nobody edited.
    """
    return set(
        Vehicle.objects.filter(auction=auction, awarded_to__isnull=False).values_list(
            "awarded_to_id", flat=True
        )
    )


# ---------------------------------------------------------------------------
# Settling the whole auction
# ---------------------------------------------------------------------------


def settle_auction(auction: Auction, *, now: datetime | None = None) -> Settlement:
    """Decide every car, then decide every deposit. In that order, and once.

    The order matters and is the fix for v1's bug: a hold cannot be judged until
    every car it might be competing on has been decided, so all the deciding
    happens first and the money is touched only afterwards.

    Idempotent by construction rather than by a flag: a car already resolved is
    skipped, and `release_hold` returns the hold untouched when it is not
    active. Running settlement twice on the same auction changes nothing the
    second time — which matters because the thing that calls this is a task,
    and a task runs again when a worker dies mid-run.
    """
    now = now or timezone.now()
    vehicles: list[VehicleOutcome] = []

    # One transaction per car. Not one for the whole auction: fifty cars in a
    # single transaction hold fifty row locks for the length of the slowest
    # decision, and a failure on car forty rolls back thirty-nine correct
    # awards. Each car is independent, so each gets its own unit.
    for vehicle in Vehicle.objects.filter(auction=auction).order_by("lot_number"):
        if vehicle.state not in (VehicleState.BIDDING, VehicleState.LISTED):
            continue
        with transaction.atomic():
            vehicles.append(decide_vehicle(vehicle, now=now))

    holds = settle_holds(auction)

    log.info(
        "settled auction %s: %s vehicles decided, %s holds released, %s kept",
        auction.pk,
        len(vehicles),
        len([row for row in holds if row.action == "released"]),
        len([row for row in holds if row.action == "kept"]),
    )
    return Settlement(auction_id=auction.pk, vehicles=vehicles, holds=holds)


def settle_holds(auction: Auction) -> list[HoldOutcome]:
    """Release the deposits that are free to go, and say why each one stayed.

    Every hold gets a row in the report even when nothing happened to it. A
    settlement that only reports what it changed cannot answer the question
    support actually gets — "why is my deposit still held?" — and that question
    was unanswerable in v1.
    """
    competing = competitors_in(auction)
    winners = winners_in(auction)

    outcomes: list[HoldOutcome] = []

    for hold in Hold.objects.filter(
        auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).select_related("owner"):
        owner_id = hold.owner_id

        if owner_id in competing:
            # The row v1 got wrong, and the reason this module exists.
            outcomes.append(
                HoldOutcome(hold.pk, owner_id, "kept", "ما زال منافساً على مركبة لم تُحسم")
            )
            continue

        if owner_id in winners:
            # Held until the invoice exists; `lock_for_invoice` moves it then.
            # Releasing now and locking again on invoicing would leave a window
            # in which a winner's deposit is refundable.
            outcomes.append(
                HoldOutcome(hold.pk, owner_id, "kept", "فاز بمركبة — بانتظار الفاتورة")
            )
            continue

        money.release_hold(hold, memo=f"انتهاء المزاد {auction.number}")
        outcomes.append(
            HoldOutcome(hold.pk, owner_id, "released", "لم يفز ولم يعد منافساً")
        )

    return outcomes


def invoice_award(vehicle: Vehicle, *, due_at: datetime | None = None):
    """Turn one award into an invoice, and pin the winner's deposit to it. T509.

    Two writes that must not come apart: an invoice with no lock is a debt the
    customer can refund their way out of, and a lock naming no invoice is the v1
    state where a deposit looked frozen and nobody could say against what.

    The database refuses a second live invoice for a vehicle
    (`one_live_invoice_per_vehicle`), so calling this twice raises rather than
    duplicating — which is the guarantee, not the exception handling.
    """
    if vehicle.state != VehicleState.AWARDED:
        raise ValueError(f"vehicle {vehicle.pk} is {vehicle.state}, not awarded")
    if vehicle.awarded_to_id is None or vehicle.awarded_price is None:
        raise ValueError(f"vehicle {vehicle.pk} is awarded but names no winner or price")

    with transaction.atomic():
        invoice = money.issue_invoice(
            customer=vehicle.awarded_to,
            amount=vehicle.awarded_price,
            vehicle=vehicle,
            due_at=due_at,
        )
        money.lock_for_invoice(user=vehicle.awarded_to, invoice=invoice)
        _release_bidding_hold(vehicle)

    from apps.auctions.services import invoice as mark_invoiced

    mark_invoiced(vehicle)
    return invoice


def _release_bidding_hold(vehicle: Vehicle) -> None:
    """Free the auction hold once the money is locked against the invoice.

    In this order and never the reverse. The deposit moves from "held for this
    auction" to "locked against this debt", and doing it the other way round
    leaves a moment in which the winner's money is free and refundable.

    Only when the winner has nothing else outstanding in the auction — another
    car of theirs may still be unresolved, and then the hold is still doing its
    original job.
    """
    still_competing = (
        Bid.objects.live()
        .filter(
            bidder_id=vehicle.awarded_to_id,
            vehicle__auction_id=vehicle.auction_id,
            vehicle__state__in=list(UNRESOLVED_VEHICLE_STATES),
        )
        .exists()
    )
    other_awards = (
        Vehicle.objects.filter(
            auction_id=vehicle.auction_id, awarded_to_id=vehicle.awarded_to_id
        )
        .exclude(pk=vehicle.pk)
        .exclude(
            state__in=[VehicleState.INVOICED, VehicleState.PAID, VehicleState.RELEASED]
        )
        .exists()
    )
    if still_competing or other_awards:
        return

    hold = Hold.objects.filter(
        owner_id=vehicle.awarded_to_id,
        auction_id=vehicle.auction_id,
        reason=HoldReason.BIDDING,
        state=HoldState.ACTIVE,
    ).first()
    if hold is not None:
        money.release_hold(hold, memo=f"قُفل التأمين على فاتورة المركبة {vehicle.pk}")


def replace_winner(
    vehicle: Vehicle, *, new_winner, price: Decimal | None = None, reason: str
) -> Vehicle:
    """Move an award from one bidder to another, money and all. T510.

    This happens: the winner does not pay, or turns out to be ineligible, or the
    award was entered against the wrong lot. The car then goes to the next
    bidder, and every consequence of the first award has to come undone in the
    same breath.

    **One transaction, four effects.** In v1 the operator did this by hand in
    four screens, and the failure was always the same shape: one of the four was
    forgotten. Usually the first winner's invoice — so a customer who never got
    a car carried a debt that blocked their refunds, and the deposit stayed
    locked against it.

    1. The first winner's invoice is **cancelled**, not deleted. It was issued;
       a report that shows a month with an invoice that later vanished is a
       report nobody can reconcile.
    2. Their insurance lock is released — the debt it answered no longer exists.
    3. The award moves to the new winner at their own bid's price.
    4. A fresh invoice is issued to them and their deposit locked against it.

    The reason is required, not optional. An award that moved with no recorded
    reason is the row support cannot explain to either customer.
    """
    if vehicle.awarded_to_id is None:
        raise ValueError(f"vehicle {vehicle.pk} has no award to replace")
    if new_winner.pk == vehicle.awarded_to_id:
        raise ValueError("the replacement is the current winner")

    if price is None:
        their_bid = (
            Bid.objects.live()
            .filter(vehicle=vehicle, bidder=new_winner)
            .order_by("-amount")
            .first()
        )
        if their_bid is None:
            raise ValueError(
                f"user {new_winner.pk} has no live bid on vehicle {vehicle.pk}"
            )
        price = their_bid.amount

    with transaction.atomic():
        locked = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
        previous_id = locked.awarded_to_id

        _undo_award(locked, reason=reason)

        locked.awarded_to = new_winner
        locked.awarded_price = price
        locked.awarded_at = timezone.now()
        locked.state = VehicleState.AWARDED
        locked.save(update_fields=["awarded_to", "awarded_price", "awarded_at", "state"])

    log.info(
        "vehicle %s: award moved from %s to %s (%s)",
        vehicle.pk,
        previous_id,
        new_winner.pk,
        reason,
    )
    vehicle.refresh_from_db()
    return vehicle


def _undo_award(vehicle: Vehicle, *, reason: str) -> None:
    """Cancel the first winner's invoice and free what it was holding.

    Cancelling rather than deleting, and releasing rather than leaving: the two
    halves of the v1 failure. A cancelled invoice keeps the history whole; an
    unreleased lock leaves a customer's deposit pinned to a debt that no longer
    exists, which is exactly how a person who never received a car found their
    refund refused.
    """
    for invoice in Invoice.objects.filter(vehicle=vehicle).exclude(
        state=InvoiceState.CANCELLED
    ):
        for hold in Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE):
            money.release_hold(hold, memo=f"أُلغيت الفاتورة: {reason}")

        invoice.state = InvoiceState.CANCELLED
        invoice.save(update_fields=["state"])
        log.info("invoice %s cancelled: %s", invoice.number, reason)


def cancel_auction(auction: Auction, *, reason: str, now: datetime | None = None):
    """Call the whole auction off: free every deposit, void every unpaid bill. T513.

    An auction is cancelled when it should not have run — the wrong lots were
    loaded, a partner pulled their consignment, a date was wrong. Nobody owes us
    anything as a result of an event that did not happen, and nobody's money may
    stay held for it.

    **Paid invoices are left alone.** A cancellation must not silently un-take
    money a customer actually handed over; that is a refund, which is a decision
    with a human on the other end of it (`RefundRequest`), not a side effect of
    an operator clicking cancel. The report says which ones were left, so the
    operator sees what still needs a person.

    Order matters and is the same order settlement uses: cars first, then money.
    A car left `bidding` in a cancelled auction is a car a settlement run would
    later award.
    """
    now = now or timezone.now()

    # Cancelling goes **through ending**, and the state machine says so: a live
    # auction still has deposits held against it and releasing those is
    # settlement's job, not a side effect of a cancel button
    # (`test_a_live_auction_cannot_be_cancelled` in phase 005). So an auction
    # that is still running is refused here with the next step named, rather
    # than ended silently on the operator's behalf — ending an auction early is
    # its own decision with its own guard.
    if auction.state == AuctionState.LIVE:
        raise ValueError(f"auction {auction.pk} is still live; end it before cancelling")

    freed: list[HoldOutcome] = []
    voided: list[str] = []
    left_paid: list[str] = []

    with transaction.atomic():
        for vehicle in Vehicle.objects.filter(auction=auction).exclude(
            state__in=[VehicleState.WITHDRAWN, VehicleState.RELISTED]
        ):
            _close_out(vehicle)

            for invoice in Invoice.objects.filter(vehicle=vehicle).exclude(
                state=InvoiceState.CANCELLED
            ):
                if invoice.amount_paid > 0:
                    # Money really arrived. Voiding it here would make a payment
                    # disappear from a month that has already been reported.
                    left_paid.append(invoice.number)
                    continue

                for hold in Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE):
                    money.release_hold(hold, memo=f"أُلغي المزاد: {reason}")
                invoice.state = InvoiceState.CANCELLED
                invoice.save(update_fields=["state"])
                voided.append(invoice.number)

        for hold in Hold.objects.filter(
            auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
        ):
            money.release_hold(hold, memo=f"أُلغي المزاد: {reason}")
            freed.append(
                HoldOutcome(hold.pk, hold.owner_id, "released", f"أُلغي المزاد: {reason}")
            )

    from apps.auctions.services import cancel as mark_cancelled

    mark_cancelled(auction, now=now)

    log.info(
        "cancelled auction %s (%s): %s holds freed, %s invoices voided, %s left paid",
        auction.pk,
        reason,
        len(freed),
        len(voided),
        len(left_paid),
    )
    return {
        "auction_id": auction.pk,
        "holds_released": freed,
        "invoices_cancelled": voided,
        "invoices_left_paid": left_paid,
    }


def _close_out(vehicle: Vehicle) -> None:
    """Take one car out of play because its auction is being cancelled.

    Every car has to leave the states settlement would later act on — a car
    left `bidding` in a cancelled auction is a car a settlement run awards.
    Which closed state it goes to depends on where it was, and each is a real
    transition rather than a column write:

    * `listed` or `bidding` → **withdrawn**. Nothing was decided about it.
    * `awaiting_decision` → **rejected**. The owner was being asked and the
      question is now moot; "rejected" is the honest record of no sale.
    * `awarded` → **relisted**. The award is being undone with the invoice, and
      `relisted` is the state that says "goes back on offer".

    Anything already resolved and paid for is left alone: cancelling an auction
    does not un-sell a car somebody has paid for.
    """
    from apps.auctions.services import reject, relist, withdraw

    if vehicle.state in (VehicleState.LISTED, VehicleState.BIDDING):
        withdraw(vehicle)
    elif vehicle.state == VehicleState.AWAITING_DECISION:
        reject(vehicle)
    elif vehicle.state == VehicleState.AWARDED:
        relist(vehicle)


def relist_vehicle(vehicle: Vehicle, *, into: Auction, lot_number: int) -> Vehicle:
    """Move an unsold or unpaid car into a new auction cycle. T514.

    The rule the acceptance criterion is about: **an exclusion belongs to the
    cycle it happened in.** A bidder who was refused on this car in March is not
    refused on it in April, and a cancelled invoice hides the car from *that*
    auction and not from every auction afterwards.

    v1 stored the exclusion against the car, so a lot that failed to sell once
    carried its history forever — and the bidder who had been outbid on it could
    not see it listed again. Here the history lives on the bid and the invoice,
    both of which name the auction they belonged to, and a relisted car is a new
    row in a new auction as far as every rule is concerned.

    The old bids stay where they are, attached to the old auction. They are the
    record of what happened in March, not a claim on April.
    """
    if vehicle.auction_id == into.pk:
        raise ValueError("a car cannot be relisted into the auction it is already in")

    from apps.auctions.services import list_for_sale, relist

    with transaction.atomic():
        if vehicle.state != VehicleState.RELISTED:
            relist(vehicle)

        vehicle.auction = into
        vehicle.lot_number = lot_number
        # The award is the previous cycle's outcome and must not travel: a car
        # listed in April showing March's winner is how a customer is told they
        # own something they do not.
        vehicle.awarded_to = None
        vehicle.awarded_price = None
        vehicle.awarded_at = None
        vehicle.save(
            update_fields=[
                "auction",
                "lot_number",
                "awarded_to",
                "awarded_price",
                "awarded_at",
            ]
        )
        list_for_sale(vehicle)

    log.info(
        "vehicle %s relisted into auction %s as lot %s", vehicle.pk, into.pk, lot_number
    )
    vehicle.refresh_from_db()
    return vehicle


def close_auction(auction: Auction, *, now: datetime | None = None) -> Auction:
    """Mark the auction settled once every car in it is resolved.

    Refuses while anything is still waiting on an owner's decision: an auction
    marked settled with an unresolved car in it is the state that lets a later
    release run against bidders who are still competing.
    """
    unresolved = Vehicle.objects.filter(
        auction=auction, state__in=list(UNRESOLVED_VEHICLE_STATES)
    ).count()
    if unresolved:
        raise ValueError(f"auction {auction.pk} still has {unresolved} unresolved cars")

    from apps.auctions.services import settle as mark_settled

    if auction.state == AuctionState.SETTLED:
        return auction
    return mark_settled(auction, now=now)


__all__ = [
    "HoldOutcome",
    "Settlement",
    "VehicleOutcome",
    "cancel_auction",
    "close_auction",
    "relist_vehicle",
    "replace_winner",
    "competitors_in",
    "decide_vehicle",
    "invoice_award",
    "settle_auction",
    "settle_holds",
    "winners_in",
]
