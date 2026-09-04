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

from apps.auctions import favourites
from apps.auctions.cards import (
    auction_card,
    card_queryset,
    vehicle_card,
    vehicle_cards,
)
from apps.auctions.favourites import Favourite
from apps.auctions.listing import (
    auction_page,
    page_totals,
    vehicle_page,
    with_vehicle_counts,
)
from apps.auctions.models import Auction, Vehicle
from apps.auctions.visibility import PUBLIC_AUCTION_STATES, visible_vehicles

from .serializers import (
    AuctionCardSerializer,
    AuctionPageSerializer,
    AuctionQuerySerializer,
    PageQuerySerializer,
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
            phase=query.get("phase", ""),
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
            phase=query.get("phase", ""),
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


class FavouriteListView(APIView):
    """`GET /api/v1/favourites/` — the cars this customer marked, newest first.

    Rendered through `cards.vehicle_card`, like every other list of vehicles in
    the product: a favourites screen that assembled its own row would be the
    second card builder `ops/checks/one_vehicle_card.py` exists to refuse, and
    the field that went missing from it would be missing only here.

    The visibility rule still applies. A car marked while it was listed and
    since withdrawn is not shown — a favourite is a bookmark, never a claim, and
    it does not grant sight of a row its owner may no longer see.
    """

    @extend_schema(
        operation_id="favourites_list",
        parameters=[PageQuerySerializer],
        responses={200: VehiclePageSerializer},
        summary="المفضّلة",
    )
    def get(self, request: Request) -> Response:
        query = _query(PageQuerySerializer, request)

        marked = Favourite.objects.filter(user=request.user).values_list(
            "vehicle_id", flat=True
        )
        queryset = visible_vehicles(request.user).filter(pk__in=marked)

        # The same page shape as every other list of cars, counters included —
        # `page_totals` costs one aggregate where a bare `.count()` cost one
        # count, so the shape is uniform for free. A favourites screen that
        # answered in a narrower shape would be the second page format the
        # clients have to branch on.
        total, counts = page_totals(queryset)
        # Ordered by the mark, not by lot: this screen answers "what did I save",
        # and the newest save is what the customer is looking for.
        page = card_queryset(queryset).order_by("-favourited_by__created_at")[
            query["offset"] : query["offset"] + query["limit"]
        ]

        return Response(
            VehiclePageSerializer(
                {"total": total, "counts": counts, "results": vehicle_cards(page)}
            ).data,
            status=status.HTTP_200_OK,
        )


class FavouriteView(APIView):
    """`PUT` and `DELETE /api/v1/favourites/{id}/` — mark and unmark.

    `PUT`, not `POST`, and both are idempotent: marking twice is marking once,
    and unmarking something unmarked is not an error. That is what a
    double-tapped heart and a retried request produce, and «هذه المركبة في
    مفضّلتك بالفعل» is a refusal for a thing that already happened the way the
    customer wanted.

    Both answer `204`. There is nothing to return — the client already knows
    which car it asked about, and a body here would be a second place the mark's
    shape is described.
    """

    @extend_schema(
        operation_id="favourites_mark",
        request=None,
        responses={204: None},
        summary="إضافة إلى المفضّلة",
    )
    def put(self, request: Request, pk: int) -> Response:
        vehicle = get_object_or_404(visible_vehicles(request.user), pk=pk)
        favourites.mark(user=request.user, vehicle=vehicle)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        operation_id="favourites_unmark",
        request=None,
        responses={204: None},
        summary="إزالة من المفضّلة",
    )
    def delete(self, request: Request, pk: int) -> Response:
        # No 404 for an unmarked car and no visibility check: removing a mark on
        # a car that has since been withdrawn is exactly what a customer
        # tidying their list does, and refusing it would leave a row they can
        # see and cannot delete.
        favourites.unmark(user=request.user, vehicle_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)
