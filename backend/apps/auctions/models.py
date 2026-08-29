"""Auctions and the vehicles in them.

Times are stored in UTC and entered in Saudi time. Nothing in this module ever
compares a stored timestamp against a locally-formatted one; the conversion
happens once, at the edge, in :mod:`apps.core.time`.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class AuctionState(models.TextChoices):
    DRAFT = "draft", "مسودة"
    SCHEDULED = "scheduled", "مجدول"
    LIVE = "live", "جارٍ"
    ENDED = "ended", "منتهٍ"
    SETTLED = "settled", "مُسوّى"
    CANCELLED = "cancelled", "ملغى"


class Auction(models.Model):
    number = models.PositiveIntegerField(unique=True, help_text="رقم المزاد المعروض")
    title = models.CharField(max_length=200)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    state = models.CharField(
        max_length=16, choices=AuctionState.choices, default=AuctionState.DRAFT
    )

    #: What a bidder must have deposited to take part.
    deposit_required = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("10000.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")),
                name="auction_ends_after_it_starts",
            ),
        ]
        indexes = [models.Index(fields=["state", "starts_at"])]
        ordering = ["-starts_at"]

    def __str__(self) -> str:
        return f"مزاد {self.number} — {self.title}"

    @property
    def is_open_for_bidding(self) -> bool:
        now = timezone.now()
        return self.state == AuctionState.LIVE and self.starts_at <= now < self.ends_at


class VehicleState(models.TextChoices):
    """Where a car stands. Deliberately wide — v1 squashed this enum once and
    lost the distinctions it had been carrying."""

    DRAFT = "draft", "مسودة"
    LISTED = "listed", "معروضة"
    BIDDING = "bidding", "تحت المزايدة"
    AWAITING_DECISION = "awaiting_decision", "بانتظار قرار المالك"
    AWARDED = "awarded", "مرسّاة"
    REJECTED = "rejected", "مرفوضة"
    INVOICED = "invoiced", "مفوترة"
    PAID = "paid", "مسدَّدة"
    RELEASED = "released", "خرجت"
    WITHDRAWN = "withdrawn", "مسحوبة"
    RELISTED = "relisted", "معادة للعرض"


class Vehicle(models.Model):
    auction = models.ForeignKey(
        Auction, on_delete=models.PROTECT, related_name="vehicles"
    )
    lot_number = models.PositiveIntegerField(help_text="رقم اللوت داخل المزاد")

    make = models.CharField(max_length=80)
    model = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField()
    vin = models.CharField(max_length=32, blank=True, db_index=True)
    plate_number = models.CharField(max_length=16, blank=True)
    plate_type = models.CharField(max_length=32, blank=True)
    odometer_km = models.PositiveIntegerField(null=True, blank=True)

    owner_company = models.ForeignKey(
        "accounts.Company",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="vehicles",
        help_text="الشريك المالك للمركبة، إن وُجد",
    )

    #: The one number that says what this car stands on. In v1 four screens each
    #: computed their own version of it; here every screen reads this field.
    reserve_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    state = models.CharField(
        max_length=24, choices=VehicleState.choices, default=VehicleState.DRAFT
    )

    awarded_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="won_vehicles",
    )
    awarded_price = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    awarded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "lot_number"], name="one_lot_number_per_auction"
            ),
            models.CheckConstraint(
                condition=Q(state="awarded", awarded_to__isnull=False)
                | ~Q(state="awarded"),
                name="an_awarded_vehicle_names_its_winner",
            ),
        ]
        indexes = [models.Index(fields=["auction", "state"])]
        ordering = ["auction", "lot_number"]

    def __str__(self) -> str:
        return f"#{self.lot_number} {self.make} {self.model} {self.year}"


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="vehicles/%Y/%m/")
    position = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(is_cover=True),
                name="one_cover_image_per_vehicle",
            ),
        ]
