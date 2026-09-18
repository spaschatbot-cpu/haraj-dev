"""مركزُ الفواتير، وحالةُ فاتورة، والقرارات المنتهية. T830ز · T936.

## شاشةٌ واحدةٌ للفواتير بعد أن كانت ثلاثاً. T936

قرارُ المالك (١٨ سبتمبر ٢٠٢٦): «اجمع التلات شاشات — مركز الفواتير وحالة
الفاتورة وتصدير الفواتير. هما بيردّوا نفس الـdata. اعمل لي منهم صفحة واحدة».

**وكان الثلاثةُ استعلاماً واحداً بثلاثة أثواب:** `people.invoices` يسرد
`Invoice` بمرشّحِ حالةٍ وبحثٍ نصّيّ، و`invoices_export` يسرد `Invoice` نفسَه
بمدىً من التواريخ، و`invoice_lookup` يجد **مركبةً** ثم فاتورتَها. فالمرشّحاتُ
اجتمعت في بانٍ واحد (:func:`invoice_rows`)، والتصديرُ صار زرّاً على الشاشة
يحمل مرشِّحَها، والبحثُ بالشاصي واللوحة صار مدخلاً في حقل البحث نفسِه.

**والفواتيرُ انتقلت من `people.py` إلى هنا.** كانت شاشتاها (`invoices` و
`invoice-detail`) في وحدة «المستخدمين» لأنها كُتبت هناك أوّلاً، ووحدةُ
الفواتير هي هذه. `apps/console/people.py` صار أقصرَ بـ١٠٦ أسطر.

## وما تعرضه v1 وكنّا لا نعرضه

قرأتُ `src/Controllers/Admin/InvoiceController.php`. جدولُه يحمل ما لا يحمله
جدولُنا: **اللوحة** و**المركبة** و**المزاد** و**معرّف أودو** و**جوّال
العميل**، وفوقه **أربعُ بطاقات** (العدد · المسدَّدة · غير المسدَّدة · إجمالي
المبالغ). وكلُّها موجودةٌ عندنا في النماذج ولم تكن تُعرَض. فأُضيفت.

**وبطاقاتُنا خمسٌ لا أربع**، والخامسةُ هي التي تجيب سؤالَ الشاشة أصلاً:
**المتبقّي**. وv1 يجمع `amount` ولا يجمع ما بقي منه — فيقرأ المدير «إجمالي
الفواتير ٤٢ مليوناً» ولا يعرف كم منها وصل.

**وحالةُ v1 تُقرأ من `PaymentStatus` عموداً يُكتب مرّةً عند الإدخال**، وحالتُنا
مشتقّةٌ من الدفعات (`derive_invoice_state`) — وذلك عطلُ T809 بعينه: حوالةٌ في
أودو كمسودّة تظهر هناك «مدفوعة»، وقد أُخرجت سيارةٌ مقابلها.

ثلاث شاشاتٍ من قائمة v1، وأولاها تختلف عن كل ما في اللوحة.

«حالة فاتورة» — الشاشة الوحيدة التي يُفتَح جوابُها لخارج الشركة
================================================================
وصفُها في v1: «البحث بالشاسيه/اللوحة/شركة التأمين لمعرفة حالة الفاتورة
**للتأمين / T-Control / الجهات الخارجية**». أي أن السائل ليس موظّفاً — هو
شركةُ تأمينٍ أو جهةٌ تسأل عن مركبةٍ بعينها، والموظّفُ يقرأ لها.

وذلك يغيّر ثلاثة أشياء في التصميم:

* **تُجيب عن مركبةٍ واحدة ولا تسرد.** حقلٌ فارغٌ لا يعرض الجدول كلّه — وهو ما
  تفعله حالةُ الفراغ في v1 صواباً، وتُنقل بنصّها.
* **ولا تعرض ما لا يخصّ السائل**: لا اسم المشتري، ولا جوّاله، ولا مبلغ
  الفاتورة. حالتُها وحدها ورقمُها وتاريخُها. وشركةُ التأمين ليست طرفاً في
  الثمن، وعرضُه لها تسريبٌ لا خدمة.
* **وقدرتُها أضيق**: `invoices.lookup` لا `invoices.view`. الثانية تفتح
  القائمة كلَّها بمشتريها ومبالغها، ومنحُها لمن يجيب هاتفاً واحداً يفتح له
  الباقي كلَّه.

**ولذلك بقيت شاشةً وإن خرجت من الشريط** (T936): بحثُها — بالشاصي واللوحة —
صار مدخلاً في «مركز الفواتير»، فالمالكُ يرى مدخلاً واحداً للفواتير كما طلب.
لكنّ الصفحةَ نفسَها باقيةٌ بقدرتها الضيّقة لمن يُمنَح `invoices.lookup` وحدَها
ولا يُمنَح `invoices.view` — ودمجُها دمجاً كاملاً كان يعني **إلغاءَ تلك
القدرة**: من يجيب شركةَ التأمين يصير قادراً على قراءة القائمة كلِّها بمبالغها.
فهي في `DETAIL_PAGES` لا في `PAGES`: محروسةٌ ومقصودة، وغيرُ معروضة.

«القرارات المنتهية» — ما حُسم، مقبولاً كان أو مرفوضاً
=====================================================
هي هنا الوجهُ الآخر لـ`console:partner-decisions`: تلك تعرض ما **ينتظر**
قراراً، وهذه ما **انتهى** إليه — والمرفوضةُ فيها كالمقبولة، لأن السؤال «ماذا
قرّرنا» لا «ماذا بعنا».

**وجدولُها ليس هنا — T922.** كان هنا استعلامٌ ثانٍ وقالبٌ ثانٍ بتسعة أعمدةٍ
ومرشّحين، وهما في v1 جدولُ «ما بعد البيع» نفسُه: `AfterSalesController` واحدةٌ
تخدم `/after-sales` و`/ended-decisions` بـ`listPage` الواحدة، والفرقُ علَمٌ
واحد `showBidders` يُظهر عموداً سادسَ عشر (قُرئ في `src/Controllers/Admin/`
و`src/Views/Admin/aftersales/index.php:131-147`). ونسختُنا الثانية كلّفت ما
تكلّفه كلُّ نسخةٍ ثانية: البحثُ العربيُّ أُصلح هناك وبقي هنا على أربعة حقول،
وحجبُ الجوّال والمبلغ (`sensitive.py`) لم يمرّ على هذه الشاشة أصلاً.

فالصفوفُ والمرشّحاتُ والأعمدةُ والتصديرُ والحارسُ في `after_sales.py`، ويبقى
هنا **ما يختلف حقاً**: :data:`DECIDED` بدل `SOLD`، ومرشّحُ `which`.

وv1 يجمعها أيضاً مع «المزايدات المقبولة» في شاشةٍ واحدة بستّة ألسنة، فيختلط
ما رسا بما رُفض تحت اسمٍ واحد.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import (
    UNPAID_INVOICE_STATES,
    Invoice,
    InvoiceState,
    Transaction,
)

from . import sensitive
from .after_sales import (
    chosen_filters,
    sale_table,
    sheet_settled_vehicle_ids,
    sold_rows,
)
from .exports import export, wants_export
from .paging import paged, pager
from .sensitive import shown_to
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")

#: و`PAGE_SIZE = 50` كانت هنا وسقطت مع استعلام «القرارات المنتهية»: مقاسُ
#: الصفحة صار من `after_sales.page_size` ومعه خانةُ «عدد النتائج في الصفحة».
#: وثابتٌ لا يقرؤه أحد يُقرأ يوماً على أنه القاعدةَ فيُبنى عليه.

#: ما حُسم فيه قرار: رسا أو رُفض. والمرفوضة معها عمداً — السؤال «ماذا قرّرنا».
DECIDED = (
    VehicleState.AWARDED,
    VehicleState.REJECTED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)


def lookup(*, vin: str = "", plate: str = "") -> dict | None:
    """حالةُ فاتورة مركبةٍ واحدة — أو `None` حين لا يُسأل عن شيء.

    وتُرجع **ما يخصّ السائل وحده**: المركبةَ وحالتَها ورقمَ الفاتورة وحالتَها
    وتاريخَها. لا مشترٍ ولا جوّال ولا مبلغ.

    والحالة مشتقّةٌ من الدفعات (`derive_invoice_state`) لا من عمودٍ يُكتب
    مرّةً — فحوالةٌ في أودو كمسودّة لا تُقرأ هنا «مدفوعة»، وهي القراءة التي
    أُخرجت سيارةٌ بناءً عليها في v1.
    """
    vin = (vin or "").strip()
    plate = (plate or "").strip()
    if not vin and not plate:
        return None

    cars = Vehicle.objects.select_related("auction")
    if vin:
        cars = cars.filter(vin__iexact=vin)
    if plate:
        cars = cars.filter(search_q(plate, "plate_number"))

    found = list(cars.order_by("-id")[:2])
    if not found:
        return {"vehicle": None, "many": False}
    if len(found) > 1:
        # لا يُختار الأول: جوابٌ عن مركبةٍ غير التي سُئل عنها يُقرأ صحيحاً
        # ويُبنى عليه، والسائلُ من خارج الشركة لا يملك ما يكذّبه به.
        return {"vehicle": None, "many": True, "count": cars.count()}

    car = found[0]
    invoice = Invoice.objects.filter(vehicle=car).order_by("-issued_at", "-id").first()
    return {
        "vehicle": car,
        "many": False,
        "invoice": invoice,
        # **الاسمُ العربيُّ لا قيمةَ العمود.** كانت الشاشةُ تطبع `paid` و`open`
        # خاماً وسطَ عربيّةٍ كاملة — وهي الشاشةُ الوحيدة الموجَّهةُ إلى **خارج
        # الشركة** (التأمين والجهات)، أي أن السائلَ لا يملك ما يترجم له الكلمة.
        # و«حالة المركبة» فوقها بسطرٍ واحدٍ كانت تُعرَض بـ`get_state_display`
        # عربيّةً، فالسطران متجاوران وأحدهما بلغةٍ أخرى.
        "state": InvoiceState(money.derive_invoice_state(invoice)).label
        if invoice
        else "",
    }


@console_page("console:invoice-lookup")
def invoice_lookup(request):
    """حالة فاتورة: مركبةٌ واحدة، وحالتُها وحدها."""
    return render(
        request,
        "console/invoice_lookup.html",
        {
            "found": lookup(
                vin=request.GET.get("vin", ""),
                plate=request.GET.get("plate", ""),
            ),
            "vin": request.GET.get("vin", ""),
            "plate": request.GET.get("plate", ""),
        },
    )


# ---------------------------------------------------------------------------
# مركز الفواتير — شاشةٌ واحدة. T936
# ---------------------------------------------------------------------------

#: ما يطابقه حقلُ البحث الواحد. **خمسةُ مداخلَ لأنها خمسةُ أشكالٍ للورقة التي
#: تصل المكتب**: رقمُ الفاتورة عندنا، ورقمُها في أودو (`INV/2026/08267`)،
#: واسمُ العميل، ولوحةُ المركبة، وشاصيها — والجوّالُ يُعالَج على حدةٍ لأنه
#: يُكتب بأشكال (`05…` · `9665…` · `+9665…`).
#:
#: واللوحةُ والشاصي هما بحثُ «حالة فاتورة» بعينه (v1: «البحث بالشاسيه/اللوحة»)،
#: فدخلا هنا — ولم تعد الورقةُ تحتاج شاشتين.
SEARCH_FIELDS = (
    "number",
    "odoo_invoice_id",
    "customer__full_name",
    "vehicle__plate_number",
    "vehicle__vin",
)


def invoice_rows(*, text: str = "", state: str = "", since: str = "", until: str = ""):
    """الفواتيرُ منقّاةً بما كُتب — **بانٍ واحدٌ للشاشة وللتصدير وللمجاميع**.

    كانت ثلاثةَ استعلاماتٍ في ثلاث شاشات (`people.invoices` ·
    `invoices_export` · `invoice_lookup`)، وكلُّها على `Invoice` نفسِه. ونسخةٌ
    ثانيةٌ من استعلامٍ تكلّف ما كلّفته في «القرارات المنتهية» (T922): البحثُ
    يُحسَّن في واحدةٍ ويبقى في الأخرى، والحجبُ يمرّ على واحدةٍ ويفوت الأخرى.

    والحالةُ المرشَّح بها هي **المشتقّة** من الدفعات، وكلمةُ أودو
    (`odoo_state_raw`) ليست خياراً أصلاً: هي شهادةٌ على ما يظنّونه، وشاشةٌ
    تُرشِّح بها تجيب «ماذا يقول أودو» والسؤالُ «ما الذي لنا».
    """
    rows = Invoice.objects.select_related(
        "customer", "vehicle", "vehicle__auction"
    ).order_by("-issued_at", "-id")

    if (state or "").strip() in InvoiceState.values:
        rows = rows.filter(state=state)

    start = parse_date((since or "").strip())
    end = parse_date((until or "").strip())
    if start:
        rows = rows.filter(issued_at__date__gte=start)
    if end:
        rows = rows.filter(issued_at__date__lte=end)

    text = (text or "").strip()
    if text:
        terms = search_q(text, *SEARCH_FIELDS)
        digits = "".join(character for character in text if character.isdigit())
        if digits:
            terms |= Q(customer__phone__contains=digits)
        rows = rows.filter(terms).distinct()

    return rows


def invoice_totals(rows) -> dict:
    """البطاقاتُ الخمس — **باستعلامٍ واحدٍ على المرشَّح نفسِه**.

    v1 يحسب بطاقاتِه على **الجدول كلِّه** (`SELECT … FROM invoices_odoo` بلا
    `WHERE`) بينما جدولُه تحتها مرشَّح. فمن يرشّح بمزادٍ يقرأ فوقه إجماليَّ
    السنة كلِّها، ويقرأ الرقمين على أنهما عن الشيء نفسه.

    **والخامسةُ — «المتبقّي» — ليست في v1**، وهي جوابُ السؤال الذي تُفتح
    الشاشةُ لأجله: «كم لنا عند الناس؟». ويُجمَع بالطرح في القاعدة لا في
    بايثون، فصفحةٌ من خمسين صفّاً لا تقرأ اثني عشر ألفاً لتجمعها.
    """
    # **أسماءُ المخرجات تختلف عن أسماء الحقول عمداً.** `amount=Sum("amount")`
    # يرفضه Django بـ«'amount' is an aggregate»: الاسمُ يصير مرجعاً يحجب
    # الحقلَ الذي يجمعه. وقع فعلاً وأسقط الصفحة بـ500.
    summed = rows.aggregate(
        count=Count("id"),
        total_amount=Sum("amount"),
        total_collected=Sum("amount_paid"),
        # من `Invoice.outstanding_sql()` لا بطرحٍ هنا: الطرحُ يعدّ الفاتورةَ
        # الملغاةَ مبلغاً علينا، ويطرح ما سُدِّد فوق مستحقّه. وقع فعلاً —
        # صفٌّ يقول «٠٫٠٠» وبطاقةٌ فوقه تعدّ ١١٬٢٧٠ منه.
        total_outstanding=Sum(Invoice.outstanding_sql()),
        unpaid=Count("id", filter=Q(state__in=list(UNPAID_INVOICE_STATES))),
        settled=Count("id", filter=Q(state=InvoiceState.PAID)),
    )
    # `Sum` على مجموعةٍ فارغة يعطي `None`، و`None` في قالبٍ يُطبع فراغاً
    # يُقرأ «لا بيانات» لا «صفر». فالأصفارُ تُكتب أصفاراً هنا مرّةً واحدة.
    for key in ("total_amount", "total_collected", "total_outstanding"):
        summed[key] = summed[key] or ZERO
    return summed


@console_page("console:invoices")
def invoices(request):
    """مركزُ الفواتير: كلُّ فاتورةٍ وما سُدِّد منها وما بقي — وشاشةٌ واحدة.

    **الثلاثةُ في واحدة** (قرار المالك، ١٨ سبتمبر ٢٠٢٦): المرشّحاتُ كلُّها هنا
    — نصٌّ وحالةٌ ومدىً زمنيّ — والتصديرُ زرٌّ يحمل المرشَّحَ نفسَه، والبحثُ
    باللوحة والشاصي مدخلٌ في الحقل نفسِه.

    **والعددُ يُرى قبل التنزيل**، وهو ما كانت تفعله شاشةُ التصدير ويستحقّ
    البقاء: في v1 التصديرُ رابطٌ يُضغط فيبدأ التنزيل، ولا يعرف الضاغطُ أهو
    ثلاثةُ صفوفٍ أم ثلاثةَ عشرَ ألفاً حتى يفتح الملفّ — ومن ينتظر ملفاً ثقيلاً
    بلا سببٍ يضغط ثانيةً. وبطاقةُ «العدد» فوق الزرّ تقولها دائماً.
    """
    text = request.GET.get("q", "")
    state = request.GET.get("state", "")
    since = request.GET.get("since", "")
    until = request.GET.get("until", "")
    rows = invoice_rows(text=text, state=state, since=since, until=until)

    seen = shown_to(request.user)

    if wants_export(request):
        return export(
            rows,
            name="الفواتير",
            headers=[
                "الرقم",
                "رقم أودو",
                "العميل",
                "الجوال",
                "المركبة",
                "اللوحة",
                "المزاد",
                "المبلغ",
                "المسدَّد",
                "المتبقّي",
                "الحالة",
                "كلمة أودو",
                "صدرت",
            ],
            cell=lambda row: [
                row.number,
                row.odoo_invoice_id,
                row.customer.full_name,
                # الجوّالُ عَرَضٌ لا موضوع، فيمرّ بحارسه كما في كلّ جدول.
                row.customer.phone if seen.customer else sensitive.HIDDEN,
                f"{row.vehicle.make} {row.vehicle.model}" if row.vehicle else "",
                row.vehicle.plate_number if row.vehicle else "",
                row.vehicle.auction.number if row.vehicle else "",
                row.amount,
                row.amount_paid,
                row.outstanding,
                row.get_state_display(),
                row.odoo_state_raw,
                row.issued_at,
            ],
        )

    page = paged(request, rows)
    with_tones(page.object_list)

    return render(
        request,
        "console/invoices.html",
        {
            "page": page,
            "pager": pager(request, page, "فاتورة"),
            "totals": invoice_totals(rows),
            "states": InvoiceState.choices,
            "state": state,
            "q": text,
            "since": since,
            "until": until,
            "seen": seen,
            "filtered": bool(text or state or since or until),
        },
    )


@console_page("console:invoice-detail")
def invoice_detail(request, pk: int):
    """فاتورةٌ واحدة، ودفعاتُها المقيَّدة، وما يسمّيها أودو.

    `derive_invoice_state` تُعيد اشتقاقَ الحالة من الدفعات هنا بدل قراءة
    العمود، فلا تعرض الشاشةُ كلمةً بائتة: العمودُ يصونه `record_payment`،
    وإعادةُ الاشتقاق عند القراءة هي ما يثبت أنهما متّفقان.

    وحوالةٌ يحملها أودو مسودّةً لا دفعةَ مقيَّدةً لها، فلا تضيف إلى
    `amount_paid` وتُقرأ الفاتورةُ مستحقّة — وهو معيارُ قبول T809 كلُّه،
    والحالةُ التي أُخرجت فيها سيارةٌ في v1.
    """
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "vehicle"), pk=pk
    )

    # الدفعاتُ المقيَّدة وحدها، تُوجَد بمفتاح المنع لا بعمودٍ على القيد:
    # `record_payment` يشتقّ المفتاح من الفاتورة، فهذا يجد **ما قُيِّد عليها
    # بالضبط** ولا شيءَ يذكرها عَرَضاً.
    payments = Transaction.objects.filter(
        idempotency_key__startswith=f"payment:{invoice.pk}:"
    ).order_by("-occurred_at")

    return render(
        request,
        "console/invoice_detail.html",
        {
            "invoice": invoice,
            "derived": money.derive_invoice_state(invoice),
            "payments": payments,
        },
    )


def decided(*, which: str = "", **filters):
    """ما حُسم فيه قرار — مقبولاً أو مرفوضاً، **ببنّاء «ما بعد البيع»**. T922

    ولماذا لا استعلامَ هنا
    ======================
    كان هنا استعلامٌ ثانٍ بأربعة حقولِ بحثٍ ومرشّحٍ واحد، بجوار استعلامِ «ما
    بعد البيع» بتسعة حقولٍ وخمسة مرشّحات — **وهما في v1 استعلامٌ واحد**
    (`AfterSalesController::listPage`، تستدعيه `index` و`decisions` معاً).
    وثمنُ النسختين قُبض فعلاً: البحثُ هنا كان لا يطابق اسمَ مشترٍ ولا جوّالاً
    ولا رقمَ مطالبةٍ ولا لوناً، وحجبُ `sensitive.py` لم يكن يمرّ على هذه
    الشاشة أصلاً.

    فالصفوفُ من :func:`~apps.console.after_sales.sold_rows` بمجموعةٍ أخرى،
    و`which` وحده يبقى هنا — لأنه وحده لا معنى له هناك.
    """
    rows = sold_rows(states=DECIDED, **filters)

    if which == "rejected":
        rows = rows.filter(state=VehicleState.REJECTED)
    elif which == "awarded":
        rows = rows.exclude(state=VehicleState.REJECTED)
    return rows


@console_page("console:ended-decisions")
def ended_decisions(request):
    """القرارات المنتهية: ما حُسم، والمرفوضُ فيه كالمقبول.

    وهي في v1 **للمالك وحده** (`AfterSalesController::decisions` ترفع ٤٠٣
    لغيره). وهنا `auctions.view` كأختها، والحسّاسُ يُحجَب حقلاً حقلاً في
    `sensitive.py` — وهو حكمُ المالك في ١٤ سبتمبر ٢٠٢٦: «تُحجب الأعمدةُ
    الحسّاسة، والشاشةُ تبقى مفتوحة». فموظّفُ الساحة يرى القرارَ وعددَ
    المزايدين، ولا يرى مشترياً ولا مبلغاً.
    """
    which = request.GET.get("which", "")
    chosen = chosen_filters(request)
    sheet_ids = sheet_settled_vehicle_ids()
    rows = decided(which=which, sheet_ids=sheet_ids, **chosen)
    seen = shown_to(request.user)

    built = sale_table(
        request,
        rows,
        chosen=chosen,
        sheet_ids=sheet_ids,
        seen=seen,
        screen="console:ended-decisions",
        name="القرارات-المنتهية",
        decided=True,
    )
    if not isinstance(built, dict):
        return built

    built["which"] = which
    # المرشّحُ السادس يدخل حسابَ «هل رُشِّحت الشاشة؟» — وإلّا اختفى زرُّ
    # «إلغاء الفلترة» لمن رشّح به وحده، فبقي على «رفضها المالك» بلا مخرج.
    built["filtered"] = built["filtered"] or bool(which)
    return render(request, "console/ended_decisions.html", built)
