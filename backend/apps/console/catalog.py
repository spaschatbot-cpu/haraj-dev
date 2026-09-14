"""كتالوج السيارات، والبحث عنها، والخروج. T830د.

ثلاثُ شاشاتٍ من قسم «إدارة المزادات» في v1، وكلُّها استعلامٌ واحد على
:class:`Vehicle` بمرشّحاتٍ مختلفة — ولذلك ملفٌّ واحد: الفرق بينها **سؤالٌ**
لا بنية.

| الشاشة | السؤال الذي تُفتح لأجله |
|---|---|
| كتالوج السيارات | ما الذي عندنا، وبأي حال؟ |
| بحث عن سيارة | أين هذه السيارة بعينها؟ |
| الخروج ونقل الملكية | ما الذي بيع وسُدِّد ولم يخرج بعد؟ |

و«ما بعد البيع» خرجت من هنا إلى `after_sales.py` (T869): صارت خمسَ مرشّحاتٍ
وستّةَ عشرَ عموداً وبطاقاتٍ ونافذةَ فاتورةٍ وتصديراً — أي أنها لم تعد
«الاستعلامَ نفسَه بسؤالٍ آخر»، وهو الشرطُ الذي جمع هذه الشاشات في ملفّ.

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

عمودان كانا غائبين ثم صارا حقلين — والفقرةُ صُحّحت
====================================================
كان مكتوباً هنا أن **اللون** و**شركة التأمين** «حقلان في v1 وليسا في
:class:`Vehicle`، ولا يُخترعان». **وذلك لم يعد صحيحاً**: `colour` و
`insurance_company` حقلان في الموديل اليوم، وعمودان مرسومان في
`vehicle_catalog.html`. صُحّح في مراجعة ١٤ سبتمبر ٢٠٢٦.

وما بقي صحيحاً منها اثنان، وكلاهما مقيسٌ على `haraj2_t307`:

* **اللون لا يحمل معلومة**: `colour = unknown` في ١٢٬٩٨٥ من ١٢٬٩٨٨ صفّاً.
  فالعمود يُرسم و«غير معروف» جوابُه في كل صفّ تقريباً، ولا يُرشَّح به هنا.
* **و«شركة التأمين» تحمل معنيين** — مملوءةٌ في ١٢٬٩٤٩ صفّاً — وقيمتُها في
  الإنتاج تشمل `الشركة التعاونية للتامين التعاوني` وتشمل **`مشتريات خارجيه`**
  — والثانية ليست شركة تأمين، هي **مصدرُ المركبة**. ونقلُ العمود كما هو نقل
  الالتباسَ معه. القرار للمالك: حقلُ «مصدر» وحقلُ «مؤمِّن»، لا واحدٌ لهما.
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
from apps.core.arabic import fold, search_q
from apps.core.permissions import Capability, can
from apps.money.models import InvoiceSource

from .dashboard import Stat
from .exports import export, wants_export
from .icons import path_of
from .tones import with_tones
from .vehicle_filters import keep
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


def _day(raw: str):
    """يومٌ من نصّ المستخدم، أو ``None`` — ولا خطأ ٥٠٠.

    `parse_date` تُرجع `None` لما **لا يشبه** تاريخاً («أمس»)، لكنها **ترفع**
    `ValueError` لما يشبهه ولا يوجد: `2026-02-30` يطابق `date_re` ثم يسقط في
    `datetime.date(2026, 2, 30)`. وكان مكتوباً هنا أن الخانة «تُقرأ لا مرشّح
    لا خطأ ٥٠٠» — **وهي تُخرج ٥٠٠ فعلاً**: قِيس على `:8001` في ١٤ سبتمبر
    ٢٠٢٦، `?listed_from=2026-02-30` و`?auction_from=2026-13-01` كلاهما
    `HTTP 500`. والخانة `<input type="date">` لا تُخرج ذلك، لكنّ الرابط يُكتب
    بيدٍ ويُحفظ في مفضّلةٍ ويُرسَل في رسالة.
    """
    try:
        return parse_date((raw or "").strip())
    except ValueError:
        return None


def _int(raw: str) -> int | None:
    """عددٌ صحيحٌ من نصّ المستخدم بعد طيّ أرقامه، أو ``None``.

    `str.isdigit()` تقول «نعم» لثلاثةٍ لا يقبل `int` منها إلا واحداً: `١٢٣`
    تمرّ، و`²` و`⑤` ترفعان `ValueError`. فـ`?q=²` كان **٥٠٠** على الكتالوج
    والبحث معاً (قِيس على `:8001` في ١٤ سبتمبر ٢٠٢٦). و`fold` تحلّ الاثنين
    معاً: تطوي `٠-٩` و`۰-۹` إلى ASCII كما يفعل `foldArabicDigits` في v1، ثم
    `NFKC` تردّ `²` إلى `2` و`⑤` إلى `5`. فما بقي بعدها رقماً لاتينياً
    فهو رقم، وما عداه ليس مرشّحاً.
    """
    digits = fold(raw)
    return int(digits) if digits.isascii() and digits.isdigit() else None


def _dated(rows, field: str, since: str, until: str):
    """ضيّق بمدىً من التواريخ — وتجاهل ما ليس تاريخاً."""
    start = _day(since)
    end = _day(until)
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
        matches = search_q(text, "vin", "plate_number", "make", "model")
        number = _int(text)
        if number is not None:
            matches |= Q(lot_number=number) | Q(auction__number=number)
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


def _catalog_cards(totals: dict) -> list[Stat]:
    """البطاقاتُ الأربع بشكل كروتٍ منظّمة — نظيرُ رأس كتالوج v1، بأرقامه."""
    return [
        Stat(
            label="إجمالي المركبات",
            value=f"{totals['vehicles']:,}",
            detail="كلُّ ما في القاعدة، على اختلاف حالاته.",
            tone="auction",
            icon="car",
        ),
        Stat(
            label="مزادات جارية",
            value=f"{totals['live_auctions']:,}",
            detail="مفتوحةٌ للمزايدة الآن.",
            tone="plain",
            icon="gavel",
        ),
        Stat(
            label="سيارات بصور",
            value=f"{totals['with_images']:,}",
            detail="لها صورةٌ واحدة على الأقل في المعرض.",
            tone="plain",
            icon="eye",
        ),
        Stat(
            label="سيارات مفوترة",
            value=f"{totals['invoiced']:,}",
            detail="صُدرت لها فاتورةٌ واحدة على الأقل.",
            tone="money",
            icon="receipt",
        ),
    ]


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

    # الفاتورةُ الكاملةُ للصفّ — تُعاد نافذةَ «سند دفع» كما في «ما بعد البيع».
    # تُستعمَل مساعِداتُها نفسُها (استيرادٌ داخل الدالة تفادياً للدور: `after_sales`
    # يستورد `SOLD` من هنا). عمودُ الفاتورة وسندُه v1 نفسُهما.
    from .after_sales import (
        latest_invoice_field,
        odoo_move_url,
        residual_of,
        state_label,
    )

    rows = rows.annotate(
        invoice_pk=latest_invoice_field("pk"),
        invoice_number=latest_invoice_field("number"),
        invoice_state=latest_invoice_field("state"),
        invoice_odoo=latest_invoice_field("odoo_state_raw"),
        invoice_amount=latest_invoice_field("amount"),
        invoice_paid=latest_invoice_field("amount_paid"),
        invoice_issued=latest_invoice_field("issued_at"),
        invoice_source=latest_invoice_field("source"),
        invoice_odoo_id=latest_invoice_field("odoo_invoice_id"),
    )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)
    # اللصائقُ والمشتقّاتُ تُحسب هنا لا في القالب (قالبٌ يفكّ تعداداً مكانٌ
    # ثانٍ للقاعدة). نظيرُ ما يفعله «ما بعد البيع» بالضبط.
    source_labels = dict(InvoiceSource.choices)
    for row in page.object_list:
        row.invoice_label = state_label(row.invoice_state) if row.invoice_state else ""
        row.invoice_residual = residual_of(row) if row.invoice_number else None
        row.invoice_source_label = source_labels.get(row.invoice_source, "—")
        row.odoo_invoice_url = odoo_move_url(row.invoice_odoo_id)

    return render(
        request,
        "console/vehicle_catalog.html",
        {
            "page": page,
            "cards": _catalog_cards(catalogue_totals()),
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "listed_from": request.GET.get("listed_from", ""),
            "listed_to": request.GET.get("listed_to", ""),
            "auction_from": request.GET.get("auction_from", ""),
            "auction_to": request.GET.get("auction_to", ""),
            # الفلاترُ مسلسلةً لروابط الصفحات. وكان القالبُ يبني `?q=…&page=`
            # بيده، فيُسقط **الخمسة الباقية**: من يرشّح بحالةِ مزادٍ أو بمدىً
            # من التواريخ ثم يضغط «التالي» يقع في الجدول كلِّه (١٢٬٩٨٩ صفّاً)
            # وهو يظنّ نفسه داخل نتيجته. وv1 لا يفعل ذلك: صفحاتُ
            # `Views/Admin/vehicles/catalog.php` تُبنى من `$_GET` كلِّها
            # منقوصةً `page` وحدها.
            "keep": keep(request.GET),
            # الشاشةُ `auctions.view`، وثلاثةٌ من أزرارها تقصد `auctions.manage`:
            # «إضافة سيارة يدويًا» (`vehicle-new`) و«إنشاء مزاد من المحدد»
            # (`auction-new`) ونافذةُ الصور (`vehicle-images`). وكان القالبُ
            # يرسمها للجميع — وفي تعليقه نفسِه مكتوبٌ أن «رابطاً يفتح ٤٠٣ أسوأ
            # من غيابه»، وهو يرسم ثلاثة. والصورُ لا تُرى اليوم لأن `image_count`
            # صفرٌ في ١٢٬٩٩٠ صفّاً (الترحيلُ لم ينقل الملفّات)، فالفخُّ نائمٌ لا
            # غائب. والنظيرُ في `auctions.py:299` يمرّر `can_manage` منذ T868.
            "can_manage": can(request.user, Capability.AUCTIONS_MANAGE),
            "states": [
                (value, AuctionState(value).label) for value in AuctionState.values
            ],
            # رسمُ عمود الصور — من `icons.py` لا محرفاً في القالب. T837
            "camera_icon": path_of("camera"),
            # و«إضافة سيارة يدويًا» كانت `➕` — والمحرفُ يرسمه نظامُ التشغيل
            # فيأتي أخضرَ سميكاً لا يشبه زرَّ اللوحة. ذيلُ T837.
            "plus_icon": path_of("plus"),
        },
    )


def found(*, plate: str = "", vin: str = "", name: str = "", lot: str = ""):
    """بحثٌ **لكل عمودٍ على حدة**، كما في v1: صفُّ خاناتٍ تحت الرؤوس.

    والفرق عن خانةٍ واحدة ليس ذوقاً: من يبحث بلوحةٍ يعرف أنها لوحة، وخانةٌ
    واحدة تطابق النصّ في ستّة أعمدة تُرجع له صفوفاً لا يفهم لماذا ظهرت.
    والاثنان معاً يضيّقان — `لكزس` في الاسم و`2024` في اللوت يعنيان الاثنين.

    و`None` تعني «لم يُطلب بحثٌ بعد»، **وتُقرَّر من القيود التي نشأت فعلاً لا
    من امتلاء الخانات**. وكان القرارُ على الامتلاء، فمُدخَلٌ يملأ الخانة ولا
    يصنع قيداً — `?lot=abc` (ليس رقماً) و`?name=-` (لا يبقى منه بعد الطيّ
    شيء) — كان يمرّ من الحارس ثم يُرشِّح بلا شيء: **١٢٬٩٨٩ مركبةً على شاشةٍ
    اسمها «بحث»** (قِيس على `:8001` في ١٤ سبتمبر ٢٠٢٦، ٢٦٠ صفحة). و`admin_v2`
    في v1 يفعل الصواب هنا: `ctype_digit` تسقط `abc` ثم `$where === []` فيردّ
    `rows: []` بحالة `empty` (`AuctionController::vehicleSearchData`).
    """
    clauses = [
        clause
        for clause in (
            search_q(plate, "plate_number"),
            search_q(vin, "vin"),
            search_q(name, "make", "model"),
        )
        if clause
    ]
    number = _int(lot)
    if number is not None:
        clauses.append(Q(lot_number=number))

    if not clauses:
        return None

    rows = Vehicle.objects.select_related("auction", "awarded_to").order_by("-id")
    for clause in clauses:
        rows = rows.filter(clause)
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
            # الخاناتُ الأربع مسلسلةً لروابط الصفحات — والقالبُ لم يكن يرسم
            # روابطَ أصلاً: كان يكتب «صفحة ١ من ٢٦٠» ولا سبيل إلى الثانية.
            "keep": keep(request.GET),
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
        matches = search_q(
            text,
            "plate_number",
            "vin",
            "make",
            "model",
            "awarded_to__full_name",
            "awarded_to__phone",
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
