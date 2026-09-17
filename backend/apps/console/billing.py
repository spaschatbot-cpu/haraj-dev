"""حالة فاتورة، وتصدير الفواتير، والقرارات المنتهية. T830ز.

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

from django.shortcuts import render
from django.utils.dateparse import parse_date

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

from .exports import export, wants_export
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


def invoices_between(*, since: str = "", until: str = "", state: str = ""):
    """الفواتير في مدىً من التواريخ — أساسُ شاشة التصدير."""
    rows = Invoice.objects.select_related("customer", "vehicle").order_by("-issued_at")

    start = parse_date((since or "").strip())
    end = parse_date((until or "").strip())
    if start:
        rows = rows.filter(issued_at__date__gte=start)
    if end:
        rows = rows.filter(issued_at__date__lte=end)

    if (state or "").strip() in InvoiceState.values:
        rows = rows.filter(state=state)
    return rows


@console_page("console:invoices-export")
def invoices_export(request):
    """تصدير الفواتير: مدىً من التواريخ، وعددٌ يُرى قبل التنزيل.

    والعدد قبل الزرّ عمداً: في v1 التصدير رابطٌ يُضغط فيبدأ التنزيل، ولا يعرف
    الضاغط أهو ثلاثةُ صفوفٍ أم ثلاثةَ عشرَ ألفاً حتى يفتح الملف. ومن ينتظر
    ملفاً ثقيلاً بلا سببٍ يضغط ثانيةً.
    """

    since = request.GET.get("since", "")
    until = request.GET.get("until", "")
    state = request.GET.get("state", "")
    rows = invoices_between(since=since, until=until, state=state)

    if wants_export(request):
        return export(
            rows,
            name="الفواتير",
            headers=[
                "الرقم",
                "صدرت",
                "العميل",
                "المركبة",
                "المزاد",
                "المبلغ",
                "المسدَّد",
                "المتبقّي",
                "الحالة",
                "كلمة أودو",
            ],
            cell=lambda row: [
                row.number,
                row.issued_at,
                row.customer.full_name,
                f"{row.vehicle.make} {row.vehicle.model}" if row.vehicle else "",
                row.vehicle.auction.number if row.vehicle else "",
                row.amount,
                row.amount_paid,
                row.outstanding,
                row.get_state_display(),
                row.odoo_state_raw,
            ],
        )

    return render(
        request,
        "console/invoices_export.html",
        {
            "count": rows.count(),
            "since": since,
            "until": until,
            "state": state,
            "states": [
                (value, InvoiceState(value).label) for value in InvoiceState.values
            ],
        },
    )
