"""مزادُ تيستٍ حيّ بسيّارات مزاد v1 رقم 1030 (نسخة ٢٤ نوفمبر) — بصورها وبياناتها.

الطريقُ المشروع نفسُه الذي تسلكه اللوحة: draft ← (المركبات) ← scheduled ← live.
والمركباتُ تُنقل لا تُنسخ (اللوحةُ والشاصيه فريدان)، ولا مزايداتَ عليها تُسحب.
"""

from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.services import move_auction
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid

assert connection.settings_dict["NAME"] == "haraj2_v2", connection.settings_dict["NAME"]

source = Auction.objects.get(number=1030)
now = timezone.now()

with transaction.atomic():
    auction, created = Auction.objects.get_or_create(
        number=1900,
        defaults={
            "title": "مزاد تجريبي — سيّارات مزاد 1030 (نسخة v1)",
            "starts_at": now - timedelta(minutes=5),
            "ends_at": now + timedelta(hours=72),
            "state": AuctionState.DRAFT,
            "location": source.location,
            "showcase": source.showcase,
            "deposit_required": source.deposit_required,
            "admin_fee": source.admin_fee,
        },
    )
    cars = Vehicle.objects.filter(
        auction=source, state__in=(VehicleState.LISTED, VehicleState.BIDDING)
    )
    live_bids = Bid.objects.live().filter(vehicle__in=cars).count()
    assert live_bids == 0, live_bids
    moved = cars.update(auction=auction)

if auction.state == AuctionState.DRAFT:
    move_auction(auction, AuctionState.SCHEDULED)
if auction.state == AuctionState.SCHEDULED:
    move_auction(auction, AuctionState.LIVE)

with_photos = Vehicle.objects.filter(auction=auction, images__isnull=False).distinct().count()
print(
    "auction", auction.number, auction.pk, auction.state,
    "cars", Vehicle.objects.filter(auction=auction).count(), "moved now", moved,
    "with photos", with_photos, "ends", timezone.localtime(auction.ends_at),
)
