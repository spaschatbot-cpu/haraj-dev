"""Partner decisions and choosing an offer. T807.

The screen v1 had no equivalent of. There, a car whose highest bid fell below
the reserve simply sat in the vehicle list in lot order, and the partner was
told about it by telephone — so "which cars are waiting on a decision?" was
answered by somebody scrolling.

Three things this screen does that the vehicle list cannot:

* **Orders by situation, not by lot.** A car waiting on its owner is at the top
  because nobody is being paid for it while it waits.
* **Shows every bidder, not the top one.** A partner refusing 45,000 usually
  wants to know what the second offer was. In v1 that meant a database query.
* **Awards to any of them in one click.** The partner's answer is often "take
  the second one" — and there was no way to do that at all, so an operator
  cancelled the auction and relisted the car.

**The accepted offer is shown, never the highest.** Once a car is awarded, the
number on this screen is what it was awarded for. In v1 the screen recomputed
the maximum bid every time it rendered, so a car awarded to the second bidder
displayed the first bidder's number — and that number went into the invoice
conversation.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect, render

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.bidding import settlement
from apps.bidding.models import Bid
from apps.core import audit

from .exports import export, wants_export
from .views import console_page

#: The states a partner decision is actually pending on. `awarded` is here
#: because an award can still be moved to another bidder (T510) — a partner who
#: changes their mind after the fact is a real Tuesday, and v1's answer was to
#: cancel the whole auction.
DECIDABLE = (VehicleState.AWAITING_DECISION, VehicleState.AWARDED)


@console_page("console:partner-decisions")
def decisions(request):
    """Cars waiting on a partner, oldest wait first.

    Sorted by how long the car has been waiting rather than by lot number: the
    question this page answers is "what has been sitting the longest", and a lot
    number answers nothing about that.
    """
    rows = (
        Vehicle.objects.filter(state__in=DECIDABLE)
        .select_related("auction", "owner_company", "awarded_to")
        .annotate(
            urgency=Case(
                When(state=VehicleState.AWAITING_DECISION, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )
        .order_by("urgency", "updated_at")
    )

    partner = request.GET.get("partner")
    if partner and partner.isdigit():
        rows = rows.filter(owner_company_id=int(partner))

    if wants_export(request):
        return export(
            rows,
            name="partner-decisions",
            headers=["المزاد", "اللوت", "المركبة", "الشريك", "الحالة", "ينتظر منذ"],
            cell=lambda v: [
                v.auction.number,
                v.lot_number,
                f"{v.make} {v.model} {v.year}",
                v.partner_name,
                v.get_state_display(),
                v.updated_at,
            ],
        )

    page = Paginator(rows, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "console/partner_decisions.html",
        {"page": page, "partner": partner or ""},
    )


@console_page("console:partner-offers")
def offers(request, pk: int):
    """Every live bid on one car, highest first, with the accepted one marked.

    The accepted offer is read off the award, not recomputed. A car awarded to
    the second bidder must not display the first bidder's number — in v1 it did,
    and that number reached the invoice conversation.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company", "awarded_to"), pk=pk
    )

    bids = (
        Bid.objects.live()
        .filter(vehicle=vehicle)
        .select_related("bidder")
        .order_by("-amount", "placed_at")
    )

    return render(
        request,
        "console/partner_offers.html",
        {
            "vehicle": vehicle,
            "bids": bids,
            # The number the partner is being asked about. Absent until there
            # is an award — an unawarded car has no accepted offer, and showing
            # the highest bid in that slot is exactly the v1 confusion.
            "accepted": vehicle.awarded_price,
            "reserve_met": [
                bid
                for bid in bids
                if vehicle.reserve_price is None or bid.amount >= vehicle.reserve_price
            ],
        },
    )


@console_page("console:partner-award")
def award(request, pk: int):
    """Award the car to a chosen bidder, or move an award to another.

    One entry point for both, because they are the same decision made at two
    moments and the money differs: awarding fresh is a settlement move, moving
    an existing award is `replace_winner`, which cancels the first invoice and
    frees the first winner's lock in the same transaction.

    Choosing which of the two to call is this view's only decision, and it reads
    it off the car rather than off the form — a form field saying "this is a
    replacement" is a form field somebody sets wrongly.
    """
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)

    if request.method != "POST":
        return redirect("console:partner-offers", pk=pk)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "سبب القرار مطلوب.")
        return redirect("console:partner-offers", pk=pk)

    bid = Bid.objects.live().filter(pk=request.POST.get("bid"), vehicle=vehicle).first()
    if bid is None:
        messages.error(request, "المزايدة المختارة لم تعد قائمة.")
        return redirect("console:partner-offers", pk=pk)

    before = audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"])

    try:
        if vehicle.awarded_to_id is None:
            settlement.award_to(vehicle, bidder=bid.bidder, price=bid.amount)
        else:
            settlement.replace_winner(
                vehicle, new_winner=bid.bidder, price=bid.amount, reason=reason
            )
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect("console:partner-offers", pk=pk)

    vehicle.refresh_from_db()
    audit.record(
        action="console.award_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"]),
        note=reason,
    )
    messages.success(request, f"رست على {bid.bidder.full_name} بمبلغ {bid.amount}.")
    return redirect("console:partner-offers", pk=pk)


@console_page("console:partner-reject")
def reject(request, pk: int):
    """The partner refused every offer. The car is rejected, not withdrawn.

    Two different facts, and v1 lost the distinction: "nobody offered enough"
    and "the owner pulled it" have opposite next steps — the first goes back
    into a later cycle, the second does not.
    """
    vehicle = get_object_or_404(Vehicle.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:partner-offers", pk=pk)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "سبب الرفض مطلوب.")
        return redirect("console:partner-offers", pk=pk)

    from apps.auctions.services import reject as reject_vehicle

    before = audit.snapshot(vehicle, ["state"])
    try:
        reject_vehicle(vehicle)
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect("console:partner-offers", pk=pk)

    audit.record(
        action="console.reject_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state"]),
        note=reason,
    )
    messages.success(request, "سُجّل رفض المالك.")
    return redirect("console:partner-offers", pk=pk)


def _amount(raw: str) -> Decimal | None:
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return None


__all__ = ["DECIDABLE", "award", "decisions", "offers", "reject"]
