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

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.visibility import visible_vehicles
from apps.bidding import services
from apps.bidding.models import Bid
from apps.bidding.throttling import BID_THROTTLES

from .serializers import (
    BidPageSerializer,
    BidSerializer,
    MyBidsQuerySerializer,
    PlaceBidSerializer,
)


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
