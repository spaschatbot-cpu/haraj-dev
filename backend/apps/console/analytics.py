"""تحليل المزايدات، ولوحة التقارير. T830ب.

الشاشتان من قسم «التقارير والتحليلات» في v1 (`/analytics/bids-analysis`
و`/analytics`)، وهما قراءةٌ محضة.

العطل الذي بُنيتا لأجل ألّا يتكرّر
==================================
شاشة «تحليل المزايدات» في الإنتاج تعرض ثماني بطاقات، وثلاثٌ منها لا تجتمع:

    مزايدات مقبولة   6,503
    مزايدات مرفوضة  70,146
    مزايدات نشطة    81,475
    ─────────────────────
    المجموع        158,124
    والإجمالي المعروض 125,006   ← فائضٌ ٣٣٬١١٨

فإمّا أن المزايدة تُحسب في حالتين، أو أن إحدى البطاقات تعدّ مدىً زمنياً آخر.
ولا شيء على الشاشة يقول أيّهما، فكلُّ قرارٍ يُبنى على أيٍّ من الأربعة يُبنى
على رقمٍ لا يُعرف مصدره (المادة ١-٦).

**فالحالات هنا قسمةٌ لا تصنيف.** ثلاثٌ يستحيل أن تجتمع في مزايدة:
`مسحوبة` (`is_withdrawn`) ثم `مستبدَلة` (`is_superseded`) ثم `قائمة` — بهذا
الترتيب، فالمسحوبة قد تكون مستبدَلةً أيضاً وتُعدّ مرّةً واحدة. ومجموعُها
**يساوي** الإجمالي، ويثبت ذلك `test_analytics.py` على صفوفٍ حقيقية.

و«المرفوضة» ليست منها أصلاً
============================
٧٠٬١٤٦ «مرفوضة» في v1 — ٥٦٪ من الكل. ومعناها إمّا أن المنصّة ترفض أكثر ممّا
تقبل، أو أن «مرفوضة» تعني «استُبدلت بأعلى» وهي الحالة الطبيعية في أي مزاد.
والفرق بين المعنيين هو الفرق بين «النظام يعمل» و«النظام معطّل».

وهنا لا التباس: **المستبدَلة مزايدةٌ وقعت** (`Bid.is_superseded`)، **والمرفوضة
لم تقع أصلاً** (`BidRefusal` — بوابةُ الأهلية منعتها، ومعها سببُها). جدولان
مختلفان، والثانية تُعدّ في بطاقتها وحدها **خارج** القسمة، ومكتوبٌ عليها أنها
محاولاتٌ لم تصر مزايدات.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.core.paginator import Paginator
from django.db.models import Avg, Count, Max, Q, Sum
from django.shortcuts import render

from apps.accounts.models import User
from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid, BidRefusal
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import Invoice

from .decisions import AWARDED as DECISION_AWARDED
from .decisions import awarded
from .exports import export, wants_export
from .money import wallet_rows
from .sensitive import shown_to
from .views import console_page

ZERO = Decimal("0.00")

#: أعلى مزايدين يُعرضون. عشرةٌ كما في v1 — والقائمة الطويلة هنا لا تُقرأ،
#: والسؤال الذي تُفتح لأجله «من الأكثر نشاطاً» لا «كم عددهم».
TOP = 10

#: كم مزايدةً أخيرةً تُعرض في تقرير الشخص. الجدول هنا **لقطةٌ لا سجلّ**:
#: السؤال «ماذا فعل مؤخّراً»، والسجلّ الكامل في مزايدات المزاد.
RECENT = 25

PAGE_SIZE = 50

#: حالاتُ المركبة التي تعني «بيعت». تُقرأ من `decisions` لا تُكتب ثانيةً:
#: تعريفان لكلمة «بيعت» في اللوحة الواحدة يجعلان تقريرين يعدّان شيئين.
AWARDED_STATES = DECISION_AWARDED


def _rounded(value: Decimal | None) -> Decimal | None:
    """مبلغٌ إلى قرشين، أو `None` كما جاء.

    `ROUND_HALF_UP` كما في `money.services._to_money`: المصرفيُّ الافتراضي في
    بايثون (`ROUND_HALF_EVEN`) يقرّب `0.125` إلى `0.12`، ولا أحد في المحاسبة
    يتوقّع ذلك. والقيمة `None` تبقى `None` — لا صفراً: «لا مزايدة بعد» ليس
    «متوسّطها صفر».
    """
    if value is None:
        return None
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# «تحليل المزايدات» كانت هنا — وحُذفت بطلب المالك (١٨ سبتمبر ٢٠٢٦). T939
# ---------------------------------------------------------------------------
#
# ومعها `bid_shape` و`top_bidders` و`_top_shown`: لا مناديَ لها بعد الشاشة،
# ودالّةٌ تبقى بلا نداء تُقرأ يوماً على أنها طريقٌ قائم فيُبنى عليها.
#
# **وما كانت تجيبه لم يُفقد كلُّه.** القسمةُ الثلاث (قائمة · مسحوبة ·
# مستبدَلة) تُقرأ لكل مزادٍ في «المزاد الجاري» (T938) ولكل مركبةٍ في «مزايدات
# المركبة». والمفقودُ حقّاً: **أكثرُ المزايدين نشاطاً** على المنصّة كلِّها،
# و«كم رسا لكلّ مزايد» — وكانت شاشةُ `bids-report` تجيبه وحُذفت معها.

def report_totals() -> dict:
    """أرقام لوحة التقارير — كلٌّ منها **يستدعي مصدرَ شاشته** لا استعلاماً ثانياً.

    في v1 يقول هذا المركز «المزايدات المقبولة 6,503» وتقول شاشتها `4,378`،
    ويقول «طلبات الاسترداد 3,342» وتقول إدارة الطلبات `500` والاستردادات `0`.
    ثلاثةُ أرقامٍ لشيءٍ واحد على ثلاث شاشات، ولا واحدةٌ تقول أي مرشّحٍ تطبّق.

    فما هنا نداءاتٌ للدوالّ نفسها التي تبني تلك الشاشات — والرقم الذي يختلف
    عن شاشته لا يمكن أن يُكتب من هنا.
    """
    return {
        "awarded": awarded().count(),
        "bids": Bid.objects.count(),
        "refusals": BidRefusal.objects.count(),
        "auctions": Auction.objects.count(),
        "vehicles": Vehicle.objects.count(),
        "awarded_value": awarded().aggregate(t=Sum("awarded_price"))["t"] or ZERO,
    }


def report_for(*, phone: str = "", name: str = "") -> dict | None:
    """تقريرُ مزايدات شخصٍ واحد، أو  حين لا يُسمّى أحد.

     لا قاموسٌ بأصفار: شاشةٌ تفتح على «إجمالي ٠» قبل أن يُبحث تقول
    للقارئ إن المستخدم بلا مزايدات وهي لم تُسأل عنه بعد. وv1 يحسن هذه:
    «ابحث برقم الجوال أو الاسم لعرض تقرير المزايدات» — تُنقل بنصّها.

    والبحث بالجوال **أو** بالاسم كما في v1، ويسبق الجوّالُ الاسمَ: هو المفتاح
    الفريد، والاسمُ يتكرّر. ومن طابق أكثرَ من واحدٍ بالاسم يُرَدُّ له العدد
    ليضيّق — لا يُختار له الأول صامتاً.
    """
    phone = (phone or "").strip()
    name = (name or "").strip()
    if not phone and not name:
        return None

    people = User.objects.filter(is_staff=False)
    if phone:
        people = people.filter(search_q(phone, "phone"))
    if name:
        people = people.filter(search_q(name, "full_name"))

    matches = list(people.order_by("full_name", "id")[:2])
    if not matches:
        return {"person": None, "ambiguous": False}
    if len(matches) > 1:
        return {"person": None, "ambiguous": True, "count": people.count()}

    person = matches[0]
    bids = Bid.objects.filter(bidder=person).select_related("vehicle", "vehicle__auction")
    numbers = bids.aggregate(
        count=Count("id"),
        value=Sum("amount"),
        highest=Max("amount"),
        average=Avg("amount"),
    )
    won = awarded().filter(awarded_to=person)

    # كم **مزاداً مختلفاً** دخل، لا كم مزايدةً قدّم. T863
    #
    # الرقمان يفترقان كثيراً: من زايد على أربعين سيارةً في مزادٍ واحد ليس
    # كمن زايد على أربعين سيارةً في عشرين مزاداً — والأوّل عميلُ مزادٍ
    # واحد، والثاني عميلٌ دائم. و«٤٠ مزايدة» وحدها لا تفرّق بينهما.
    #
    # والعدُّ على `vehicle__auction`: المزايدةُ على مركبة، والمركبةُ في مزاد.
    spread = bids.values("vehicle__auction").distinct().count()

    # وإجماليٌّ **شاملَ الضريبة**، من الموضع الوحيد الذي يضربها. T863
    #
    # `tax_added_to` لا حسابٌ هنا: `ops/checks/one_tax_rule.py` يرفض موضعاً
    # ثانياً يضرب بالنسبة ومعه حقّ — و«١٥٪» مكتوبةً في شاشةٍ ثانية هي كيف
    # تختلف شاشتان في اليوم الذي تتغيّر فيه النسبة.
    #
    # ومبالغُ المزايدات **لا تحمل الضريبة**، فهي `tax_added_to` لا `tax_of`:
    # الثانية تسأل عن فاتورةٍ ومصدرِها، ولا فاتورةَ هنا تُسأل.
    total = numbers["value"] or ZERO
    with_tax = money.tax_added_to(total).total if total else ZERO

    return {
        "person": person,
        "ambiguous": False,
        "count": numbers["count"] or 0,
        "auctions": spread,
        "value": total,
        "value_with_tax": with_tax,
        "highest": numbers["highest"],
        "average": _rounded(numbers["average"]),
        # قسمةُ الحالات نفسها التي في  — الشاشتان تعدّان بالقاعدة
        # ذاتها، فلا يقول تقريرُ الشخص شيئاً ويقول تحليلُ المنصّة غيره.
        "withdrawn": bids.filter(is_withdrawn=True).count(),
        "superseded": bids.filter(is_withdrawn=False, is_superseded=True).count(),
        "standing": bids.filter(is_withdrawn=False, is_superseded=False).count(),
        "refused": BidRefusal.objects.filter(bidder=person).count(),
        "won": won,
        "won_count": won.count(),
        "won_value": won.aggregate(t=Sum("awarded_price"))["t"] or ZERO,
        "recent": bids.order_by("-placed_at")[:RECENT],
    }


@console_page("console:user-bids")
def user_bids(request):
    """تقرير مزايدات مستخدم: يُسأل عن شخصٍ بعينه، ولا يفتح على أصفار."""
    return render(
        request,
        "console/user_bids.html",
        {
            "report": report_for(
                phone=request.GET.get("phone", ""),
                name=request.GET.get("name", ""),
            ),
            "phone": request.GET.get("phone", ""),
            "name": request.GET.get("name", ""),
        },
    )


@console_page("console:analytics")
def reports(request):
    """لوحة التقارير: خمسة أرقام، وكلٌّ منها بابٌ إلى شاشته."""
    # خمسةٌ منها أعداد، والسادس **مبلغ**: «إجمالي أسعار الترسية» هو بعينه
    # الرقمُ الذي حُجب في «ملخّص المقبولة» التي يشير إليها الرابطُ بجواره.
    # فإظهارُه هنا يُبطل حجبَه هناك بنقرةٍ أقلّ. قِيس: `52000.00` كانت تُقرأ
    # بـ`auctions.view` وحدَها على `haraj2_t307`.
    return render(
        request,
        "console/analytics.html",
        {"totals": report_totals(), "show_money": shown_to(request.user).money},
    )


# ---------------------------------------------------------------------------
# أرقامُ المزاد الجاري — «لو أُغلق الآن». T830ح · T938
# ---------------------------------------------------------------------------
#
# **وشاشتُها لم تعد هنا.** «احصائيات المزاد النشط» و«مزايدات المزاد الجاري»
# كانتا شاشتين عن الشيء نفسِه — المزادُ المفتوحُ الآن: تلك تعدّ وهذه تسرد —
# فدُمجتا في `console:live-bids` بقرار المالك (١٨ سبتمبر ٢٠٢٦): «ادمج لي
# صفحة مزايدات المزاد الجاري مع صفحة إحصائيات المزاد النشط».
#
# والحسابُ باقٍ هنا لأنه حسابٌ لا عرض، وينادى من `apps.console.bids`.


def live_shape(auctions) -> dict | None:
    """صورةُ المزادات المعطاة الآن — أو `None` حين لا مزادَ فيها.

    **تأخذ المزاداتِ ولا تختارها**: كانت تقرأ `engine.open_now()` بنفسها
    وتأخذ أوّلَها، فصارت الشاشةُ التي تسرد مزايداتِ **كلِّ** المزادات
    المفتوحة تعرض فوقها أرقامَ **واحدٍ** منها — رقمان متجاوران عن نطاقين.
    فالنطاقُ يُقرَّر في مكانٍ واحد (الشاشة) ويُمرَّر.

    و«القيمة الحالية» **مجموعُ أعلى مزايدةٍ لكل سيارة**، لا مجموعُ المزايدات:
    الثاني يجمع عشرَ مزايداتٍ على سيارةٍ واحدة فيقول إنها بيعت عشر مرّات.
    """
    auctions = list(auctions)
    if not auctions:
        return None

    cars = Vehicle.objects.filter(auction__in=auctions)
    bids = Bid.objects.filter(vehicle__auction__in=auctions)

    # أعلى مزايدةٍ لكل سيارة، مجموعةً في القاعدة لا في بايثون.
    tops = (
        cars.annotate(top=Max("bids__amount"))
        .filter(top__isnull=False)
        .values_list("top", flat=True)
    )
    current = sum(tops, ZERO)

    return {
        "auctions": auctions,
        # مزادٌ واحدٌ يُسمّى في الترويسة، وأكثرُ من واحدٍ يُسرَد. والفرقُ
        # يُقرَّر هنا لا في القالب: قالبٌ يعدّ قائمةً ليقرّر ما يعرض هو قاعدةٌ
        # في موضعٍ لا يُراجَع (المادة ٤-٤).
        "one": auctions[0] if len(auctions) == 1 else None,
        "vehicles": cars.count(),
        "with_bids": cars.filter(bids__isnull=False).distinct().count(),
        "without_bids": cars.filter(bids__isnull=True).count(),
        "bids": bids.count(),
        "bidders": bids.values("bidder").distinct().count(),
        "highest": bids.aggregate(m=Max("amount"))["m"],
        "average": _rounded(bids.aggregate(a=Avg("amount"))["a"]),
        # الاسم يقول شرطَه: «لو أُغلق الآن» — جملةُ v1 نفسها، وهي ما يجعل
        # الرقم نافعاً بدل أن يُقرأ مبيعاتٍ وقعت.
        "if_closed_now": current,
    }


# ---------------------------------------------------------------------------
# تقرير الأرباح — وقاعدةُ كسر التعادل تُقرأ من مكانها. T830ك
# ---------------------------------------------------------------------------
#
# عنوان شاشة v1 يحمل قاعدةً: «أعلى مزايد لكل مزاد، **مع كسر التعادل بـMIN(id)**».
# والقاعدة صحيحة — الأسبقُ إدخالاً يفوز عند التساوي — **وموضعُها خطأ**: قاعدةٌ
# تعيش في نصّ عنوانٍ تُنسى يوم تُعاد كتابة الشاشة.
#
# وفي v2 هي في `apps/bidding/settlement.py`: `order_by("-amount", "placed_at")`،
# ومعها `Bid.Meta.ordering` نفسه. فهذه الشاشة **تقرأ الترتيب من هناك** ولا
# تعيد كتابته — ولو تغيّرت القاعدة يوماً تغيّر التقريرُ معها.
#
# و«رأس المال» في v1 حقلُ إدخالٍ يكتبه الموظّف في كل مرّة، والربحُ يُحسب عليه.
# أي أن **الرقم الناتج لا يُعاد إنتاجه**: من يفتح التقرير غداً بقيمةٍ أخرى يرى
# ربحاً آخر، ولا شيء يقول أيّهما كان. فهو ليس هنا — والتقرير يعرض ما وقع
# (إيراد الترسية والمفوتَر والمحصَّل)، والمقارنةُ برأس مالٍ قرارٌ يُكتب في
# مكانٍ يُراجَع لا خانةٌ تُملأ.


def profit_base(*, first: str = "", last: str = "", state: str = ""):
    """المزاداتُ المطلوبة **بلا تجميع** — أساسُ الإجماليّات.

    تُفصَل عن `profit_rows` لأن الإجماليَّ المحسوبَ فوق طبقةِ التجميع يقتل
    الخادم: ضمُّ `vehicles__bids` إلى استعلامٍ يحمل أربعةَ `Count/Sum` على
    ضمِّ `vehicles` يُنتج حاصلَ ضربٍ ديكارتيّاً (١٢٬٩٨١ مركبةً × ١٦٣٬٢٨٣
    مزايدة) يُغلَّف في `COUNT(*) FROM (SELECT DISTINCT …)`. قِيس على
    `haraj2_t307`: **يتجاوز ٢٠ ثانية بحدٍّ زمنيّ، و١٠ دقائقَ بلا حدّ حتى
    تموت عمليّةُ الخادم** فتسقط اللوحةُ كلُّها لا هذه الشاشةُ وحدها. والعدُّ
    نفسُه على قاعدةٍ نظيفة: **٠٫٢٤ ثانية، والجواب ٢١**.
    """
    rows = Auction.objects.all()

    if (first or "").strip().isdigit():
        rows = rows.filter(number__gte=int(first))
    if (last or "").strip().isdigit():
        rows = rows.filter(number__lte=int(last))
    if (state or "").strip() in AuctionState.values:
        rows = rows.filter(state=state)

    return rows


def profit_rows(*, first: str = "", last: str = "", state: str = ""):
    """كل مزادٍ وما أنتجه — من المركبات المرساة فيه لا من عمودٍ مخزَّن."""
    rows = profit_base(first=first, last=last, state=state)

    won = Q(vehicles__state__in=AWARDED_STATES)
    return rows.annotate(
        cars=Count("vehicles", distinct=True),
        sold=Count("vehicles", filter=won, distinct=True),
        revenue=Sum("vehicles__awarded_price", filter=won),
        unsold=Count("vehicles", filter=~won, distinct=True),
    ).order_by("-starts_at", "-number")


def profit_totals(base) -> dict:
    """الإجماليّات — والمفوتَرُ والمحصَّلُ من الفواتير لا من ضربٍ في نسبة.

    v1 يعرض «مع الضريبة» و«بدون الضريبة» فيضرب الإجمالي في ١٫١٥. وهنا
    «المفوتَر» مجموعُ الفواتير الصادرة فعلاً، و«المحصَّل» ما وصل منها —
    والفرقُ بين الثلاثة هو ما يُقرأ.

    ويأخذ **قاعدةً بلا تجميع** (`profit_base`) لا صفوفَ الشاشة: انظر ثمنَ
    ذلك في `profit_base`.
    """
    invoices = Invoice.objects.filter(vehicle__auction__in=base)
    return {
        "auctions": base.count(),
        "with_bids": base.filter(vehicles__bids__isnull=False).distinct().count(),
        "revenue": base.aggregate(t=Sum("vehicles__awarded_price"))["t"] or ZERO,
        "invoiced": invoices.aggregate(t=Sum("amount"))["t"] or ZERO,
        "collected": invoices.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
    }


@console_page("console:profit-report")
def profit_report(request):
    """تقرير الأرباح: ما أنتجه كل مزاد، وما فُوتِر منه وما وصل."""
    first = request.GET.get("from", "")
    last = request.GET.get("to", "")
    state = request.GET.get("state", "")
    rows = profit_rows(first=first, last=last, state=state)

    if wants_export(request):
        return export(
            rows,
            name="تقرير-الأرباح",
            headers=[
                "المزاد",
                "الاسم",
                "الحالة",
                "بدأ",
                "المركبات",
                "المباعة",
                "غير المباعة",
                "إيراد الترسية",
            ],
            cell=lambda row: [
                row.number,
                row.title,
                row.get_state_display(),
                row.starts_at,
                row.cars,
                row.sold,
                row.unsold,
                row.revenue or ZERO,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "console/profit_report.html",
        {
            "page": page,
            "totals": profit_totals(profit_base(first=first, last=last, state=state)),
            "first": first,
            "last": last,
            "state": state,
            "states": [
                (value, AuctionState(value).label) for value in AuctionState.values
            ],
        },
    )


# ---------------------------------------------------------------------------
# منصة الملاك — روابطُ شاشاتٍ موجودة، وأرقامٌ من مصادرها. T830ك
# ---------------------------------------------------------------------------
#
# شاشة v1 «الإدارة العليا… في صفحة واحدة موحدة»، وهي أربعةَ عشرَ كرتاً
# **معظمُها روابطُ شاشاتٍ قائمة**. وأولُ رابطٍ فيها يخرج من `admin_v2` إلى
# `admin2/bills/index.php` — أي أن «الصفحة الموحدة» تُحيل إلى نظامٍ ثالث.
#
# و«تعديل المزايدات» فيها: «تعديل مبلغ مزايدة معيّنة». وتعديلُ مبلغِ مزايدةٍ
# بعد وقوعها أخطرُ ما في اللوحة بعد الخصم المباشر — المزايدة عرضٌ قانونيّ.
# وفي v2 لا يُعدَّل `Bid.amount` أبداً: يُسحَب ويُستبدَل بقيدٍ يقول من ولماذا.
# فالكرتُ غير موجودٍ هنا، ومكتوبٌ في القالب لماذا.


@console_page("console:owners-console")
def owners_console(request):
    """منصة الملاك: الأرقام السبعة، وكلٌّ منها من مصدر شاشته."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    live = engine.open_now()

    # **والرقمُ نفسُه يستحقّ حارسَ شاشته نفسَه.** T901
    #
    # ستّةٌ من السبعة أعداد، و«إجمالي التأمين» مبلغٌ — ومبلغُ **دفتر
    # المحفظة** لا مبلغُ فاتورة، فقدرتُه `money.view` لا `invoices.view`
    # (`sensitive.WALLET`). وهو الرقمُ الذي يحرسه `money.view` في «تقرير
    # المحفظة» التي يفتحها الرابطُ بجواره، **وبالدالّة ذاتها**
    # (`money.wallet_rows` — انتقلت إليه في T935 حين دُمجت الشاشتان) — فكان
    # يُقرأ هنا بـ`auctions.view` وحدَها:
    # `9,050,004.00` على `haraj2_t307` لموظّف ساحة.
    seen = shown_to(request.user)

    return render(
        request,
        "console/owners_console.html",
        {
            "staff": User.objects.filter(is_staff=True).count(),
            "customers": User.objects.filter(is_staff=False).count(),
            "auctions": Auction.objects.count(),
            "live": live.count(),
            "show_wallet": seen.wallet,
            # الرقم نفسه الذي يعرضه «سجل المحفظة» — من الدفتر، وبالدالّة
            # ذاتها. فلا يقول هذا تسعةً وثلاثمئة ألفٍ ويقول ذاك غيرها.
            # ولا يُجمَع أصلاً لمن لا يراه: استعلامُ تجميعٍ على أربعةٍ
            # وأربعين ألف عميلٍ ثمنُه يُدفَع، والحجبُ بعد الدفع ليس توفيراً.
            "insurance": (
                wallet_rows().aggregate(t=Sum("held_total"))["t"] or ZERO
                if seen.wallet
                else None
            ),
            "bidders": Bid.objects.values("bidder").distinct().count(),
            "awarded": awarded().count(),
        },
    )
