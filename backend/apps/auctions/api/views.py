"""The HTTP edge of auctions and vehicles. Read-only, and it decides nothing.

Each view does four things: validate the query, call one function in
:mod:`apps.auctions.listing` or :mod:`apps.auctions.cards`, and render what came
back. No view filters for visibility itself — `apps.auctions.visibility` owns
that rule and owns it for the admin screens too, so a car hidden in one place
cannot be visible in another (T409).

Anonymous callers are allowed here on purpose. A customer browsing before they
sign in is the whole of how the platform is found, and the web client renders
these pages server-side for search engines (Phase 011). What an anonymous caller
*sees* is still the visibility rule's decision, not this file's.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.cards import auction_card, card_queryset, vehicle_card
from apps.auctions.listing import auction_page, vehicle_page, with_vehicle_counts
from apps.auctions.models import Auction, Vehicle
from apps.auctions.visibility import PUBLIC_AUCTION_STATES, visible_vehicles

from .serializers import (
    AuctionCardSerializer,
    AuctionPageSerializer,
    AuctionQuerySerializer,
    VehicleCardSerializer,
    VehiclePageSerializer,
    VehicleQuerySerializer,
)


def _query(serializer_class, request: Request) -> dict:
    """Validated query parameters, or a 400 naming the one that was wrong."""
    query = serializer_class(data=request.query_params)
    query.is_valid(raise_exception=True)
    return query.validated_data


class AuctionListView(APIView):
    """`GET /api/v1/auctions/` — the auctions a caller may see, newest first."""

    permission_classes = [AllowAny]

    @extend_schema(
        # Named explicitly, and every operation below is. Left to itself
        # drf-spectacular derives the id from the path and resolves a collision
        # between `/auctions/` and `/auctions/{id}/` with a numeral — so the
        # generated Dart carries `v1AuctionsRetrieve` and
        # `v1AuctionsRetrieve2`, and the caller has to guess which is the list.
        # `--fail-on-warn` in T621 is what turned that into a build failure.
        operation_id="auctions_list",
        parameters=[AuctionQuerySerializer],
        responses={200: AuctionPageSerializer},
        summary="قائمة المزادات",
    )
    def get(self, request: Request) -> Response:
        query = _query(AuctionQuerySerializer, request)
        page = auction_page(
            request.user,
            state=query.get("state", ""),
            limit=query["limit"],
            offset=query["offset"],
        )
        return Response(AuctionPageSerializer(page).data, status=status.HTTP_200_OK)


class AuctionDetailView(APIView):
    """`GET /api/v1/auctions/{id}/` — one auction, in the list's own shape.

    Built by `cards.auction_card` with the same annotations the list uses, so
    the detail page and the row a customer tapped cannot disagree about how many
    cars an auction holds. An auction the caller may not see is a 404: a 403
    would confirm it exists, which is enough to enumerate auctions before they
    open.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auctions_retrieve",
        responses={200: AuctionCardSerializer},
        summary="تفاصيل المزاد",
    )
    def get(self, request: Request, pk: int) -> Response:
        auctions = Auction.objects.all()
        if not request.user.is_staff:
            auctions = auctions.filter(state__in=list(PUBLIC_AUCTION_STATES))

        auction = get_object_or_404(with_vehicle_counts(auctions), pk=pk)

        return Response(
            AuctionCardSerializer(auction_card(auction)).data, status=status.HTTP_200_OK
        )


class AuctionVehicleListView(APIView):
    """`GET /api/v1/auctions/{id}/vehicles/` — one auction's cars."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auctions_vehicles_list",
        parameters=[VehicleQuerySerializer],
        responses={200: VehiclePageSerializer},
        summary="مركبات المزاد",
    )
    def get(self, request: Request, pk: int) -> Response:
        auction = get_object_or_404(Auction.objects.all(), pk=pk)
        query = _query(VehicleQuerySerializer, request)

        page = vehicle_page(
            request.user,
            auction=auction,
            search=query.get("search", ""),
            state=query.get("state", ""),
            make=query.get("make", ""),
            year_from=query.get("year_from"),
            year_to=query.get("year_to"),
            limit=query["limit"],
            offset=query["offset"],
        )
        return Response(VehiclePageSerializer(page).data, status=status.HTTP_200_OK)


class VehicleListView(APIView):
    """`GET /api/v1/vehicles/` — cars across auctions, searched and filtered."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="vehicles_list",
        parameters=[VehicleQuerySerializer],
        responses={200: VehiclePageSerializer},
        summary="قائمة المركبات",
    )
    def get(self, request: Request) -> Response:
        query = _query(VehicleQuerySerializer, request)

        auction = None
        if query.get("auction"):
            auction = get_object_or_404(Auction.objects.all(), pk=query["auction"])

        page = vehicle_page(
            request.user,
            auction=auction,
            search=query.get("search", ""),
            state=query.get("state", ""),
            make=query.get("make", ""),
            year_from=query.get("year_from"),
            year_to=query.get("year_to"),
            limit=query["limit"],
            offset=query["offset"],
        )
        return Response(VehiclePageSerializer(page).data, status=status.HTTP_200_OK)


class VehicleDetailView(APIView):
    """`GET /api/v1/vehicles/{id}/` — one car, through the one card builder.

    T609's whole requirement is that this returns the *same* fields as the list.
    It does so by construction rather than by discipline: both call
    `cards.vehicle_card`, and there is no second assembly of a vehicle anywhere
    (`ops/checks/one_vehicle_card.py` fails the build if one appears).

    A car the caller may not see is a 404, not a 403. A 403 confirms the row
    exists, which is enough to enumerate an auction before it opens.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="vehicles_retrieve",
        responses={200: VehicleCardSerializer},
        summary="تفاصيل المركبة",
    )
    def get(self, request: Request, pk: int) -> Response:
        queryset = card_queryset(visible_vehicles(request.user))
        vehicle: Vehicle = get_object_or_404(queryset, pk=pk)

        return Response(
            VehicleCardSerializer(vehicle_card(vehicle)).data, status=status.HTTP_200_OK
        )
