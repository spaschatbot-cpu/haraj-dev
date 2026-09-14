"""كتالوج السيارات، والبحث عنها. T830د.

شاشتان من قسم «إدارة المزادات» في v1، وكلتاهما استعلامٌ واحد على
:class:`Vehicle` بمرشّحاتٍ مختلفة — ولذلك ملفٌّ واحد: الفرق بينهما **سؤالٌ**
لا بنية.

| الشاشة | السؤال الذي تُفتح لأجله |
|---|---|
| كتالوج السيارات | ما الذي عندنا، وبأي حال؟ |
| بحث عن سيارة | أين هذه السيارة بعينها؟ |

و«ما بعد البيع» خرجت من هنا إلى `after_sales.py` (T869): صارت خمسَ مرشّحاتٍ
وستّةَ عشرَ عموداً وبطاقاتٍ ونافذةَ فاتورةٍ وتصديراً — أي أنها لم تعد
«الاستعلامَ نفسَه بسؤالٍ آخر»، وهو الشرطُ الذي جمع هذه الشاشات في ملفّ.

**و«الخروج ونقل الملكية» خرجت إلى `exits.py`** مع موديل `VehicleExit`
(`c3188e6`) — وبقيت هنا `vehicle_exit` **ميّتةً ستّةَ وأربعين سطراً** بلا
مسارٍ ولا مستورِد، ومعها فقرةٌ في هذا الرأس تشرح شاشةً بـ«لسانين لا أربعة»
بينما `exits.py` الحيُّ يفتتح بـ«أربعةُ ألسنة على شاشةٍ واحدة». **شرحان
متناقضان لشاشةٍ واحدة، وأوّلُ من يقرأ الميّتَ يظنّه العقدَ الحاليّ** — فحُذف
الاثنان في ١٤ سبتمبر ٢٠٢٦. وما يخصّ الخروجَ من أعطال v1 يُقرأ في `exits.py`.

ثلاثة أعطالٍ مقيسةٍ في v1 لا تُنقَل
====================================

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

import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

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
from .exports import export_table, oversize, refuse, wants_export
from .icons import path_of
from .sensitive import prepare, shown_to
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


def _amount(raw: str) -> Decimal | None:
    """مبلغٌ من نصّ المستخدم، أو ``None`` — بلا خطأ ٥٠٠.

    و**مقارنةُ مساواةٍ لا `LIKE` على نصّ**: v1 يرشّح السعر بـ
    `CAST(av.starting_price AS CHAR) LIKE '%9500%'`
    (`AuctionController::vehicleSearchData`) — فمن يكتب `9500` يأتيه `19500`
    و`95000` و`9500.00` معاً، ولا سبيل إلى أن يقول «هذا السعرُ بالضبط». ومن
    يكتب سعراً في خانةِ سعرٍ يقصد سعراً. فالمطابقةُ هنا عدديّةٌ تامّة، والطيُّ
    يسبقها فتُقبل `٩٥٠٠` العربية كما تُقبل `9500`.

    **والفاصلةُ العشريّة تُفصَل قبل الطيّ**: `fold` تحذف `. - _ /` والمسافاتِ
    كلَّها (وهو صوابُها في اللوحات: «د ط ق 1265» تجد «دطق1265»)، فطيُّ
    `1000.00` كاملةً يعطي `100000` — أي **مئة ألفٍ مكان ألف**. فيُقسَم النصُّ
    على النقطة أوّلاً ويُطوى كلُّ شقٍّ وحدَه؛ والمسافةُ داخل الشقّ تُطوى، فـ
    `9 500` تُقرأ `9500` كما يقصد كاتبُها.
    """
    text = (raw or "").strip().replace(",", "")
    if not text:
        return None
    parts = text.split(".")
    if len(parts) > 2:
        return None
    folded = [fold(part) for part in parts]
    if not all(part.isascii() and part.isdigit() for part in folded):
        return None
    try:
        return Decimal(".".join(folded))
    except (InvalidOperation, ValueError):
        return None


def _prefix_day(raw: str) -> tuple[date, date] | None:
    """مدىً من يومٍ ناقص: `2026` سنةٌ، و`2026-06` شهرٌ، و`2026-06-14` يوم.

    v1 يرشّح تاريخَ الإدراج بـ`CAST(av.created_at AS CHAR) LIKE '%2026-06%'`
    وخانتُه مكتوبٌ فيها `2026-06…` حرفياً. **والنصُّ يطابق ما ليس تاريخاً**:
    `LIKE '%2026%'` تجد الساعةَ `20:26` أيضاً، و`CAST` يمنع استعمالَ الفهرس
    فيُمسح الجدولُ كلُّه. فهنا يُقرأ الناقصُ **مدىً على العمود نفسِه** — أرخصُ
    على القاعدة، وأدقُّ في الجواب، وهو ما تعنيه الخانةُ أصلاً.

    وما لا يشبه تاريخاً يُقرأ «لا مرشّح» لا خطأً: الخانةُ نصٌّ حرّ.

    **والشرطاتُ تُفصَل قبل الطيّ**: `fold` تحذف `-` نفسَها (وهو صوابُها في
    اللوحات والشواصي)، فطيُّ `2026-09` كاملةً يعطي `202609` — ستّةَ أرقامٍ لا
    تُقرأ شهراً ولا سنة، فيسقط المرشّحُ صامتاً. فيُقسَم أوّلاً ويُطوى كلُّ
    شقٍّ وحدَه، فتُقبل `٢٠٢٦-٠٩` العربية كما تُقبل `2026-09`.
    """
    text = (raw or "").strip()
    if not text:
        return None
    parts = [fold(part) for part in text.split("-")]
    if not all(part.isascii() and part.isdigit() for part in parts):
        return None
    try:
        if len(parts) == 1 and len(parts[0]) == 4:
            year = int(parts[0])
            return date(year, 1, 1), date(year, 12, 31)
        if len(parts) == 2:
            year, month = int(parts[0]), int(parts[1])
            last = calendar.monthrange(year, month)[1]
            return date(year, month, 1), date(year, month, last)
        if len(parts) == 3:
            day = date(int(parts[0]), int(parts[1]), int(parts[2]))
            return day, day
    except ValueError:
        # `calendar.IllegalMonthError` وريثةُ `ValueError` — فشهرُ ١٣ وسنةُ صفر
        # يقعان هنا معاً، ولا حاجة إلى فرعٍ ثانٍ يمسك أحدَهما.
        return None
    return None


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

    # الفاتورةُ الكاملةُ للصفّ — تُعاد نافذةَ «سند دفع» كما في «ما بعد البيع»،
    # و**قبل فرع التصدير** لأن عمود «الفاتورة» في الملفّ يقرأ `invoice_number`.
    # و`COUNT` لا يدفع ثمنَها: جانغو يُسقط الاستعلاماتِ الفرعيّةَ غيرَ
    # المستعملة من العدّ (قِيس: ٠٫٠٠٤ ثانيةٍ على اثني عشر ألفَ صفّ).
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

    if wants_export(request):
        count = oversize(rows)
        if count:
            return refuse(request, count)
        # **أعمدةُ الملفّ = أعمدةُ الشاشة، عموداً بعمود.** كانت ثلاثةٌ على
        # الشاشة تسقط من الملفّ (اللون · شركة التأمين · الفاتورة) وأربعةٌ في
        # الملفّ ليست على الشاشة (ناقل الحركة · الوقود · حالة المركبة · سعر
        # الوقوف) — فمن يقارن الملفَّ بالشاشة يجد جدولين لا واحداً، والعمودُ
        # الذي يخرج في ملفٍّ ولا يظهر على شاشةٍ هو بعينه بابُ التسريب.
        #
        # وحُكم على الأربعة واحداً واحداً (١٤ سبتمبر ٢٠٢٦):
        # * **ناقل الحركة** و**الوقود** حُذفا: مواصفتان تفصيليّتان مكانُهما
        #   `vehicle-detail`، ولا عمودَ لهما في ترويسة v1 ولا عندنا.
        # * **حالة المركبة** و**سعر الوقوف** صارا عمودين على الشاشة: كلاهما
        #   معروضٌ أصلاً في «بحث عن سيارة» **بالقدرة نفسِها** (`auctions.view`)،
        #   فإظهارُهما هنا لا يفتح ثقةً جديدة — ويجيبان سؤالَ الشاشة نفسَه
        #   («ما عندنا وبأيّ حال») الذي كانت تجيبه نصفَ إجابةٍ بحالة المزاد
        #   وحدها.
        return export_table(
            rows,
            name="كتالوج-السيارات",
            columns=[
                ("المعرّف", lambda row: row.pk),
                ("رقم الموقف", lambda row: row.lot_number),
                ("المزاد", lambda row: row.auction.number),
                ("السيارة", lambda row: f"{row.make} {row.model}"),
                ("السنة", lambda row: row.year),
                ("اللون", lambda row: row.get_colour_display()),
                ("العداد", lambda row: row.odometer_km),
                ("الحالة الفنية", lambda row: row.get_condition_display()),
                ("شركة التأمين", lambda row: row.insurance_company),
                ("الشاصي", lambda row: row.vin),
                ("اللوحة", lambda row: row.plate_number),
                ("الصور", lambda row: row.image_count),
                ("حالة المزاد", lambda row: row.auction.get_state_display()),
                ("بداية المزاد", lambda row: row.auction.starts_at),
                ("نهاية المزاد", lambda row: row.auction.ends_at),
                ("حالة المركبة", lambda row: row.get_state_display()),
                ("سعر الوقوف", lambda row: row.reserve_price),
                # رقمُ الفاتورة وحدَه — لا مبلغَها ولا مشتريها. عمودُ «الفاتورة»
                # على الشاشة رقمٌ كذلك، وتفاصيلُه في السند خلف `invoices.view`
                # و`users.view` (`sensitive.py`). ولا يُصدَّر ما لا يُعرَض.
                ("الفاتورة", lambda row: row.invoice_number),
            ],
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

    # **المحجوبُ يُمحى هنا، بعد الحساب وقبل القالب.** كان كلُّ صفٍّ مفوتَر يحمل
    # في مصدر الصفحة `data-phone="966…"` و`data-amount` و`data-paid`
    # و`data-residual` — لا عند الضغط بل في HTML — والشاشةُ `auctions.view`
    # وحدَها. والقاعدةُ واحدةٌ في `sensitive.py` تخدم هذه الشاشة و«ما بعد
    # البيع» معاً، فلا تُطبَّق في واحدةٍ وتُترك في أختها.
    seen = shown_to(request.user)
    prepare(page.object_list, seen)

    return render(
        request,
        "console/vehicle_catalog.html",
        {
            "page": page,
            "show_money": seen.money,
            "show_customer": seen.customer,
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


def found(
    *,
    plate: str = "",
    vin: str = "",
    name: str = "",
    lot: str = "",
    number: str = "",
    claim: str = "",
    price: str = "",
    state: str = "",
    listed: str = "",
):
    """بحثٌ **لكل عمودٍ على حدة**، كما في v1: صفُّ خاناتٍ تحت الرؤوس.

    ثمانيةُ مرشّحاتٍ في v1، وكان هنا منها ثلاثة
    ===========================================
    مرجعُ v1: `AuctionController::vehicleSearchData:4090-4101` — ثمانيةُ فروعِ
    `$where` بينها `AND`، وخانةٌ لكلٍّ تحت رأس عمودها في
    `Views/Admin/auctions/vehicle_search.php:66-80`. وكان عندنا `plate`
    و`chassis` و`details` (اسماً) وحدَها، وزيادةُ `lot`.

    * `id` ← `av.id` صار `number` على `pk`. **أُضيف**: عمودُ `#` على الشاشة
      هو `pk`، ومن ينسخ الرقمَ منها لم يكن يجد به شيئاً.
    * `details` عند v1 خمسةُ أعمدة، منها **سنةُ الصنع**. **أُضيفت السنة**:
      مُدخَلٌ من أربعة أرقامٍ يُقارَن بـ`year` أيضاً.
    * `plate` و`chassis` كما كانا — مُطبَّعين (`search_q`).
    * `claim` ← `claim_number LIKE`. **أُضيف ومعه عمودُه**؛ و`claim_number`
      مفهرسٌ ومملوءٌ في ٩٦٠ صفّاً على `t307`، ووصفُ الشاشة في v1
      (`AdminV2Sections.php:34`) يعدّه أحدَ محاورها الأربعة.
    * `price` ← `CAST(starting_price AS CHAR) LIKE`. **أُضيف** على
      `reserve_price` مساواةً لا `LIKE` (:func:`_amount`).
    * `status` ← `LOWER(av.status)` من سبع. **أُضيف** على
      :class:`VehicleState` بقائمةٍ بيضاء — وهو عمودُ «الحالة» المعروضُ أصلاً.
    * `date` ← `CAST(created_at AS CHAR) LIKE`. **أُضيف** مدىً
      (:func:`_prefix_day`).

    **واللونُ وحدَه لم يُضَف، وهذه نتيجةٌ لا نقص**: `colour = unknown` في
    **١٢٬٩٨٥ من ١٢٬٩٩٣** صفّاً على `haraj2_t307`. فخانةُ لونٍ تُرجع صفراً لكلّ
    ما يُكتب فيها إلّا «غير معروف» — وخانةٌ تُجيب دائماً بلا نتيجة تُقرأ عطلاً
    في الشاشة لا فراغاً في البيانات.

    **ولا تطبيعَ عربيّاً على الشاصي الكامل ولا على الأرقام**: `search_q` تطبّع
    اللوحةَ والاسمَ والمطالبةَ والشاصي — وهو صوابٌ فيها (لوحاتُ القاعدة مكتوبةٌ
    «د ط ق 1265» بمسافات) — أمّا `pk` و`lot` و`price` و`state` فمعرّفاتٌ آليّةٌ
    تُطابَق مطابقةً تامّة، لأن المقصودَ بها الدقّةُ لا التقريب.

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
    # خانةُ «تفاصيل المركبة» تُطابق الاسمَ والماركةَ والموديل — **وسنةَ الصنع**
    # إن كان المكتوبُ أربعةَ أرقام، كما يفعل `details` في v1
    # (`year_of_manufacture LIKE`). و`year` عددٌ صحيح، فلا `iregex` عليه:
    # مطابقةٌ تامّة، ورقمٌ من أربعة أرقامٍ هو سنةٌ في هذا السياق.
    named = search_q(name, "make", "model")
    year = _int(name)
    if named and year is not None and 1000 <= year <= 9999:
        named |= Q(year=year)

    clauses = [
        clause
        for clause in (
            search_q(plate, "plate_number"),
            search_q(vin, "vin"),
            named,
            search_q(claim, "claim_number"),
        )
        if clause
    ]

    lot_number = _int(lot)
    if lot_number is not None:
        clauses.append(Q(lot_number=lot_number))

    row_id = _int(number)
    if row_id is not None:
        clauses.append(Q(pk=row_id))

    amount = _amount(price)
    if amount is not None:
        clauses.append(Q(reserve_price=amount))

    state = (state or "").strip()
    if state in VehicleState.values:
        clauses.append(Q(state=state))

    span = _prefix_day(listed)
    if span is not None:
        clauses.append(Q(created_at__date__gte=span[0], created_at__date__lte=span[1]))

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
        number=request.GET.get("number", ""),
        claim=request.GET.get("claim", ""),
        price=request.GET.get("price", ""),
        state=request.GET.get("state", ""),
        listed=request.GET.get("listed", ""),
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
            "number": request.GET.get("number", ""),
            "claim": request.GET.get("claim", ""),
            "price": request.GET.get("price", ""),
            "state": request.GET.get("state", ""),
            "listed": request.GET.get("listed", ""),
            # حالاتُ المركبة للقائمة المنسدلة — من التعداد لا مكتوبةً في
            # القالب: قائمةٌ في قالبٍ هي مكانٌ ثانٍ للقاعدة، تتفارق عن
            # القائمة البيضاء في :func:`found` أوّلَ ما تُضاف حالة.
            "states": [
                (value, VehicleState(value).label) for value in VehicleState.values
            ],
            # الخاناتُ الأربع مسلسلةً لروابط الصفحات — والقالبُ لم يكن يرسم
            # روابطَ أصلاً: كان يكتب «صفحة ١ من ٢٦٠» ولا سبيل إلى الثانية.
            "keep": keep(request.GET),
        },
    )
