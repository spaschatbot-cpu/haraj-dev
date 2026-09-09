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

from apps.core import uploads

from .states import AuctionState, VehicleState

__all__ = [
    "Auction",
    "Showcase",
    "AuctionState",
    "FuelType",
    "PlateType",
    "Transmission",
    "Vehicle",
    "VehicleCondition",
    "VehicleImage",
    "VehicleState",
]


class Showcase(models.TextChoices):
    """عرضُ المزاد قبل أن يبدأ — لافتةٌ لا مرحلةُ حياة.

    الثلاثةُ من `auctions.status` في v1، وهي هناك مختلطةٌ بالحالة. وهنا
    مفصولة: `AuctionState` تقول أين المزاد من دورته، وهذه تقول ماذا يرى
    العميل قبل انطلاقه.
    """

    LATER = "later", "لاحقاً — مخفيّ عن العملاء"
    UPCOMING = "upcoming", "قادم — معلَن بلا عدّاد"
    SOON = "soon", "قريباً — معلَن بعدّاد"


class Auction(models.Model):
    number = models.PositiveIntegerField(unique=True, help_text="رقم المزاد المعروض")
    title = models.CharField(max_length=200)

    #: الموقع كما يعرضه كرت v1: «الرياض / طريق الحائر».
    #
    # على **المزاد** لا على المركبة، وذلك مقيس: كل صفٍّ في صفحة الإنتاج الحيّة
    # يحمل الموقع نفسه. فمزادٌ يقع في ساحةٍ واحدة، ونسخُ النصّ على كل مركبة
    # يعني ثلاثة عشر ألف نسخةٍ من قيمةٍ واحدة — وثلاثة عشر ألف موضعٍ تختلف
    # فيه عن أختها يوم يُصحَّح اسم الطريق.
    location = models.CharField(max_length=200, blank=True)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    #: كيف يُعرض المزاد على العميل **قبل أن يبدأ** — T846.
    #
    # v1 يخلط هذا بالحالة: `later` و`upcoming` و`soon` ثلاثُ قيمٍ في العمود
    # `status` نفسه الذي يحمل `active` و`ended`. وهي ليست مراحلَ حياة بل
    # **طرقَ عرض** لمزادٍ واحدٍ لم يبدأ: مخفيّ، أو معلَن بلا عدّاد، أو معلَن
    # بعدّاد. وخلطُها بالحالة يعني أن نقل مزادٍ من «لاحقاً» إلى «قادم» يمرّ
    # بآلة الحالات ويوقظ التسوية والبوّابة — وهو تغييرُ لافتةٍ لا أكثر.
    #
    # فالحالةُ تبقى واحدةً (`SCHEDULED`)، والعرضُ عمودٌ بجانبها. والبادج على
    # الشاشة يجمعهما في كلمةٍ واحدة عبر `engine.showcase_status`.
    showcase = models.CharField(
        max_length=16, choices=Showcase.choices, default=Showcase.UPCOMING
    )

    #: موعد رسائل التذكير قبل الانطلاق — `auctions.sms_reminder_time` في v1.
    #
    # حقلٌ يُخزَّن ولا يُرسل بنفسه: إرسالُ رسالةٍ إلى آلافٍ يكلّف مالاً لا
    # يُسترد، والمادة ٥-٢ تمنع مهمّةً مجدولة تُنفق بلا موافقةٍ صريحة. فهذا
    # موعدٌ مسجَّل، ومن يبنيه مُرسِلاً يقرأ هذا السطر أولاً.
    sms_reminder_at = models.DateTimeField(null=True, blank=True)

    state = models.CharField(
        max_length=16, choices=AuctionState.choices, default=AuctionState.DRAFT
    )

    #: متى أُدرج تذكيرُ هذا المزاد في الطابور — وهو ما يمنع إدراجَه مرّتين.
    #
    # `sms_reminder_at` يقول **متى**، ولا شيء في v1 ولا هنا كان يقول **هل
    # أُرسل**. فبلا هذا العمود يصير كلُّ ضغطٍ على «أرسل» دفعةً ثانية إلى الناس
    # أنفسهم — والرسالةُ الثانية تكلّف كالأولى ولا تُسترد.
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    #: What a bidder must have deposited to take part.
    deposit_required = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("10000.00")
    )

    #: «رسوم إدارية» على شاشة المزايدة في v1 — ٨٠٠ ر.س، وتُعرض معها
    #: «الرسوم + الضريبة (15%)».
    #
    # على **المزاد** لا على المركبة، ومقيسٌ من v1: العمود هناك
    # `auctions.fees` (`specs/004-data-migration/field-map.md`)، أي أن الرسم
    # خاصّيةُ مزادٍ لا خاصّيةُ سيارة. وهو غير `deposit_required`: التأمين
    # مبلغٌ **يُحجَز ويُردّ**، والرسم مبلغٌ **يُدفَع ولا يُردّ** — ودمجُهما
    # في عمودٍ واحد يجعل ردّ التأمين يردّ الرسم معه.
    admin_fee = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("800.00")
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
        """يفوّض إلى :mod:`apps.auctions.engine` — ولا يحسب الساعة هنا.

        كان هذا السطر يحسبها بنفسه، و`bidding/eligibility.py` يحسبها ثانيةً
        بفرعين، واللوحة لا تحسبها أصلاً وتعدّ `state=LIVE` وحدها. ثلاثةُ
        أجوبةٍ لسؤالٍ واحد، وقد اختلفت فعلاً: مزادٌ حالتُه `live` وانتهى وقتُه
        قبل تسع ساعات كان «جارياً» على اللوحة و«مضى» عند العميل.

        والاستيراد داخل الدالّة لا في رأس الملفّ: `engine` يستورد `models`،
        فاستيرادُه هنا في الأعلى دورةٌ مغلقة.
        """
        from .engine import is_open_for_bidding

        return is_open_for_bidding(self)


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


class VehicleColour(models.TextChoices):
    """لون المركبة — يعرضه كرت v1 ولم يكن عندنا حقلٌ له.

    المفردات مقروءةٌ من الإنتاج الحيّ لا مخترعة: `فضي` و`ذهبي` و`رمادي`
    و`ابيض` و`اسود` و`ازرق غامق` كلّها ظهرت في صفحةٍ واحدة. و`UNKNOWN` موجود
    لأن المجهول ليس لوناً يُخمَّن (المادة ٢-٣)، وثلاثة عشر ألف صفٍّ قادمة من
    v1 فيها ما لا لون له.
    """

    WHITE = "white", "أبيض"
    BLACK = "black", "أسود"
    SILVER = "silver", "فضي"
    GREY = "grey", "رمادي"
    BLUE = "blue", "أزرق"
    DARK_BLUE = "dark_blue", "أزرق غامق"
    RED = "red", "أحمر"
    GREEN = "green", "أخضر"
    GOLD = "gold", "ذهبي"
    BEIGE = "beige", "بيج"
    BROWN = "brown", "بني"
    YELLOW = "yellow", "أصفر"
    OTHER = "other", "لون آخر"
    UNKNOWN = "unknown", "غير محدد"


class VehicleCondition(models.TextChoices):
    """حالة المركبة — ووُسِّعت لتحمل وصف الضرر لا التشغيل وحده.

    كرت v1 يعرض هنا `حادث` و`حريق`، وهما وصفُ **ما أصابها**؛ وقيمنا الأصلية
    وصفُ **هل تسير**. والسؤالان مختلفان، ومعروضان في المكان نفسه.
    فوُسِّع التعداد بدل أن يُشقّ عمودان: عمودٌ واحد بمفرداتٍ أوسع يُقرأ في
    موضعٍ واحد، وعمودان يعنيان قراءتين وقاعدتين تتباعدان (المادة ٤-٥).
    وواسعٌ من البداية لأن ضيّقه هو ما يُجبر على هجرةٍ يوم تصل قيمةٌ سادسة
    (المادة ٣-٥).
    """

    RUNNING = "running", "تسير"
    NOT_RUNNING = "not_running", "لا تسير"
    ACCIDENT = "accident", "حادث"
    FIRE = "fire", "حريق"
    FLOOD = "flood", "غرق"
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


class PartnerDecision(models.TextChoices):
    """حُكمُ شريك التسويق على سيارته. الفراغُ يعني «لم يحكم بعد»."""

    ACCEPTED = "accepted", "قبل الشريك العرض"
    REJECTED = "rejected", "رفض الشريك العروض"


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
    #: اللون — يعرضه كرت v1 بين سنة الصنع والممشى.
    colour = models.CharField(
        max_length=16, choices=VehicleColour.choices, default=VehicleColour.UNKNOWN
    )

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

    # ------------------------------------------------------------------
    # الخمسةُ الباقية من شاشة سيارات المزاد في v1 — T853.
    #
    # كانت الشاشةُ عندنا تعرض ثلاثةَ عشرَ عموداً من ثمانيةَ عشر، والخمسةُ
    # الغائبة لم تكن قراراً بل نقصَ حقول. وهي في v1 على `auction_vehicles`
    # بأنواعها هذه، وتُنقل كما هي:
    #
    # **ولماذا نصٌّ حرٌّ لا تعدادات** في «حالة المحرّك» و«المفاتيح»: v1
    # يخزّنهما `varchar(100)` بلا قائمةٍ مغلقة، ولم تُقرأ قيمُهما الفعلية من
    # النسخة بعد. وتعدادٌ يُخترَع اليوم يرفض القيمةَ التي كتبها الموظّف أمس
    # (المادة ٢-٣: المجهول لا يُخمَّن). فحين تُقرأ المفردات تُضيَّق بهجرة.
    # ------------------------------------------------------------------

    #: رقم المطالبة — `auction_vehicles.claim_number` (varchar 60).
    claim_number = models.CharField(max_length=60, blank=True, db_index=True)

    #: شركة التأمين — `insurance_company` (varchar 255).
    insurance_company = models.CharField(max_length=255, blank=True)

    #: حالة المحرّك — `runs_status`. «تعمل / لا تعمل / تدور ولا تتحرّك».
    runs_status = models.CharField(max_length=100, blank=True)

    #: المفاتيح — `key_status`. «مفتاح واحد / مفتاحان / بلا مفتاح».
    key_status = models.CharField(max_length=100, blank=True)

    #: للتسويق — `is_marketing`. سيارةٌ تُعرض للدعاية لا للبيع في هذه الدورة.
    is_marketing = models.BooleanField(default=False)

    #: إخفاءٌ عن العملاء لا سحبٌ من المزاد — نظيرُ `status='coming'` في v1
    #: (`setVehicleVisibility`): السيارةُ تبقى في المزاد وحالتُها كما هي، لكنها
    #: تُطوى عن قوائم العموم. مستقلٌّ عن آلة الحالة عمداً: يُخفى ما هو تحت
    #: المزايدة دون لمس مزايداته، ويُظهَر بضغطةٍ ثانية. البوّابةُ الوحيدة التي
    #: تقرؤه هي `visibility.is_public`/`public_q`.
    is_hidden = models.BooleanField(default=False)

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

    #: حُكمُ شريك التسويق على سيارته — قرارٌ **غيرُ** قرارِ المنصّة.
    #
    # التعاونيةُ تودع السيارة عندنا وهي صاحبةُ القرار في قبول العرض عليها،
    # والمنصّةُ تُفوتر وتُشعر بعد ذلك. فهذان فاعلان اثنان وقراران اثنان، ولا
    # يُستدلّ على أحدهما بحالة المركبة: `awarded` تقول ما فعلته المنصّة، وهذه
    # تقول ما حكم به الشريك — وبينهما القفلُ في `partner_lock_reason`.
    #
    # v1 بنى القاعدة نفسها بعد حادثةٍ مكتوبةٍ في `PartnerVehicleLock`
    # (٢٠٢٦-٠٨-٢٢): قُبل عرضٌ بـ١٦٢٬٣٥٠ على مركبةِ شريكٍ وحقلُ قراره خالٍ، لأن
    # اللوحات القديمة تنادي خدمةَ القبول مباشرةً وهي لا تقرأ المركبة أصلاً.
    partner_decision = models.CharField(
        max_length=16, choices=PartnerDecision.choices, blank=True, default=""
    )
    partner_decided_at = models.DateTimeField(null=True, blank=True)
    partner_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="partner_rulings",
    )
    #: العرضُ الذي وافق عليه الشريك — قد يخالف الفائزَ النهائيّ لو نُقلت الترسية.
    partner_decision_bid = models.ForeignKey(
        "bidding.Bid",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="partner_rulings",
    )

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
            # HR-11 — السيارة الواحدة لا تدخل المزاد الواحد مرتين.
            #
            # في v1 كانت تُدخَل بلوتين مختلفين، فتُعرض مرتين ويزايد عليها
            # مزايدان مختلفان، ولا يُكتشف ذلك إلا عند الترسية.
            #
            # **والقيد جزئي، وذلك هو القرار.** الشاصي `blank=True` — تصل
            # مركبات بلا شاصي معروف. وقيدٌ كامل يقول إن مركبتين مجهولتَي
            # الشاصي في مزادٍ واحد نسخةٌ من بعضهما، وهو ادّعاء: المجهول ليس
            # قيمةً تتكرّر، ومنعُ الثانية يمنع إدخال أسطول لم تصل أوراقه بعد.
            #
            # فالفرادة على ما نعرفه، والفراغ يبقى فراغاً (نظير قاعدة v1
            # «ما لا يُثبَت لا يُخمَّن»).
            models.UniqueConstraint(
                fields=["auction", "vin"],
                condition=~Q(vin=""),
                name="one_vin_per_auction",
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

    #: `upload_to` is a callable from `apps.core.uploads`, not a path template,
    #: and that is the whole of T912's name half: a template keeps the
    #: uploader's own file name on the end, so `../../public/shell.php` and
    #: `car.png.php` are both a stored path away. The callable throws the
    #: submitted name away and mints one. `ops/checks/one_upload_gate.py`
    #: refuses any file field on the project that does not use one.
    image = models.ImageField(upload_to=uploads.vehicle_image_path)

    #: Generated on upload and stored on disk next to the original. A list of
    #: fifty cars must never touch the full-size files: in v1 the bottleneck
    #: was never the request count, it was 50 × 3 MB of JPEG.
    thumbnail = models.ImageField(upload_to=uploads.vehicle_thumbnail_path, blank=True)

    #: The middle tier (HR-12). Without it a detail screen has two choices —
    #: enlarge the 400px card thumbnail, or fetch the original — and the second
    #: is the 13 GB incident on the screen a customer stays on longest.
    preview = models.ImageField(upload_to=uploads.vehicle_preview_path, blank=True)

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
