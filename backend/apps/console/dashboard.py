"""لوحة التحليلات — أرقامٌ كلٌّ منها بابٌ إلى الشاشة التي تتصرّف فيه.

`console:home` صفحة تنقّل عمداً، وتعليقها يقول لماذا: «لوحة أرقامٍ لا يستطيع
أحد التصرّف فيها هي ما كانت عليه رئيسية v1». هذه الصفحة لا تنقض ذلك القرار —
تجيب عليه. **كل رقم هنا رابط**، ووجهته الشاشة التي يُفعل فيها شيء: الفواتير
المعلّقة تفتح قائمة الفواتير، والتأمين المحتجَز يفتح دفتر التأمينات، والعجز
يفتح صحّة المال.

وثلاثة فروق عن لوحة v1، كلٌّ منها من حادثة:

* **كل رقم مالي مشتقٌّ من الدفتر، لا من عمود مخزَّن.** جرد T302 وجد في
  `userss` **ثلاثة أعمدة رصيد مشتقّة** — `total_insurance_paid` المحذَّر منه،
  و`wallet` و`purchases_balance` بلا تحذير — وكلها تُهمَل. لوحةٌ تقرأ عموداً
  مجمَّعاً تعرض رقماً لا يعرف أحدٌ من أين جاء (المادة ١-٦).
* **الصحّة أولاً لا آخراً.** إن كان `verify_ledger` غير نظيف فذلك أول ما
  يُقرأ، قبل أي إجمالي. رقمٌ كبير فوق دفترٍ لا يتّزن ليس معلومة، وv1 لم يكن
  عنده هذا المفهوم أصلاً.
* **وما لا يُسمح لك برؤيته لا يُعرض.** الصفحة محروسة بـ`console.access`،
  **وكل بطاقة تسأل `can()` عن قدرتها** — فالمالية ترى المال والتشغيل لا يراه،
  بالبوابة الواحدة نفسها (T801) لا ببوابة ثانية.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid, BidRefusal
from apps.core.permissions import Capability, can
from apps.money.models import (
    UNPAID_INVOICE_STATES,
    Account,
    AccountKind,
    Hold,
    HoldState,
    Invoice,
)
from apps.odoo.models import InboundMessage, InboundState, RefundShortfall

from .health import health_report
from .views import console_page

ZERO = Decimal("0.00")

#: كم يوماً يعرضه شريط الحركة. سبعة لأن السؤال الذي تجيبه هو «ما الذي جرى هذا
#: الأسبوع» — ومدىً أطول يجعل يوم اليوم شعرةً لا تُقرأ.
TREND_DAYS = 7


@dataclass(frozen=True)
class Delta:
    """كم تغيّر هذا الرقم عن المدّة السابقة، وباتجاهٍ أيّ.

    مقارنةٌ لا زخرفة: «١٢٠ ألف مزايدة» رقمٌ لا يقول شيئاً وحده، و«أعلى بـ١٨٪
    عن الأسبوع الماضي» يقول. والاتجاه مكتوبٌ نصّاً مع السهم، فمن لا يميّز
    الأخضر من الأحمر يقرأ الجملة نفسها.
    """

    percent: int
    direction: str  # "up" · "down" · "flat"
    note: str

    @property
    def arrow(self) -> str:
        return {"up": "↗", "down": "↘"}.get(self.direction, "→")

    @property
    def word(self) -> str:
        """الاتجاه كلمةً. محسوبٌ هنا لا بمرشّح في القالب.

        `yesno` كان الحلّ الواضح وهو خطأ صامت: `"up"` و`"down"` كلاهما نصٌّ
        غيرُ فارغ فيقرأهما المرشّح «صحيحاً»، فتقول البطاقة «أعلى» في الحالتين.
        """
        return {"up": "أعلى", "down": "أقل"}.get(self.direction, "مستقر")


@dataclass(frozen=True)
class Stat:
    """رقمٌ واحد، ومعه إلى أين يذهب من يريد التصرّف فيه."""

    label: str
    value: str
    #: سطرٌ يقول ما الذي يعدّه هذا الرقم بالضبط — لا تكراراً للعنوان.
    detail: str = ""
    href: str = ""
    #: نبرة البطاقة: `plain` · `money` · `auction` · `people` · `warn` · `alarm`.
    #: لا لونٌ بلا معنى.
    tone: str = "plain"
    #: رمزٌ في مربّعه. تزيينيٌّ صراحةً — ولذلك `aria-hidden` في القالب، ولا
    #: يحمل معلومةً لا تُقرأ بدونه.
    icon: str = ""
    #: نصّ الرابط في التذييل. فارغٌ يعني بطاقةً بلا فعل.
    action: str = ""
    delta: Delta | None = None
    #: نقاطٌ للخطّ المصغَّر داخل البطاقة، مقيسةً على 0-100. فارغةٌ تعني لا خطّ.
    #: شكلٌ لا رقم: الرقم مكتوبٌ فوقه، وهذا يقول «إلى أين يتجه» في لمحة.
    spark: tuple[int, ...] = ()

    @property
    def spark_points(self) -> str:
        """النقاط كما يقرأها `<polyline>` — محسوبةً هنا لا في القالب.

        قالبٌ يحسب إحداثيات هو مكانٌ ثانٍ للقاعدة ولا يُختبَر (المادة ٤-٤).
        والمحور الرأسي مقلوبٌ لأن أعلى القيمة أدنى الإحداثي في SVG.
        """
        if len(self.spark) < 2:
            return ""
        step = 100 / (len(self.spark) - 1)
        return " ".join(
            f"{i * step:.1f},{30 - value * 0.28:.1f}"
            for i, value in enumerate(self.spark)
        )


@dataclass
class Board:
    """كل ما تعرضه الصفحة، مجموعاً مرة واحدة."""

    is_clean: bool = True
    alarms: list[Stat] = field(default_factory=list)
    stats: list[Stat] = field(default_factory=list)
    auction_states: list[tuple[str, int, int]] = field(default_factory=list)
    auction_wheel: str = ""
    auction_total: int = 0
    trend: list[tuple[str, int, int]] = field(default_factory=list)


def _money(amount: Decimal) -> str:
    """مبلغٌ كما يُقرأ. نصٌّ لا عدد عائم — المادة ٣-٢، وحتى في تقرير."""
    return f"{amount:,.2f}"


def _sum_of(kind: str) -> Decimal:
    """رصيد دلوٍ عبر كل العملاء، **من الحسابات لا من عمودٍ مجمَّع**."""
    return Account.objects.filter(kind=kind).aggregate(t=Sum("balance"))["t"] or ZERO


def board_for(user) -> Board:
    """اجمع ما يُعرض لهذا الشخص — وما لا يراه لا يُحسب أصلاً."""
    board = Board()
    sees_money = can(user, Capability.MONEY_VIEW)
    sees_auctions = can(user, Capability.AUCTIONS_VIEW)
    sees_invoices = can(user, Capability.INVOICES_VIEW)
    sees_users = can(user, Capability.USERS_VIEW)
    sees_diagnostics = can(user, Capability.DIAGNOSTICS_VIEW)

    # ---- الصحّة أولاً --------------------------------------------------
    if sees_diagnostics:
        report = health_report()
        board.is_clean = report.is_clean
        if report.findings:
            board.alarms.append(
                Stat(
                    "الدفتر لا يتّزن",
                    str(len(report.findings)),
                    "ملاحظةٌ من `verify_ledger` — تُقرأ قبل أي إجمالي أدناه",
                    reverse("console:money-health"),
                    "alarm",
                )
            )
        if report.suspense.balance != ZERO:
            board.alarms.append(
                Stat(
                    "معلّق بلا صاحب",
                    _money(report.suspense.balance),
                    "مالٌ وصل ولم يُنسب — لا يُسقَط ولا يُخمَّن صاحبه",
                    reverse("console:money-health"),
                    "warn",
                )
            )

    open_shortfalls = RefundShortfall.objects.filter(resolved_at__isnull=True).count()
    if open_shortfalls and sees_money:
        board.alarms.append(
            Stat(
                "عجز استرداد مفتوح",
                str(open_shortfalls),
                "أودو طلب سحب وديعةٍ مرهونة — لم يُنفَّذ، وينتظر قراراً",
                reverse("console:refund-queue"),
                "warn",
            )
        )

    stuck = InboundMessage.objects.filter(state=InboundState.FAILED).count()
    if stuck and sees_diagnostics:
        board.alarms.append(
            Stat(
                "رسائل واردة فاشلة",
                str(stuck),
                "لم تُفهَم ولم تُسقَط — تُقرأ ويُعاد تشغيلها",
                reverse("console:odoo-inbox"),
                "warn",
            )
        )

    # ---- المال ----------------------------------------------------------
    if sees_money:
        free = _sum_of(AccountKind.INSURANCE_FREE)
        held = _sum_of(AccountKind.INSURANCE_HELD)
        locked = _sum_of(AccountKind.INSURANCE_LOCKED)
        board.stats.append(
            Stat(
                "إجمالي التأمين",
                _money(free + held + locked),
                f"متاح {_money(free)} · محجوز {_money(held)} · مرهون {_money(locked)}"
                " — مشتقٌّ من الدفتر لا من عمود",
                reverse("console:money-ledger"),
                "money",
                "◈",
                "افتح دفتر التأمينات",
            )
        )
        active_holds = Hold.objects.filter(state=HoldState.ACTIVE).count()
        board.stats.append(
            Stat(
                "حجوزات قائمة",
                f"{active_holds:,}",
                "كلٌّ منها يسمّي مزاده أو فاتورته — لا فلوس محجوزة «كده»",
                reverse("console:money-ledger"),
                "money",
                "▣",
                "من عليه حجز",
            )
        )

    # ---- الفواتير --------------------------------------------------------
    if sees_invoices:
        unpaid = Invoice.objects.filter(state__in=list(UNPAID_INVOICE_STATES))
        outstanding = unpaid.aggregate(t=Sum("amount") - Sum("amount_paid"))["t"] or ZERO
        board.stats.append(
            Stat(
                "فواتير معلّقة",
                f"{unpaid.count():,}",
                f"بقيمة {_money(outstanding)} ريال ما زالت مستحقّة",
                reverse("console:invoices"),
                "money",
                "▤",
                "افتح الفواتير",
            )
        )

    # ---- المزادات والمركبات ----------------------------------------------
    if sees_auctions:
        live = Auction.objects.filter(state=AuctionState.LIVE).count()
        scheduled = Auction.objects.filter(state=AuctionState.SCHEDULED).count()
        board.stats.append(
            Stat(
                "المزادات",
                f"{Auction.objects.count():,}",
                f"{live} جارٍ · {scheduled} مجدول",
                reverse("console:auctions"),
                "auction" if live or scheduled else "warn",
                "◉",
                "افتح المزادات",
            )
        )
        undecided = Vehicle.objects.filter(state=VehicleState.AWAITING_DECISION).count()
        board.stats.append(
            Stat(
                "مركبات تنتظر قراراً",
                f"{undecided:,}",
                "عرضٌ معلّق على المالك — وحجز كل منافسٍ عليها يبقى حتى تُحسم",
                reverse("console:partner-decisions"),
                "warn" if undecided else "plain",
                "◐",
                "قرارات الشركاء",
            )
        )
        board.stats.append(
            Stat(
                "المزايدات",
                f"{Bid.objects.count():,}",
                f"{_bids_since(hours=24):,} خلال ٢٤ ساعة",
                "",
                "auction",
                "⟁",
                "",
                _week_over_week(Bid, "placed_at"),
                _daily_shape(Bid, "placed_at"),
            )
        )
        board.auction_states = _auction_states()
        board.auction_wheel = _wheel(board.auction_states)
        board.auction_total = sum(n for _, n, _ in board.auction_states)
        board.trend = _trend()

    # ---- الناس -----------------------------------------------------------
    if sees_users:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        board.stats.append(
            Stat(
                "المستخدمون",
                f"{User.objects.filter(is_staff=False).count():,}",
                f"{User.objects.filter(is_staff=True).count()} من الموظفين",
                reverse("console:customers"),
                "people",
                "◇",
                "افتح المستخدمين",
            )
        )
        refusals = BidRefusal.objects.filter(
            refused_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        board.stats.append(
            Stat(
                "مزايدات مرفوضة اليوم",
                f"{refusals:,}",
                "كلٌّ منها بسببه ولقطةٍ لماله وقتها",
                reverse("console:why-no-bid"),
                "warn" if refusals else "plain",
                "⊘",
                "لماذا رُفضت",
                _week_over_week(BidRefusal, "refused_at"),
                _daily_shape(BidRefusal, "refused_at"),
            )
        )

    return board


def _daily_shape(model, field: str, days: int = TREND_DAYS) -> tuple[int, ...]:
    """آخرُ أيامٍ من عدّاد يومي، مقيسةً على 0-100.

    مقياسٌ نسبيٌّ لا مطلق: الخطّ يقول «صاعدٌ أم هابط»، والرقم المطلق مكتوبٌ
    فوقه. خلطُ الاثنين في رسمٍ واحد يجعل يوماً بمزايدةٍ واحدة يبدو كيومٍ بألف.
    """
    today = timezone.localtime().date()
    counts = [
        model.objects.filter(**{f"{field}__date": today - timedelta(days=offset)}).count()
        for offset in range(days - 1, -1, -1)
    ]
    top = max(counts) or 1
    return tuple(round(n * 100 / top) for n in counts)


def _week_over_week(model, field: str) -> Delta | None:
    """هذا الأسبوع مقابل الذي قبله — مقارنةٌ تُحسب لا تُدَّعى.

    ``None`` حين لا يكون في الأسبوع السابق شيءٌ يُقاس عليه: نسبةٌ مئوية من صفر
    ليست «زيادة لا نهائية»، هي **لا مقارنة**، وعرضها رقماً هو كيف تصير اللوحة
    مصدرَ ادّعاء.
    """
    now = timezone.now()
    this_week = model.objects.filter(**{f"{field}__gte": now - timedelta(days=7)}).count()
    last_week = model.objects.filter(
        **{
            f"{field}__gte": now - timedelta(days=14),
            f"{field}__lt": now - timedelta(days=7),
        }
    ).count()
    if not last_week:
        return None
    change = round((this_week - last_week) * 100 / last_week)
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return Delta(abs(change), direction, "عن الأسبوع الماضي")


def _bids_since(*, hours: int) -> int:
    return Bid.objects.filter(
        placed_at__gte=timezone.now() - timedelta(hours=hours)
    ).count()


#: ألوان قطاعات الدائرة، بترتيب حالات المزاد. أربعةٌ تكفي لستّ حالاتٍ لأن
#: القائمة تتخطّى الحالات الفارغة — والخامسة تدور على الأولى.
WHEEL = ("#0f6f75", "#3d9bd6", "#6d4aa8", "#8a5a00", "#18794e", "#b42318")


def _wheel(rows: list[tuple[str, int, int]]) -> str:
    """قطاعات الدائرة كـ`conic-gradient` — بلا مكتبة رسم ولا Node.

    القرار نفسه الذي اتُّخذ في T819: باك-إند بلا Node، وسلسلةُ بناءٍ لأجل رسمٍ
    واحد تكلفةٌ بلا مقابل. و`conic-gradient` تفعلها بسطرٍ يقرؤه المتصفح.
    """
    stops, at = [], 0.0
    for index, (_, _, share) in enumerate(rows):
        colour = WHEEL[index % len(WHEEL)]
        stops.append(f"{colour} {at:.1f}% {at + share:.1f}%")
        at += share
    if at < 100:
        stops.append(f"var(--line-soft) {at:.1f}% 100%")
    return "conic-gradient(" + ", ".join(stops) + ")"


def _auction_states() -> list[tuple[str, int, int]]:
    """توزيع حالات المزادات، ومعه نسبةٌ تُرسم — لا رسمٌ يُقرأ منه رقم."""
    counts = dict(
        Auction.objects.values_list("state")
        .annotate(n=Count("id"))
        .values_list("state", "n")
    )
    total = sum(counts.values()) or 1
    rows = []
    for state in AuctionState:
        n = counts.get(state.value, 0)
        if n:
            rows.append((state.label, n, round(n * 100 / total)))
    return rows


def _trend() -> list[tuple[str, int, int]]:
    """المزايدات يوماً بيوم، ومعها ارتفاعُ عمودها نسبةً إلى أعلى يوم.

    الحساب هنا لا في القالب: قالبٌ يقسّم أرقاماً هو مكانٌ ثانٍ للقاعدة، ولا
    يُختبَر (المادة ٤-٤).
    """
    today = timezone.localtime().date()
    days = [today - timedelta(days=offset) for offset in range(TREND_DAYS - 1, -1, -1)]
    counts = {day: Bid.objects.filter(placed_at__date=day).count() for day in days}
    top = max(counts.values()) or 1
    return [
        (day.strftime("%m-%d"), n, max(round(n * 100 / top), 2 if n else 0))
        for day, n in counts.items()
    ]


@console_page("console:dashboard")
def dashboard(request):
    return render(
        request,
        "console/dashboard.html",
        {"board": board_for(request.user)},
    )
