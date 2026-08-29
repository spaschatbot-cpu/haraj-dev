"""Bids, and — just as importantly — the bids we refused.

Support's most common question in v1 was «ليه ما يقدرش يزايد؟», and the system
had no answer because a refusal left no trace. Here every refusal is written
down with the reason and a snapshot of the money at that instant, so the answer
takes seconds and needs no reconstruction.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q


class Bid(models.Model):
    vehicle = models.ForeignKey(
        "auctions.Vehicle", on_delete=models.PROTECT, related_name="bids"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bids"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    #: Sealed auctions let a bidder revise downward, which is a deliberate rule
    #: and not a bug. Superseded bids stay in the table so the history is whole.
    superseded_by = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supersedes",
    )
    is_withdrawn = models.BooleanField(default=False)

    placed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="bid_is_positive"),
            models.UniqueConstraint(
                fields=["vehicle", "bidder"],
                condition=Q(superseded_by__isnull=True, is_withdrawn=False),
                name="one_live_bid_per_bidder_per_vehicle",
            ),
        ]
        indexes = [
            models.Index(fields=["vehicle", "-amount"]),
            models.Index(fields=["bidder", "-placed_at"]),
        ]
        ordering = ["-amount", "placed_at"]

    def __str__(self) -> str:
        return f"{self.bidder_id} → {self.amount} on {self.vehicle_id}"


class RefusalReason(models.TextChoices):
    AUCTION_NOT_LIVE = "auction_not_live", "المزاد ليس جارياً"
    AUCTION_ENDED = "auction_ended", "المزاد انتهى"
    VEHICLE_NOT_BIDDABLE = "vehicle_not_biddable", "المركبة غير قابلة للمزايدة"
    BELOW_FLOOR = "below_floor", "أقل من الحد الأدنى"
    NO_DEPOSIT = "no_deposit", "لا يوجد تأمين متاح"
    UNPAID_DUES = "unpaid_dues", "عليه مستحقات غير مسدَّدة"
    PHONE_NOT_VERIFIED = "phone_not_verified", "الجوال غير موثّق"
    PROFILE_INCOMPLETE = "profile_incomplete", "الملف غير مكتمل"
    OWN_VEHICLE = "own_vehicle", "المركبة تخصّه"


class BidRefusal(models.Model):
    """One refused attempt, with the evidence attached."""

    vehicle = models.ForeignKey(
        "auctions.Vehicle", on_delete=models.PROTECT, related_name="refusals"
    )
    bidder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bid_refusals"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=32, choices=RefusalReason.choices)
    detail = models.CharField(max_length=500, blank=True)

    #: What the bidder's money looked like at the moment of refusal. Kept as a
    #: snapshot because the balances will have moved by the time anyone asks.
    insurance_free = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    insurance_held = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    insurance_locked = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    outstanding_dues = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    refused_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["bidder", "-refused_at"]),
            models.Index(fields=["reason", "-refused_at"]),
        ]
        ordering = ["-refused_at"]

    def __str__(self) -> str:
        return f"{self.bidder_id} refused: {self.reason}"
