"""محرّك المزاد — سؤالٌ واحد عن المزاد، وجوابٌ واحد تقرؤه كل الشاشات. T843.

المالك بالحرف: «المحرك الاساسي للمزاد يكون زي العربية كده — محرك واحد للمزاد
والصفحات كلها بتخدم عليه بدل ما تقعد تكرر أكتر من اسكريبت».

ما هذا الملفّ، وما ليس هو
=========================
ليس كتابةً ثانية لما هو مكتوب. الكتابةُ في الحالات تبقى في
:mod:`apps.auctions.services` وحدها (يحرسها `auction_state_single_writer`)،
وبوابةُ المزايدة تبقى في :mod:`apps.bidding.eligibility` وحدها (يحرسها
`one_eligibility_gate`)، والمالُ يبقى في :mod:`apps.money`. هذا الملفّ **يملك
الأسئلة** ويوجّهها إلى كاتبيها، ويملك بنفسه سؤالاً واحداً لم يكن يملكه أحد:

    **أين المزاد من الساعة الآن؟**

وذلك السؤال كان مكرَّراً ثلاث مرّاتٍ متضاربة، مقيساً
=================================================
قبل هذا الملفّ، ثلاثة مواضع تجيب عليه ولا تتّفق:

1. ``Auction.is_open_for_bidding`` (models.py) —
   ``state == LIVE and starts_at <= now < ends_at``. تحسب الساعة.
2. ``bidding/eligibility.py`` — فرعان منفصلان يعيدان بناء الشرط نفسه بيدٍ
   أخرى، وينتجان سببَي رفضٍ مختلفين.
3. لوحةُ الإدارة — ``dashboard.py`` و``analytics.py`` و``catalog.py``
   و``partner_console.py`` تعدّ ``state=LIVE`` **بلا أيّ نظرٍ إلى الساعة**.

فالثالث يقول «جارٍ» عن مزادٍ انتهى وقتُه ولم يُغلَق بعد؛ وقد رأيناه في هذه
القاعدة نفسها: مزادٌ في الحالة ``live`` ونهايتُه قبل تسع ساعات، فالعدّاد على
واجهة العميل يقول «مضى» واللوحة تقول «جارٍ» — وكلاهما يقرأ الصفّ نفسه.

والفارق ليس تجميلاً: الحالةُ عمودٌ يكتبه عاملُ خلفيّة، والساعةُ لا تنتظر
العامل. فبين لحظة الانتهاء ولحظة كتابة العمود توجد فجوةٌ يجب أن يكون لها
**اسم** بدل أن تُقرأ في كل شاشةٍ على هواها. اسمُها هنا
:attr:`Phase.OVERDUE_END`، ووجودُ اسمٍ لها هو ما يجعل اللوحة تعرضها تنبيهاً
لا حالةً عاديّة.

المزاد مُجمَّع، والتأمين واحد
=============================
المالك بالحرف: «مزاد مجمع وداخله مجموعة من السيارات. المزاد الواحد مطلوب
عشان المشاركة فيه تأمين واحد للمزايدة فيه حتى لو هيزايد على كل السيارات اللي
فيه. ولو زايد وكسب سيارات، السيارات تتربط بالتأمين ده — يعني فواتير المزاد
الواحد تتربط برده بنفس التأمين بتاعه بعد اتخاذ القرار».

وهذا مضمونٌ في القاعدة لا في الشيفرة: ``one_active_hold_per_customer_and_auction``
يجعل الحجزَ الثاني على المزاد نفسه مستحيلاً. فالربط الذي يطلبه المالك
**مشتَقٌّ ووحيد**، لا عمودٌ جديد:

    فاتورة → مركبة → مزاد → (صاحب الفاتورة، المزاد) → حجزٌ واحد

وعمودٌ ثانٍ يحمل الجواب نفسه هو موضعُ قرارٍ ثانٍ (المادة ٤-٥): يوم يختلف عن
السلسلة لا يقول أحدٌ أيّهما الصحيح. فالسلسلة تُقرأ هنا في
:func:`deposit_behind` و:func:`participants`، وتُعرَض على الشاشة، ولا تُنسَخ.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone

from .models import Auction, Vehicle, VehicleImage
from .states import AUCTION_MOVES, AuctionState, VehicleState

ZERO = Decimal("0.00")


# ---------------------------------------------------------------------------
# ١ — الساعة: الموضع الوحيد الذي يقارن `starts_at`/`ends_at` بالآن
# ---------------------------------------------------------------------------


class Phase(models.TextChoices):
    """أين المزاد من الساعة **ومن الحالة معاً**.

    ست حالاتٍ مخزَّنة، وثمانِ مراحل: المرحلتان الزائدتان هما الفجوتان بين
    ما يقوله العمود وما تقوله الساعة، ولهما اسمٌ عمداً.

    ``OVERDUE_START`` مزادٌ مجدولٌ حان وقتُه ولم يبدأ بعد — عاملُ الخلفية
    متأخّر، أو متوقّف. و``OVERDUE_END`` مزادٌ حالتُه ``live`` وانتهى وقتُه —
    وهذه الأخطر، لأن كل شاشةٍ تعدّ ``state=LIVE`` تعرضه «جارياً» ولا مزايدةَ
    فيه تُقبل: البوّابة ترفض، والعدّاد يقول «مضى»، واللوحة وحدها تقول إنه شغّال.
    """

    DRAFT = "draft", "مسودة"
    SCHEDULED = "scheduled", "مجدول"
    OVERDUE_START = "overdue_start", "حان وقته ولم يبدأ"
    # القيمة `open_for_bidding` لا `open`: خريطةُ النغمات في اللوحة
    # (`console/tones.py`) مفتاحُها القيمةُ المجرّدة، وفيها `open` بالفعل
    # بمعنى «فاتورةٌ مستحقّة». وقيمتان بمعنيين متضادّين تحت مفتاحٍ واحد تجعل
    # المزادَ المفتوح يُرسم بلون الدَّين. وبقيّةُ المراحل تتقاسم قيمَ
    # `AuctionState` عمداً — هناك المعنى واحد.
    OPEN = "open_for_bidding", "مفتوح للمزايدة"
    OVERDUE_END = "overdue_end", "انتهى وقته ولم يُغلَق"
    ENDED = "ended", "منتهٍ"
    SETTLED = "settled", "مُسوّى"
    CANCELLED = "cancelled", "ملغى"


def has_started(auction: Auction, *, now: datetime | None = None) -> bool:
    """أَبلَغ المزادُ لحظةَ بدايته المعلنة؟ — بغضّ النظر عن عموده."""
    return auction.starts_at <= (now or timezone.now())


def has_finished(auction: Auction, *, now: datetime | None = None) -> bool:
    """أَبلَغ المزادُ لحظةَ نهايته المعلنة؟ — بغضّ النظر عن عموده."""
    return auction.ends_at <= (now or timezone.now())


#: المراحل التي تُقبل فيها المزايدة. واحدةٌ فقط، وذلك مقصود: `OVERDUE_END`
#: ليست منها، فالساعة تسبق العمود ولا يُقبل مالٌ بعد النهاية المعلنة.
BIDDABLE_PHASES = frozenset({Phase.OPEN})


def phase(auction: Auction, *, now: datetime | None = None) -> Phase:
    """المرحلة، من الحالة والساعة معاً — والموضع الوحيد الذي يجمع بينهما.

    كلُّ من يريد أن يعرف «هل المزاد شغّال» يسأل هنا. ومن قارن ``ends_at``
    بالآن في ملفٍّ آخر أنشأ جواباً ثانياً، ويرسبه
    ``ops/checks/one_auction_clock.py``.
    """
    now = now or timezone.now()
    state = auction.state

    if state == AuctionState.SCHEDULED:
        return Phase.OVERDUE_START if has_started(auction, now=now) else Phase.SCHEDULED

    if state == AuctionState.LIVE:
        if not has_started(auction, now=now):
            # حالةٌ لا يصنعها الانتقالُ الشرعيّ (`_auction_start_time_reached`
            # يمنعها)، لكنها تُصنَع بتحريك `starts_at` إلى المستقبل على مزادٍ
            # جارٍ من شاشة التعديل. وقراءتُها «مفتوحاً» تقبل مزايدةً قبل
            # موعدها المعلن.
            return Phase.SCHEDULED
        return Phase.OVERDUE_END if has_finished(auction, now=now) else Phase.OPEN

    return Phase(state)


def is_open_for_bidding(auction: Auction, *, now: datetime | None = None) -> bool:
    """هل تُقبل مزايدةٌ على هذا المزاد الآن؟ سؤالُ نعم/لا، وجوابُه المرحلة."""
    return phase(auction, now=now) in BIDDABLE_PHASES


#: المراحل التي تستحقّ تنبيهاً على شاشة الموظّف: العمود والساعة لا يتّفقان.
LATE_PHASES = frozenset({Phase.OVERDUE_START, Phase.OVERDUE_END})


def is_late(auction: Auction, *, now: datetime | None = None) -> bool:
    """تأخّر عاملُ الخلفية عن هذا المزاد — لا عطلٌ في المزاد نفسه."""
    return phase(auction, now=now) in LATE_PHASES


# ---------------------------------------------------------------------------
# ٢ — المُجمَّع: ما في المزاد، ومن دخله، وبأيّ تأمين
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VehicleTally:
    """عدُّ مركبات المزاد بحالاتها — استعلامٌ واحد، لا استعلامٌ لكل حالة.

    الشاشة تعرض ستّ أرقامٍ على الأقلّ (معروضة، تحت المزايدة، تنتظر قراراً،
    مرسّاة، مفوترة، مسدَّدة). ستةُ ``.count()`` هي ستةُ ذهاباتٍ إلى القاعدة
    لصفحةٍ واحدة، وكانت ثلاثٌ منها مكتوبةً بالفعل في ثلاث شاشاتٍ مختلفة.
    """

    total: int = 0
    by_state: dict[str, int] = field(default_factory=dict)

    def of(self, state: str) -> int:
        return self.by_state.get(state, 0)

    @property
    def awaiting_decision(self) -> int:
        return self.of(VehicleState.AWAITING_DECISION)

    @property
    def awarded(self) -> int:
        return self.of(VehicleState.AWARDED)

    @property
    def sold(self) -> int:
        """ما خرج من المزاد ببيعٍ فعليّ — مرسّاةً كانت أو مفوترةً أو مسدَّدة."""
        return sum(
            self.of(state)
            for state in (
                VehicleState.AWARDED,
                VehicleState.INVOICED,
                VehicleState.PAID,
                VehicleState.RELEASED,
            )
        )


def tally(auction: Auction) -> VehicleTally:
    rows = (
        Vehicle.objects.filter(auction=auction)
        .values("state")
        .annotate(n=Count("id"))
        .order_by()
    )
    by_state = {row["state"]: row["n"] for row in rows}
    return VehicleTally(total=sum(by_state.values()), by_state=by_state)


def deposit_of(customer, auction: Auction):
    """حجزُ هذا العميل على هذا المزاد — واحدٌ أو لا شيء.

    «واحدٌ» ليست أملاً حسن النيّة: ``one_active_hold_per_customer_and_auction``
    قيدٌ في القاعدة يجعل الثاني مستحيلاً، وهو ما يطلبه المالك حرفياً — تأمينٌ
    واحد للمزاد مهما بلغ عدد السيارات التي يزايد عليها أو يكسبها.
    """
    from apps.money.models import Hold, HoldState

    return (
        Hold.objects.filter(owner=customer, auction=auction, state=HoldState.ACTIVE)
        .select_related("owner")
        .first()
    )


def deposit_behind(invoice):
    """التأمينُ الذي تقف خلفه هذه الفاتورة — بالسلسلة لا بعمودٍ ثانٍ.

    فاتورة → مركبة → مزاد → (صاحب الفاتورة، المزاد) → حجز. وكلُّ خطوةٍ فيها
    مضمونةُ الوحدانيّة بقيدٍ في القاعدة: ``one_live_invoice_per_vehicle``،
    و``Vehicle.auction`` مفتاحٌ واحد، و``one_active_hold_per_customer_and_auction``.

    فتُعيد ``None`` عن فاتورةٍ لا مركبة لها (فاتورةُ مستحقاتٍ عامّة)، وعن
    فاتورةٍ فُكّ حجزُها بعد السداد — والثانية ليست عطلاً بل نهايةَ الدورة.
    """
    vehicle = invoice.vehicle
    if vehicle is None:
        return None
    return deposit_of(invoice.customer, vehicle.auction)


@dataclass(frozen=True)
class Participant:
    """عميلٌ واحد داخل مزادٍ واحد: تأمينُه، وما كسبه، وما فُوتر عليه.

    هذا هو المُجمَّع كما وصفه المالك، مقروءاً في صفٍّ واحد: التأمينُ عمودٌ
    واحد مهما بلغ عدد السيارات، والفواتيرُ تحته لا بجانبه.
    """

    customer: object
    hold: object | None
    held_amount: Decimal
    won: list[Vehicle]
    invoices: list[object]

    #: ما بقي عليه — يحسبه **محرّك المال** لا هذا الملفّ.
    #:
    #: `Invoice.outstanding` تعرف أن الملغاة صفر وأن المدفوع لا يتجاوز
    #: المبلغ، وطرحُ العمودين هنا ينسى الشرطين يوم يتغيّران. و`unpaid` لا
    #: `outstanding` اسماً: الثانية مفردةٌ من قاموس البوّابة، واستعارتُها
    #: تجعل قارئاً يظنّ أن هذا الصفَّ يقرّر منعاً — وهو لا يقرّر شيئاً.
    unpaid: Decimal = ZERO

    @property
    def won_total(self) -> Decimal:
        return sum((car.awarded_price or ZERO for car in self.won), ZERO)

    @property
    def invoiced_total(self) -> Decimal:
        return sum((invoice.amount for invoice in self.invoices), ZERO)


    @property
    def has_deposit(self) -> bool:
        return self.hold is not None


def participants(auction: Auction) -> list[Participant]:
    """كلُّ من له تأمينٌ قائم في هذا المزاد أو كسب فيه سيارة.

    «أو» لا «و» عمداً: من كسب سيارةً وسُدِّدت فاتورتُها فُكّ حجزُه، فحصرُ
    القائمة على أصحاب الحجوز يُخفي المشترين الذين أتمّوا — وهم بالضبط من
    يسأل عنهم الموظّف في شاشة ما بعد البيع. ومن له حجزٌ ولم يكسب شيئاً يبقى
    في القائمة لأن ماله محجوزٌ وسؤال «لماذا» له جوابٌ هنا.
    """
    from apps.money.models import Hold, HoldState, Invoice

    holds = list(
        Hold.objects.filter(auction=auction, state=HoldState.ACTIVE).select_related(
            "owner"
        )
    )
    won = list(
        Vehicle.objects.filter(auction=auction, awarded_to__isnull=False)
        .select_related("awarded_to")
        .order_by("lot_number")
    )
    invoices = list(
        Invoice.objects.filter(vehicle__auction=auction)
        .exclude(state="cancelled")
        .select_related("customer", "vehicle")
        .order_by("issued_at")
    )

    people: dict[int, object] = {}
    for hold in holds:
        people[hold.owner_id] = hold.owner
    for vehicle in won:
        people.setdefault(vehicle.awarded_to_id, vehicle.awarded_to)
    for invoice in invoices:
        people.setdefault(invoice.customer_id, invoice.customer)

    by_owner = {hold.owner_id: hold for hold in holds}

    unpaid = (
        Invoice.objects.filter(vehicle__auction=auction)
        .exclude(state="cancelled")
        .unpaid_by_customer()
    )

    rows = [
        Participant(
            customer=customer,
            hold=by_owner.get(pk),
            held_amount=by_owner[pk].amount if pk in by_owner else ZERO,
            won=[car for car in won if car.awarded_to_id == pk],
            invoices=[bill for bill in invoices if bill.customer_id == pk],
            unpaid=unpaid.get(pk, ZERO),
        )
        for pk, customer in people.items()
    ]
    # الأكبر مالاً أولاً: الموظّف يفتح هذه الشاشة ليجد من عليه أكثر ما لم يُسدَّد.
    rows.sort(key=lambda row: (-row.unpaid, -row.held_amount, str(row.customer)))
    return rows


def money_held_in(auction: Auction) -> Decimal:
    """مجموعُ التأمينات المحجوزة على هذا المزاد الآن."""
    from apps.money.models import Hold, HoldState

    total = Hold.objects.filter(auction=auction, state=HoldState.ACTIVE).aggregate(
        total=Sum("amount")
    )["total"]
    return total if total is not None else ZERO


# ---------------------------------------------------------------------------
# ٢ب — ملخّصُ الصفّ: الأعمدة التي تعرضها شاشةُ إدارة المزادات في v1
# ---------------------------------------------------------------------------
#
# المالك بالحرف: «عايز نفس الحقول، و اتأكد من المنطق التشغيلي بتاع كل حقل».
# فكلُّ حقلٍ أدناه مقروءٌ من قاعدة v1 الحقيقية (نسخة 2026-09-05)، لا من صورة
# الشاشة: الصورةُ تقول «٦٨٣ سيارة» ولا تقول من أين، والعمودُ يقول.
#
# ولماذا **ثلاثةُ استعلاماتٍ تُدمَج في بايثون** لا `annotate` واحدة:
# `Vehicle` و`VehicleImage` و`Bid` ثلاثةُ فروعٍ متعدّدة على المزاد الواحد،
# وجمعُها في `annotate` واحدة يضرب الصفوف بعضَها في بعض — فتصير «٣٠٠ صورة»
# ثلاثَ آلاف لأن لكل سيارةٍ عشرَ صورٍ وعشرَ مزايدات. و`distinct=True` يُصلح
# العدّ ولا يُصلح `Sum` ولا `Max`. فثلاثةُ استعلاماتٍ مجمَّعة، عددُها ثابتٌ
# مهما بلغ عدد المزادات في الصفحة.


#: حالاتُ المركبة التي تعني «معروضة على العميل الآن» — عمود «التفعيل» في v1.
#:
#: في v1 كان `auction_vehicles.activation_status` عموداً نصّياً بثلاث قيم
#: (`active` · `not active` · `soon`) يُكتب بيد الموظّف **بجانب** حالة
#: السيارة، فيختلفان: سيارةٌ `activation_status='active'` وقد رست على مشترٍ
#: منذ أسبوع. هنا لا عمودَ ثانٍ — التفعيل مشتقٌّ من الحالة الواحدة.
OFFERED_STATES = frozenset({VehicleState.LISTED, VehicleState.BIDDING})


@dataclass(frozen=True)
class RowSummary:
    """ما يُعرض عن مزادٍ واحد في صفٍّ من قائمة الإدارة."""

    cars: int = 0
    makes: int = 0
    top_makes: tuple[str, ...] = ()

    #: «متاحة» — معروضةٌ للعميل الآن.
    offered: int = 0
    #: «سعر مسجل» — لها سعرُ وقوفٍ مكتوب. وv1 يسمّيه «سعر افتتاحي».
    with_reserve: int = 0
    reserve_low: Decimal | None = None
    reserve_high: Decimal | None = None

    #: سيارةٌ **لها صورةٌ واحدة على الأقلّ**، وإجماليُّ الصور. الرقمان مختلفان
    #: عمداً: «٣١٠ سيارة · ٣٦٧٠ صورة» يقول إن التغطية كاملة، و«٣٠٠ من ٦٨٣»
    #: يقول إن نصف المزاد بلا صورة — وهو ما لا يقوله الإجماليّ وحده.
    cars_with_images: int = 0
    images: int = 0

    bids: int = 0
    bidders: int = 0
    top_bid: Decimal | None = None

    @property
    def images_missing(self) -> int:
        return max(self.cars - self.cars_with_images, 0)


def summarise(auctions) -> dict[int, RowSummary]:
    """ملخّصُ كل مزادٍ في هذه الصفحة — ثلاثةُ استعلاماتٍ لا أكثر.

    ``auctions`` صفوفُ **الصفحة** لا الاستعلام كلّه: صفحةٌ من خمسة وعشرين لا
    تحتاج ملخّصَ ستّةٍ وخمسين مزاداً، وv1 كان يحسبها كلَّها في كل تحميل.
    """
    from apps.bidding.models import Bid

    ids = [auction.pk for auction in auctions]
    if not ids:
        return {}

    cars: dict[int, dict] = {pk: {} for pk in ids}

    # ١ — المركبات: العدد، والماركات، والمتاحة، والمسعَّرة، ومدى السعر.
    for row in (
        Vehicle.objects.filter(auction_id__in=ids)
        .values("auction_id")
        .annotate(
            cars=Count("id"),
            makes=Count("make", distinct=True),
            offered=Count("id", filter=Q(state__in=OFFERED_STATES)),
            with_reserve=Count("id", filter=Q(reserve_price__isnull=False)),
            reserve_low=Min("reserve_price"),
            reserve_high=Max("reserve_price"),
        )
        .order_by()
    ):
        cars[row.pop("auction_id")].update(row)

    # ٢ — الصور: كم سيارةً لها صورة، وكم صورةً في المزاد كلّه.
    for row in (
        VehicleImage.objects.filter(vehicle__auction_id__in=ids)
        .values("vehicle__auction_id")
        .annotate(images=Count("id"), cars_with_images=Count("vehicle_id", distinct=True))
        .order_by()
    ):
        cars[row.pop("vehicle__auction_id")].update(row)

    # ٣ — المزايدات: العدد، والمزايدون، وأعلى رقم.
    #
    # `Bid.objects.live()` لا شرطٌ مكتوبٌ هنا: هي التعريفُ الواحد لِما «ما
    # زال قائماً»، وهي نفسُ العمودين اللذين يُبنى عليهما القيدُ في القاعدة.
    # وv1 كان يعدّ الصفوف كلَّها فيقول «٦٥١٨ مزايدة» وفيها مسحوبةٌ ومتجاوَزة —
    # فيُقرأ الرقم نشاطاً وهو ليس كذلك، و«أعلى» يُعلن رقماً لا يشتري به أحد.
    for row in (
        Bid.objects.live().filter(vehicle__auction_id__in=ids)
        .values("vehicle__auction_id")
        .annotate(
            bids=Count("id"),
            bidders=Count("bidder_id", distinct=True),
            top_bid=Max("amount"),
        )
        .order_by()
    ):
        cars[row.pop("vehicle__auction_id")].update(row)

    # ٤ — أشهرُ ماركتين، لأن «١٩٢ ماركة» رقمٌ لا يصف مزاداً. استعلامٌ رابع
    # ولكنّه مجمَّعٌ أيضاً، ويُقصَر على ماركتين لكل مزاد في بايثون.
    ranked: dict[int, list[str]] = {pk: [] for pk in ids}
    for row in (
        Vehicle.objects.filter(auction_id__in=ids)
        .values("auction_id", "make")
        .annotate(n=Count("id"))
        .order_by("auction_id", "-n", "make")
    ):
        bucket = ranked[row["auction_id"]]
        if len(bucket) < 2 and row["make"]:
            bucket.append(row["make"])

    return {
        pk: RowSummary(top_makes=tuple(ranked[pk]), **fields)
        for pk, fields in cars.items()
    }


def summarise_onto(auctions) -> None:
    """يعلّق ``.summary`` على كل صفٍّ — للقالب، بلا استعلامٍ في حلقة."""
    rows = summarise(auctions)
    for auction in auctions:
        auction.summary = rows.get(auction.pk, RowSummary())


# ---------------------------------------------------------------------------
# ٣ — العمليّات: ما يجوز فعله بالمزاد الآن، ولماذا لا يجوز غيره
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Operation:
    """نقلةٌ معروضة على الشاشة، ومعها إن كانت ممكنةً الآن ولماذا لا.

    الشاشةُ لا تقرّر. كانت ``auction_detail`` تبني قائمة النقلات بنفسها،
    و``auctions_bulk`` تبنيها ثانيةً بشرطٍ مختلف، و``partner_console`` ثالثةً
    — وثلاثتُها تقرأ الجدول نفسه بثلاث قراءات. هنا قراءةٌ واحدة، ومعها
    الجوابُ عن «لماذا الزرّ مطفأ» بدل زرٍّ يعمل ثم يرمي رسالة خطأ.
    """

    target: str
    label: str
    why: str
    allowed: bool
    blocked_by: str = ""


def operations(auction: Auction, *, now: datetime | None = None) -> list[Operation]:
    now = now or timezone.now()
    out: list[Operation] = []
    for move in AUCTION_MOVES:
        if move.source != auction.state:
            continue
        blocked = move.guard(auction, now) if move.guard else None
        out.append(
            Operation(
                target=move.target,
                label=AuctionState(move.target).label,
                why=move.why,
                allowed=blocked is None,
                blocked_by=blocked or "",
            )
        )
    return out


# ---------------------------------------------------------------------------
# ٤ — اللقطة: كلُّ ما تعرضه شاشةُ مزادٍ واحد، في نداءٍ واحد
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Snapshot:
    auction: Auction
    phase: Phase
    is_open: bool
    is_late: bool
    cars: VehicleTally
    held: Decimal
    operations: list[Operation]

    @property
    def phase_label(self) -> str:
        return Phase(self.phase).label


def snapshot(auction: Auction, *, now: datetime | None = None) -> Snapshot:
    """المزاد كما تعرضه أيّ شاشة. أربعةُ استعلاماتٍ ثابتة مهما كبر المزاد."""
    now = now or timezone.now()
    current = phase(auction, now=now)
    return Snapshot(
        auction=auction,
        phase=current,
        is_open=current in BIDDABLE_PHASES,
        is_late=current in LATE_PHASES,
        cars=tally(auction),
        held=money_held_in(auction),
        operations=operations(auction, now=now),
    )


# ---------------------------------------------------------------------------
# ٥ — القوائم: نفس الجواب على مستوى الاستعلام
# ---------------------------------------------------------------------------


def open_now(queryset=None, *, now: datetime | None = None):
    """المزادات المفتوحة فعلاً — بالحالة **والساعة**.

    هذه هي التي كانت اللوحةُ تكتبها ``filter(state=LIVE)`` في أربعة ملفّات،
    فتعدّ مزاداً انتهى وقته ولم يُغلَق بعدُ ضمن «الجارية».
    """
    now = now or timezone.now()
    rows = Auction.objects.all() if queryset is None else queryset
    return rows.filter(state=AuctionState.LIVE, starts_at__lte=now, ends_at__gt=now)


def due_to_start(queryset=None, *, now: datetime | None = None):
    """مزاداتٌ مجدولةٌ بلغت لحظةَ بدايتها ولم تُفتَح — أي :attr:`Phase.OVERDUE_START`.

    نُقلت من ``services.due_to_activate``: هي والمرحلةُ سؤالٌ واحد، وكان
    مكتوباً مرّتين. والكاتبُ يبقى ``services.activate_due`` — هذه تسأل ولا تكتب.
    """
    now = now or timezone.now()
    rows = Auction.objects.all() if queryset is None else queryset
    return rows.filter(state=AuctionState.SCHEDULED, starts_at__lte=now)


def due_to_finish(queryset=None, *, now: datetime | None = None):
    """مزاداتٌ جاريةٌ بلغت لحظةَ نهايتها ولم تُغلَق — أي :attr:`Phase.OVERDUE_END`."""
    now = now or timezone.now()
    rows = Auction.objects.all() if queryset is None else queryset
    return rows.filter(state=AuctionState.LIVE, ends_at__lte=now)


def due_to_settle(queryset=None, *, now: datetime | None = None):
    """مزاداتٌ انتهت ولم تُسوَّ — طابورُ عاملِ التسوية.

    الشرطُ الزمنيّ ليس زائداً وإن بدا كذلك: الانتقالُ إلى ``ended`` يشترط
    بلوغَ لحظة النهاية، **لكن** شاشة التعديل تستطيع تحريك ``ends_at`` إلى
    المستقبل على مزادٍ منتهٍ، وتسويةُ مزادٍ موعدُه لم يحن تفكّ تأميناتٍ
    وتُصدر فواتير قبل أوانها. فيبقى الشرط، ويُقرأ من هنا لا من عاملِ الخلفية.
    """
    now = now or timezone.now()
    rows = Auction.objects.all() if queryset is None else queryset
    return rows.filter(state=AuctionState.ENDED, ends_at__lte=now)


def late_now(queryset=None, *, now: datetime | None = None):
    """المزادات التي تخلّف عنها عاملُ الخلفية — بدءاً أو إغلاقاً.

    شاشةُ صحّةٍ لا تجميل: صفٌّ هنا يعني أن Celery متوقّف أو متأخّر، وأن
    عميلاً يرى «جارٍ» على مزادٍ لا تُقبل فيه مزايدة.
    """
    now = now or timezone.now()
    rows = Auction.objects.all() if queryset is None else queryset
    return rows.filter(
        Q(pk__in=due_to_start(rows, now=now)) | Q(pk__in=due_to_finish(rows, now=now))
    )


def phases_of(auctions: Iterable[Auction], *, now: datetime | None = None) -> None:
    """يعلّق ``.phase`` و``.is_late`` على كل صفٍّ في القائمة، بلا استعلام.

    للقوالب: ``{{ row.phase_label }}`` بدل ``{{ row.get_state_display }}``
    الذي يقول «جارٍ» عن مزادٍ مضى وقتُه.
    """
    now = now or timezone.now()
    for auction in auctions:
        current = phase(auction, now=now)
        auction.phase = current
        auction.phase_label = Phase(current).label
        auction.is_late = current in LATE_PHASES


__all__ = [
    "BIDDABLE_PHASES",
    "LATE_PHASES",
    "OFFERED_STATES",
    "Operation",
    "Participant",
    "Phase",
    "RowSummary",
    "Snapshot",
    "VehicleTally",
    "deposit_behind",
    "deposit_of",
    "due_to_finish",
    "due_to_settle",
    "due_to_start",
    "has_finished",
    "has_started",
    "is_late",
    "is_open_for_bidding",
    "late_now",
    "money_held_in",
    "open_now",
    "operations",
    "participants",
    "phase",
    "phases_of",
    "snapshot",
    "summarise",
    "summarise_onto",
    "tally",
]
