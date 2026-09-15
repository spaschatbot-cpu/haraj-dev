"""لوحة التحليلات — أرقامٌ كلٌّ منها بابٌ إلى الشاشة التي تتصرّف فيه.

هذه الصفحة **هي** جذر اللوحة (`console:home`)، كما هي في v1: الجذر هناك
«لوحة التحليلات والإحصائيات». وكان الجذر هنا شبكةَ كروتٍ تشرح الشاشات، واللوحة
تحتها في `console:dashboard` — فصار في القسم الواحد مدخلان، وأوّلُهما يقول ما
يقوله الشريط الجانبي الملاصق له.

والاعتراض القديم على رئيسية v1 كان: «لوحة أرقامٍ لا يستطيع أحد التصرّف فيها».
وهو اعتراضٌ على تلك اللوحة لا على كون الجذر لوحة — **فكل رقم هنا رابط**،
ووجهته الشاشة التي يُفعل فيها شيء: الفواتير المعلّقة تفتح قائمة الفواتير،
والتأمين المحتجَز يفتح دفتر التأمينات، والعجز يفتح صحّة المال. وسطرُ «ما تفعله
كل شاشة» — الذي كانت الشبكة تحمله وحدها — انتقل إلى `title` كلِّ رابطٍ في
الشريط، فيُقرأ من كل صفحة لا من صفحةٍ واحدة تُغادَر فوراً.

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

from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid, BidRefusal
from apps.core.permissions import Capability, Role, can
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
from .icons import path_of
from .views import console_page

ZERO = Decimal("0.00")

#: أسماء أيقونات البطاقات — مصرَّحٌ بها هنا لا مستنتَجة من لوحةٍ مبنيّة.
#:
#: البطاقات تُبنى شرطياً بحسب صلاحية القارئ، فأيقونةٌ لا يراها إلا المالك لا
#: تظهر في لوحة موظّفٍ أصلاً. ولولا هذا السطر لكان الحارس الذي يمنع «رسماً
#: يُصان بلا سبب» يمرّ على أيقونةٍ أُهملت — أو يصرخ على أيقونةٍ تُستعمل ولم
#: يرها. و`test_icons.py` يقابله بلوحةٍ حقيقية لمالك، فافتراقُ الاثنين يسقط.
STAT_ICONS = ("book", "lock", "file", "award", "scale", "gavel", "users", "help")

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
    #: **اسمُ** أيقونةٍ في `icons.py` لا رمزٌ نصّي. تزيينيٌّ صراحةً — ولذلك
    #: `aria-hidden` في القالب، ولا يحمل معلومةً لا تُقرأ بدونه.
    icon: str = ""
    #: نصّ الرابط في التذييل. فارغٌ يعني بطاقةً بلا فعل.
    action: str = ""
    delta: Delta | None = None
    #: نقاطٌ للخطّ المصغَّر داخل البطاقة، مقيسةً على 0-100. فارغةٌ تعني لا خطّ.
    #: شكلٌ لا رقم: الرقم مكتوبٌ فوقه، وهذا يقول «إلى أين يتجه» في لمحة.
    spark: tuple[int, ...] = ()
    #: وحدةُ ما يعدّه الرقم — «ريال» أو «مزاد» أو «عميل». تُعرض حبّةً في أعلى
    #: البطاقة على مقابل الرمز، كما في لوحة v1 التي أقرّها المالك.
    #:
    #: وهي **وحدةٌ لا زخرفة**: «70,000.00» وحده لا يقول ريالاً أم مزاداً، وكان
    #: يُقرأ من سطر الشرح تحته أو لا يُقرأ. ولا تُعرض مع المقارنة — مكانٌ واحد
    #: لا يحمل شيئين، والمقارنةُ أولى به لأنها تتغيّر.
    #:
    #: **في آخر الحقول عمداً**: كلُّ نداءٍ في هذا الملفّ موضعيٌّ، وحقلٌ يُدسّ
    #: في الوسط يزيح ثلاثةَ عشرَ نداءً صامتةً — فيصير `tone` رمزاً و`icon` فعلاً.
    unit: str = ""

    @property
    def icon_path(self) -> str:
        """مسارُ الرسم، أو الفراغ لبطاقةٍ بلا أيقونة."""
        return path_of(self.icon)

    @property
    def _spark_xy(self) -> list[tuple[float, float]]:
        """إحداثياتُ الخطّ المصغَّر، محسوبةً مرّةً واحدة.

        الحسابُ هنا لا في القالب: قالبٌ يحسب إحداثيات هو مكانٌ ثانٍ للقاعدة
        ولا يُختبَر (المادة ٤-٤). والمحور الرأسي مقلوبٌ لأن أعلى القيمة أدنى
        الإحداثي في SVG. والصندوق `0 0 100 32`.
        """
        if len(self.spark) < 2:
            return []
        step = 100 / (len(self.spark) - 1)
        return [(i * step, 30 - v * 0.28) for i, v in enumerate(self.spark)]

    @property
    def spark_points(self) -> str:
        """هل للبطاقة رسمٌ أصلاً — يقرؤه القالبُ شرطاً لا إحداثيات."""
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in self._spark_xy)

    @property
    def spark_curve(self) -> str:
        """الخطُّ منحنىً ناعماً، مسارَ `<path>` بقطع بيزيه تكعيبية.

        **ولماذا منحنىً لا خطوطاً مستقيمة**: سبعُ نقاطٍ موصولةٌ بمستقيمات
        تعطي سبعَ زوايا حادّة في 50px من الارتفاع، فيُقرأ الرسمُ مسنَّناً —
        وهو أول ما يميّز رسماً مرتجلاً من رسمِ لوحةٍ مصنوعة.

        والطريقةُ Catmull-Rom محوَّلةً إلى بيزيه: لكل قطعةٍ ضابطان مشتقّان
        من **جارَي** طرفيها، فيمرّ المنحنى بكل نقطةٍ بالضبط ولا «يخترعها»
        بينها. وهذا شرطٌ لا تحسين: رسمٌ ماليّ يمرّ فوق قيمةٍ لم تقع هو رسمٌ
        يكذب، ومنحنياتُ التنعيم الأخرى (B-spline) تفعل ذلك.

        والضابطُ يُقصّ رأسياً عند حدّي القطعة (`min`/`max`)، وإلا تجاوز
        المنحنى قمّةً حادّةً فارتفع فوق أعلى قيمةٍ في الأسبوع — وقارئٌ يرى
        الذروةَ أعلى من رقمها المكتوب لا يصدّق أحدَهما.
        """
        pts = self._spark_xy
        if len(pts) < 2:
            return ""
        out = [f"M {pts[0][0]:.1f} {pts[0][1]:.1f}"]
        for i in range(len(pts) - 1):
            p0 = pts[i - 1] if i else pts[0]
            p1, p2 = pts[i], pts[i + 1]
            p3 = pts[i + 2] if i + 2 < len(pts) else p2
            c1x, c1y = p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6
            c2x, c2y = p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6
            lo, hi = min(p1[1], p2[1]), max(p1[1], p2[1])
            c1y, c2y = min(max(c1y, lo), hi), min(max(c2y, lo), hi)
            out.append(f"C {c1x:.1f} {c1y:.1f} {c2x:.1f} {c2y:.1f} {p2[0]:.1f} {p2[1]:.1f}")
        return " ".join(out)

    @property
    def spark_area(self) -> str:
        """المساحةُ تحت المنحنى — المنحنى نفسُه مغلقاً عند القاع.

        خطٌّ وحدَه يقول «إلى أين يتجه»؛ والمساحةُ تحته تقول «كم» — تُقرأ
        حجماً قبل أن يُتتبَّع الخطّ. وتُغلق عند القاع (`32`) لا عند أوّل
        نقطةٍ ولا آخرِها، وإلا مالت قاعدةُ الرسم مع البيانات.
        """
        pts = self._spark_xy
        curve = self.spark_curve
        if not curve:
            return ""
        return f"{curve} L {pts[-1][0]:.1f} 32 L {pts[0][0]:.1f} 32 Z"

    #: موضعُ نقطة «اليوم» على الرسم، **نسبةً مئوية لا إحداثيَّ SVG**.
    #:
    #: النقطةُ تُرسم عنصرَ HTML فوق الرسم لا `<circle>` داخله، لأن الرسم
    #: يُمطّ أفقياً (`preserveAspectRatio="none"`) فيتحوّل كلُّ دائرةٍ فيه
    #: إلى قطعٍ ناقص. وعنصرٌ فوقه لا يمسّه المطّ.
    #:
    #: والمحور الأفقيُّ هنا **لا ينقلب مع اتجاه الصفحة**: فضاءُ إحداثيات SVG
    #: يبدأ من اليسار دائماً، فالموضعُ يُكتب بـ`left` الفيزيائية لا بحافةٍ
    #: منطقية — ومنطقيّةٌ هنا كانت ستضع «اليوم» في طرف الأسبوع الآخر.
    @property
    def spark_last_x(self) -> str:
        """بُعدُ آخر نقطةٍ عن يسار الرسم، ٪."""
        xy = self._spark_xy
        return f"{xy[-1][0]:.1f}" if xy else ""

    @property
    def spark_last_y(self) -> str:
        """بُعدُ آخر نقطةٍ عن أعلى الرسم، ٪ — من ارتفاع الصندوق (32)."""
        xy = self._spark_xy
        return f"{xy[-1][1] / 32 * 100:.1f}" if xy else ""


@dataclass
class Board:
    """كل ما تعرضه الصفحة، مجموعاً مرة واحدة."""

    is_clean: bool = True
    alarms: list[Stat] = field(default_factory=list)
    stats: list[Stat] = field(default_factory=list)
    #: البطاقاتُ التي تحمل رسماً، مفصولةً عن `stats` في شبكةٍ خاصّة بها.
    #:
    #: وليست ترتيباً بصرياً فحسب: البطاقةُ ذاتُ الرسم تحتاج عرضاً مضاعفاً
    #: ليُقرأ شكلُها، وبطاقتان كذلك في شبكةٍ من **ثلاثة** أعمدة لا تجتمعان
    #: في صفّ — تأخذ الأولى عمودين والثانية تنزل وحدها، فتبقى في الصفّ
    #: فجوةٌ وتُدفع البطاقاتُ العادية بعدها إلى أسفل. وشبكةٌ ثانيةٌ بعمودين
    #: تحلّ الأمرين معاً: الرسمان في صفٍّ، والعاديةُ تملأ صفوفَها.
    charts: list[Stat] = field(default_factory=list)
    auction_states: list[tuple[str, int, int]] = field(default_factory=list)
    #: أكثرُ الحالات عدداً — `(الاسم، العدد)` أو `None` حين لا مزاد.
    #:
    #: مشتقٌّ هنا لا في القالب: `max` بمفتاحٍ ليس مما تفعله لغةُ القوالب،
    #: ومحاولةُ إيجادها بحلقةٍ ومقارنةٍ فيها قاعدةٌ في مكانٍ لا يُختبَر.
    auction_top: tuple[str, int] | None = None
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
                    unit="ملاحظة",
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
                    unit="ريال",
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
                unit="عجز",
            )
        )

    # مزادٌ تخلّف عنه عاملُ الخلفية: العمودُ يقول شيئاً والساعةُ تقول غيره.
    # ليس عطلاً في المزاد بل في العامل — Celery متوقّف أو متأخّر — ولذلك مكانُه
    # التنبيهات لا الأرقام: كلُّ دقيقةٍ يبقى فيها مزادٌ «جارياً» بعد نهايته هي
    # دقيقةٌ يرى فيها العميل عدّاداً يقول «مضى» وزرَّ مزايدةٍ يُرفض ضغطُه.
    late = engine.late_now().count()
    if late and sees_auctions:
        board.alarms.append(
            Stat(
                "مزادات تخلّف عنها العامل",
                str(late),
                "حان وقتها ولم تُفتَح، أو انتهى ولم تُغلَق — تحقّق من Celery",
                reverse("console:auctions"),
                "warn",
                unit="مزاد",
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
                unit="رسالة",
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
                "book",
                "افتح دفتر التأمينات",
                unit="ريال",
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
                "lock",
                "من عليه حجز",
                unit="حجز",
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
                "file",
                "افتح الفواتير",
                unit="فاتورة",
            )
        )

    # ---- المزادات والمركبات ----------------------------------------------
    if sees_auctions:
        # `open_now` لا `state=LIVE`: العمودُ يكتبه عاملُ خلفيّة والساعة لا
        # تنتظره، فمزادٌ انتهى وقتُه ولم يُغلَق بعد كان يُعدّ هنا «جارياً»
        # بينما البوّابة ترفض كل مزايدة فيه والعدّاد عند العميل يقول «مضى».
        live = engine.open_now().count()
        scheduled = Auction.objects.filter(state=AuctionState.SCHEDULED).count()
        board.stats.append(
            Stat(
                "المزادات",
                f"{Auction.objects.count():,}",
                f"{live} جارٍ · {scheduled} مجدول",
                reverse("console:auctions"),
                "auction" if live or scheduled else "warn",
                "award",
                "افتح المزادات",
                unit="مزاد",
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
                "scale",
                "قرارات الشركاء",
                unit="مركبة",
            )
        )
        board.stats.append(
            Stat(
                "المزايدات",
                f"{Bid.objects.count():,}",
                f"{_bids_since(hours=24):,} خلال ٢٤ ساعة",
                "",
                "auction",
                "gavel",
                "",
                _week_over_week(Bid, "placed_at"),
                _daily_shape(Bid, "placed_at"),
            )
        )
        board.auction_states = _auction_states()
        board.auction_wheel = _wheel(board.auction_states)
        board.auction_total = sum(n for _, n, _ in board.auction_states)
        if board.auction_states:
            top = max(board.auction_states, key=lambda row: row[1])
            board.auction_top = (top[0], top[1])
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
                "users",
                "افتح المستخدمين",
                unit="عميل",
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
                "help",
                "لماذا رُفضت",
                _week_over_week(BidRefusal, "refused_at"),
                _daily_shape(BidRefusal, "refused_at"),
                unit="اليوم",
            )
        )

    # الفصلُ في آخر السطر لا عند كل إضافة: بناءُ البطاقات مشروطٌ بصلاحيات
    # القارئ في ستّة مواضع، وشرطُ «هل تحمل رسماً» في كلٍّ منها ستّةُ أماكن
    # للقاعدة الواحدة.
    board.charts = [s for s in board.stats if s.spark]
    board.stats = [s for s in board.stats if not s.spark]

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
#: قطاعات الدائرة. رُفعت درجتُها لمّا صار للوحة مظهرٌ داكن (T833): الألوان
#: الأولى كانت مشتقّةً من ألوان النصّ — `#0f6f75` و`#b42318` — وهي على بطاقةٍ
#: بيضاء واضحة، وعلى بطاقةٍ كحليّة كتلٌ داكنة لا يُميَّز بعضها من بعض. وهذه
#: ليست نصّاً فلا يلزمها ٤٫٥؛ يلزمها أن تُفرَّق عن جارتها وعن الأرضيّتين.
#:
#: و`.wheel__dot` في `app.css` يكرّرها لأن المفتاح يُرسم بـCSS والقطاعات
#: بـ`conic-gradient` من هنا — و`test_dashboard.py` يقرأ هذه القائمة ويطابقها
#: بالورقة، فقائمتان تفترقان تسقط الحزمة لا العين.
WHEEL = ("#1a9aa1", "#4aa5df", "#8c6ad6", "#c9891a", "#21a06a", "#e05a4c")


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


def _role_label(user) -> str:
    """اسمُ دور اللوحة عربياً، أو الفراغ لمن لا دور مسجَّلاً له.

    **مصدران بترتيبٍ مقصود**: التعدادُ في الشيفرة أولاً، ثم الجدول. الأدوارُ
    الأربعة الأولى (`owner` · `operations` · `finance` · `support`) تسبق
    الجدول ولا صفَّ لها فيه — وقراءةُ الجدول وحده كانت تترك الحبّةَ فارغةً
    لأربعةٍ من كلّ ستّة، ومنهم المالك نفسه.

    والـslug لا يُعرض أبداً: «operations» ليست كلمةً يقرأها من يفتح اللوحة.
    """
    slug = getattr(user, "console_role", "")
    if not slug:
        return ""
    label = dict(Role.choices).get(slug)
    if label:
        return label
    from apps.accounts.models import ConsoleRole

    # دورٌ مصنوعٌ في الجدول. و`first()` لا `get()`: دورٌ حُذف وبقي اسمُه في
    # العمود يترك الحبّة غائبةً، ولا يكسر الصفحة.
    return ConsoleRole.objects.filter(slug=slug).values_list("label", flat=True).first() or ""


@console_page("console:home")
def dashboard(request):
    board = board_for(request.user)
    return render(
        request,
        "console/dashboard.html",
        {
            "board": board,
            # اسمُ الدور عربياً لحبّةٍ بجوار الاسم. `console_role` عمودُ slug
            # لاتينيّ يدخل العناوين، و**لا يُعرض** — «ops» ليست كلمةً يقرأها
            # من يفتح اللوحة. والاستعلامُ واحدٌ ومحروسٌ بـ`first()`: دورٌ
            # حُذف من الجدول وبقي اسمُه في العمود يترك الحبّة غائبةً لا
            # يكسر الصفحة.
            "role_label": _role_label(request.user),
            # عددُ ما يحتاج نظراً — يُقرأ في الرأس قبل النزول إلى البطاقات.
            "alarm_count": len(board.alarms),
            # أسبوعٌ بلا مزايدةٍ واحدة: الرسم يخرج سبعةَ أعمدةٍ بارتفاع صفر،
            # أي لوحةً بيضاء تُقرأ «الرسم معطّل». الجملةُ تُقال فوقه.
            "trend_is_empty": not any(n for _, n, _ in board.trend),
        },
    )
