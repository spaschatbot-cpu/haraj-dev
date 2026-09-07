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

from django.core.paginator import Paginator
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django.shortcuts import render

from apps.accounts.models import Company
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

from .archive import ARCHIVED
from .exports import export, wants_export
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
    """ضيّق على شريكٍ بعينه، أو أعِد الكلّ.

    ولا يُخمَّن شريكٌ حين لا يُختار: «كل الشركاء» جوابٌ صحيح لموظّفٍ يقارن،
    و«الأول في القائمة» جوابٌ عن سؤالٍ لم يُطرح.
    """
    partner = (partner or "").strip()
    if partner.isdigit():
        return rows.filter(owner_company_id=int(partner))
    return rows


def summary_for(partner: str = "") -> dict:
    """أرقام لوحة الشريك — كلُّها من الفاتورة لا من جدولٍ مرفوع."""
    cars = _scoped(Vehicle.objects.all(), partner)
    won = cars.filter(state__in=AWARDED)

    invoices = Invoice.objects.filter(vehicle__in=won)
    paid = invoices.filter(state=InvoiceState.PAID)

    return {
        "vehicles": cars.count(),
        "auctions": cars.values("auction").distinct().count(),
        "won": won.count(),
        "unsold": cars.exclude(state__in=AWARDED).count(),
        "won_value": won.aggregate(t=Sum("awarded_price"))["t"] or ZERO,
        "invoiced": invoices.count(),
        "paid": paid.count(),
        "unpaid": won.count() - paid.count(),
        "paid_value": paid.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
    }


@console_page("console:partner-console")
def partner_console(request):
    """لوحة الشريك: أرقامُ شريكٍ واحد، وكلٌّ منها بابٌ إلى صفوفه."""
    partner = request.GET.get("partner", "")
    return render(
        request,
        "console/partner_console.html",
        {
            "totals": summary_for(partner),
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


def _auctions_screen(request, state: str = ""):
    """جسمُ شاشة مزادات الشريك — يشترك فيه أربعةُ مداخل.

    ولماذا أربعةُ **دوالّ** فوقه لا دالّةٌ واحدة بأربعة مسارات: `console_page`
    يأخذ اسمَ صفحةٍ واحدة ويقرأ قدرتَها من السجلّ. ودالّةٌ واحدة تخدم أربعة
    أسماء تعني أن ثلاثةً منها **محروسةٌ بصفِّ رابعة** — وهو بعينه الافتراق
    الذي وُجد `navigation.py` لمنعه. فالجسم مشترك، والحراسةُ لكلٍّ صفُّه.
    """
    partner = request.GET.get("partner", "")
    rows = auctions_of(partner, state or request.GET.get("state", ""))
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
    return _auctions_screen(request, AuctionState.SCHEDULED)


@console_page("console:partner-active")
def partner_active(request):
    """المزاد الشغال — الجاري الآن."""
    return _auctions_screen(request, AuctionState.LIVE)


@console_page("console:partner-ended")
def partner_ended(request):
    """المزادات المنتهية — بتعريف الأرشيف نفسه: منتهٍ ومُسوّى وملغى."""
    return _auctions_screen(request, ARCHIVED)


def vehicles_of(partner: str = "", which: str = "", text: str = ""):
    """سيارات الشريك، بمرشّحات v1 الأربعة: الكل · مباعة · غير مباعة · تنتظر قراري."""
    rows = _scoped(
        Vehicle.objects.select_related("auction", "awarded_to", "owner_company"),
        partner,
    ).order_by("-id")

    if which == "sold":
        rows = rows.filter(state__in=AWARDED)
    elif which == "unsold":
        rows = rows.exclude(state__in=AWARDED).exclude(
            state=VehicleState.AWAITING_DECISION
        )
    elif which == "deciding":
        rows = rows.filter(state=VehicleState.AWAITING_DECISION)

    text = (text or "").strip()
    if text:
        matches = (
            Q(plate_number__icontains=text)
            | Q(vin__icontains=text)
            | Q(make__icontains=text)
            | Q(model__icontains=text)
        )
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
                "الشاصي",
                "سعر الوقوف",
                "سعر الترسية",
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
                row.vin,
                row.reserve_price,
                row.awarded_price,
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
