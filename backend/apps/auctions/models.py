"""Auctions and the vehicles in them.

Times are stored in UTC and entered in Saudi time. Nothing in this module ever
compares a stored timestamp against a locally-formatted one; the conversion
happens once, at the edge, in :mod:`apps.core.time`.

State lives here as a plain column, but nothing in this module moves it. The
table of legal moves is in :mod:`apps.auctions.states` and the only code that
writes the column is :mod:`apps.auctions.services` — a rule a CI check
enforces, because "we all know not to" is exactly what failed in v1.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .states import AuctionState, VehicleState

__all__ = [
    "Auction",
    "AuctionState",
    "FuelType",
    "PlateType",
    "Transmission",
    "Vehicle",
    "VehicleCondition",
    "VehicleImage",
    "VehicleState",
]


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


class Transmission(models.TextChoices):
    AUTOMATIC = "automatic", "أوتوماتيك"
    MANUAL = "manual", "عادي"
    CVT = "cvt", "CVT"
    UNKNOWN = "unknown", "غير محدد"


class FuelType(models.TextChoices):
    PETROL = "petrol", "بنزين"
    DIESEL = "diesel", "ديزل"
    HYBRID = "hybrid", "هجين"
    ELECTRIC = "electric", "كهرباء"
    UNKNOWN = "unknown", "غير محدد"


class VehicleCondition(models.TextChoices):
    RUNNING = "running", "تسير"
    NOT_RUNNING = "not_running", "لا تسير"
    DAMAGED = "damaged", "متضررة"
    SALVAGE = "salvage", "تشليح"
    UNKNOWN = "unknown", "غير محدد"


class PlateType(models.TextChoices):
    PRIVATE = "private", "خصوصي"
    PUBLIC_TRANSPORT = "public_transport", "نقل عام"
    TAXI = "taxi", "أجرة"
    HEAVY = "heavy", "نقل ثقيل"
    EXPORT = "export", "تصدير"
    NONE = "none", "بدون لوحة"


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

    # ------------------------------------------------------------------
    # Specifications — columns on this table, never a side table.
    #
    # v1 kept these in a `details` table joined on a different key, so a card
    # cost a second query, half the rows had no row there at all, and adding a
    # spec meant a backfill. Five columns and a NULL are cheaper than a join
    # that is missing half the time.
    # ------------------------------------------------------------------
    plate_type = models.CharField(
        max_length=32, choices=PlateType.choices, default=PlateType.PRIVATE
    )
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    transmission = models.CharField(
        max_length=16, choices=Transmission.choices, default=Transmission.UNKNOWN
    )
    fuel_type = models.CharField(
        max_length=16, choices=FuelType.choices, default=FuelType.UNKNOWN
    )
    condition = models.CharField(
        max_length=16, choices=VehicleCondition.choices, default=VehicleCondition.UNKNOWN
    )

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
    #: What it actually sold for — a settlement result, not a price the car
    #: stands on. `reserve_price` remains the only "what does this car cost"
    #: field (T406).
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
        indexes = [
            models.Index(fields=["auction", "state"]),
            models.Index(fields=["owner_company", "state"]),
        ]
        ordering = ["auction", "lot_number"]

    def __str__(self) -> str:
        return f"#{self.lot_number} {self.make} {self.model} {self.year}"

    @property
    def partner_name(self) -> str:
        """Whose car this is, for a screen or a file. Presentation, not a rule.

        It exists so that showing a partner's name does not require reading
        `owner_company` in a module that also touches bidding. That attribute is
        an **eligibility fact** — a bidder may not bid on their own car — and
        `ops/checks/one_eligibility_gate.py` refuses to let any file but
        `apps/bidding/eligibility.py` read one, precisely because in v1 the same
        column was consulted in six places and the sixth forgot what it meant.

        The guard is right to refuse, and the answer is not to work around it:
        the screen wanted a *label*, and a label is a property of the car. The
        eligibility question keeps its single door.
        """
        return "" if self.owner_company is None else self.owner_company.name


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="vehicles/%Y/%m/")

    #: Generated on upload and stored on disk next to the original. A list of
    #: fifty cars must never touch the full-size files: in v1 the bottleneck
    #: was never the request count, it was 50 × 3 MB of JPEG.
    thumbnail = models.ImageField(upload_to="vehicles/%Y/%m/thumbs/", blank=True)

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

    def __str__(self) -> str:
        return f"صورة {self.position} للوت {self.vehicle_id}"


# ---------------------------------------------------------------------------
# المفضّلة — النموذج يعيش في `apps/auctions/favourites.py` مع خدماته.
#
# Imported here so Django's app registry finds it: a model defined outside
# `models.py` is invisible to `makemigrations` unless something in `models.py`
# imports it. Kept *next to its services* rather than moved here, because the
# rules about a favourite — idempotent marking, one query for a whole page — are
# what somebody reading it needs, and they are three lines away there.
# ---------------------------------------------------------------------------

from .favourites import Favourite  # noqa: E402,F401  (registration import)
