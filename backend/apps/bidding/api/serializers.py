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


class PageQuerySerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        required=False, min_value=1, max_value=100, default=20
    )
    offset = serializers.IntegerField(required=False, min_value=0, default=0)


class ParticipationAuctionSerializer(serializers.Serializer):
    """The auction, as the person who is in it needs to see it named."""

    id = serializers.IntegerField()
    number = serializers.IntegerField()
    title = serializers.CharField()
    state = serializers.CharField()
    #: The auction's own Arabic word for its state. A client that maps `live`
    #: to «جارٍ» owns a second copy of the vocabulary, and it drifts the day a
    #: state is added (Article 4-5).
    state_label = serializers.CharField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class ParticipationInsuranceSerializer(serializers.Serializer):
    """What this bidder's deposit for this auction is doing, per the ledger.

    Read off `money.Hold` and nothing else. The alternative — the app matching
    «مزايداتي» against «المحفظة» — is a rule in a screen, and it is wrong the
    moment a hold is released or consumed while the bids stay as they were.
    """

    #: A `HoldState` value, or `none` when this bidder has no hold on this
    #: auction at all. `none` is not a `HoldState`: there is no row, and
    #: inventing one to say so would put a hold in the ledger that holds nothing.
    state = serializers.CharField()
    state_label = serializers.CharField()

    #: A decimal string, never a number (Article 3-2), and `null` unless the
    #: money is actually pinned right now. A released hold still carries the
    #: figure it once held, and showing it reads as "still held".
    amount = serializers.CharField(allow_null=True)
    currency = serializers.CharField(allow_null=True)


class ParticipationSerializer(serializers.Serializer):
    auction = ParticipationAuctionSerializer()
    #: Bids that still stand. Withdrawn and superseded rows are kept forever
    #: (T507) and counting them would tell a customer they have five live bids
    #: on a car they bid on five times.
    bids_count = serializers.IntegerField()
    insurance = ParticipationInsuranceSerializer()


class ParticipationPageSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    results = ParticipationSerializer(many=True)
