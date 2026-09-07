"""كتالوج السيارات، والبحث عنها، وما بعد البيع، والخروج. T830د.

أربع شاشاتٍ من قسم «إدارة المزادات» في v1، وكلُّها استعلامٌ واحد على
:class:`Vehicle` بمرشّحاتٍ مختلفة — ولذلك ملفٌّ واحد: الفرق بينها **سؤالٌ**
لا بنية.

| الشاشة | السؤال الذي تُفتح لأجله |
|---|---|
| كتالوج السيارات | ما الذي عندنا، وبأي حال؟ |
| بحث عن سيارة | أين هذه السيارة بعينها؟ |
| ما بعد البيع | ما الذي بيع، ولمن، وهل وصل ماله؟ |
| الخروج ونقل الملكية | ما الذي بيع وسُدِّد ولم يخرج بعد؟ |

خمسة أعطالٍ مقيسةٍ في v1 لا تُنقَل
===================================

**١ — «رقم الموقف» يحمل مفتاحين من نظامين.** في الكتالوج `384` في صفٍّ
و`AUC-1017-743` في آخر. وعمودٌ كهذا لا يُفرَز ولا يُبحث فيه برقمٍ فيجد نصفَه.
وهنا `lot_number` عددٌ صحيح، والبحث برقمٍ يجد كلَّ ما يطابقه.

**٢ — `...` و`—` قيمتان في العمود نفسه.** «العداد `...`» و«العداد `—`» في
صفّين متجاورين، ولا أحد يعرف أيّهما «لم يُقَس». وهنا `odometer_km` رقمٌ أو
`NULL`، والقالب يكتب `—` لواحدةٍ لا لاثنتين.

**٣ — «مدفوعة» تعني «لها فاتورة أودو».** في «ما بعد البيع» رقمُ الفاتورة
شكلان: `317263` (شكل v1) و`INV/2026/08267` (شكل أودو)، **وثلاثةُ صفوفٍ فقط من
الخمسين تحمل الثاني — وهي وحدها «مدفوعة»**. فالعمود لا يقول «وصل المال» بل
«صار لها معرّفٌ هناك».

وهذا عطلُ T809 نفسه: `derive_invoice_state` بُنيت لأنه v1 يعكس حالة أودو في
عمودٍ يُكتب مرّةً عند الإدخال، فحوالةٌ في أودو كمسودّة تظهر «مدفوعة» — وأُخرجت
سيارةٌ مقابلها. فحالة الفاتورة هنا **مشتقّةٌ من الدفعات المسجَّلة**، وكلمةُ
أودو تُعرض بجوارها دليلاً لا حقيقة.

**٤ — عمود المزاد يقول `0`.** في «الخروج ونقل الملكية» الخمسون صفّاً كلُّها
`المزاد 0`، والسيارة خرجت من مزادٍ له رقم. وهذه أسوأ من عمودٍ بقيمةٍ واحدة
صحيحة: **القيمة خاطئة**، والربط لم يُقرأ. وهنا رقمُ المزاد يأتي من
`vehicle.auction.number` بمفتاحٍ أجنبي، فلا يكون صفراً.

**٥ — «حالة الخروج: لم يُنشأ» في اثني عشر ألفاً.** أي أن الشاشة التي تُفتح
لتُتابِع نقل الملكية لا تعرف عن نقلٍ واحد. وهنا الخروج **حالةٌ في المركبة**
(`VehicleState.RELEASED`) تكتبها `auctions.services` وحدها، فما يُعرض هنا هو
ما وقع فعلاً.

وعمودان من v1 لا مقابل لهما هنا — ويُقالان
==========================================
**اللون** و**شركة التأمين** حقلان في v1 وليسا في :class:`Vehicle`. ولا
يُخترعان: عمودٌ فارغٌ في كل صفّ أسوأ من عمودٍ غائب.

و«شركة التأمين» يجب أن تُحسم قبل أن تُنقَل أصلاً: قيمتها في الإنتاج تشمل
`الشركة التعاونية للتامين التعاوني` وتشمل **`مشتريات خارجيه`** — والثانية
ليست شركة تأمين، هي **مصدرُ المركبة**. فالعمود يحمل معنيين، ونقلُه كما هو
ينقل الالتباس. القرار للمالك: حقلُ «مصدر» وحقلُ «مؤمِّن»، لا واحدٌ لهما.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from apps.auctions import engine
from apps.auctions.models import Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.money import services as money
from apps.money.models import Invoice

from .exports import export, wants_export
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50

#: ما يُعدّ مبيعاً. الترسية بيعٌ وقع؛ وما بعدها خطواتُ تحصيلٍ لا خطواتُ بيع.
SOLD = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)

#: ما ينتظر خروجاً: بيع وسُدِّد ولم يخرج. و`AWARDED` و`INVOICED` خارجها عمداً
#: — لا تُسلَّم سيارةٌ لم يصل مالُها، وشاشةٌ تعرضها في طابور الخروج تدعو إلى
#: ذلك. (وv1 يعرض اثني عشر ألفاً كلُّها «لم يُنشأ»، بلا تمييزٍ بين ما سُدِّد
#: وما لم يُسدَّد أصلاً.)
AWAITING_EXIT = (VehicleState.PAID,)


def _dated(rows, field: str, since: str, until: str):
    """ضيّق بمدىً من التواريخ — وتجاهل ما ليس تاريخاً.

    `parse_date` تُرجع `None` لما لا يُقرأ، فخانةٌ يكتب فيها موظّفٌ حرفاً
    تُقرأ «لا مرشّح» لا «لا نتائج» ولا خطأ ٥٠٠.
    """
    start = parse_date((since or "").strip())
    end = parse_date((until or "").strip())
    if start:
        rows = rows.filter(**{f"{field}__date__gte": start})
    if end:
        rows = rows.filter(**{f"{field}__date__lte": end})
    return rows


def catalogue(
    *,
    text: str = "",
    state: str = "",
    listed_from: str = "",
    listed_to: str = "",
    auction_from: str = "",
    auction_to: str = "",
):
    """كل المركبات، بمرشّحات v1 الستّة.

    و`Count` على الصور مرّةً واحدة في الاستعلام لا استعلاماً لكل صفّ: عمودُ
    «الصور» يعرض عددها، وخمسون صفّاً بخمسين استعلاماً هو ما يجعل صفحةً
    تُفتح في ثانيتين.
    """
    rows = (
        Vehicle.objects.select_related("auction", "owner_company", "awarded_to")
        .annotate(image_count=Count("images", distinct=True))
        .order_by("-id")
    )

    text = (text or "").strip()
    if text:
        matches = (
            Q(vin__icontains=text)
            | Q(plate_number__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
        )
        if text.isdigit():
            matches |= Q(lot_number=int(text)) | Q(auction__number=int(text))
        rows = rows.filter(matches)

    state = (state or "").strip()
    if state in AuctionState.values:
        rows = rows.filter(auction__state=state)

    rows = _dated(rows, "created_at", listed_from, listed_to)
    rows = _dated(rows, "auction__starts_at", auction_from, auction_to)
    return rows


def catalogue_totals() -> dict:
    """البطاقات الأربع في رأس الكتالوج — كما في v1، بأسمائها.

    ومحسوبةٌ من الجداول لا من عمودٍ مخزَّن: جرد T302 وجد في v1 ثلاثة أعمدة
    رصيدٍ مشتقّة كلّها تُهمَل، والعدّاد المخزَّن من نفس العائلة.
    """
    return {
        "vehicles": Vehicle.objects.count(),
        "live_auctions": engine.open_now().count(),
        "with_images": Vehicle.objects.filter(images__isnull=False).distinct().count(),
        "invoiced": Vehicle.objects.filter(invoices__isnull=False).distinct().count(),
    }


@console_page("console:vehicle-catalog")
def vehicle_catalog(request):
    """كتالوج السيارات: ما عندنا، وبأي حال."""
    rows = catalogue(
        text=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
        listed_from=request.GET.get("listed_from", ""),
        listed_to=request.GET.get("listed_to", ""),
        auction_from=request.GET.get("auction_from", ""),
        auction_to=request.GET.get("auction_to", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="كتالوج-السيارات",
            headers=[
                "المعرّف",
                "اللوت",
                "المزاد",
                "السيارة",
                "السنة",
                "العداد",
                "الحالة الفنية",
                "ناقل الحركة",
                "الوقود",
                "الشاصي",
                "اللوحة",
                "الصور",
                "حالة المزاد",
                "بداية المزاد",
                "نهاية المزاد",
                "حالة المركبة",
                "سعر الوقوف",
            ],
            cell=lambda row: [
                row.pk,
                row.lot_number,
                row.auction.number,
                f"{row.make} {row.model}",
                row.year,
                row.odometer_km,
                row.get_condition_display(),
                row.get_transmission_display(),
                row.get_fuel_type_display(),
                row.vin,
                row.plate_number,
                row.image_count,
                row.auction.get_state_display(),
                row.auction.starts_at,
                row.auction.ends_at,
                row.get_state_display(),
                row.reserve_price,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/vehicle_catalog.html",
        {
            "page": page,
            "totals": catalogue_totals(),
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "listed_from": request.GET.get("listed_from", ""),
            "listed_to": request.GET.get("listed_to", ""),
            "auction_from": request.GET.get("auction_from", ""),
            "auction_to": request.GET.get("auction_to", ""),
            "states": [
                (value, AuctionState(value).label) for value in AuctionState.values
            ],
        },
    )


def found(*, plate: str = "", vin: str = "", name: str = "", lot: str = ""):
    """بحثٌ **لكل عمودٍ على حدة**، كما في v1: صفُّ خاناتٍ تحت الرؤوس.

    والفرق عن خانةٍ واحدة ليس ذوقاً: من يبحث بلوحةٍ يعرف أنها لوحة، وخانةٌ
    واحدة تطابق النصّ في ستّة أعمدة تُرجع له صفوفاً لا يفهم لماذا ظهرت.
    والاثنان معاً يضيّقان — `لكزس` في الاسم و`2024` في اللوت يعنيان الاثنين.
    """
    rows = Vehicle.objects.select_related("auction", "awarded_to").order_by("-id")

    plate = (plate or "").strip()
    vin = (vin or "").strip()
    name = (name or "").strip()
    lot = (lot or "").strip()

    if not any((plate, vin, name, lot)):
        return None

    if plate:
        rows = rows.filter(plate_number__icontains=plate)
    if vin:
        rows = rows.filter(vin__icontains=vin)
    if name:
        rows = rows.filter(Q(make__icontains=name) | Q(model__icontains=name))
    if lot.isdigit():
        rows = rows.filter(lot_number=int(lot))
    return rows


@console_page("console:vehicle-search")
def vehicle_search(request):
    """بحث عن سيارة: خانةٌ لكل عمود، ولا تفتح على القائمة كلّها.

    `None` قبل أن يُكتب شيء — لا الثلاثةَ عشرَ ألفاً: قائمةٌ كاملة على شاشةٍ
    اسمها «بحث» تعني أن أول ما يراه القارئ ليس جوابَ سؤاله.
    """
    rows = found(
        plate=request.GET.get("plate", ""),
        vin=request.GET.get("vin", ""),
        name=request.GET.get("name", ""),
        lot=request.GET.get("lot", ""),
    )

    page = None
    if rows is not None:
        page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
        with_tones(page.object_list)

    return render(
        request,
        "console/vehicle_search.html",
        {
            "page": page,
            "plate": request.GET.get("plate", ""),
            "vin": request.GET.get("vin", ""),
            "name": request.GET.get("name", ""),
            "lot": request.GET.get("lot", ""),
        },
    )


def sold(*, text: str = "", state: str = ""):
    """ما بيع: مركبةٌ رست ومعها من أخذها وفاتورتها."""
    rows = (
        Vehicle.objects.filter(state__in=SOLD)
        .select_related("auction", "awarded_to")
        .order_by("-awarded_at", "-id")
    )

    text = (text or "").strip()
    if text:
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
            | Q(awarded_to__full_name__icontains=text)
            | Q(awarded_to__phone__icontains=text)
        )
        if text.isdigit():
            matches |= Q(lot_number=int(text)) | Q(auction__number=int(text))
        rows = rows.filter(matches)

    state = (state or "").strip()
    if state in VehicleState.values:
        rows = rows.filter(state=state)
    return rows


def invoice_of(vehicle: Vehicle) -> dict:
    """فاتورةُ هذه المركبة وحالتُها — **مشتقّةً من الدفعات لا من عمود**.

    وهذا هو T809 بعينه: v1 يعكس حالة أودو في عمودٍ يُكتب مرّةً عند الإدخال،
    فحوالةٌ هناك كمسودّة تظهر هنا «مدفوعة» — وأُخرجت سيارةٌ مقابلها. وكلمةُ
    أودو تُعرض بجوار الحالة **دليلاً** لا حقيقة.
    """
    invoice = (
        Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
    )
    if invoice is None:
        return {"invoice": None, "state": "", "odoo": ""}
    return {
        "invoice": invoice,
        "state": money.derive_invoice_state(invoice),
        "odoo": invoice.odoo_state_raw,
    }


@console_page("console:after-sales")
def after_sales(request):
    """ما بعد البيع: ما بيع، ولمن، وهل وصل مالُه."""
    rows = sold(text=request.GET.get("q", ""), state=request.GET.get("state", ""))
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    for vehicle in page.object_list:
        vehicle.billing = invoice_of(vehicle)

    return render(
        request,
        "console/after_sales.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "states": [(value, VehicleState(value).label) for value in SOLD],
        },
    )


@console_page("console:vehicle-exit")
def vehicle_exit(request):
    """الخروج ونقل الملكية: ما سُدِّد ولم يخرج، وما خرج.

    لسانان لا أربعة: v1 عنده «إنشاء الخروج» و«متابعة نقل الملكية» و«أرشيف
    المنقولة» و«البوابة»، **وكلُّها تعرض الصفوف نفسها بحالة «لم يُنشأ»**.
    فالتقسيم هناك أربع شاشاتٍ لحالةٍ واحدة لم تُسجَّل قطّ؛ وهنا الحالة تُقرأ
    من المركبة، فاللسانان هما ما تحمله فعلاً.
    """
    which = request.GET.get("state", "awaiting")
    states = AWAITING_EXIT if which != "released" else (VehicleState.RELEASED,)

    rows = (
        Vehicle.objects.filter(state__in=states)
        .select_related("auction", "awarded_to")
        .order_by("-awarded_at", "-id")
    )

    text = (request.GET.get("q", "") or "").strip()
    if text:
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
            | Q(awarded_to__full_name__icontains=text)
            | Q(awarded_to__phone__icontains=text)
        )
        if text.isdigit():
            matches |= Q(auction__number=int(text))
        rows = rows.filter(matches)

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/vehicle_exit.html",
        {
            "page": page,
            "q": text,
            "which": which,
            "awaiting_count": Vehicle.objects.filter(state__in=AWAITING_EXIT).count(),
            "released_count": Vehicle.objects.filter(state=VehicleState.RELEASED).count(),
        },
    )
