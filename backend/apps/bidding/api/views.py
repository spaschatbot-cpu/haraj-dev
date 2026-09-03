"""The HTTP edge of bidding. Four endpoints, and not one of them decides.

Every refusal a customer can meet here is raised by `apps.bidding.services`,
which raises it because `apps.bidding.eligibility` said so — one gate, and
`ops/checks/one_eligibility_gate.py` fails the build if a second appears. So
there is no `if` in this file that asks whether somebody may bid, and no
error body written here: `apps.core.exceptions` renders every `DomainError`
into the one envelope with its Arabic sentence.

Two things this file deliberately does *not* offer:

* **No endpoint that lists the bids on a car.** A sealed auction's whole
  property is that bidders cannot see each other's numbers. `MyBidsView`
  filters by the caller from the token, so the absence is structural rather
  than a permission somebody could relax later.
* **No amount taken as a number.** It arrives as a string and reaches
  `services.place_bid` as one (Article 3-2).
"""

from __future__ import annotations

import time

from django.conf import settings
from django.db.models import Count
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.models import Auction
from apps.auctions.states import AuctionState
from apps.auctions.visibility import visible_vehicles
from apps.bidding import live, services
from apps.bidding.models import Bid
from apps.bidding.throttling import BID_THROTTLES
from apps.money.models import Hold, HoldState

from .serializers import (
    BidPageSerializer,
    BidSerializer,
    MyBidsQuerySerializer,
    PageQuerySerializer,
    ParticipationPageSerializer,
    PlaceBidSerializer,
)

#: What "this bidder has no hold on this auction" is called on the wire.
#:
#: Deliberately *not* a `HoldState` member. There is no row — adding a fourth
#: state to the enum to describe the absence of a row would put it on `Hold`
#: itself, where it would mean a hold that holds nothing.
NO_HOLD = "none"
NO_HOLD_LABEL = "لا تأمين محجوز لهذا المزاد"


def bid_row(bid: Bid) -> dict:
    """One bid, rendered. The single place a bid becomes JSON."""
    vehicle = bid.vehicle
    return {
        "id": bid.pk,
        "vehicle_id": bid.vehicle_id,
        "auction_id": vehicle.auction_id,
        "lot_number": vehicle.lot_number,
        "vehicle_title": f"{vehicle.make} {vehicle.model} {vehicle.year}",
        # A string. `str(Decimal("55000.50"))` keeps the hundredths a float
        # would round away on the client (Article 3-2).
        "amount": str(bid.amount),
        "placed_at": bid.placed_at,
        "is_withdrawn": bid.is_withdrawn,
        "is_superseded": bid.is_superseded,
    }


class PlaceBidView(APIView):
    """`POST /api/v1/vehicles/{id}/bids/` — bid, or be told exactly why not.

    Lowering a standing bid is refused the first time with
    `lower_needs_confirm` and accepted when the caller comes back with
    ``confirm_lower``. That two-step is T506: lowering is a real feature of a
    sealed auction and also exactly what a fat finger does, so it costs one
    deliberate extra round trip.

    The car is resolved through `visible_vehicles`, so bidding on something the
    caller cannot see is a 404 — the same answer as a car that does not exist,
    which is what stops the endpoint being used to probe an unopened auction.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = BID_THROTTLES

    @extend_schema(
        operation_id="bids_place",
        request=PlaceBidSerializer,
        responses={201: BidSerializer},
        summary="وضع مزايدة",
    )
    def post(self, request: Request, pk: int) -> Response:
        payload = PlaceBidSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        vehicle = get_object_or_404(visible_vehicles(request.user), pk=pk)

        bid = services.place_bid(
            user=request.user,
            vehicle=vehicle,
            amount=payload.validated_data["amount"],
            confirm_lower=payload.validated_data["confirm_lower"],
        )
        return Response(BidSerializer(bid_row(bid)).data, status=status.HTTP_201_CREATED)


class WithdrawBidView(APIView):
    """`POST /api/v1/bids/{id}/withdraw/` — pull a bid back.

    The bid is fetched **filtered by the caller** rather than fetched and then
    checked, so somebody else's bid id is a 404 and not a 403. The service
    refuses it a second time anyway (`NotYourBid`) — the two guards are not
    redundant: this one decides what a stranger learns, that one is the rule.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = BID_THROTTLES

    @extend_schema(
        operation_id="bids_withdraw",
        request=None,
        responses={200: BidSerializer},
        summary="سحب مزايدة",
    )
    def post(self, request: Request, pk: int) -> Response:
        bid = get_object_or_404(
            Bid.objects.select_related("vehicle"), pk=pk, bidder=request.user
        )

        withdrawn = services.withdraw_bid(user=request.user, bid=bid)
        return Response(BidSerializer(bid_row(withdrawn)).data, status=status.HTTP_200_OK)


class MyBidsView(APIView):
    """`GET /api/v1/bids/mine/` — the caller's own bids, and only those."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="bids_mine",
        parameters=[MyBidsQuerySerializer],
        responses={200: BidPageSerializer},
        summary="مزايداتي",
    )
    def get(self, request: Request) -> Response:
        query = MyBidsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        bids = Bid.objects.filter(bidder=request.user).select_related("vehicle")
        if not query.validated_data["include_history"]:
            bids = bids.live()

        total = bids.count()
        page = bids.order_by("-placed_at")[
            query.validated_data["offset"] : query.validated_data["offset"]
            + query.validated_data["limit"]
        ]

        return Response(
            BidPageSerializer(
                {"total": total, "results": [bid_row(bid) for bid in page]}
            ).data,
            status=status.HTTP_200_OK,
        )


class MyParticipationsView(APIView):
    """`GET /api/v1/participations/` — the auctions the caller is in.

    One row per auction, carrying the two facts a «مشاركاتي» screen needs and
    cannot combine for itself: how many of the caller's bids still stand, and
    what their deposit for that auction is doing.

    Why the server and not the screen
    ---------------------------------
    Both halves exist separately — `bids/mine/` and the wallet — and the app
    could in principle match one against the other. It must not. That match is a
    rule, and a rule in a screen is a second copy of a rule (Article 4-5): the
    day a hold is released or consumed while the bid rows stay exactly as they
    were, the screen's «محجوز» and the ledger's disagree, and the customer is
    told two different things about one deposit. The hold is the only thing that
    knows, so the hold is what this reads.

    Being *in* an auction is either half on its own: a standing bid, or money
    pinned to it. A bidder whose deposit is held but whose only bid was
    withdrawn is still in — otherwise their wallet shows 10,000 محجوز against a
    list that shows nothing holding it.

    No eligibility is decided here and none is read. This says what is, not what
    may be; `check_eligibility` remains the one door (T502).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="participations_mine",
        parameters=[PageQuerySerializer],
        responses={200: ParticipationPageSerializer},
        summary="مشاركاتي",
    )
    def get(self, request: Request) -> Response:
        query = PageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        user = request.user
        standing = (
            Bid.objects.live()
            .filter(bidder=user)
            .values_list("vehicle__auction_id", flat=True)
        )
        holds = {
            hold.auction_id: hold
            for hold in Hold.objects.filter(owner=user, auction__isnull=False).order_by(
                "created_at"
            )
        }

        auction_ids = set(standing) | set(holds)
        auctions = Auction.objects.filter(pk__in=auction_ids).order_by(
            "-starts_at", "-id"
        )

        total = auctions.count()
        offset = query.validated_data["offset"]
        page = list(auctions[offset : offset + query.validated_data["limit"]])

        counts = dict(
            Bid.objects.live()
            .filter(bidder=user, vehicle__auction__in=page)
            .values_list("vehicle__auction_id")
            .annotate(count=Count("id"))
        )

        return Response(
            ParticipationPageSerializer(
                {
                    "total": total,
                    "results": [
                        participation_row(
                            auction,
                            bids_count=counts.get(auction.pk, 0),
                            hold=holds.get(auction.pk),
                        )
                        for auction in page
                    ],
                }
            ).data,
            status=status.HTTP_200_OK,
        )


def participation_row(auction, *, bids_count: int, hold) -> dict:
    """One auction the caller is in. The single place a participation is JSON."""
    active = hold is not None and hold.state == HoldState.ACTIVE
    return {
        "auction": {
            "id": auction.pk,
            "number": auction.number,
            "title": auction.title,
            "state": auction.state,
            "state_label": AuctionState(auction.state).label,
            "starts_at": auction.starts_at,
            "ends_at": auction.ends_at,
        },
        "bids_count": bids_count,
        "insurance": {
            "state": hold.state if hold is not None else NO_HOLD,
            "state_label": (
                HoldState(hold.state).label if hold is not None else NO_HOLD_LABEL
            ),
            # A string, and only while the money is actually pinned. See
            # `ParticipationInsuranceSerializer`.
            "amount": str(hold.amount) if active else None,
            "currency": settings.CURRENCY if active else None,
        },
    }


class LiveUpdatesView(APIView):
    """`GET /api/v1/live/` — server-sent events for the signed-in caller.

    A long-lived `text/event-stream`: the client opens it once and is told when
    something it may see has changed, instead of asking every two seconds. What
    may be seen is `apps.bidding.live`'s decision — **the caller's own bids and
    public states, never another bidder's number** — and that module's docstring
    is where the reasoning lives.

    Streaming without Channels
    --------------------------
    A `StreamingHttpResponse` over the ASGI application already in
    `config/asgi.py`. No Channels, no Redis, no second process: the added
    infrastructure would be a second thing to deploy, monitor and get wrong, and
    what it buys — push instead of a two-second re-derivation — is not
    perceptible to a person.

    The cost is one connection held per watching customer and one small query
    per connection per tick. That is a real cost and it is stated rather than
    hidden: it is the number to watch when this platform gets busy, and the
    moment it stops being acceptable is the moment Channels earns its place.

    Every stream ends
    -----------------
    After `MAX_STREAM_SECONDS` the server closes and the client reconnects. A
    stream that lives forever outlives the deploy that replaced the code running
    it, and the reconnect is what gets the customer onto the current version.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="live_updates",
        request=None,
        responses={(200, "text/event-stream"): OpenApiTypes.STR},
        summary="التحديث الحي",
    )
    def get(self, request: Request) -> StreamingHttpResponse:
        response = StreamingHttpResponse(
            _live_frames(request.user, since=request.headers.get("Last-Event-ID", "")),
            content_type="text/event-stream",
        )
        # Buffering is what makes an event stream arrive in one lump at the end.
        # `X-Accel-Buffering` is nginx's switch and is harmless elsewhere; the
        # cache headers stop a proxy storing a stream that is different every
        # time it is read.
        response["Cache-Control"] = "no-cache, no-transform"
        response["X-Accel-Buffering"] = "no"
        return response


def _live_frames(user, *, since: str):
    """Emit a frame when the caller's picture changes, and a heartbeat otherwise.

    The first frame is always sent, even when it matches `since`: a client that
    has just connected needs the current state to render, and «nothing changed»
    is indistinguishable to it from «not connected yet».

    The heartbeat is what lets a client show «انقطع الاتصال» honestly. Without
    it a dead connection and a quiet one look identical, and a bid amount from
    ten minutes ago sits on screen looking current — which the task calls out
    directly: *رقم مزايدة قديم يبدو حياً أسوأ من لا رقم*.
    """
    started = time.monotonic()
    last = since

    # `: ` is an SSE comment. Sent immediately so the connection is established
    # in the client's eyes before the first tick, rather than looking stalled
    # for two seconds.
    yield ": connected\n\n"
    yield f"retry: {live.INTERVAL_SECONDS * 1000}\n\n"

    first = True
    while time.monotonic() - started < live.MAX_STREAM_SECONDS:
        snapshot = live.snapshot_for(user)

        if first or snapshot.digest != last:
            yield snapshot.as_event()
            last = snapshot.digest
            first = False
        else:
            yield ": heartbeat\n\n"

        time.sleep(live.INTERVAL_SECONDS)

    yield "event: reconnect\ndata: {}\n\n"
