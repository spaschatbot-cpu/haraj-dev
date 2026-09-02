"""What the bidding endpoints take and return.

The amount arrives as a **string** and is parsed by `bidding.services` into a
`Decimal`, never by a serializer into a float. `serializers.DecimalField` would
be safe here, but it publishes `type: number` in the schema — and a generated
JavaScript client reading `55000.50` off the wire has already lost it to a
float before any of our code sees it (Article 3-2). A string in, a string out,
on every money path.
"""

from __future__ import annotations

from rest_framework import serializers


class PlaceBidSerializer(serializers.Serializer):
    """One bid on one car."""

    #: Digits and at most two decimals, as text. The pattern refuses `1e5` and
    #: `55_000` before they reach `Decimal`, so the refusal is a named field
    #: error rather than an exception from the parser.
    amount = serializers.RegexField(
        r"^\d{1,12}(\.\d{1,2})?$",
        error_messages={"invalid": "المبلغ لازم يكون رقماً بريالات وهللات."},
    )

    #: The second half of the two-step that T506 requires. A first attempt to
    #: lower a standing bid is refused with `lower_needs_confirm`; the client
    #: shows what that means and comes back with this set. Defaulting it to
    #: true anywhere would delete the whole protection.
    confirm_lower = serializers.BooleanField(required=False, default=False)


class BidSerializer(serializers.Serializer):
    """A bid as the owner of it sees it.

    Never anybody else's: a sealed auction's whole property is that bidders
    cannot see each other's numbers, so there is no endpoint here that lists the
    bids *on* a car — only the bids *by* the caller.
    """

    id = serializers.IntegerField()
    vehicle_id = serializers.IntegerField()
    auction_id = serializers.IntegerField()
    lot_number = serializers.IntegerField()
    vehicle_title = serializers.CharField()
    amount = serializers.CharField()
    placed_at = serializers.DateTimeField()
    is_withdrawn = serializers.BooleanField()
    is_superseded = serializers.BooleanField()


class BidPageSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    results = BidSerializer(many=True)


class MyBidsQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=20
    )
    offset = serializers.IntegerField(required=False, min_value=0, default=0)

    #: Withdrawn and superseded rows are kept forever (the history is the
    #: point), so the default page shows only what still stands — otherwise a
    #: customer who revised five times sees six rows for one car.
    include_history = serializers.BooleanField(required=False, default=False)
