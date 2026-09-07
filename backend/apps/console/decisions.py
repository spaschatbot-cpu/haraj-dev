"""قرارات المزايدات: ما رسا، وملخّصُه. T830-أ.

الشاشتان من قائمة v1 (`/bills/accepted` و`/auctions/bids/accepted-summary`)،
وهما قراءةٌ محضة: لا ترسية تُطلَق من هنا ولا فاتورةٌ تُصدَر. الترسية في
`apps.auctions.services` وحدها، والفاتورة في `apps.money.services` — وشاشةٌ
تعرض ما وقع لا يجوز أن تكون بابَ تغييرٍ فيه.

ثلاثة فروقٍ عن v1، كلٌّ منها من عطلٍ مقيسٍ في الإنتاج
=====================================================

**١ — «مقبولة» تعني صفّاً واحداً لكل مركبة.** شاشة v1 تعرض ٤٬٣٧٨ صفّاً،
وعشرةٌ منها المتتالية لمركبةٍ واحدة (`معرف 1017`، اللوحة `6996 ر أ و`) بعشرة
مزايدين ومبالغ من `6,777` إلى `315,000`، **وكلُّها بحالة «مقبول»**. ومن قرأها
ظنَّ عشرة فائزين على سيارة. والمبالغ تكشف السبب: `مسافه التوصيل` وحده ثلاثة
صفوف (`6,777` ثم `10,777` ثم `20,777`) — أي مزايداتٌ متتالية لشخصٍ واحد،
والمستبدَلةُ منها تُعرض «مقبولة».

فهذه الشاشة تُبنى على **المركبة** لا على المزايدة: `Vehicle.awarded_to`
واحدٌ بقيدٍ في القاعدة (`an_awarded_vehicle_names_its_winner`)، فصفٌّ واحدٌ
لكلّ مركبةٍ رست — لا يُمكن غيرُه.

**٢ — الضريبة لا تُحسب هنا.** v1 يكتب `15%` عموداً نصّياً ويضرب فيه. وفي هذا
المستودع `money.services.tax_of` هي **الموضع الوحيد** الذي يضرب في النسبة،
و`ops/checks/one_tax_rule.py` يُسقط البناء على ثانٍ — لأن الفاتورة التي نصدرها
نحن تحمل مبلغاً **قبل** الضريبة، والتي تصل من أودو تحمله **شاملاً**؛ ومعادلةٌ
واحدة عليهما تُحمّل العميل ١٥٪ على رقمٍ فيه ١٥٪ أصلاً.

ولذلك: **الضريبة تُقرأ من الفاتورة، لا من سعر الترسية.** المركبة التي رست ولم
تُفوتَر بعدُ تعرض `—` في عمودَي الضريبة والإجمالي، وتقول «بلا فاتورة». وذلك
ليس نقصاً في الشاشة — هو الحقيقة: لا ضريبةَ على مبلغٍ لم يُفوتَر، والرقم الذي
كان سيُعرَض هناك تخمينٌ.

**٣ — الملخّص يعدّ ما تعدّه القائمة.** في v1 تقول «المزايدات المقبولة»
٤٬٣٧٨ صفّاً و«ملخّص المقبولة» بجوارها `0.00` و`0.00` و`0` — لأن فلترَ الأولى
«مقبول» وفلترَ الثانية «نشطة/مقبولة»، فالشاشتان تعدّان شيئين مختلفين تحت اسمٍ
واحد. وهنا الملخّص يستدعي `awarded()` نفسها التي تبنيها القائمة، بالمرشّحات
نفسها — فرقمُه **هو** عدد صفوفها بحكم البناء، ويثبت ذلك اختبارٌ يقارنهما.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.money import services as money
from apps.money.models import Invoice

from .exports import export, wants_export
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")

PAGE_SIZE = 50

#: المركبة التي رست. تُقرأ من الحالة لا من وجود `awarded_to`: الحالتان
#: متلازمتان بقيدٍ في القاعدة، والقراءة من الحالة تُفهرَس.
AWARDED = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)


def awarded(*, text: str = "", first: str = "", last: str = ""):
    """المركبات التي رست، الأحدث ترسيةً أولاً — صفٌّ واحدٌ لكلٍّ منها.

    مفصولةٌ عن العرض ليسألها الاختبار والملخّصُ **الاستعلام نفسه**: ادّعاءُ أن
    الرقمين يعدّان الشيء ذاته يجب أن يكون خاصيّةَ بناءٍ لا وعداً في تعليق.

    `select_related` على الثلاثة لأن كل صفٍّ يعرض اسم الفائز وجوّاله ورقم
    المزاد: بدونها صفحةٌ من ٥٠ صفّاً تساوي ١٥١ استعلاماً.
    """
    rows = (
        Vehicle.objects.filter(state__in=AWARDED, awarded_to__isnull=False)
        .select_related("auction", "awarded_to", "owner_company")
        .order_by("-awarded_at", "-id")
    )

    text = (text or "").strip()
    if text:
        # ما يُتذكَّر من مركبةٍ رست: لوحتها، أو شاصيها، أو اسم من أخذها، أو
        # رقم مزادها. ولا يُعرف أيُّها في يد السائل، فتُطابَق الأربعة.
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(awarded_to__full_name__icontains=text)
            | Q(awarded_to__phone__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
        )
        if text.isdigit():
            matches |= Q(auction__number=int(text)) | Q(lot_number=int(text))
        rows = rows.filter(matches)

    # مدى أرقام المزادات كما في v1 («من رقم مزاد» / «إلى رقم مزاد»). والقيمة
    # غيرُ الرقمية تُهمَل ولا تُسقِط الصفحة: خانةٌ يكتب فيها موظّفٌ حرفاً
    # فتُرمى 500 هي خانةٌ لا تُستعمل مرّةً ثانية.
    if (first or "").strip().isdigit():
        rows = rows.filter(auction__number__gte=int(first))
    if (last or "").strip().isdigit():
        rows = rows.filter(auction__number__lte=int(last))

    return rows


def money_of(vehicle: Vehicle) -> dict:
    """ما تحمله هذه الترسية من مالٍ — **من فاتورتها إن وُجدت**.

    ولا يُحسب هنا شيء: `tax_of` هي القارئ الوحيد للنسبة في المستودع، وتنظر في
    `Invoice.source` قبل أن تضرب. والمركبة بلا فاتورةٍ تُرجع `None` في
    الثلاثة — لا أصفاراً: الصفر رقمٌ يُجمَع، و«لا يوجد» ليس صفراً.
    """
    invoice = (
        Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
    )
    if invoice is None:
        return {"invoice": None, "base": None, "tax": None, "total": None}

    split = money.tax_of(invoice)
    return {
        "invoice": invoice,
        "base": split.base,
        "tax": split.tax,
        "total": split.total,
    }


@console_page("console:accepted-bids")
def accepted_bids(request):
    """المزايدات المقبولة: صفٌّ لكل مركبةٍ رست، ومالُها من فاتورتها."""
    rows = awarded(
        text=request.GET.get("q", ""),
        first=request.GET.get("from", ""),
        last=request.GET.get("to", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="المزايدات-المقبولة",
            headers=[
                "المزاد",
                "اللوت",
                "المركبة",
                "السنة",
                "اللوحة",
                "رقم الهيكل",
                "الفائز",
                "الجوال",
                "سعر الترسية",
                "الحالة",
                "رقم الفاتورة",
                "قبل الضريبة",
                "الضريبة",
                "الإجمالي",
            ],
            cell=lambda row: [
                row.auction.number,
                row.lot_number,
                f"{row.make} {row.model}",
                row.year,
                row.plate_number,
                row.vin,
                row.awarded_to.full_name,
                row.awarded_to.phone,
                row.awarded_price or ZERO,
                row.get_state_display(),
                *_export_money(row),
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    # الفاتورة تُقرأ لصفحةٍ واحدة لا للاستعلام كلّه: `money_of` استعلامٌ لكل
    # صفّ، وخمسون منها مقبولةٌ في صفحة، وأربعةُ آلافٍ في تصدير ليست كذلك —
    # ولذلك التصدير يمرّ بـ`_export_money` التي تقرأ من `prefetch`.
    for vehicle in page.object_list:
        vehicle.money = money_of(vehicle)

    return render(
        request,
        "console/accepted_bids.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "first": request.GET.get("from", ""),
            "last": request.GET.get("to", ""),
        },
    )


def _export_money(vehicle: Vehicle) -> list:
    """الأعمدة المالية الأربعة في التصدير — أو أربع فراغات."""
    split = money_of(vehicle)
    if split["invoice"] is None:
        return ["", "", "", ""]
    return [
        split["invoice"].number,
        split["base"],
        split["tax"],
        split["total"],
    ]


def summary(*, text: str = "", first: str = "", last: str = "") -> dict:
    """أرقام الملخّص — من `awarded()` نفسها التي تبني القائمة.

    و«قبل الضريبة» هنا هو **مجموع أسعار الترسية**، و«بعد الضريبة» مجموعُ
    إجماليّات الفواتير الصادرة عليها. والاثنان لا يتساويان بالضرورة ولا يُراد
    لهما ذلك: الفرق هو ما رسا ولم يُفوتَر بعد، وهو رقمٌ يُقرأ — لا فجوةٌ
    تُخبَّأ بضربِ الأول في النسبة.
    """
    rows = awarded(text=text, first=first, last=last)

    awarded_total = rows.aggregate(t=Sum("awarded_price"))["t"] or ZERO

    invoiced = Invoice.objects.filter(vehicle__in=rows)
    invoiced_total = ZERO
    invoiced_tax = ZERO
    for invoice in invoiced.iterator():
        split = money.tax_of(invoice)
        invoiced_total += split.total
        invoiced_tax += split.tax

    count = rows.count()
    return {
        "count": count,
        "awarded_total": awarded_total,
        "invoiced_count": invoiced.count(),
        "invoiced_total": invoiced_total,
        "invoiced_tax": invoiced_tax,
        "uninvoiced_count": count - invoiced.count(),
    }


@console_page("console:accepted-summary")
def accepted_summary(request):
    """ملخّص المقبولة: ثلاثةُ أرقامٍ، وكلٌّ منها بابٌ إلى صفوفه."""
    text = request.GET.get("q", "")
    first = request.GET.get("from", "")
    last = request.GET.get("to", "")

    return render(
        request,
        "console/accepted_summary.html",
        {
            "totals": summary(text=text, first=first, last=last),
            "q": text,
            "first": first,
            "last": last,
        },
    )
