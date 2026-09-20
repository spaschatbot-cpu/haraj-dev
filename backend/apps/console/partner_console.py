"""شريك التسويق — مزاداته وسياراته وتسويته. T830و.

عشرُ شاشاتٍ من قسم «شريك التسويق» في v1، وكلُّها سؤالٌ واحد بمرشّحاتٍ مختلفة:
**ماذا لشريكٍ بعينه، وأين وصل ماله؟**

العطل الذي بُني هذا الملف لأجل ألّا يُنقَل
==========================================
شاشة «اعتماد مدفوعات الشريك» في v1 تقول القاعدة بنفسها، مكتوبةً على الشاشة:

    «الشريك لا يرى أي حالة سداد من النظام المحاسبي — لا فواتير ولا مدفوعات
     ولا مستحقّات. صفحته تقرأ **هذا الجدول فقط**، ومصدره الوحيد هو ملفك.»

أي أن للسداد **حقيقتين**: واحدةٌ في المحاسبة وواحدةٌ يراها الشريك، ولا شيء
يوفّق بينهما. ورقمُ «مسددة» هناك لا يمسّ دفتراً ولا فاتورةً ولا حساباً — هو
صفٌّ في جدولٍ يُرفع بملفّ إكسل.

**وهنا مصدرٌ واحد: الفاتورة.** سيارةُ الشريك «مسدَّدة» حين تكون فاتورتُها
مسدَّدة، و`money.services.derive_invoice_state` تحسب ذلك **من الدفعات
المسجَّلة** لا من عمودٍ يُكتب مرّةً. فلا يُرفع ملفٌّ ولا تُسجَّل دفعةٌ مرّتين
ولا يبقى «تجنّب رفع الملف نفسه مرتين» تحذيراً يحلّ محلّ مفتاح تفرُّد.

والفارق يُقاس: v1 يعدّ غير المسدَّدة ٢٩١ في شاشة الإدارة و٢٩٠ في صفحة الشريك،
والفرقُ سيارةٌ واحدة (`فورد ميلان #12276`) **لم تُبع ولم يزايد عليها أحد** —
ومع ذلك يعرض عليها زرَّ «اعتماد السداد». وهنا لا تدخل الحساب أصلاً: التسوية
تبدأ من المرساة، والمرساةُ لها فائزٌ بقيدٍ في القاعدة.

ولماذا شاشاتٌ للموظّف لا للشريك
================================
**الشريك في v2 لا حساب لوحةٍ له.** هو مستخدمٌ عادي له `Company`، والأدوار
أربعةٌ ليس فيها «شريك»، و`capabilities_of` تُعيد الفراغ لمن ليس `is_staff` —
والعزل قائمٌ بالبناء، يحرسه `test_partner_isolation.py` على **كل** مسارٍ
يكتشفه محلّل جانغو.

فهذه الشاشات يقرأها الموظّف عن شريكٍ يختاره، لا الشريكُ عن نفسه. وv1 يخلط
الاثنين على المسارات نفسها — وهو بعينه ما جعل حسابَ شريكٍ هناك يكتب رابط
فاتورة عميلٍ آخر فيصل إليها.
"""

from __future__ import annotations

import operator
from decimal import Decimal
from functools import reduce

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import (
    CharField,
    Count,
    Exists,
    F,
    Func,
    Max,
    OuterRef,
    Q,
    Sum,
    Value,
)
from django.db.models import DecimalField, Subquery
from django.db.models.functions import Cast
from django.shortcuts import render

from apps.accounts.models import Company
from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.bidding.models import Bid
from apps.auctions.states import AuctionState, VehicleState
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import Entry, Invoice, InvoiceState, Transaction

from . import payments
from .after_sales import state_label
from .archive import ARCHIVED
from .exports import export, wants_export
from .icons import path_of
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50

#: ما رسا للشريك. التسوية تبدأ من هنا لا من كل سياراته: سيارةٌ لم تُبع لا
#: تُسدَّد، وv1 يعرضها في طابور «غير المسددة» ومعها زرُّ اعتماد.
AWARDED = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)


def partners():
    """الشركات التي لها مركبات — وحدها. قائمةُ اختيارٍ لا سجلّ شركات."""
    # `car_count` لا `vehicles`: الاسم الثاني هو `related_name` على النموذج،
    # وجانغو يرفض تسميةً تصادم حقلاً — والرفض `ValueError` عند أول طلب لا عند
    # الاستيراد، أي أنه كان سيصل الشاشة لا الحزمة لولا `MUST_RENDER`.
    return (
        Company.objects.annotate(car_count=Count("vehicles"))
        .filter(car_count__gt=0)
        .order_by("name")
    )


def _scoped(rows, partner: str):
    """ضيّق على شريكٍ بعينه، أو على **الشركاء جميعاً** — لا على كلّ شيء.

    ولا يُخمَّن شريكٌ حين لا يُختار: «كل الشركاء» جوابٌ صحيح لموظّفٍ يقارن،
    و«الأول في القائمة» جوابٌ عن سؤالٍ لم يُطرح.

    **لكنّ «كل الشركاء» ليست «كل السيارات».** كانت الدالّة تُعيد `rows` كما هي
    حين لا يُختار شريك، فتعرض لوحةُ الشريك مركباتٍ **لا مالكَ شركةً لها
    أصلاً** — وهي سيارات الشركة نفسِها، لا شأنَ لأيّ شريكٍ بها. قِيس على قاعدة
    التطوير: ٢٣ مركبةً في القاعدة، **صفرٌ منها له `owner_company`**، واللوحةُ
    تعرض الثلاثَ والعشرين وتقول «بانتظار قرار الشريك: ٢٣».

    وv1 لا يقع في هذا لأن نطاقَه علمٌ على الصفّ (`is_marketing = 1`): سيارةٌ
    بلا علمٍ لا تظهر أبداً. والنظيرُ هنا `owner_company IS NOT NULL`.
    """
    partner = (partner or "").strip()
    if partner.isdigit():
        return rows.filter(owner_company_id=int(partner))
    return rows.filter(owner_company__isnull=False)


def summary_for(partner: str = "") -> dict:
    """أرقام لوحة الشريك — كلُّها من الفاتورة لا من جدولٍ مرفوع."""
    cars = _scoped(Vehicle.objects.all(), partner)
    won = cars.filter(state__in=AWARDED)

    invoices = Invoice.objects.filter(vehicle__in=won)
    paid = invoices.filter(state=InvoiceState.PAID)

    total = cars.count()
    won_count = won.count()
    won_value = won.aggregate(t=Sum("awarded_price"))["t"] or ZERO

    # **سعرُ الوقوف للمرساة وحدها لا لكلّ سياراته.** «كم فوق سعر الوقوف بعتُ؟»
    # سؤالٌ عن المبيع؛ وقسمةُ حصيلةِ المبيع على أسعارِ وقوفِ **كلّ** سياراته
    # (ومنها ما لم يُعرَض أصلاً) تُنتج نسبةً سالبةً دائماً بلا معنى.
    reserve_of_won = won.aggregate(t=Sum("reserve_price"))["t"] or ZERO

    # الطلبُ على سياراته: كم عرضاً ومن كم شخص. و`distinct` على المزايد لا على
    # المزايدة: من زايد عشراً شخصٌ واحد.
    demand = Bid.objects.filter(vehicle__in=cars).aggregate(
        bids=Count("id"), bidders=Count("bidder", distinct=True)
    )

    # «بانتظار قرار الشريك» — **في المزادات المنتهية وحدها**، وهو تعريفُ
    # `console:partner-decisions` نفسُه. وفي v1 كان العدّاد يعدّ كلَّ ما لم
    # يُقرَّر فيه أيّاً كان مزادُه: أظهر ١٧١ والصفحةُ نفسُها تعرض صفراً لأن
    # المزاد لم يبدأ بعد. فالتعريفُ واحدٌ هنا يقرؤه الرقمُ والصفحة.
    pending = cars.filter(
        auction__state__in=ARCHIVED, partner_decided_at__isnull=True
    ).count()

    return {
        "vehicles": total,
        "auctions": cars.values("auction").distinct().count(),
        "won": won_count,
        "unsold": cars.exclude(state__in=AWARDED).count(),
        "won_value": won_value,
        "invoiced": invoices.count(),
        "paid": paid.count(),
        "unpaid": won_count - paid.count(),
        "paid_value": paid.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
        # ── السبعةُ التي كانت في v1 ولم تكن هنا ──────────────────────────
        "sale_rate": round(won_count / total * 100, 1) if total else 0.0,
        "avg_price": round(won_value / won_count, 2) if won_count else ZERO,
        "best_sale": won.aggregate(t=Max("awarded_price"))["t"] or ZERO,
        "reserve_value": reserve_of_won,
        "uplift_pct": (
            round((won_value - reserve_of_won) / reserve_of_won * 100, 1)
            if reserve_of_won
            else 0.0
        ),
        "bids": demand["bids"] or 0,
        "bidders": demand["bidders"] or 0,
        "pending_decision": pending,
    }


def breakdown_for(partner: str = "", limit: int = 24) -> list:
    """الأداء لكل مزاد — نظيرُ جدول v1، بالمزادات الأحدث أوّلاً.

    **ولماذا جدولٌ تحت البطاقات وقد قالت البطاقاتُ الأرقام.** لأن الإجماليّ
    يخفي التوزيع: شريكٌ باع نصفَ سياراته قد يكون باع كلَّ شيءٍ في مزادٍ ولا
    شيءَ في آخر — وذلك قرارُ توريدٍ للمزاد القادم، لا يُقرأ من رقمٍ واحد.

    و`limit` أربعةٌ وعشرون كـ v1: سنتان بمزادٍ شهريّ، وما قبلهما تاريخٌ لا
    يُقرَّر عليه.
    """
    cars = _scoped(Vehicle.objects.all(), partner)
    rows = (
        Auction.objects.filter(vehicles__in=cars)
        .distinct()
        .annotate(
            cars=Count("vehicles", filter=Q(vehicles__in=cars), distinct=True),
            sold=Count(
                "vehicles",
                filter=Q(vehicles__in=cars, vehicles__state__in=AWARDED),
                distinct=True,
            ),
            sales=Sum("vehicles__awarded_price", filter=Q(vehicles__in=cars)),
            # **سعرُ وقوفِ المرساة وحدها، لا وقوفِ كلّ سياراته في المزاد.**
            #
            # كان بلا شرطِ الحال، فيُطرح مبيعُ **المباع** من وقوفِ **الجميع**
            # ويُسمّى «الفرق». وأثرُه مقيسٌ على الشاشة: «مزاد الرياض —
            # الأسبوع القادم · سياراته ٢ · مباعة ٠ · سعر الوقوف ٢٠٥٬٠٠٠ ·
            # المبيعات ٠ · الفرق −٢٠٥٬٠٠٠» — مزادٌ **لم يبدأ بعد** يُقرأ
            # خسارةً بمئتي ألف.
            #
            # وهو عطلُ v1 نفسُه (`auctionBreakdown`: `SUM(av.starting_price)`
            # بلا شرط)، وقد أُصلح هنا في الرقم العامّ وحدَه
            # (`summary_for.uplift_pct` على المرساة) — فصار للمفهوم الواحد
            # حسابان على الصفحة الواحدة. الآن حسابٌ واحد.
            reserve=Sum(
                "vehicles__reserve_price",
                filter=Q(vehicles__in=cars, vehicles__state__in=AWARDED),
            ),
        )
        .order_by("-starts_at", "-number")[:limit]
    )

    out = []
    for row in rows:
        sales = row.sales or ZERO
        reserve = row.reserve or ZERO
        out.append(
            {
                "auction": row,
                "cars": row.cars,
                "sold": row.sold,
                "rate": round(row.sold / row.cars * 100, 1) if row.cars else 0.0,
                "reserve": reserve,
                "sales": sales,
                # الفرقُ مبلغٌ لا نسبة: «زاد ٤٠ ألفاً» يُقرأ، و«زاد ٣٪» على
                # مزادٍ صغيرٍ يُقرأ أكبرَ مما هو.
                #
                # و`None` حين لا مباع: صفرٌ يُقرأ «تعادل» ولم يجرِ بيعٌ أصلاً،
                # والشرطةُ تقول «لا شيءَ يُقارَن».
                "diff": (sales - reserve) if row.sold else None,
            }
        )
    return out


@console_page("console:partner-console")
def partner_console(request):
    """لوحة الشريك: أرقامُ شريكٍ واحد، وكلٌّ منها بابٌ إلى صفوفه.

    **وشريكٌ واحدٌ دائماً، ولو لم يُختَر** (قرار المالكة، ٢٠ سبتمبر ٢٠٢٦: «شيل
    كل الشركاء»). وكانت الشاشةُ تُفتح على «كل الشركاء» كأخواتها، وسطرُها
    الأوّل يقول «أرقامُ شريكٍ واحد» — فيقرأ الموظّفُ نقيضَ ما يرى.

    والجمعُ هنا ليس مجرّدَ تناقضِ عبارة: «نسبة البيع» و«متوسّط سعر البيع»
    و«أعلى بيعة» و«فوق سعر الوقوف» مجموعةً على الشركاء كلِّهم أرقامٌ لا تخصّ
    أحداً ولا يُتّخذ عليها قرارُ توريد. والشاشاتُ الأخرى تُجمَع بلا ضررٍ لأنها
    صفوفٌ مرشَّحةٌ لا خلاصاتٌ محسوبة.

    والافتراضيُّ أوّلُ الشركاء بالاسم — لا «أوّلُ من له سيارات» ولا الأكبر:
    ترتيبٌ ثابتٌ يفتح الشاشةَ نفسَها في كل مرّة، ويُبدَّل من القائمة.
    """
    partner = (request.GET.get("partner") or "").strip()
    companies = partners()
    company = companies.filter(pk=int(partner)).first() if partner.isdigit() else None
    if company is None:
        company = companies.first()
    partner = str(company.pk) if company else ""

    return render(
        request,
        "console/partner_console.html",
        {
            "totals": summary_for(partner),
            "breakdown": breakdown_for(partner),
            "partner": partner,
            # الشركةُ نفسُها لا معرّفُها وحده: اسمُها كان لا يُكتب في الصفحة
            # إلا داخل قائمة الاختيار، فلمّا حُذفت صارت خمسةَ عشرَ رقماً بلا
            # صاحب.
            "company": company,
            "partners": companies,
        },
    )


def _money_of(rows, field: str):
    """مجموعُ عمودٍ ماليٍّ على مركبات المزاد — استعلاماً فرعيّاً.

    `Sum("vehicles__x")` على استعلامٍ يصل `vehicles__bids` يجمع العمودَ
    مرّةً لكلّ مزايدة، و`distinct=True` لا يُنقذ `Sum` (مبلغان متساويان
    ليسا تكراراً يُحذف). والاستعلامُ الفرعيّ يجمع على المركبات وحدَها.
    """
    return Subquery(
        rows.values("auction").annotate(t=Sum(field)).values("t")[:1],
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )


def auctions_of(partner: str = "", state: str = ""):
    """مزادات الشريك — ومعها **عدد سياراته هو** لا عدد سيارات المزاد.

    وذلك العمود هو ما يصنع الشاشة: «سياراتي ٢٠٦» في مزادٍ فيه ٣٨٦ سيارة رقمٌ
    مختلف، والخلطُ بينهما يجعل الشريك يقرأ حصّةً ليست له.
    """
    rows = Auction.objects.all()
    if (partner or "").strip().isdigit():
        rows = rows.filter(vehicles__owner_company_id=int(partner)).distinct()

    # `state` قد يكون قيمةً واحدة أو مجموعةً: «المنتهية» في قائمة v1 تعني
    # كلَّ ما انتهى — منتهٍ ومُسوّى وملغى — وهو تعريفُ `archive.ARCHIVED`
    # نفسه. وتعريفان لكلمة «منتهٍ» في اللوحة الواحدة يجعلان شاشتين تعدّان
    # شيئين تحت اسمٍ واحد، وهو العطل الذي تكرّر في v1 ثلاث مرّات.
    if isinstance(state, tuple):
        rows = rows.filter(state__in=state)
    elif (state or "").strip() in AuctionState.values:
        rows = rows.filter(state=state)

    mine = Q(vehicles__owner_company_id=int(partner)) if partner.isdigit() else Q()

    # نظيرُ `mine` استعلاماً فرعيّاً على المركبات — للمبالغ، انظر أدناه.
    # و«بلا شريكٍ مختار» تعني هنا **كلَّ مركبات المزاد** كما تعنيه `mine`
    # الفارغة، لا مركباتِ الشركاء وحدَهم: تعريفان لعمودٍ واحدٍ في الدالّة
    # الواحدة أسوأ من تعريفٍ واسع، والقالبُ يقول للقارئ أيَّهما يرى.
    mine_sub = Vehicle.objects.filter(auction=OuterRef("pk"))
    if partner.isdigit():
        mine_sub = mine_sub.filter(owner_company_id=int(partner))

    # **تعريفُ «المزايدة» يتغيّر بحال المزاد** — قاعدةُ v1، ووراءها عطلٌ وقع
    # هناك: المزادُ الجاري تُعدّ فيه **العروضُ القائمة**، والمنتهي يُعدّ فيه
    # **التاريخُ كلُّه** — لأن مزايداتِ المنتهي تصير كلُّها مرفوضةً عند
    # التسوية، فعدُّ القائم منها يعطي **صفراً**. وخلطُ التعريفين أظهر في v1
    # «١٩٥ مزايدة» بجوار «٠ سيارة عليها عروض» في الشاشة الواحدة.
    live_only = state == AuctionState.LIVE
    # و«القائمة» هنا تعريفُ `BidQuerySet.live` نفسُه — لا عمودَ حالةٍ على
    # المزايدة في v2، بل رايتان: لم تُستبدَل ولم تُسحَب. وكتابةُ تعريفٍ ثانٍ
    # لها هنا يعني أن يفترقا أوّلَ ما يتغيّر أحدُهما.
    standing = Q(vehicles__bids__is_superseded=False, vehicles__bids__is_withdrawn=False)
    # **والذي يتغيّر هو الحياةُ لا الوجود.** كُتب أوّلَ مرّةٍ `Q()` لغير
    # الجاري، فسقط شرطُ «عليها مزايدة» كلُّه وصار `with_bids` يعدّ **كلَّ**
    # سياراته — فظهر «مزاد ١٠٠٢: مزايدات ٠ · عليها عروض ٢»، وهو التناقضُ
    # نفسُه الذي وقع في v1 («١٩٥ مزايدة» بجوار «٠ سيارة عليها عروض»).
    # فالشرطُ قائمٌ دائماً: مزايدةٌ موجودة، وفي الجاري تكون قائمةً أيضاً.
    exists = Q(vehicles__bids__isnull=False)
    bid_filter = mine & (standing if live_only else exists)

    return rows.annotate(
        mine=Count("vehicles", filter=mine, distinct=True),
        sold=Count(
            "vehicles",
            filter=mine & Q(vehicles__state__in=AWARDED),
            distinct=True,
        ),
        # إحصاءُ v1 لكلّ مزاد: كم عرضاً، ومن كم شخص، وكم سيارةً عليها عرض.
        bids=Count("vehicles__bids", filter=bid_filter, distinct=True),
        bidders=Count("vehicles__bids__bidder", filter=bid_filter, distinct=True),
        with_bids=Count("vehicles", filter=bid_filter, distinct=True),
        # **ومبالغُ المركبات باستعلامٍ فرعيّ لا بـ`Sum` على الوصلة.**
        #
        # عطلٌ قِيس على الشاشة: «كل المزادات» تعرض لمزاد ١٠٠١ «سعر الوقوف
        # ٩٦٠٬٠٠٠» و«المبيعات ٢١٩٬٠٠٠»، والصحيحُ ٣٢٠٬٠٠٠ و٧٣٬٠٠٠ —
        # **ثلاثةُ أضعاف**، وعددُ مزايدات كلّ مركبةٍ ثلاث.
        #
        # والسببُ أن الأعمدة أعلاه تصل `vehicles__bids`، فتتضاعف صفوفُ
        # المركبة بعدد مزايداتها ويُجمع سعرُ وقوفها مرّةً لكلّ مزايدة. و
        # `distinct=True` يعالج `Count` ولا يعالج `Sum` — لأن مبلغين
        # متساويين ليسا تكراراً يُحذف.
        #
        # وكان الرقمُ يناقض نفسَه على شاشتين: «الأداء لكل مزاد» في لوحة
        # الشريك لا تصل المزايدات فتقول ٧٣٬٠٠٠، وهذه تقول ٢١٩٬٠٠٠.
        reserve=_money_of(mine_sub, "reserve_price"),
        reserve_sold=_money_of(mine_sub.filter(state__in=AWARDED), "reserve_price"),
        sales=_money_of(mine_sub, "awarded_price"),
        top_bid=Max("vehicles__bids__amount", filter=mine),
    ).order_by(
        # **الترتيبُ يتبع الحال** كـ v1: المزادُ الجاري شيءٌ عاجل، فالأقربُ
        # قفلاً أوّلاً لأنه الذي يحتاج قراراً. والمنتهي تاريخٌ، فالأحدثُ أوّلاً.
        *(("ends_at", "number") if live_only else ("-starts_at", "-number"))
    )


def cars_in(partner: str, auctions, live_only: bool = False) -> dict[int, list]:
    """سيارات الشريك في مزاداتٍ بعينها، مجموعةً بمزادها — جدولُ v1 داخلَ كلّ قسم.

    **وهو محتوى الشاشة لا زينتُها.** صفحةُ v1 لكلّ حالٍ («قريباً» و«نشط»
    و«منتهي») تعرض تحت كلّ مزادٍ **سياراتِ الشريك فيه**؛ وكانت الشاشةُ هنا
    صفَّ مزادٍ وحده، فمن يسأل «أيُّ سياراتي في مزاد الخميس؟» — وهو سؤالُ
    الشاشة الأوّل قبل مزادٍ لم يُفتح — لا يجد جواباً إلا بفتح المزاد.

    واستعلامٌ واحدٌ لمزادات الصفحة كلِّها، ثم تجميعٌ في الذاكرة: خمسون مزاداً
    تعني خمسين استعلاماً لو سُئل كلُّ قسمٍ عن سياراته (المادة ٢).

    و«المزايدة» تتبع الحال كما في `auctions_of`: الجاري تُعدّ فيه القائمةُ
    وحدَها، والمنتهي تاريخُه كلُّه — وإلّا قرأ المنتهي صفراً لأن مزايداتِه
    تصير مرفوضةً عند التسوية.
    """
    if not str(partner).strip().isdigit() or not auctions:
        return {}

    standing = Q(bids__is_superseded=False, bids__is_withdrawn=False)
    rows = (
        Vehicle.objects.filter(
            auction__in=auctions, owner_company_id=int(partner)
        )
        .select_related("auction")
        .annotate(
            top_amount=Max("bids__amount", filter=standing if live_only else Q()),
            bids_count=Count(
                "bids", filter=standing if live_only else Q(), distinct=True
            ),
        )
        .order_by("auction", "lot_number")
    )

    grouped: dict[int, list] = {}
    for vehicle in rows:
        # الفرقُ عن سعر الوقوف — عمودُ v1 في الشاشة الجارية. ولا يُحسب في
        # القالب: لغةُ القوالب لا تطرح.
        vehicle.gap = (
            (vehicle.top_amount - (vehicle.reserve_price or ZERO))
            if vehicle.top_amount is not None
            else None
        )
        grouped.setdefault(vehicle.auction_id, []).append(vehicle)
    return grouped


def state_totals(rows, partner: str, kind: str) -> dict:
    """شريطُ أرقامِ الحالة — على الطابور كلِّه لا على الصفحة.

    v1 يجمعها على المزادات المعروضة ويضع فوقها بطاقاتٍ تختلف بالحال: القادمُ
    لا مبيعاتِ له ولا مزايدات، فبطاقتان؛ والجاري سؤالُه «هل يزايد أحد»؛
    والمنتهي «بكم بعت». وبطاقةٌ تقول صفراً لأن الحدثَ لم يقع بعدُ تُقرأ «لم
    يزايد أحد» لا «لم يُفتح المزاد».

    **وتُجمع من المركبات لا من أعمدة `auctions_of`.** جُرّب
    ``rows.aggregate(Sum("mine"))`` فسقط: `mine` نفسُها `Count` مجمَّعة،
    وجانغو يكتب `SUM("sold")` على عمودٍ لا وجود له — ``column "sold" does
    not exist``. والجمعُ من المصدر أصحُّ أيضاً: تعريفُ «سياراته» يبقى في
    `_scoped` وحدَه.
    """
    cars = _scoped(Vehicle.objects.filter(auction__in=rows.values("pk")), partner)
    money_row = cars.aggregate(
        n=Count("id"),
        reserve=Sum("reserve_price"),
        sales=Sum("awarded_price", filter=Q(state__in=AWARDED)),
        reserve_sold=Sum("reserve_price", filter=Q(state__in=AWARDED)),
        sold=Count("id", filter=Q(state__in=AWARDED)),
    )

    # «المزايدة» تتبع الحال كما في `auctions_of`: الجاري تُعدّ فيه القائمةُ
    # وحدَها، والمنتهي تاريخُه كلُّه — وإلّا قرأ المنتهي صفراً لأن مزايداتِه
    # تصير مرفوضةً عند التسوية.
    bids = Bid.objects.filter(vehicle__in=cars)
    if kind == "live":
        bids = bids.filter(is_superseded=False, is_withdrawn=False)
    demand = bids.aggregate(n=Count("id"), on=Count("vehicle", distinct=True))

    total = money_row["n"] or 0
    sold = money_row["sold"] or 0
    with_bids = demand["on"] or 0
    reserve_sold = money_row["reserve_sold"] or ZERO
    sales = money_row["sales"] or ZERO

    return {
        "kind": kind,
        "auctions": rows.count(),
        "cars": total,
        "sold": sold,
        "unsold": total - sold,
        "bids": demand["n"] or 0,
        "with_bids": with_bids,
        "no_bids": total - with_bids,
        "reserve": money_row["reserve"] or ZERO,
        "sales": sales,
        "rate": round(sold / total * 100, 1) if total else 0.0,
        "coverage": round(with_bids / total * 100, 1) if total else 0.0,
        # **الزيادةُ على وقوفِ المُباع وحدَه.** v1 يقسم على وقوفِ الجميع
        # فيُنتج سالباً دائماً على مزادٍ باع نصفَه — العطلُ المُصلَح في لوحة
        # الشريك وفي «الأداء لكل مزاد»، ولا يُعاد هنا.
        "uplift": (
            round((sales - reserve_sold) / reserve_sold * 100, 1)
            if reserve_sold
            else 0.0
        ),
    }


def state_counts(partner: str = "") -> dict:
    """عدّادُ كلّ حالٍ — الأرقامُ في شرائح v1 الثلاث.

    **والعدّادُ هو ما يجعل الشريحةَ معلومةً لا رابطاً مكرَّراً.** الشاشاتُ
    الثلاثُ في الشريط الجانبيّ أصلاً؛ وما ليس فيه أن «القادمة صفر والمنتهية
    اثنان» — وهو ما يوفّر فتحَ شاشتين فارغتين. وv1 يكتبه: «قريباً (0) · نشط
    (0) · منتهي (2)».
    """
    base = Auction.objects.all()
    if (partner or "").strip().isdigit():
        base = base.filter(vehicles__owner_company_id=int(partner)).distinct()
    return {
        "soon": base.filter(state=AuctionState.SCHEDULED).count(),
        # «الشغّال» بالساعة لا بالعمود، كما في `partner_active` — وعدّادٌ
        # يقول ٣ وشاشةٌ تفتح على صفرٍ أسوأ من غياب العدّاد.
        "live": base.filter(state=AuctionState.LIVE, pk__in=engine.open_now()).count(),
        "ended": base.filter(state__in=ARCHIVED).count(),
    }


def _auctions_screen(request, state: str = "", *, only=None, screen=None):
    """جسمُ شاشة مزادات الشريك — يشترك فيه أربعةُ مداخل.

    ولماذا أربعةُ **دوالّ** فوقه لا دالّةٌ واحدة بأربعة مسارات: `console_page`
    يأخذ اسمَ صفحةٍ واحدة ويقرأ قدرتَها من السجلّ. ودالّةٌ واحدة تخدم أربعة
    أسماء تعني أن ثلاثةً منها **محروسةٌ بصفِّ رابعة** — وهو بعينه الافتراق
    الذي وُجد `navigation.py` لمنعه. فالجسم مشترك، والحراسةُ لكلٍّ صفُّه.
    """
    partner = (request.GET.get("partner") or "").strip()
    kind = (screen or {}).get("kind", "")
    companies = partners()

    # **شاشاتُ الحال الثلاث بلا مُنتقٍ، وشريكٌ واحدٌ دائماً** (قرار المالكة،
    # ٢٠ سبتمبر ٢٠٢٦: «شيل دي»). وهي شاشاتُ «سياراتي في المزاد»: جدولُ
    # السيارات تحت كلّ مزادٍ لا يُبنى أصلاً بلا شريكٍ مختار، فتُفتح الشاشةُ
    # على مزاداتٍ بلا محتواها وسطرٍ يقول «اختر شريكاً» — أي أنها لا تعمل حتى
    # يُنقَر شيء. والافتراضيُّ أوّلُ الشركاء بالاسم، كما في لوحة الشريك.
    #
    # و«كل المزادات» تُبقي مُنتقيها: هي شاشةُ نظرةٍ عامّة فيها قائمةُ حالٍ
    # أيضاً، و«كل الشركاء» فيها جوابٌ صحيح.
    company = None
    if kind:
        company = companies.filter(pk=int(partner)).first() if partner.isdigit() else None
        if company is None:
            company = companies.first()
        partner = str(company.pk) if company else ""

    rows = auctions_of(partner, state or request.GET.get("state", ""))
    if only is not None:
        # `only` ضيقٌ على ما بناه `auctions_of`، لا استعلامٌ بديل: الفلترةُ
        # بالشريك تبقى واحدةً لكل المداخل الأربعة، ويضيف المدخلُ شرطَه فوقها.
        rows = rows.filter(pk__in=only)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    # النسبتان تُحسبان هنا لا في القالب: لغةُ القوالب لا تقسم، وحسابُهما في
    # `annotate` يعني `Case/When` على كلّ صفٍّ لاتّقاء القسمة على صفر.
    for row in page.object_list:
        row.rate = round(row.sold / row.mine * 100, 1) if row.mine else 0.0
        row.coverage = round(row.with_bids / row.mine * 100, 1) if row.mine else 0.0
        # **الفرقُ على وقوفِ المُباع.** كان على وقوفِ الجميع، فمزادٌ لم
        # يُفتح بعد يُقرأ خسارةً بمبلغ أسعار وقوفه كلِّها — العطلُ نفسُه
        # المُصلَح في «الأداء لكل مزاد».
        row.diff = (row.sales or ZERO) - (row.reserve_sold or ZERO)

    cars = cars_in(partner, [row.pk for row in page.object_list], state == AuctionState.LIVE)
    for row in page.object_list:
        row.cars = cars.get(row.pk, [])

    return render(
        request,
        "console/partner_auctions.html",
        {
            "page": page,
            "partner": partner,
            "partners": companies,
            "company": company,
            "state": state,
            # **العنوانُ يقول أيَّ المداخل الأربعة هذا.** القالبُ واحدٌ
            # لأربعة صفوفٍ في الشريط الجانبي (كلُّ المزادات · القادمة ·
            # الشغال · المنتهية)، وكان يكتب «مزادات الشريك» في الأربعة —
            # فمن ضغط «المزاد الشغال» يقرأ العنوانَ نفسَه الذي قرأه قبل
            # ضغطه، ولا يعرف أنَّ الترشيح وقع.
            "screen": screen or {
                "title": "مزادات الشريك",
                "say": "كلُّ مزاداته، بلا ترشيحٍ على الحالة.",
            },
            # **قائمةُ الحالة تُرسَم في مدخلٍ واحد.** المداخلُ الثلاثةُ
            # الأخرى تُثبّت حالتَها في الدالّة (`AuctionState.LIVE` وأختاها)
            # وتتجاهل ما يصل في `GET` — فقائمةٌ فيها تعرض «كل الحالات» على
            # شاشةٍ مرشَّحةٍ بالفعل، ويختار منها الموظّفُ فلا يقع شيء.
            # وخانةٌ لا تفعل شيئاً أسوأُ من غيابها: تُقرأ عطلاً.
            "may_pick_state": screen is None,
            # **هل اختير شريك؟** بلا شريكٍ يصير `mine` عدَّ مركبات المزاد
            # كلِّها (`Q()` فارغةٌ لا تُرشّح شيئاً)، فعمودٌ عنوانُه «سياراته»
            # يعرض ٣٨٦ وهي سياراتُ المزاد لا سياراتِ أحد — أي أن الشاشةَ
            # تناقض السطرَ الذي تحذّر به من هذا الخلط بعينه.
            "picked": str(partner).strip().isdigit(),
            "states": [
                (value, AuctionState(value).label) for value in AuctionState.values
            ],
            # **أيُّ حالٍ هذه الشاشة** — والقالبُ يبني بها أعمدتَه وبطاقاتِه.
            # «القادمة» لا مبيعاتِ لها ولا مزايدات، وعمودٌ لا يحمل إلا صفراً
            # يُقرأ «لم يزايد أحد» لا «لم يُفتح المزاد».
            "kind": kind,
            "totals": state_totals(rows, partner, kind) if kind else None,
            # شرائحُ v1 الثلاث بعدّاداتها — وهي معلومةٌ لا تكرارٌ للشريط:
            # «قريباً (0) · نشط (0) · منتهي (2)» يوفّر فتحَ شاشتين فارغتين.
            "counts": state_counts(partner) if kind else None,
        },
    )


@console_page("console:partner-auctions")
def partner_auctions(request):
    """كل مزادات الشريك، بلا ترشيحٍ على الحالة."""
    return _auctions_screen(request, request.GET.get("state", ""))


@console_page("console:partner-auction")
def partner_auction(request, pk: int):
    """سيارات الشريك في مزادٍ بعينه — نظيرُ `partner/auction_vehicles.php`.

    **والوجهةُ هي المسألة.** «فتح ←» في قائمة v1 تذهب إلى
    `/partner/auctions/{id}`: صفحةٌ **مقصورةٌ على سياراته** في ذلك المزاد.
    وكانت هنا تذهب إلى صفحة المزاد العامّة — التي تعرض مركباته **كلَّها**
    (٣٨٦ في مزادٍ للشريك منها ٢٠٦) ومعها «إضافة مركبة» و«تعديل المزاد»
    و«رفع إكسل». فمن دخل من قسم الشريك يقرأ حصّةً ليست له، ويرى أزرارَ
    إدارةٍ لا شأنَ لسؤاله بها. وهو الخلطُ نفسُه الذي بُني عمودُ «سياراته»
    لمنعه.

    والصفحةُ لا تحكم: القبولُ والرفضُ في «اتخاذ القرار» وحدَها كما في v1،
    وهذه للاطّلاع — فلا يكون للقرار مدخلان أحدُهما بلا شرط انتهاء المزاد.
    """
    from django.shortcuts import get_object_or_404

    auction = get_object_or_404(Auction, pk=pk)
    partner = (request.GET.get("partner") or "").strip()
    companies = partners()
    company = companies.filter(pk=int(partner)).first() if partner.isdigit() else None
    if company is None:
        # أوّلُ شريكٍ **له مركبةٌ في هذا المزاد** لا أوّلُ الشركاء مطلقاً:
        # صفحةُ مزادٍ تُفتح على شريكٍ لا سيارةَ له فيه تقول «لا سيارات» وهي
        # مليئة.
        company = companies.filter(vehicles__auction=auction).first() or companies.first()
    partner = str(company.pk) if company else ""

    live = auction.state == AuctionState.LIVE
    cars = cars_in(partner, [auction.pk], live).get(auction.pk, [])
    pending = sum(1 for car in cars if car.partner_decided_at is None)

    return render(
        request,
        "console/partner_auction.html",
        {
            "auction": auction,
            "cars": cars,
            "company": company,
            "partner": partner,
            "pending": pending,
            "live": live,
            "ended": auction.state in ARCHIVED,
        },
    )


@console_page("console:partner-soon")
def partner_soon(request):
    """المزادات القادمة — المجدولة وحدها."""
    return _auctions_screen(
        request,
        AuctionState.SCHEDULED,
        screen={
            "kind": "soon",
            "title": "المزادات القادمة",
            "say": "المجدولةُ وحدَها — لم تُفتح للمزايدة بعد.",
        },
    )


@console_page("console:partner-active")
def partner_active(request):
    """المزاد الشغال — الجاري الآن **بالساعة**، لا بالعمود وحده.

    الشريكُ يفتح هذه ليرى أين ماله الآن. ومزادٌ حالتُه `live` وانتهى وقتُه
    ولم يُغلَق بعدُ ليس شغّالاً: لا مزايدةَ تُقبل فيه، وعرضُه هنا يقول للشريك
    إن سيارته ما زالت تُنافس عليها وهي لا تُنافس.
    """
    return _auctions_screen(
        request,
        AuctionState.LIVE,
        only=engine.open_now(),
        screen={
            "kind": "live",
            "title": "المزاد الشغال",
            "say": (
                # بلا نجمتين: النصُّ يُخرَج مهرَّباً في القالب، فـ`**` تُرسم
                # كما هي — رُئي «**بالساعة**» على الشاشة.
                "الجاري الآن بالساعة لا بالعمود وحده: مزادٌ حالتُه «جارٍ» "
                "وانتهى وقتُه ولم يُغلَق بعدُ ليس شغّالاً — لا مزايدةَ تُقبل "
                "فيه، وعرضُه هنا يقول للشريك إن سيارته ما زالت تُنافَس عليها "
                "وهي لا تُنافَس."
            ),
        },
    )


@console_page("console:partner-ended")
def partner_ended(request):
    """المزادات المنتهية — بتعريف الأرشيف نفسه: منتهٍ ومُسوّى وملغى."""
    return _auctions_screen(
        request,
        ARCHIVED,
        screen={
            "kind": "ended",
            "title": "المزادات المنتهية",
            "say": "بتعريف الأرشيف نفسِه: منتهٍ ومُسوّى وملغى.",
        },
    )


def vehicles_of(partner: str = "", which: str = "", text: str = ""):
    """سيارات الشريك، بمرشّحات v1 الأربعة: الكل · مباعة · غير مباعة · تنتظر قراره.

    **و«تنتظر قراره» تعني ما يعنيه v1 لا ما كانت تعنيه هنا.** كان المرشّح
    `state = AWAITING_DECISION` — وتلك حالةُ مركبةٍ تنتظر قرارَ **المالك**،
    وقائمةُ الاختيار نفسُها كانت تقول «بانتظار قرار المالك». فالشريحةُ لم تكن
    تجيب سؤالَ v1 أصلاً: هناك الشرطُ `partner_decided_at IS NULL` — أي ما لم
    يحكم فيه **الشريك** بعد.

    والسؤالان مختلفان في الاتجاه: مركبةٌ حكم فيها الشريكُ وتنتظر المالك تظهر
    في القديم **لا** وفي الجديد **نعم** — وهي أكثرُ ما يقرؤه الشريك.

    ويُضاف شرطُ «المزاد منتهٍ» كما في صفحة القرار: قرارٌ قبل انتهاء المزاد
    مرفوضٌ أصلاً (409 في v1)، فعرضُه في طابورٍ اسمه «ينتظر قرارك» وعدٌ كاذب.

    وعددُ المزايدات وأعلى عرضٍ يُحسبان هنا لا في القالب: عمودان في v1، وحسابُهما
    في حلقةٍ على الصفوف يعني استعلامين لكلّ صفّ.
    """
    rows = (
        _scoped(
            Vehicle.objects.select_related("auction", "awarded_to", "owner_company"),
            partner,
        )
        .annotate(bids_count=Count("bids", distinct=True), top_bid=Max("bids__amount"))
        .order_by("-id")
    )

    if which == "sold":
        rows = rows.filter(state__in=AWARDED)
    elif which == "unsold":
        rows = rows.exclude(state__in=AWARDED).exclude(
            state=VehicleState.AWAITING_DECISION
        )
    elif which == "deciding":
        rows = rows.filter(
            auction__state__in=ARCHIVED, partner_decided_at__isnull=True
        )

    text = (text or "").strip()
    if text:
        # ستّةُ حقولٍ كـ v1، ومنها **رقم المطالبة**: لا يُعرف أيُّ رقمٍ في يد
        # السائل — قد تكون بيده ورقةٌ فيها رقمُ المطالبة وحده.
        matches = search_q(text, "plate_number", "vin", "make", "model", "claim_number")
        if text.isdigit():
            matches |= Q(lot_number=int(text)) | Q(auction__number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:partner-vehicles")
def partner_vehicles(request):
    """كل سيارات الشريك — ونتيجةُ كلٍّ منها وقرارُ المالك فيها."""
    partner = request.GET.get("partner", "")
    which = request.GET.get("which", "")
    rows = vehicles_of(partner, which, request.GET.get("q", ""))

    if wants_export(request):
        return export(
            rows,
            name="سيارات-الشريك",
            headers=[
                "المعرّف",
                "اللوت",
                "المزاد",
                "السيارة",
                "السنة",
                "اللوحة",
                "رقم المطالبة",
                # والشاصي يبقى في **الملفّ** وإن غاب عن الشاشة: الورقةُ تُقرأ
                # بعيداً عن اللوحة وقد يكون هو المفتاحَ الوحيدَ بيد قارئها،
                # والعرضُ فيها لا يُزاحم أحداً.
                "الشاصي",
                "البداية",
                "أعلى عرض",
                "مزايدات",
                "النتيجة",
                "قراري",
            ],
            cell=lambda row: [
                row.pk,
                row.lot_number,
                row.auction.number,
                f"{row.make} {row.model}",
                row.year,
                row.plate_number,
                row.claim_number,
                row.vin,
                row.reserve_price,
                row.top_bid,
                row.bids_count,
                row.awarded_to.full_name if row.awarded_to else row.get_state_display(),
                row.get_partner_decision_display() or "بانتظار قراري",
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/partner_vehicles.html",
        {
            "page": page,
            "partner": partner,
            "partners": partners(),
            "which": which,
            "q": request.GET.get("q", ""),
            "totals": summary_for(partner),
            # الشرائحُ الأربعُ من مكانٍ واحد: القالبُ يرسمها والمنظرُ يعرفها،
            # فإضافةُ خامسةٍ يوماً سطرٌ واحد لا سطران يفترقان.
            # ورسمٌ لكلّ شريحة من `icons.py`: أربعُ كلماتٍ متشابهةِ الطول في
            # صفٍّ واحد تُقرأ بالقراءة وحدها، والرسمُ يجعل الاختيارَ يُلتقط
            # بالنظر. وv1 يضع `✅ ⏳ 🔔` — يرسمها نظامُ التشغيل فتخرج بأساليبَ
            # مختلفة (T837).
            # ولكلٍّ **نبرتُها** لا لونٌ يُختار: `ok` للمباع و`warn` لما لم
            # يُبَع و`bad` لما ينتظر قراراً — وهي النبراتُ نفسُها التي تلوّن
            # شاراتِ الحالة في كلّ جداول اللوحة. فلونُ الشريحة يقول ما يقوله
            # لونُ الصفّ الذي تفتحه، ولا يُتعلَّم لونان لمعنًى واحد.
            "chips": (
                ("", "الكل", path_of("grid"), "plain"),
                ("sold", "مباعة", path_of("check"), "ok"),
                # «غير مباعة» **`info` لا `warn`.** ونبرتُها الدلاليّة `warn`،
                # لكنّ `--warn` في هذه اللوحة ورديٌّ (`#f0a6c6`) و`--danger`
                # سلمونيٌّ (`#fca19a`) — درجتان متجاورتان، وشريحتان متجاورتان
                # بهما لا يفترقان بالنظر وهو كلُّ غرض التلوين. و`info`
                # (`#93b8ff`) يفصلهما، و«لم تُبَع» خبرٌ لا إنذار.
                ("unsold", "غير مباعة", path_of("hourglass"), "info"),
                ("deciding", "بانتظار قراره", path_of("scale"), "bad"),
            ),
        },
    )


def settlement_of(partner: str = "", paid: bool = False):
    """تسويةُ الشريك — **من حالة الفاتورة**، لا من جدولٍ يُرفع بملفّ.

    وسيارةٌ رست بلا فاتورةٍ بعد تُعدّ غير مسدَّدة: هي كذلك فعلاً، ولا يُخفيها
    غيابُ الفاتورة عن الطابور الذي ينتظر عملاً.
    """
    rows = _scoped(
        Vehicle.objects.filter(state__in=AWARDED).select_related(
            "auction", "awarded_to", "owner_company"
        ),
        partner,
        # الترتيبُ بالمزاد ثم اللوط لا بتاريخ الترسية: الشاشةُ تُجمَّع
        # بالمزاد كما في v1، والتجميعُ يمرّ على صفوف الصفحة مرّةً واحدةً —
        # فمزادٌ متقطّعٌ في الترتيب يصير مجموعتين برأسٍ مكرَّر.
    ).order_by("-auction__number", "lot_number")

    # استعلامٌ فرعيّ لا مجموعةٌ في بايثون: قائمةُ معرّفاتٍ من عشرة آلاف صفّ
    # تُبنى في الذاكرة ثم تُرسَل `IN (...)` بعشرة آلاف قيمة — والقاعدة تعرف
    # كيف تفعلها أفضل، ولا يتغيّر الجواب بين قراءتين.
    settled = Invoice.objects.filter(vehicle=OuterRef("pk"), state=InvoiceState.PAID)
    marked = rows.annotate(is_settled=Exists(settled))
    return marked.filter(is_settled=True) if paid else marked.filter(is_settled=False)


def _payment_facts(invoices) -> dict[int, tuple]:
    """متى وصل مالُ كلِّ فاتورة ومن أين — من الدفتر، لا من عمودٍ يُكتب مرّةً.

    **ولا يُقرأ من عمود لأنّه لا وجود له**: الدفعةُ حركةٌ في الدفتر ولا مفتاحَ
    أجنبيّاً منها إلى الفاتورة. والرابطُ مفتاحُ المنع، **وله شكلان**:
    ``payment:<pk>:<ref>`` يكتبه `money.services.record_payment`، و
    ``invoice-payment:<number>:<ref>`` يكتبه `pay_invoice_from_balance`.

    ولذلك تُقرأ القاعدةُ من `console.payments` ولا تُنسَخ هنا: كُتب هذا أوّلَ
    مرّةٍ بالشكل الأوّل وحدَه، **فخرج عمودُ التاريخ فارغاً على كلّ فاتورةٍ
    سُدِّدت من الرصيد** — وهي في قاعدة التطوير الفاتورةُ المسدَّدة الوحيدة.
    وشرطةٌ تُقرأ «لم يُسجَّل» وهي في الحقيقة «قرأتُ نصفَ المفاتيح».

    واستعلامٌ واحدٌ للصفحة لا واحدٌ لكلّ صفّ (المادة ٢).
    """
    if not invoices:
        return {}

    shapes = []
    by_pk, by_number = {}, {}
    for invoice in invoices:
        by_pk[invoice.pk] = invoice.pk
        by_number[invoice.number] = invoice.pk
        shapes.append(Q(idempotency_key__startswith=f"{payments.KEY_BY_PK}{invoice.pk}:"))
        shapes.append(
            Q(idempotency_key__startswith=f"{payments.KEY_BY_NUMBER}{invoice.number}:")
        )

    facts: dict[int, tuple] = {}
    rows = Transaction.objects.filter(
        reduce(operator.or_, shapes), kind__in=payments.PAYMENT_KINDS
    ).values_list("idempotency_key", "occurred_at")
    for key, when in rows:
        shape, value = payments.invoice_of(key)
        pk = by_pk.get(value) if shape == "pk" else by_number.get(value)
        if pk is None:
            continue
        if pk not in facts or when > facts[pk][0]:
            facts[pk] = (when, payments.source_of(key))
    return facts


#: حكمُ الشريك كما يُقرأ — v1 يكتب «بانتظار قرارك» لأن قارئَه الشريك، وقارئُ
#: هذه الشاشة موظّفٌ يسأل عن شريكٍ اختاره، فالضميرُ يتغيّر مع القارئ.
_RULINGS = {
    "accepted": ("قبِله الشريك", "ok"),
    "rejected": ("رفضه الشريك", "danger"),
}


def _settlement_groups(rows, paid: bool) -> list[dict]:
    """اجمع صفوفَ الصفحة تحت مزاداتها، ومع كلِّ مزادٍ حسابُه — تجميعُ v1.

    **الجدولُ المسطّح كان يقول الأرقامَ نفسَها ولا يجيب السؤال.** من يفتح
    «غير المسدَّدة» يسأل «كم بقي على مزاد كذا» لا «كم بقي إجمالاً»، وهو رقمٌ
    لا يُستخرج من جدولٍ مسطّحٍ إلا بالعدّ باليد على أربعين صفّاً. وv1 يجمعها
    كذلك ويضع تحت رأس كلّ مزادٍ عدَّه ومجموعَه.

    والتجميعُ على صفوف الصفحة لا على الاستعلام كلِّه (كما في
    `partners._group_by_auction`): استعلامٌ ثانٍ ليجمع ثمنٌ لا يُدفع لأجل
    رأسِ مجموعةٍ يقطعه ترقيمُ الصفحات مرّةً كلَّ خمسين صفّاً.
    """
    groups: list[dict] = []
    for row in rows:
        if not groups or groups[-1]["auction"].pk != row.auction_id:
            groups.append(
                {
                    "auction": row.auction,
                    "rows": [],
                    "money": ZERO,
                    "with_vat": ZERO,
                }
            )
        group = groups[-1]
        group["rows"].append(row)
        group["money"] += row.settled_amount if paid else row.due_amount
        group["with_vat"] += row.due_with_vat
    return groups


def _settlement_screen(request, paid: bool):
    """جسمُ شاشة التسوية — طابوران، ولكلٍّ صفُّه في السجلّ."""
    partner = request.GET.get("partner", "")
    rows = settlement_of(partner, paid)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    invoices = {
        invoice.vehicle_id: invoice
        for invoice in Invoice.objects.filter(vehicle__in=page.object_list).order_by(
            "issued_at", "id"
        )
    }
    facts = _payment_facts(list(invoices.values())) if paid else {}

    for vehicle in page.object_list:
        invoice = invoices.get(vehicle.pk)
        vehicle.invoice = invoice
        vehicle.invoice_state = money.derive_invoice_state(invoice) if invoice else ""
        # **الاسمُ العربيُّ لا القيمة.** كان القالبُ يطبع `invoice_state`
        # نفسَها، فيقرأ الموظّفُ `open` و`partial` في شاشةٍ عربيّةٍ كلِّها —
        # وهو العطلُ نفسُه الذي أُصلح في «ما بعد البيع» بـ`state_label`.
        # والقيمةُ تبقى كما هي لمن يرشّح بها.
        vehicle.invoice_label = state_label(vehicle.invoice_state)

        # ثلاثةُ أرقامٍ لا رقمٌ واحد — وعمودُ v1 «شامل الضريبة» جنبَ المبلغ
        # لأنّ السؤال «ده شامل الضريبة؟» كان يتكرّر على كلّ شاشة، والعمودُ
        # الواحد لا يجيب عنه.
        price = vehicle.awarded_price or ZERO
        vehicle.due_amount = invoice.outstanding if invoice else price
        vehicle.settled_amount = invoice.amount_paid if invoice else ZERO
        # **ولا تُضرَب النسبةُ هنا.** `tax_of` تقرأ المكوّنات المختومة على
        # فاتورةٍ أصدرناها، و`tax_added_to` تضرب على مبلغٍ لا فاتورةَ له بعد —
        # وهي الموضعُ الوحيد الذي يضرب في المشروع كلِّه.
        vehicle.due_with_vat = (
            money.tax_of(invoice).total if invoice else money.tax_added_to(price).total
        )
        # ومصدرُ الدفعة يقوم مقام عمود «ملاحظة» في v1: هناك خانةٌ حرّةٌ
        # يكتبها رافعُ الملفّ، وهنا مشتقٌّ من مرجع الدفعة في الدفتر.
        vehicle.paid_at, vehicle.paid_from = (
            facts.get(invoice.pk) or (None, "") if invoice else (None, "")
        )
        vehicle.ruling, vehicle.ruling_tone = _RULINGS.get(
            vehicle.partner_decision, ("بانتظار قرار الشريك", "warn")
        )

    groups = _settlement_groups(page.object_list, paid)
    return render(
        request,
        "console/partner_settlement.html",
        {
            "page": page,
            "groups": groups,
            "partner": partner,
            "partners": partners(),
            "paid": paid,
            "totals": summary_for(partner),
            # ثلاثةُ أرقامِ v1 فوق الجدول: كم سيارةً · في كم مزاداً · وكم
            # مالُها. وهي **على الصفحة المعروضة** لا على الطابور كلِّه، ولذلك
            # تُسمّى في القالب باسمها.
            "kpi": {
                "vehicles": len(page.object_list),
                "auctions": len(groups),
                "money": sum((g["money"] for g in groups), ZERO),
            },
        },
    )


@console_page("console:partner-unpaid")
def partner_unpaid(request):
    """غير المسدَّدة — ما رسا ولم تُسدَّد فاتورتُه."""
    return _settlement_screen(request, paid=False)


@console_page("console:partner-paid")
def partner_paid(request):
    """المسدَّدة — ما وصل مالُه فعلاً."""
    return _settlement_screen(request, paid=True)


def payments_of(partner: str = ""):
    """دفعاتُ الشريك — **صفٌّ لكلِّ دفعة**، من الدفتر.

    كانت هذه الدالّة تُعيد **فواتيرَ** وصل منها مال، وتسمّي الشاشةَ «سجل
    الدفعات». والفرقُ ليس تسمية:

    * فاتورةٌ سُدِّدت على قسطين تُقرأ **دفعةً واحدة**، فيُسأل «فين الدفعة
      التانية؟» وهي مقيَّدةٌ في الدفتر؛
    * والتاريخُ المعروضُ كان `issued_at` — **تاريخَ إصدار الفاتورة لا وصولِ
      المال**. وفي سجلِّ دفعاتٍ يُقرأ عمودُ «التاريخ» تاريخَ الدفعة، ولا شيء
      على الشاشة يقول غيرَ ذلك.

    وv1 يعرضها دفعةً دفعةً (`payments` صفوفاً)، وهو الصواب هنا.

    **والنطاقُ يُدفع إلى القاعدة لا يُبنى في الذاكرة.** الدفعةُ لا مفتاحَ
    أجنبيّاً لها إلى الفاتورة — الرابطُ مفتاحُ المنع بشكليه (`console.payments`)
    — فتُشقّ بادئتُه ومرجعُه في القاعدة بـ`split_part` ويُقارَنان باستعلامَين
    فرعيَّين. والبديلُ قائمةُ معرّفاتٍ بآلاف القيم تُرسَل `IN (...)`.
    """
    cars = _scoped(Vehicle.objects.filter(state__in=AWARDED), partner)
    invoices = Invoice.objects.filter(vehicle__in=cars)

    split = lambda part: Func(  # noqa: E731
        F("idempotency_key"),
        Value(":"),
        Value(part),
        function="split_part",
        output_field=CharField(),
    )
    mine = Q(
        shape=payments.KEY_BY_PK.rstrip(":"),
        ref__in=invoices.annotate(text=Cast("pk", CharField())).values("text"),
    ) | Q(
        shape=payments.KEY_BY_NUMBER.rstrip(":"),
        ref__in=invoices.values("number"),
    )
    return (
        Transaction.objects.filter(kind__in=payments.PAYMENT_KINDS)
        .annotate(shape=split(1), ref=split(2))
        .filter(mine)
        .prefetch_related("entries__owner")
        .order_by("-occurred_at", "-id")
    )


@console_page("console:partner-payments")
def partner_payments(request):
    """سجل دفعات الشريك — **الدفعات المسجَّلة**، لا صفوفَ ملفٍّ مرفوع.

    v1 يعرض هنا ما رُفع بإكسل ويقول في شاشته الأخرى «تجنّب رفع الملف نفسه
    مرتين حتى لا تُسجَّل الدفعة مرتين» — أي أن التفرُّد تذكيرٌ لا مفتاح. وهنا
    الصفُّ دفعةٌ على فاتورة، ولها معرّفُها ومصدرُها وتاريخُها من الدفتر.
    """
    partner = request.GET.get("partner", "")
    rows = payments_of(partner)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    page_rows = list(page.object_list)
    payments.decorate(page_rows)

    # المركبةُ عمودان في v1 (اللوط واللوحة) وليست على الحركة: تُقرأ من فواتير
    # الصفحة باستعلامٍ واحد.
    vehicles = {
        vehicle.pk: vehicle
        for vehicle in Vehicle.objects.filter(
            pk__in={row.invoice.vehicle_id for row in page_rows if row.invoice}
        ).select_related("auction")
    }
    for row in page_rows:
        row.vehicle = vehicles.get(row.invoice.vehicle_id) if row.invoice else None

    return render(
        request,
        "console/partner_payments.html",
        {
            "page": page,
            "rows": page_rows,
            "partner": partner,
            "partners": partners(),
            # **مجموعُ الطابور كلِّه لا الصفحة.** «إجمالي المعتمد» في v1 جوابُ
            # «كم قبضنا له»، وصفحةٌ من خمسين تجيب عن خمسين.
            #
            # ويُجمع في القاعدة لا بالمرور على الصفوف: `Transaction` لا عمودَ
            # مبلغٍ له — الحركةُ طرفان — فيُجمع الطرفُ الموجب من `Entry`
            # باستعلامٍ واحد. والمرورُ على ثلاثةَ عشرَ ألفَ قيدٍ في بايثون
            # لجمع عمودٍ هو ما يجعل الصفحةَ تُحمَّل في ثوانٍ.
            "total": Entry.objects.filter(
                transaction__in=rows, amount__gt=ZERO
            ).aggregate(t=Sum("amount"))["t"]
            or ZERO,
        },
    )


@console_page("console:partner-rule")
def partner_rule(request, pk: int):
    """اختِم حكمَ شريك التسويق على سيارته — البابُ الذي يفكّ قفل القرار.

    الخدمةُ (`auctions.services.record_partner_ruling`) تحمل الشروط كلَّها:
    سيارةُ تسويقٍ، ومزادٌ انتهى، وحكمٌ لم يُختَم قبلاً. وهذه الشاشةُ بابٌ إليها
    لا نسخةٌ منها — فما يُرفض هنا يُرفض من أي طريقٍ آخر.

    وليست فعلَ المنصّة على السيارة: الحكمُ **إذنٌ** للمنصّة أن تقرّر، والقرارُ
    بعده في شاشة العروض. ولذلك لا تنقل حالةً ولا تُرسي.
    """
    from django.shortcuts import get_object_or_404, redirect

    from apps.auctions import services as auction_services
    from apps.auctions.models import PartnerDecision
    from apps.core import audit

    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction"), pk=pk
    )
    back = redirect(request.POST.get("next") or "console:partner-vehicles")

    if request.method != "POST":
        return back

    decision = (request.POST.get("decision") or "").strip()
    if decision not in PartnerDecision.values:
        messages.error(request, "حكمٌ غير معروف.")
        return back

    try:
        auction_services.record_partner_ruling(
            vehicle, decision=decision, actor=request.user
        )
    except (auction_services.PartnerRulingPending, ValueError) as refusal:
        messages.error(request, str(refusal))
        return back

    audit.record(
        action="console.partner_ruling",
        entity=vehicle,
        actor=request.user,
        after={"partner_decision": decision},
        note=(request.POST.get("reason") or "").strip(),
    )
    messages.success(
        request, f"سُجّل حكم الشريك: {vehicle.get_partner_decision_display()}."
    )
    return back
