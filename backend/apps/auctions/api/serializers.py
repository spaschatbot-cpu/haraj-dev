"""What the auction and vehicle endpoints accept, and the shape they answer in.

The response serialisers here are **descriptions of the card**, not a second
definition of it. `apps.auctions.cards` builds every card the platform renders —
the list, the detail page, the admin table, the export — and these classes exist
so drf-spectacular can publish that shape, not so a view can assemble one.
`test_cards.py` and `ops/checks/one_vehicle_card.py` are what keep that true;
a field added to the card and forgotten here shows up as a schema diff, which is
the point of T621 pinning the file.

The query serialisers are the interesting half. Every one of them **bounds its
parameter**: v1's list endpoint took whatever `limit` the caller sent, so one
request for `limit=100000` was a table scan a customer could ask for.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.auctions.listing import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import Phase


class PageQuerySerializer(serializers.Serializer):
    """Paging, with a ceiling.

    ``max_value`` on the limit is not politeness. The listing counts and slices
    in SQL (T414), so a page is cheap — but only because the page is small. An
    unbounded limit turns the one endpoint every screen opens with into a way to
    ask for the whole table.
    """

    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=MAX_PAGE_SIZE, default=DEFAULT_PAGE_SIZE
    )
    offset = serializers.IntegerField(required=False, min_value=0, default=0)


class VehicleQuerySerializer(PageQuerySerializer):
    """Paging plus the filters the vehicle list understands.

    Every filter is a column with an index behind it or a state in a small set.
    There is deliberately no free-form ordering parameter: an `order_by` a caller
    controls is an invitation to sort a million rows by a column with no index,
    and every screen we have sorts by lot number inside an auction anyway.
    """

    #: One box on the screen, matched against make, model and lot number. Not a
    #: full-text index — at this size a trigram-free `ILIKE` on two indexed
    #: columns is honest, and pretending otherwise would hide the day it stops
    #: being enough.
    search = serializers.CharField(
        required=False, allow_blank=True, max_length=80, trim_whitespace=True
    )
    auction = serializers.IntegerField(required=False, min_value=1)
    state = serializers.ChoiceField(
        choices=VehicleState.choices, required=False, allow_blank=True
    )

    #: The browse page's tab. A property of the **auction**, not of the car, and
    #: the mapping from a tab to the auction states behind it is written once in
    #: `apps.auctions.visibility` — never here and never in a client.
    #:
    #: Optional on purpose: leaving it out is what the endpoint did before this
    #: parameter existed, so no consumer breaks by not knowing about it.
    phase = serializers.ChoiceField(
        choices=Phase.choices, required=False, allow_blank=True
    )

    make = serializers.CharField(required=False, allow_blank=True, max_length=80)
    year_from = serializers.IntegerField(required=False, min_value=1900, max_value=2200)
    year_to = serializers.IntegerField(required=False, min_value=1900, max_value=2200)

    def validate(self, attrs: dict) -> dict:
        first, last = attrs.get("year_from"), attrs.get("year_to")
        if first and last and first > last:
            raise serializers.ValidationError(
                {"year_from": "أول سنة لازم تكون قبل آخر سنة."}
            )
        return attrs


class AuctionQuerySerializer(PageQuerySerializer):
    state = serializers.ChoiceField(
        choices=AuctionState.choices, required=False, allow_blank=True
    )


class AuctionCardSerializer(serializers.Serializer):
    """The auction row, as `cards.auction_card` builds it."""

    id = serializers.IntegerField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    state = serializers.CharField()
    state_label = serializers.CharField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    vehicle_count = serializers.IntegerField(allow_null=True)
    open_vehicle_count = serializers.IntegerField(allow_null=True)


class VehicleCardSerializer(serializers.Serializer):
    """The vehicle card — the same fields in the list and on the detail page.

    T609's acceptance criterion is that those two are identical, and
    `test_vehicle_api.py` asserts it by comparing the key sets rather than by
    reading this class, so the guarantee does not depend on this file being
    kept honest by hand.
    """

    id = serializers.IntegerField()
    auction_id = serializers.IntegerField()
    auction_number = serializers.IntegerField()
    auction_title = serializers.CharField()
    auction_state = serializers.CharField()

    #: The countdown's two ends, UTC on the wire. On the card and not behind a
    #: second request: a grid of twenty cars would otherwise open twenty-one
    #: connections to draw twenty clocks.
    auction_starts_at = serializers.DateTimeField()
    auction_ends_at = serializers.DateTimeField()

    lot_number = serializers.IntegerField()
    title = serializers.CharField()
    make = serializers.CharField()
    model = serializers.CharField()
    year = serializers.IntegerField()
    odometer_km = serializers.IntegerField(allow_null=True)
    transmission = serializers.CharField()
    transmission_label = serializers.CharField()
    fuel_type = serializers.CharField()
    fuel_type_label = serializers.CharField()
    condition = serializers.CharField()
    condition_label = serializers.CharField()
    plate_type = serializers.CharField()
    plate_type_label = serializers.CharField()

    #: A string, never a number. Article 3-2 forbids a float on a money path,
    #: and JSON has no other numeric type to offer — `1234.50` parsed by a
    #: JavaScript client is a float whatever the schema calls it.
    reserve_price = serializers.CharField(allow_null=True)

    state = serializers.CharField()
    state_label = serializers.CharField()
    listing_state = serializers.CharField()
    owner_company_name = serializers.CharField(allow_null=True)
    thumbnail_url = serializers.CharField(allow_null=True)


class AuctionPageSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    results = AuctionCardSerializer(many=True)


class PhaseCountsSerializer(serializers.Serializer):
    """The three tab counters, in the one response that carries the page.

    Three named fields and not a map keyed by phase: a generated Dart or
    TypeScript client turns the first into three typed getters and the second
    into `Map<String, int>?`, and a screen reading `counts['activ']` compiles.
    """

    soon = serializers.IntegerField()
    active = serializers.IntegerField()
    ended = serializers.IntegerField()


class VehiclePageSerializer(serializers.Serializer):
    """A page of cars, its total, and the three tab counters.

    The counters ride along on **every** vehicle page, whichever tab was asked
    for, because all three tabs are on screen at all times. Splitting them into
    a second endpoint is what v1 did — six requests to draw three numbers — and
    it made the three numbers three different moments.
    """

    total = serializers.IntegerField()
    counts = PhaseCountsSerializer()
    results = VehicleCardSerializer(many=True)
