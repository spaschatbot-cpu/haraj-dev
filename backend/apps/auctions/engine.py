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
السلسلة لا يقول أحدٌ أيّهما الصحيح. فالسلسلة موجودةٌ في القاعدة، ولا تُقرأ
هنا: عرضُ أموال العملاء — تأميناتٍ وفواتيرَ وأرصدة — له شاشاتُه المخصّصة في
:mod:`apps.money` و:mod:`apps.bidding`، وإخراجُه في شاشة المزاد كان يكسر
تصميم الصلاحيات (من يملك `auctions.view` يرى أرصدةً لا تخصّه). فحُذفت
``participants`` و``deposit_behind`` من هذا المحرّك في T849، وبقي هنا سؤالُ
المزاد عن نفسه: ساعتُه، ومركباتُه، وما يجوز فعله به.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.db.models import Count, Max, Min, Q
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


def window_is_valid(auction: Auction) -> bool:
    """أنهايتُه بعد بدايته؟ — سؤالٌ عن الموعدين، لا عن الساعة.

    وهو هنا مع أسئلة الساعة لا في الشاشة التي تسأله: القيد
    `auction_ends_after_it_starts` هو الضمانة، وهذه قراءتُه قبل الحفظ ليقرأ
    الموظّف جملةً بدل صفحة خطأ ٥٠٠. وموضعُ القراءة واحدٌ لأن أيَّ شاشةٍ
    تكتبه بيدها تكتب `<` حيث يجب `<=` يوماً، فتقبل مزاداً طولُه صفر.
    """
    return auction.ends_at > auction.starts_at


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


# ---------------------------------------------------------------------------
# ١ب — البادج: مفرداتُ v1 الخمس، محسوبةً لا مخزَّنة
# ---------------------------------------------------------------------------


class Badge(models.TextChoices):
    """ما يظهر في خانة «الحالة» — خمسُ كلماتٍ كما في v1، وسادسةٌ للملغى.

    v1 يخزّنها في عمودٍ واحد، فيخلط **دورةَ الحياة** بـ**لافتة العرض**:
    نقلُ مزادٍ من «لاحقاً» إلى «قادم» هناك كتابةٌ في العمود نفسه الذي تقرؤه
    التسويةُ والبوّابة. وهنا تُحسب من ثلاثة: الحالة، والساعة، ولافتةُ العرض.

    وسابعةٌ لا يعرفها v1 ولا تُخفى: `LATE` — انتهى وقتُه ولم يُغلَق، أو حان
    ولم يبدأ. هي حالةُ عاملِ الخلفية لا حالةُ المزاد، ولها في القالب حبّةٌ
    ثانية بجانب الأولى لا بدلاً منها.
    """

    LATER = "later", "لاحقاً"
    UPCOMING = "upcoming", "قادم"
    SOON = "soon", "قريباً"
    ACTIVE = "active", "نشط"
    ENDED = "ended", "منتهٍ"
    CANCELLED = "cancelled", "ملغى"
    DRAFT = "draft", "مسودة"


def badge_of(auction: Auction, *, now: datetime | None = None) -> Badge:
    """كلمةُ الحالة كما يراها الموظّف — من الحالة والساعة واللافتة معاً."""
    current = phase(auction, now=now)

    if current in (Phase.OPEN, Phase.OVERDUE_END):
        # `OVERDUE_END` تُعرض «نشطاً» لأن الحالة المخزَّنة ما زالت كذلك،
        # وحبّةُ «متأخّر» بجانبها هي التي تقول إن العامل لم يلحق. وإخفاؤها
        # هنا يجعل الموظّف يبحث عن مزادٍ اختفى من القائمة.
        return Badge.ACTIVE
    if current in (Phase.ENDED, Phase.SETTLED):
        return Badge.ENDED
    if current == Phase.CANCELLED:
        return Badge.CANCELLED
    if current == Phase.DRAFT:
        return Badge.DRAFT
    return Badge(auction.showcase)


#: البادج إلى نغمةِ الحبّة. هنا لا في `console/tones.py` لأن `ended` و`draft`
#: و`cancelled` مفرداتٌ مشتركة مع الفواتير والمركبات، وثلاثتُها تعني هنا
#: شيئاً آخر — و`active` ليست حالةً مخزَّنة أصلاً.
BADGE_TONES: dict[str, str] = {
    Badge.LATER: "",
    Badge.UPCOMING: "info",
    Badge.SOON: "warn",
    Badge.ACTIVE: "ok",
    Badge.ENDED: "",
    Badge.CANCELLED: "bad",
    Badge.DRAFT: "",
}


def tick(*, now: datetime | None = None) -> dict[str, list[int]]:
    """يُلحق ما تخلّف عنه عاملُ الخلفية — نداءٌ خفيفٌ عند فتح القائمة.

    **لا يستبدل Celery ولا يكرّره:** يستدعي `services.activate_due` و
    `end_due` نفسَيهما، فالكاتبُ يبقى واحداً (يحرسه
    `auction_state_single_writer`). وهو هنا لأن الموظّف لا يحتمل أن يفتح
    الشاشة فيرى «قريباً» على مزادٍ بدأ قبل دقيقتين لأن العامل متوقّف —
    ولأن العامل يتوقّف فعلاً.

    ويعمل بلا استعلامٍ في الحالة الشائعة: `due_to_start` و`due_to_finish`
    استعلامان بفهرسٍ على `(state, starts_at)` يعودان فارغين في أغلب النداءات.
    """
    from . import services

    return {
        "started": services.activate_due(now),
        "ended": services.end_due(now),
    }


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

    #: عيّنةٌ تعرّف المزاد بلمحة: «تويوتا كامري 2023».
    sample: str = ""

    #: **رابط** المصغّرة، لا بايتاتها.
    #:
    #: v1 كان يستعلم `TO_BASE64(image_blob)` فوق آلاف الصفوف لرسم مربّعٍ
    #: بـ50×38 بكسل، فتأخذ الصفحة ثماني ثوانٍ ويتجمّد الخادم. والصورةُ هنا
    #: مخزَّنةٌ ملفّاً أصلاً، ولها **طبقةُ مصغّرات** جاهزة (`VehicleImage.thumbnail`)
    #: — فالصفّ يحمل عنواناً نصّياً، والمتصفّح يجلبه كسولاً وبالتوازي ومن
    #: ذاكرته في المرّة الثانية. ولا بايت صورةٍ واحد يمرّ بهذا الاستعلام.
    thumbnail: str | None = None

    @property
    def images_missing(self) -> int:
        return max(self.cars - self.cars_with_images, 0)


def summarise(auctions) -> dict[int, RowSummary]:
    """ملخّصُ كل مزادٍ في هذه الصفحة — ثلاثةُ استعلاماتٍ لا أكثر.

    ``auctions`` صفوفُ **الصفحة** لا الاستعلام كلّه: صفحةٌ من خمسة وعشرين لا
    تحتاج ملخّصَ ستّةٍ وخمسين مزاداً، وv1 كان يحسبها كلَّها في كل تحميل.
    """
    from apps.bidding.models import Bid

    from .cards import media_url

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

    # ٥ — العيّنة والمصغّرة: أول سيارةٍ في كل مزاد، وغلافُها إن وُجد.
    #
    # استعلامان لا اثنان لكل صفّ: الأول يأخذ سيارةً واحدة لكل مزاد بترتيب
    # اللوت، والثاني غلافَ تلك السيارات دفعةً واحدة.
    sample_cars = {}
    for car in (
        Vehicle.objects.filter(auction_id__in=ids)
        .order_by("auction_id", "lot_number")
        .only("id", "auction_id", "make", "model", "year")
    ):
        sample_cars.setdefault(car.auction_id, car)

    covers: dict[int, str] = {}
    if sample_cars:
        for image in (
            VehicleImage.objects.filter(
                vehicle_id__in=[car.pk for car in sample_cars.values()]
            )
            .order_by("vehicle_id", "-is_cover", "position", "id")
            .only("id", "vehicle_id", "thumbnail", "image")
        ):
            covers.setdefault(image.vehicle_id, media_url(image.thumbnail or image.image))

    return {
        pk: RowSummary(
            top_makes=tuple(ranked[pk]),
            sample=_name_of(sample_cars.get(pk)),
            thumbnail=covers.get(sample_cars[pk].pk) if pk in sample_cars else None,
            **fields,
        )
        for pk, fields in cars.items()
    }


def _name_of(car: Vehicle | None) -> str:
    return f"{car.make} {car.model} {car.year}".strip() if car else ""


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
    "BADGE_TONES",
    "BIDDABLE_PHASES",
    "Badge",
    "LATE_PHASES",
    "OFFERED_STATES",
    "Operation",
    "Phase",
    "RowSummary",
    "Snapshot",
    "VehicleTally",
    "badge_of",
    "due_to_finish",
    "due_to_settle",
    "due_to_start",
    "has_finished",
    "has_started",
    "is_late",
    "window_is_valid",
    "is_open_for_bidding",
    "late_now",
    "open_now",
    "operations",
    "phase",
    "phases_of",
    "snapshot",
    "summarise",
    "summarise_onto",
    "tally",
    "tick",
]
