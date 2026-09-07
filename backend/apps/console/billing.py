"""حالة فاتورة، وتصدير الفواتير، والقرارات المنتهية. T830-ز.

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
v1 يضعها لساناً في `BillController`. وهي هنا الوجهُ الآخر لـ
`console:partner-decisions`: تلك تعرض ما **ينتظر** قراراً، وهذه ما **انتهى**
إليه — والمرفوضةُ فيها كالمقبولة، لأن السؤال «ماذا قرّرنا» لا «ماذا بعنا».

وv1 يجمعها مع «المزايدات المقبولة» في شاشةٍ واحدة بستّة ألسنة، فيختلط ما رسا
بما رُفض تحت اسمٍ واحد.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.dateparse import parse_date

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.money import services as money
from apps.money.models import Invoice

from .exports import export, wants_export
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50

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
        cars = cars.filter(plate_number__icontains=plate)

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
        "state": money.derive_invoice_state(invoice) if invoice else "",
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

    from apps.money.models import InvoiceState

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
    from apps.money.models import InvoiceState

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


def decided(*, text: str = "", which: str = ""):
    """ما حُسم فيه قرار — مقبولاً أو مرفوضاً."""
    rows = (
        Vehicle.objects.filter(state__in=DECIDED)
        .select_related("auction", "awarded_to", "owner_company")
        .order_by("-awarded_at", "-id")
    )

    if which == "rejected":
        rows = rows.filter(state=VehicleState.REJECTED)
    elif which == "awarded":
        rows = rows.exclude(state=VehicleState.REJECTED)

    text = (text or "").strip()
    if text:
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
        )
        if text.isdigit():
            matches |= Q(auction__number=int(text)) | Q(lot_number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:ended-decisions")
def ended_decisions(request):
    """القرارات المنتهية: ما حُسم، والمرفوضُ فيه كالمقبول."""
    which = request.GET.get("which", "")
    rows = decided(text=request.GET.get("q", ""), which=which)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/ended_decisions.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "which": which,
            "rejected": Vehicle.objects.filter(state=VehicleState.REJECTED).count(),
            "awarded": Vehicle.objects.filter(state__in=DECIDED)
            .exclude(state=VehicleState.REJECTED)
            .count(),
        },
    )
