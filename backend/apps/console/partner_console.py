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

from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Exists, Max, OuterRef, Q, Sum
from django.shortcuts import render

from apps.accounts.models import Company
from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.bidding.models import Bid
from apps.auctions.states import AuctionState, VehicleState
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

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
            reserve=Sum("vehicles__reserve_price", filter=Q(vehicles__in=cars)),
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
                "diff": sales - reserve,
            }
        )
    return out


@console_page("console:partner-console")
def partner_console(request):
    """لوحة الشريك: أرقامُ شريكٍ واحد، وكلٌّ منها بابٌ إلى صفوفه."""
    partner = request.GET.get("partner", "")
    return render(
        request,
        "console/partner_console.html",
        {
            "totals": summary_for(partner),
            "breakdown": breakdown_for(partner),
            "partner": partner,
            "partners": partners(),
        },
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
    return rows.annotate(
        mine=Count("vehicles", filter=mine, distinct=True),
        sold=Count(
            "vehicles",
            filter=mine & Q(vehicles__state__in=AWARDED),
            distinct=True,
        ),
    ).order_by("-starts_at", "-number")


def _auctions_screen(request, state: str = "", *, only=None, screen=None):
    """جسمُ شاشة مزادات الشريك — يشترك فيه أربعةُ مداخل.

    ولماذا أربعةُ **دوالّ** فوقه لا دالّةٌ واحدة بأربعة مسارات: `console_page`
    يأخذ اسمَ صفحةٍ واحدة ويقرأ قدرتَها من السجلّ. ودالّةٌ واحدة تخدم أربعة
    أسماء تعني أن ثلاثةً منها **محروسةٌ بصفِّ رابعة** — وهو بعينه الافتراق
    الذي وُجد `navigation.py` لمنعه. فالجسم مشترك، والحراسةُ لكلٍّ صفُّه.
    """
    partner = request.GET.get("partner", "")
    rows = auctions_of(partner, state or request.GET.get("state", ""))
    if only is not None:
        # `only` ضيقٌ على ما بناه `auctions_of`، لا استعلامٌ بديل: الفلترةُ
        # بالشريك تبقى واحدةً لكل المداخل الأربعة، ويضيف المدخلُ شرطَه فوقها.
        rows = rows.filter(pk__in=only)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/partner_auctions.html",
        {
            "page": page,
            "partner": partner,
            "partners": partners(),
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
        },
    )


@console_page("console:partner-auctions")
def partner_auctions(request):
    """كل مزادات الشريك، بلا ترشيحٍ على الحالة."""
    return _auctions_screen(request, request.GET.get("state", ""))


@console_page("console:partner-soon")
def partner_soon(request):
    """المزادات القادمة — المجدولة وحدها."""
    return _auctions_screen(
        request,
        AuctionState.SCHEDULED,
        screen={
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
                "الشاصي",
                "سعر الوقوف",
                "سعر الترسية",
                "مزايدات",
                "أعلى عرض",
                "الحالة",
                "الفائز",
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
                row.awarded_price,
                row.bids_count,
                row.top_bid,
                row.get_state_display(),
                row.awarded_to.full_name if row.awarded_to else "",
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
    ).order_by("-awarded_at", "-id")

    # استعلامٌ فرعيّ لا مجموعةٌ في بايثون: قائمةُ معرّفاتٍ من عشرة آلاف صفّ
    # تُبنى في الذاكرة ثم تُرسَل `IN (...)` بعشرة آلاف قيمة — والقاعدة تعرف
    # كيف تفعلها أفضل، ولا يتغيّر الجواب بين قراءتين.
    settled = Invoice.objects.filter(vehicle=OuterRef("pk"), state=InvoiceState.PAID)
    marked = rows.annotate(is_settled=Exists(settled))
    return marked.filter(is_settled=True) if paid else marked.filter(is_settled=False)


def _settlement_screen(request, paid: bool):
    """جسمُ شاشة التسوية — طابوران، ولكلٍّ صفُّه في السجلّ."""
    partner = request.GET.get("partner", "")
    rows = settlement_of(partner, paid)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    for vehicle in page.object_list:
        invoice = (
            Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
        )
        vehicle.invoice = invoice
        vehicle.invoice_state = money.derive_invoice_state(invoice) if invoice else ""
        # **الاسمُ العربيُّ لا القيمة.** كان القالبُ يطبع `invoice_state`
        # نفسَها، فيقرأ الموظّفُ `open` و`partial` في شاشةٍ عربيّةٍ كلِّها —
        # وهو العطلُ نفسُه الذي أُصلح في «ما بعد البيع» بـ`state_label`.
        # والقيمةُ تبقى كما هي لمن يرشّح بها.
        vehicle.invoice_label = state_label(vehicle.invoice_state)

    return render(
        request,
        "console/partner_settlement.html",
        {
            "page": page,
            "partner": partner,
            "partners": partners(),
            "paid": paid,
            "totals": summary_for(partner),
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


@console_page("console:partner-payments")
def partner_payments(request):
    """سجل دفعات الشريك — **الدفعات المسجَّلة**، لا صفوفَ ملفٍّ مرفوع.

    v1 يعرض هنا ما رُفع بإكسل ويقول في شاشته الأخرى «تجنّب رفع الملف نفسه
    مرتين حتى لا تُسجَّل الدفعة مرتين» — أي أن التفرُّد تذكيرٌ لا مفتاح. وهنا
    الصفُّ دفعةٌ على فاتورة، ولها معرّفُها ومصدرُها وتاريخُها من الدفتر.
    """
    partner = request.GET.get("partner", "")
    cars = _scoped(Vehicle.objects.filter(state__in=AWARDED), partner)

    rows = (
        Invoice.objects.filter(vehicle__in=cars, amount_paid__gt=ZERO)
        .select_related("customer", "vehicle", "vehicle__auction")
        .order_by("-issued_at", "-id")
    )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(
        request,
        "console/partner_payments.html",
        {
            "page": page,
            "partner": partner,
            "partners": partners(),
            "total": rows.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
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
