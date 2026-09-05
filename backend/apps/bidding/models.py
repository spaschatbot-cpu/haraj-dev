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


class BidQuerySet(models.QuerySet):
    def live(self):
        """The bids that still stand.

        One definition of "live", used by every reader, and the same pair of
        columns the unique index below is built on — so what the code calls a
        live bid and what the database refuses a second of are the same thing.
        """
        return self.filter(is_superseded=False, is_withdrawn=False)


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
    #:
    #: The link points *backwards*, from the new bid to the one it replaces,
    #: and the old row carries its own :attr:`is_superseded` flag. Both exist
    #: because the partial unique index below can only read columns on the row
    #: it indexes: with the link pointing forwards, freeing the slot would need
    #: the new row's id before the new row exists, and the index — a partial
    #: unique index, which postgres cannot defer — refuses the two live rows
    #: that momentarily overlap. Revising a bid is therefore: flag the old row,
    #: insert the new one pointing at it.
    supersedes = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="superseded_by",
    )
    is_superseded = models.BooleanField(default=False)

    is_withdrawn = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    placed_at = models.DateTimeField(auto_now_add=True)

    objects = BidQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="bid_is_positive"),
            models.UniqueConstraint(
                fields=["vehicle", "bidder"],
                condition=Q(is_superseded=False, is_withdrawn=False),
                name="one_live_bid_per_bidder_per_vehicle",
            ),
            # A withdrawal is an event with a moment, not a flag somebody set.
            # "When did he pull out?" is the first question asked about one.
            models.CheckConstraint(
                condition=Q(is_withdrawn=False, withdrawn_at__isnull=True)
                | Q(is_withdrawn=True, withdrawn_at__isnull=False),
                name="a_withdrawn_bid_names_its_moment",
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
    REFUND_PENDING = "refund_pending", "تأمينه مطلوبٌ استرداده"


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

    @property
    def insurance_total(self):
        """The three insurance buckets added up, as they stood at the refusal.

        This is the number the customer says on the phone. He remembers what he
        deposited, not how it was split — «كان عندي عشرة آلاف» is true of a
        person holding 2,000 free and 8,000 locked against a debt, and a support
        agent who can only see the split has to do the addition in their head
        before they can agree with him and then explain.

        Derived from this row's own stored figures and nothing else: it is a
        different arrangement of the snapshot, never a fresh reading of a
        balance that has moved since.
        """
        return self.insurance_free + self.insurance_held + self.insurance_locked
