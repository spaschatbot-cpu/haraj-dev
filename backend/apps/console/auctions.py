"""The auctions and vehicles screens. T805.

Four pages, and each answers a question an operator actually asks:

* **المزادات** — what is running, what is coming, and how many cars in each.
* **تفاصيل المزاد** — this auction's cars, with the one that needs a decision
  visible rather than buried on page four.
* **المركبات** — find a car across auctions, by make or by lot.
* **تغيير حالة المركبة** — the quick edit, and the only write here.

Nothing on these pages decides anything. The listing comes from
`apps.auctions.listing`, which is the same code the customer API pages use, so
the console and the app cannot disagree about how many cars an auction holds.
State changes go through `apps.auctions.services` — `auction_state_single_writer`
fails the build if a screen ever writes a state column itself.

**Every write demands a reason.** Spec 009 §"قواعد المال في اللوحة" 2 asks it of
financial actions; this file asks it of state changes too, for the same reason:
a car that moved and nobody can say why is the row support cannot explain to the
partner who owned it.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from apps.auctions import services as auction_services
from apps.auctions.listing import MAX_PAGE_SIZE, with_vehicle_counts
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import visible_vehicles
from apps.core import audit

from .views import console_page

#: Rows per page. Twenty-five rather than the API's twenty: a console user is
#: scanning rather than scrolling a phone, and a page that ends after twenty
#: rows costs an operator a click on every auction.
PAGE_SIZE = 25


def _page(request, queryset):
    """One page of ``queryset``, with the size bounded.

    `MAX_PAGE_SIZE` is shared with the customer API deliberately: `?limit=100000`
    is a table scan whoever asks for it, and an operator's session is not a
    reason to allow one.
    """
    try:
        size = min(int(request.GET.get("limit", PAGE_SIZE)), MAX_PAGE_SIZE)
    except (TypeError, ValueError):
        size = PAGE_SIZE

    return Paginator(queryset, max(size, 1)).get_page(request.GET.get("page"))


@console_page("console:auctions")
def auctions(request):
    """Every auction, newest first, with its counts.

    Staff see drafts and cancelled auctions; `apps.auctions.listing` already
    makes that distinction for the customer API, and this reuses the same
    annotation so the counts on both cannot drift.
    """
    rows = Auction.objects.all()

    state = request.GET.get("state", "")
    if state in AuctionState.values:
        rows = rows.filter(state=state)

    search = (request.GET.get("q") or "").strip()
    if search:
        rows = (
            rows.filter(title__icontains=search)
            if not search.isdigit()
            else rows.filter(number=int(search))
        )

    return render(
        request,
        "console/auctions.html",
        {
            "page": _page(request, with_vehicle_counts(rows).order_by("-starts_at")),
            "states": AuctionState.choices,
            "state": state,
            "q": search,
        },
    )


@console_page("console:auction-detail")
def auction_detail(request, pk: int):
    """One auction and its cars, with what needs a decision put first.

    The ordering is the screen's whole value: a car waiting on its owner's
    decision is a car nobody is being paid for, and in v1 it sat in lot order on
    page four until somebody went looking.
    """
    auction = get_object_or_404(with_vehicle_counts(Auction.objects.all()), pk=pk)

    from django.db.models import Case, IntegerField, Value, When

    cars = (
        Vehicle.objects.filter(auction=auction)
        .select_related("owner_company", "awarded_to")
        .annotate(
            urgency=Case(
                When(state=VehicleState.AWAITING_DECISION, then=Value(0)),
                When(state=VehicleState.AWARDED, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("urgency", "lot_number")
    )

    return render(
        request,
        "console/auction_detail.html",
        {"auction": auction, "page": _page(request, cars)},
    )


@console_page("console:vehicles")
def vehicles(request):
    """Find a car across auctions.

    The visibility rule is applied even here. Staff see everything through it —
    `visible_vehicles` already returns the full set for staff — but routing the
    console through the same function is what keeps "who may see this car" a
    single answer rather than two that agree until one is edited (T409).
    """
    rows = visible_vehicles(request.user).select_related("auction", "owner_company")

    search = (request.GET.get("q") or "").strip()
    if search:
        from django.db.models import Q

        terms = Q(make__icontains=search) | Q(model__icontains=search)
        if search.isdigit():
            terms = terms | Q(lot_number=int(search)) | Q(auction__number=int(search))
        rows = rows.filter(terms)

    state = request.GET.get("state", "")
    if state in VehicleState.values:
        rows = rows.filter(state=state)

    return render(
        request,
        "console/vehicles.html",
        {
            "page": _page(request, rows.order_by("auction_id", "lot_number")),
            "states": VehicleState.choices,
            "state": state,
            "q": search,
        },
    )


@console_page("console:vehicle-detail")
def vehicle_detail(request, pk: int):
    """One car: what it is, where it stands, and where it may go next.

    The moves offered are computed from the state machine rather than listed in
    a template. A button for a transition the machine refuses is a button that
    produces an error message, and v1's screens were full of them.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company", "awarded_to"), pk=pk
    )

    from apps.auctions.states import VEHICLE_MOVES

    moves = [
        {"target": move.target, "label": VehicleState(move.target).label, "why": move.why}
        for move in VEHICLE_MOVES
        if move.source == vehicle.state
    ]

    return render(
        request,
        "console/vehicle_detail.html",
        {"vehicle": vehicle, "moves": moves},
    )


@console_page("console:vehicle-state")
def vehicle_state(request, pk: int):
    """Move one car, with a reason. The only write on these screens.

    A reason is required and recorded. A car that changed state and nobody can
    say why is the row support cannot explain to the partner who owns it — and
    partners ask.
    """
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)

    if request.method != "POST":
        return redirect("console:vehicle-detail", pk=pk)

    target = request.POST.get("target", "")
    reason = (request.POST.get("reason") or "").strip()

    if not reason:
        messages.error(request, "سبب التغيير مطلوب.")
        return redirect("console:vehicle-detail", pk=pk)

    before = audit.snapshot(vehicle, ["state", "auction_id", "lot_number"])

    try:
        auction_services.move_vehicle(vehicle, target)
    except Exception as refusal:
        # The state machine's own sentence, shown as it is. It already says
        # whether the move does not exist or is merely not ready yet, and
        # rewording it here would lose that distinction.
        messages.error(request, str(refusal))
        return redirect("console:vehicle-detail", pk=pk)

    audit.record(
        action="console.move_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state", "auction_id", "lot_number"]),
        note=reason,
    )
    messages.success(request, f"المركبة صارت «{VehicleState(vehicle.state).label}».")
    return redirect("console:vehicle-detail", pk=pk)
