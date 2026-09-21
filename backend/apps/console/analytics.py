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

from django.db.models import Avg, Count, Max, Sum
from django.shortcuts import render

from apps.accounts.models import User
from apps.auctions.models import Vehicle
from apps.bidding.models import Bid, BidRefusal
from apps.core.arabic import search_q
from apps.money import services as money

from .decisions import AWARDED as DECISION_AWARDED
from .decisions import awarded
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
# قسمُ «التقارير والتحليلات» كان هنا — وحُذف كلُّه. T940
# ---------------------------------------------------------------------------
#
# قرارُ المالك (١٨ سبتمبر ٢٠٢٦): «احذف القسم كامل… الصفحات التانية بتعمل
# وظيفته». وهو وصفٌ دقيق: كلُّ رقمٍ في «لوحة التقارير» كان **بابَ** شاشةٍ
# أخرى تقرؤه من مصدره — بنصّ تعليقها: «كلُّ رقمٍ يُقرأ من مصدر شاشته لا من
# استعلامٍ ثانٍ». فهي صفحةُ عبورٍ لا صفحةُ جواب، والأرقامُ نفسُها في
# الرئيسية وفي «منصّة الملّاك» ومعها أبوابُها.
#
# و«تقرير الأرباح» (`profit_base` · `profit_rows` · `profit_totals`) حُذف
# معه. وما كان يجيبه — ما أنتجه كلُّ مزادٍ وما فُوتِر منه وما وصل — **يُفقد
# فعلاً**: «مركز الفواتير» يجيب «كم لنا» على الفواتير كلِّها لا مزاداً مزاداً.
#
# وحُذفت الدوالُّ مع شاشاتها لا بعدها، لسبب T939 نفسِه.


# ---------------------------------------------------------------------------
# و«منصة الملاك» لم تعد هنا — T965
# ---------------------------------------------------------------------------
#
# كانت شاشتُها سبعةَ أرقامٍ وأربعَ عشرةَ بطاقةً معظمُها روابطُ شاشاتٍ في
# الشريط الجانبيّ أصلاً. وقرارُ المالك (٢١ سبتمبر ٢٠٢٦): «استبدل صفحة منصّة
# الملّاك بالصفحة دي» — ومعه رابطُ `admin2/bills/index.php`، أي **شاشةُ اختيار
# العروض**. فالمسارُ نفسُه (`console:owners-console`) يرسم الآن تلك الشاشة،
# وبناؤها في `apps/console/offers.py`.
#
# وحُذفت الدالّةُ مع شاشتها لا بعدها: دالّةٌ لا يستدعيها مسارٌ ليست شيفرةً
# ميّتةً فحسب — هي وعدٌ بشاشةٍ لا وجودَ لها، يقرؤه من يبحث عن «منصة الملاك»
# في هذا الملفّ فيصلحها هنا ولا يتغيّر شيء.
