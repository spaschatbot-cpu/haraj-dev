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
from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.shortcuts import render

from apps.accounts.models import User
from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid, BidRefusal
from apps.money.models import AccountKind, Invoice

from .decisions import AWARDED as DECISION_AWARDED
from .decisions import awarded
from .exports import export, wants_export
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


def bid_shape(*, first: str = "", last: str = "") -> dict:
    """أرقام المزايدات — **والحالات الثلاث قسمةٌ يساوي مجموعُها الإجمالي**.

    مفصولةٌ عن العرض ليسألها الاختبار: ادّعاءُ أن المجموع يساوي الكلّ خاصيّةُ
    هذه الدالّة لا خاصيّةُ صفحةٍ من HTML — وهو الادّعاء الذي تكسره v1.
    """
    rows = Bid.objects.all()

    if (first or "").strip().isdigit():
        rows = rows.filter(vehicle__auction__number__gte=int(first))
    if (last or "").strip().isdigit():
        rows = rows.filter(vehicle__auction__number__lte=int(last))

    # قسمةٌ بالترتيب: المسحوبة أوّلاً، فالمستبدَلة **من غير المسحوب**، فالباقي.
    # وبلا هذا الترتيب تُعدّ المزايدةُ المسحوبةُ المستبدَلةُ مرّتين — وهو
    # بالضبط شكلُ الفائض في v1.
    withdrawn = rows.filter(is_withdrawn=True)
    superseded = rows.filter(is_withdrawn=False, is_superseded=True)
    standing = rows.filter(is_withdrawn=False, is_superseded=False)

    numbers = rows.aggregate(
        total=Count("id"),
        highest=Max("amount"),
        lowest=Min("amount"),
        average=Avg("amount"),
        value=Sum("amount"),
    )

    return {
        "total": numbers["total"] or 0,
        "highest": numbers["highest"],
        "lowest": numbers["lowest"],
        # `Avg` تُرجع كسراً بثمانية عشر رقماً (`88352.941176470588`)، وهو مبلغٌ
        # لا يُقرأ ولا يوجد بهذه الدقّة: الريال قرشان لا أكثر. والتقريب هنا لا
        # في القالب — مرشّحٌ في القالب مكانٌ ثانٍ للقاعدة ولا يُختبَر.
        "average": _rounded(numbers["average"]),
        "value": numbers["value"] or ZERO,
        "withdrawn": withdrawn.count(),
        "superseded": superseded.count(),
        "standing": standing.count(),
        # خارج القسمة عمداً: محاولةٌ منعتها البوابة ليست مزايدةً وقعت.
        "refused": BidRefusal.objects.count(),
        "bidders": rows.values("bidder").distinct().count(),
        "auctions": rows.values("vehicle__auction").distinct().count(),
        "vehicles": rows.values("vehicle").distinct().count(),
    }


def top_bidders(*, limit: int = TOP):
    """أكثر المزايدين نشاطاً، بعدد مزايداتهم وإجمالي قيمتها.

    والعدُّ يشمل المستبدَلة عمداً — السؤال «من يزايد كثيراً» لا «من يفوز
    كثيراً»، والثاني شاشةٌ أخرى. ومكتوبٌ في العنوان كي لا يُقرأ الأول ثانياً:
    في v1 أعلى مزايدٍ `5,636` مزايدة بإجمالي `93,556,250`، ولا شيء يقول أهي
    مزايداتٌ متتالية على سيارةٍ واحدة أم سياراتٍ كثيرة.
    """
    return (
        Bid.objects.values("bidder__id", "bidder__full_name", "bidder__phone")
        .annotate(
            bids=Count("id"),
            value=Sum("amount"),
            vehicles=Count("vehicle", distinct=True),
        )
        .order_by("-bids", "bidder__id")[:limit]
    )


@console_page("console:analytics-bids")
def bids_analysis(request):
    """تحليل المزايدات: قسمةٌ تجمع، وأعلى المزايدين."""
    first = request.GET.get("from", "")
    last = request.GET.get("to", "")
    shape = bid_shape(first=first, last=last)

    return render(
        request,
        "console/analytics_bids.html",
        {
            "shape": shape,
            "top": top_bidders(),
            "first": first,
            "last": last,
            # يُحسب هنا لا في القالب: قالبٌ يجمع ثلاثة أرقامٍ ليعرض رابعاً هو
            # مكانٌ ثانٍ للقاعدة ولا يُختبَر (المادة ٤-٤).
            "partition_total": shape["withdrawn"]
            + shape["superseded"]
            + shape["standing"],
        },
    )


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
        people = people.filter(phone__icontains=phone)
    if name:
        people = people.filter(full_name__icontains=name)

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

    return {
        "person": person,
        "ambiguous": False,
        "count": numbers["count"] or 0,
        "value": numbers["value"] or ZERO,
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
    return render(request, "console/analytics.html", {"totals": report_totals()})


# ---------------------------------------------------------------------------
# تقرير المحفظة — الشاشة التي هي دليلُ أطروحة v2 كاملةً. T830ح
# ---------------------------------------------------------------------------
#
# شاشة v1 المقابلة تكتب مصدرَها على نفسها: «إجمالي مبالغ التأمين
# `9,390,004.00` — `SUM(total_insurance_paid)`». وذلك العمود **بالحرف** أحد
# الثلاثة التي وجدها جرد T302 في `userss` أعمدةَ رصيدٍ مشتقّة كلُّها تُهمَل.
#
# وهو نفسه «إجمالي التأمين» في رئيسية v1 — أي أن **الرقم الأكبر في لوحة
# الإدارة كلّها مقروءٌ من عمودٍ محذَّرٍ منه في الكود ولا يُحدَّث بانتظام**.
#
# وهنا يُجمَع من `money.Account` عند كل عرض. وقد يختلف عن العمود القديم يوم
# التحويل — **والاختلاف هو الجواب لا المشكلة.**


#: دلاءُ العميل الثلاثة. الإجمالي مجموعُها لا واحدٌ منها: عميلٌ كلُّ تأمينه
#: محجوزٌ لمزادٍ جارٍ **دفع** تأمينه، وقراءة `insurance_free` وحدها تقول صفراً.
INSURANCE = (
    AccountKind.INSURANCE_FREE,
    AccountKind.INSURANCE_HELD,
    AccountKind.INSURANCE_LOCKED,
)


def wallet_rows(*, text: str = "", low: str = "", high: str = "", order: str = ""):
    """عملاء التأمين وأرصدتُهم — **مجموعةً من الدفتر لا من عمود**.

    و`filter` على الدلاء داخل `Sum` لا استعلامٌ لكل عميل: أربعةٌ وأربعون ألف
    عميلٍ بأربعةٍ وأربعين ألف استعلام هي الشاشة التي لا تُفتح.
    """
    from django.contrib.auth import get_user_model

    rows = (
        get_user_model()
        .objects.filter(is_staff=False)
        .annotate(
            insurance=Sum(
                "accounts__balance",
                filter=Q(accounts__kind__in=INSURANCE),
            )
        )
        .filter(insurance__gt=ZERO)
    )

    text = (text or "").strip()
    if text:
        rows = rows.filter(Q(full_name__icontains=text) | Q(phone__icontains=text))

    for value, field in ((low, "insurance__gte"), (high, "insurance__lte")):
        value = (value or "").strip()
        if value.replace(".", "", 1).isdigit():
            rows = rows.filter(**{field: Decimal(value)})

    # «الأعلى أولاً» افتراضاً كما في v1: السؤال الذي تُفتح الشاشة لأجله «من
    # عنده مالٌ عندنا» لا «من سجّل أوّلاً».
    return rows.order_by("insurance" if order == "asc" else "-insurance", "id")


@console_page("console:insurance-report")
def insurance_report(request):
    """تقرير المحفظة: من دفع تأميناً وكم — من الدفتر."""
    rows = wallet_rows(
        text=request.GET.get("q", ""),
        low=request.GET.get("low", ""),
        high=request.GET.get("high", ""),
        order=request.GET.get("order", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="تقرير-المحفظة",
            headers=["المعرّف", "الاسم", "الجوال", "إجمالي التأمين"],
            cell=lambda row: [row.pk, row.full_name, row.phone, row.insurance],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "console/insurance_report.html",
        {
            "page": page,
            "customers": rows.count(),
            "total": rows.aggregate(t=Sum("insurance"))["t"] or ZERO,
            "q": request.GET.get("q", ""),
            "low": request.GET.get("low", ""),
            "high": request.GET.get("high", ""),
            "order": request.GET.get("order", ""),
        },
    )


# ---------------------------------------------------------------------------
# احصائيات المزاد النشط — «لو أُغلق المزاد الآن». T830ح
# ---------------------------------------------------------------------------


def live_shape(number: str = "") -> dict | None:
    """صورةُ مزادٍ واحد الآن — أو `None` حين لا مزادَ يُقرأ.

    و«القيمة الحالية» **مجموعُ أعلى مزايدةٍ لكل سيارة**، لا مجموعُ المزايدات:
    الثاني يجمع عشرَ مزايداتٍ على سيارةٍ واحدة فيقول إنها بيعت عشر مرّات.
    """
    auctions = engine.open_now().order_by("-starts_at")
    if (number or "").strip().isdigit():
        auctions = Auction.objects.filter(number=int(number))

    auction = auctions.first()
    if auction is None:
        return None

    cars = Vehicle.objects.filter(auction=auction)
    bids = Bid.objects.filter(vehicle__auction=auction)

    # أعلى مزايدةٍ لكل سيارة، مجموعةً في القاعدة لا في بايثون.
    tops = (
        cars.annotate(top=Max("bids__amount"))
        .filter(top__isnull=False)
        .values_list("top", flat=True)
    )
    current = sum(tops, ZERO)

    return {
        "auction": auction,
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


@console_page("console:active-auction")
def active_auction(request):
    """احصائيات المزاد النشط: ما قيمتُه **لو أُغلق الآن**."""
    return render(
        request,
        "console/active_auction.html",
        {
            "shape": live_shape(request.GET.get("number", "")),
            "number": request.GET.get("number", ""),
            "live": engine.open_now().count(),
        },
    )


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


def profit_rows(*, first: str = "", last: str = "", state: str = ""):
    """كل مزادٍ وما أنتجه — من المركبات المرساة فيه لا من عمودٍ مخزَّن."""
    rows = Auction.objects.all()

    if (first or "").strip().isdigit():
        rows = rows.filter(number__gte=int(first))
    if (last or "").strip().isdigit():
        rows = rows.filter(number__lte=int(last))
    if (state or "").strip() in AuctionState.values:
        rows = rows.filter(state=state)

    won = Q(vehicles__state__in=AWARDED_STATES)
    return rows.annotate(
        cars=Count("vehicles", distinct=True),
        sold=Count("vehicles", filter=won, distinct=True),
        revenue=Sum("vehicles__awarded_price", filter=won),
        unsold=Count("vehicles", filter=~won, distinct=True),
    ).order_by("-starts_at", "-number")


def profit_totals(rows) -> dict:
    """الإجماليّات — والمفوتَرُ والمحصَّلُ من الفواتير لا من ضربٍ في نسبة.

    v1 يعرض «مع الضريبة» و«بدون الضريبة» فيضرب الإجمالي في ١٫١٥. وهنا
    «المفوتَر» مجموعُ الفواتير الصادرة فعلاً، و«المحصَّل» ما وصل منها —
    والفرقُ بين الثلاثة هو ما يُقرأ.
    """
    invoices = Invoice.objects.filter(vehicle__auction__in=rows)
    return {
        "auctions": rows.count(),
        "with_bids": rows.filter(vehicles__bids__isnull=False).distinct().count(),
        "revenue": rows.aggregate(t=Sum("vehicles__awarded_price"))["t"] or ZERO,
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
            "totals": profit_totals(rows),
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

    return render(
        request,
        "console/owners_console.html",
        {
            "staff": User.objects.filter(is_staff=True).count(),
            "customers": User.objects.filter(is_staff=False).count(),
            "auctions": Auction.objects.count(),
            "live": live.count(),
            # الرقم نفسه الذي يعرضه «تقرير المحفظة» — من الدفتر، وبالدالّة
            # ذاتها. فلا يقول هذا تسعةً وثلاثمئة ألفٍ ويقول ذاك غيرها.
            "insurance": wallet_rows().aggregate(t=Sum("insurance"))["t"] or ZERO,
            "bidders": Bid.objects.values("bidder").distinct().count(),
            "awarded": awarded().count(),
        },
    )
