"""اعتماد مدفوعات الشريك — ملفٌّ يُقيَّد في الدفتر، لا جدولٌ موازٍ. T830ي.

شاشة v1 المقابلة تكتب عطلَها على نفسها، بالحرف:

    «الشريك لا يرى أي حالة سداد من النظام المحاسبي — لا فواتير ولا مدفوعات
     ولا مستحقّات. صفحته تقرأ **هذا الجدول فقط**، ومصدره الوحيد هو ملفك.»

أي أن الملفّ المرفوع **جدولٌ ثانٍ للحقيقة**: «مسدَّدة» فيه لا تمسّ دفتراً ولا
فاتورةً ولا حساباً. فللسداد حقيقتان، ولا شيء يوفّق بينهما.

**وهنا الملفّ مصدرُ استيرادٍ لا مصدرُ حقيقة.** كلُّ صفٍّ يُقيَّد دفعةً على
فاتورة المركبة عبر `bidding.settlement.record_vehicle_payment` — وهي
`money.services.record_payment` ومعها نقلُ المركبة إلى «مسدَّدة» في المعاملة
نفسِها — فيظهر في هذه الشاشة وفي حساب العميل وفي صحّة المال وفي صفحات الشريك
وفي طابور الخروج — **رقمٌ واحد**.

ثلاثة أشياء تتغيّر بذلك، وكلُّها كانت جملاً على الشاشة فصارت بناءً
=================================================================

**١ — «تجنّب رفع الملف نفسه مرتين» صار مفتاحاً.** بصمةُ الملفّ (SHA-256)
حقلٌ فريد في :class:`~apps.money.models.PaymentSheet`، فالرفعُ الثاني يُرفض
قبل أن يُقرأ صفٌّ واحد. ورافعُ الملفّ مرّتين ليس مهملاً غالباً: هو من انقطع
اتصالُه فأعاد، أو لم يجد رسالة نجاحٍ فضغط ثانيةً — والتحذير لا يمنعه.

ومفتاحٌ ثانٍ تحته: `record_payment` نفسها تحمل مفتاح تفرُّدٍ لكل صفّ
(`payment:{invoice}:{reference}`)، فحتى لو رُفع الصفُّ في ملفَّين مختلفين
قُيّد مرّةً.

**٢ — «حذف» صار عكسَ قيد.** سجلُّ v1 يعرض زرَّ «حذف» بجوار كل دفعة. وحذفُ صفِّ
دفعةٍ من الدفتر محوُ تدقيق: القيد المغلوط **يُعكَس** (`money.services.reverse`)
فيبقى الاثنان ومعهما من عكس ولماذا. وهذه الشاشة لا تحذف شيئاً.

**٣ — «المبلغ فارغ = أعلى عرض» أُسقط.** خانةُ v1 تقول «اتركه فارغاً = أعلى
عرض»، فتُقيَّد دفعةٌ على **رقمٍ لم يكتبه أحد**. وهي خانة المبلغ الحرّة نفسها
التي أُسقطت من «خصم مباشر»، وأثرُها مقيسٌ هناك: «خرج 29,990 مقابل مدفوع
20,000». فالمبلغ هنا مكتوبٌ في الصفّ أو يُرفض الصفّ.

وصفٌّ لا يطابق مركبةً يُتخطّى **ويُذكر**
========================================
كما في v1 («الصف الذي لا يطابق سيارة تسويق يُتخطّى ويُذكر لك») — وهي إحسانٌ
فيها. والزيادةُ هنا أن سببَ التخطّي مكتوبٌ لكل صفّ: لا مركبة بهذا المفتاح، أو
المركبة لم تُبع، أو لا فاتورة عليها بعد، أو المبلغ ليس رقماً.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q, Sum
from django.shortcuts import redirect, render

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import VehicleState
from apps.bidding import settlement
from apps.bidding.models import Bid
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.sheets import Sheet, SheetError
from apps.money.models import Invoice, InvoicePaymentSource, PaymentSheet

from . import payments
from .exports import export
from .icons import path_of
from .views import console_page

ZERO = Decimal("0.00")

#: ما يقبله الرفع. أكبرُ من ذلك خطأٌ — جدولُ الأسطول كلّه، أو صورةٌ أُعيدت
#: تسميتها — وقراءتُه في الذاكرة لاكتشاف ذلك هي كيف تسقط لوحة.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_RECEIPT_BYTES = 8 * 1024 * 1024

#: ما يدخل شاشةَ الاعتماد: ما رسا ولم يخرج بعد. ومركبةٌ لم تُبع لا
#: تُسدَّد — وv1 يعرضها ومعها زرُّ اعتماد (`فورد ميلان #12276`).
SETTLING = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)

#: أسماء الأعمدة المقبولة، بالعربية والإنجليزية كما في v1. والمفتاح خمسةٌ
#: بدائل لأن الملفّ يأتي من نظامٍ لا نملكه، ولا يُعرف أيُّها فيه.
KEY_HEADERS = {
    "رقم المطالبة",
    "رقم السيارة",
    "معرف المركبة",
    "اللوحة",
    "الشاصي",
    "الشاسيه",
    "اللوط",
    "claim",
    "vehicle",
    "plate",
    "vin",
    "lot",
}
AMOUNT_HEADERS = {"المبلغ", "amount"}
NOTE_HEADERS = {"ملاحظات", "ملاحظة", "note", "notes"}

AWARDED = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)


def _column(headers: list[str], names: set[str]) -> int | None:
    """موضعُ أول عمودٍ يطابق أحد الأسماء — أو `None`."""
    for index, header in enumerate(headers):
        if header.strip().lower() in {name.lower() for name in names}:
            return index
    return None


def _vehicle_for(key: str) -> Vehicle | None:
    """المركبة التي يشير إليها هذا المفتاح، أو `None`.

    خمسةُ بدائل كما في v1، وتُجرَّب بالترتيب من الأدقّ إلى الأوسع: المعرّف
    فالشاصي فاللوحة فاللوط. والمطابقة **تامّة** لا جزئية: صفٌّ يُقيَّد على
    مركبةٍ «تشبه» مفتاحَه هو دفعةٌ على سيارةٍ أخرى.
    """
    key = (key or "").strip()
    if not key:
        return None

    cars = Vehicle.objects.filter(state__in=AWARDED)
    if key.isdigit():
        found = cars.filter(Q(pk=int(key)) | Q(lot_number=int(key)))
        if found.count() == 1:
            return found.first()

    found = cars.filter(Q(vin__iexact=key) | Q(plate_number__iexact=key))
    return found.first() if found.count() == 1 else None


def _amount(raw: str) -> Decimal | None:
    """المبلغ كما كُتب — ولا يُخمَّن حين يغيب.

    v1 يقول «اتركه فارغاً = أعلى عرض»، فتُقيَّد دفعةٌ على رقمٍ لم يكتبه أحد.
    """
    text = (raw or "").strip().replace(",", "")
    if not text:
        return None
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return value if value > ZERO else None


def read_rows(sheet: Sheet) -> tuple[list[dict], list[dict]]:
    """اقرأ الملفّ إلى صفوفٍ مفهومة، وصفوفٍ مُتخطّاة بسببها.

    مفصولةٌ عن الكتابة ليسألها الاختبار على ملفٍّ بصفوفٍ سيّئة بلا قاعدة
    بيانات، وليقرأها العرضُ الجافّ (المعاينة قبل الاعتماد) بلا قيدٍ واحد.
    """
    key_at = _column(sheet.headers, KEY_HEADERS)
    amount_at = _column(sheet.headers, AMOUNT_HEADERS)
    note_at = _column(sheet.headers, NOTE_HEADERS)

    if key_at is None or amount_at is None:
        raise SheetError(
            "الملفّ ينقصه عمود المفتاح (رقم المطالبة أو السيارة أو اللوحة أو "
            "الشاصي أو اللوط) أو عمود المبلغ."
        )

    good: list[dict] = []
    skipped: list[dict] = []
    for number, row in enumerate(sheet.rows, start=2):
        key = row[key_at] if key_at < len(row) else ""
        amount = _amount(row[amount_at] if amount_at < len(row) else "")
        note = row[note_at] if note_at is not None and note_at < len(row) else ""

        if not (key or "").strip():
            skipped.append({"line": number, "key": "", "why": "لا مفتاح في الصفّ"})
            continue
        if amount is None:
            skipped.append({"line": number, "key": key, "why": "المبلغ ليس رقماً موجباً"})
            continue
        good.append({"line": number, "key": key, "amount": amount, "note": note})
    return good, skipped


@console_page("console:partner-payments-template")
def payment_template(request):
    """**نزّل القالب** — ورقةٌ تخرج مُعبّأةً بالمستحقّ ومراجعه. زرُّ v1.

    سؤالُ المالك في v1 مكتوبٌ في تعليقها: «وين الإكسل اللي أرفع بيه؟». فالقالبُ
    يخرج **بالسيارات ومراجعها** — رقمُ المطالبة واللوط واللوحة والاسم — ولا
    يبقى إلا كتابةُ المبلغ ورفعُه كما هو. وبناءُ الورقة باليد يعني خطأً في
    مرجعٍ يُسقط صفّاً عند الرفع.

    **ويُختار مزادُه وحالتُه قبل التنزيل** (طلبُ المالك ٢٠٢٦-٠٩-٠٦: «اختار
    المزاد اللي هنزّل الملف بتاعه، وفلتر هل بننزّل المسدّدة ولا إيه»): كان
    يخرج بكلّ المزادات وبغير المسدَّدة وحدها، فيدفع لمزادٍ وهو يقرأ ورقةَ
    مزادين.

    **والمبلغُ مُعبّأٌ بالمتبقّي لا فارغاً**: الحالةُ الغالبة سدادٌ كامل،
    ومن يريد جزئيّاً يعدّل الخانة. وهو عكسُ «اتركه فارغاً = أعلى عرض» في v1:
    هناك الفراغُ يعني رقماً يختاره النظام، وهنا الرقمُ مكتوبٌ في الورقة
    يراه من يرفعها.
    """
    auction = (request.GET.get("auction") or "").strip()
    state = (request.GET.get("state") or "unpaid").strip()

    rows = (
        Vehicle.objects.filter(owner_company__isnull=False, state__in=SETTLING)
        .select_related("auction")
        .order_by("-auction__number", "lot_number")
    )
    if auction.isdigit():
        rows = rows.filter(auction__number=int(auction))

    cars = list(rows[:5000])
    _decorate_cars(cars)
    if state == "paid":
        cars = [car for car in cars if car.is_paid]
    elif state == "unpaid":
        cars = [car for car in cars if not car.is_paid]

    name = "قالب-دفعات-الشريك"
    if auction.isdigit():
        name += f"-مزاد-{auction}"
    return export(
        cars,
        name=name,
        headers=[
            # أسماءُ الأعمدة التي يقبلها القارئُ نفسُه — فما يخرج يدخل.
            "رقم المطالبة",
            "اللوط",
            "اللوحة",
            "السيارة",
            "المبلغ",
            "التاريخ",
            "ملاحظات",
        ],
        cell=lambda car: [
            car.claim_number,
            car.lot_number,
            car.plate_number,
            f"{car.make} {car.model}",
            car.due,
            "",
            "",
        ],
    )


@console_page("console:partner-payments-approve")
def approve(request):
    """اعتماد مدفوعات الشريك — أقسامُ v1 الأربعة، وقيدٌ في الدفتر لا جدولٌ موازٍ.

    v1 يضع في هذه الشاشة أربعةَ أشياء، وكان هنا واحدٌ منها (الرفع):

    1. بطاقةَ رفعٍ ومعها **قالبٌ يُنزَّل** مرشَّحاً بالمزاد والحالة؛
    2. بطاقةَ إحصاء: إجمالي المعتمد وعددُ الصفوف والسيارات وآخرُ دفعةٍ مرفوعة؛
    3. **«السيارات حسب المزاد»** — كلُّ مركبةٍ تحت مزادها ومعها زرُّ اعتماد؛
    4. **«سجل الدفعات المعتمدة»**.

    والثالثُ هو عملُ الشاشة: طلبُ المالك في v1 مكتوبٌ في تعليقها — «يعلّم
    المالك كلاً منها من هنا مباشرةً **بدل أن يكتب رقمها غيباً**». وكان على من
    يريد اعتمادَ سيارةٍ واحدةٍ هنا أن يرفع ملفّاً لأجلها.
    """
    if request.method == "POST":
        op = request.POST.get("op")
        if op == "pay":
            return _pay_one(request)
        if op == "mark":
            return _mark_one(request)
        if op == "reverse":
            return _reverse_one(request)
        return _upload(request)

    text = (request.GET.get("q") or "").strip()
    auction = (request.GET.get("auction") or "").strip()

    cars = (
        Vehicle.objects.filter(owner_company__isnull=False, state__in=SETTLING)
        .select_related("auction", "owner_company", "awarded_to")
        .order_by("-auction__number", "lot_number")
    )
    if auction.isdigit():
        cars = cars.filter(auction__number=int(auction))
    if text:
        cars = cars.filter(
            search_q(text, "plate_number", "make", "model", "claim_number")
        )

    rows = list(cars[:400])
    _decorate_cars(rows)
    groups = _by_auction(rows)

    sheets = PaymentSheet.objects.select_related("uploaded_by")[:20]
    posted = Invoice.objects.filter(
        vehicle__owner_company__isnull=False, amount_paid__gt=ZERO
    )
    return render(
        request,
        "console/partner_payments_approve.html",
        {
            "sheets": sheets,
            "groups": groups,
            "log": _payment_log(),
            "q": text,
            "auction": auction,
            "auctions": (
                Auction.objects.filter(vehicles__owner_company__isnull=False)
                .distinct()
                .order_by("-number")[:60]
            ),
            "total": posted.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
            "count": posted.count(),
            # بطاقةُ إحصاء v1: كم صفّاً قُيّد، وكم سيارةً، ومتى آخرُ ملفّ.
            "rows_posted": PaymentSheet.objects.aggregate(t=Sum("rows_posted"))["t"] or 0,
            "last_sheet": sheets[0] if sheets else None,
            "icon_pay": path_of("coins"),
            "icon_export": path_of("download"),
        },
    )


def _receipts_for(invoices) -> dict:
    """إيصالُ الملفّ لكلّ فاتورةٍ قُيّدت منه — استعلامان لا استعلامٌ لكلّ صفّ."""
    if not invoices:
        return {}

    keys = []
    for invoice in invoices:
        keys.append(Q(idempotency_key__startswith=f"{payments.KEY_BY_PK}{invoice.pk}:"))
        keys.append(
            Q(idempotency_key__startswith=f"{payments.KEY_BY_NUMBER}{invoice.number}:")
        )

    from functools import reduce
    import operator

    by_number = {invoice.number: invoice.pk for invoice in invoices}
    by_pk = {invoice.pk: invoice.pk for invoice in invoices}

    digests: dict[int, str] = {}
    rows = payments.recorded().filter(reduce(operator.or_, keys))
    for key in rows.values_list("idempotency_key", flat=True):
        shape, value = payments.invoice_of(key)
        pk = by_pk.get(value) if shape == "pk" else by_number.get(value)
        tail = key.split(":", 2)[-1]
        if pk is not None and tail.startswith("sheet:"):
            digests.setdefault(pk, tail.split(":")[1])

    if not digests:
        return {}

    sheets = {
        sheet.digest[:12]: sheet
        for sheet in PaymentSheet.objects.filter(
            reduce(
                operator.or_,
                (Q(digest__startswith=d) for d in set(digests.values())),
            )
        ).exclude(receipt="")
    }
    return {pk: sheets[d] for pk, d in digests.items() if d in sheets}


def partner_console_payment_dates(invoices) -> dict:
    """تاريخُ آخر دفعةٍ لكلّ فاتورة — تُقرأ من `partner_console` لا تُنسَخ.

    وكُتبت مرّةً هناك بشكلٍ واحدٍ من شكلَي مفتاح المنع فخرج العمودُ فارغاً؛
    فالنداءُ على الدالّة نفسِها، لا نسخةٌ ثالثة.
    """
    from apps.console import partner_console

    return {pk: when for pk, (when, _src) in partner_console._payment_facts(invoices).items()}


def _decorate_cars(rows) -> None:
    """أضِف لكلّ مركبةٍ فاتورتَها وصورتَها وأعلى عرضٍ عليها ومتى سُدِّدت.

    وأربعةُ استعلاماتٍ للصفحة كلِّها لا أربعةٌ لكلّ صفّ: الشاشةُ تُفتح على
    أربعمئة مركبة.
    """
    invoices = {
        invoice.vehicle_id: invoice
        for invoice in Invoice.objects.filter(vehicle__in=rows).order_by(
            "issued_at", "id"
        )
    }
    covers: dict[int, object] = {}
    for shot in VehicleImage.objects.filter(vehicle__in=rows).order_by(
        "vehicle_id", "-is_cover", "position", "id"
    ):
        covers.setdefault(shot.vehicle_id, shot)

    # **«أعلى عرض» عمودُ v1** — وهو ما رستْ به إن رستْ، وإلّا أعلى مزايدةٍ
    # قائمة. واستعلامٌ واحدٌ للصفحة.
    tops = dict(
        Bid.objects.filter(vehicle__in=rows, is_superseded=False, is_withdrawn=False)
        .values_list("vehicle")
        .annotate(top=Max("amount"))
    )

    # ومتى سُدِّدت — من الدفتر، بمفتاح المنع بشكليه (`console.payments`).
    paid_at = partner_console_payment_dates(list(invoices.values()))

    # **عمودُ «الحوالة» في v1** — وهو إيصالُ الملفّ الذي قُيّدت منه الدفعة.
    #
    # ولا حقلَ إيصالٍ على المركبة هنا: الإيصالُ على **صفّ الملفّ**، إيصالٌ
    # واحدٌ لكلّ صفوفه. والوصلةُ مرجعُ الدفعة نفسُه — `_upload` يكتبه
    # `sheet:<اثنتا عشرة من البصمة>:<السطر>` — فتُقرأ منه البصمةُ ويُؤخذ
    # الإيصال. ومن قُيّدت دفعتُه من النافذة أو يدويّاً لا إيصالَ له، وتلك
    # شرطةٌ صادقة.
    receipts = _receipts_for(list(invoices.values()))

    for car in rows:
        invoice = invoices.get(car.pk)
        car.invoice = invoice
        car.cover = covers.get(car.pk)
        car.top_amount = car.awarded_price or tops.get(car.pk)
        car.paid_amount = invoice.amount_paid if invoice else ZERO
        car.due = invoice.outstanding if invoice else (car.awarded_price or ZERO)
        car.paid_at = paid_at.get(invoice.pk) if invoice else None
        # **إيصالُ المركبة أوّلاً، ثم إيصالُ الملفّ الذي قُيّدت منه.** ما
        # رُفع مع اعتمادها بعينه أدلُّ من إيصالِ دفعةٍ ضمّت مئةَ سيارة.
        car.receipt = receipts.get(invoice.pk) if invoice else None
        # «مسدَّدة» هنا = **لا بقيّةَ على الفاتورة**، لا علمٌ يُرفع بملفّ.
        car.is_paid = bool(invoice) and invoice.outstanding <= ZERO


def _by_auction(rows) -> list[dict]:
    """اجمع المركبات تحت مزاداتها بإحصاء v1: كم سيارة، كم مسدَّدة، وكم مالُها."""
    groups: list[dict] = []
    for car in rows:
        if not groups or groups[-1]["auction"].pk != car.auction_id:
            groups.append(
                {"auction": car.auction, "rows": [], "paid": 0, "amount": ZERO}
            )
        group = groups[-1]
        group["rows"].append(car)
        group["paid"] += 1 if car.is_paid else 0
        group["amount"] += car.awarded_price or ZERO
    for group in groups:
        group["cars"] = len(group["rows"])
        group["unpaid"] = group["cars"] - group["paid"]
    return groups


def _payment_log(limit: int = 50):
    """سجلُّ الدفعات المعتمدة — قسمُ v1 الأخير، من الدفتر لا من جدولٍ مرفوع."""
    from apps.console import partner_console

    rows = list(partner_console.payments_of("")[:limit])
    payments.decorate(rows)
    cars = {
        car.pk: car
        for car in Vehicle.objects.filter(
            pk__in={r.invoice.vehicle_id for r in rows if r.invoice}
        ).select_related("auction")
    }
    # **عمودُ «الدفعة» في v1** (`batch_ref`): من أيّ ملفٍّ جاء هذا القيد.
    # ويُقرأ من مرجعه — `sheet:<بصمة>:<سطر>` — فيُعرض اسمُ الملفّ لا بصمتُه.
    # ومن قُيّد يدويّاً أو من النافذة يُقال فيه ذلك، لا يُترك فارغاً.
    names = {
        sheet.digest[:12]: (sheet.filename or sheet.digest[:12])
        for sheet in PaymentSheet.objects.all()[:500]
    }
    for row in rows:
        row.vehicle = cars.get(row.invoice.vehicle_id) if row.invoice else None
        tail = row.idempotency_key.split(":", 2)[-1]
        if tail.startswith("sheet:"):
            row.batch = names.get(tail.split(":")[1], "ملفّ محذوف")
        elif tail.startswith("mark:"):
            row.batch = "تعليمٌ يدويّ"
        elif tail.startswith("approve:"):
            row.batch = "اعتمادٌ من الجدول"
        else:
            row.batch = row.source
    return rows


def _pay_one(request):
    """اعتمِد سدادَ مركبةٍ واحدة — نافذةُ v1 «اعتماد سداد سيارة».

    **وهي عملُ الشاشة الذي كان غائباً.** طلبُ المالك في v1 مكتوبٌ في تعليقها:
    «يعلّم المالك كلاً منها من هنا مباشرةً بدل أن يكتب رقمها غيباً». وكان على
    من يريد اعتمادَ سيارةٍ واحدةٍ هنا أن **يرفع ملفّاً لأجلها**.

    والدفعةُ تمرّ من `settlement.record_vehicle_payment` كصفوفِ الملفّ — البابُ
    نفسُه: قيدٌ في الدفتر ونقلُ المركبة إلى «مسدَّدة» في معاملةٍ واحدة. فلا
    يصير للاعتماد طريقان أحدُهما ينسى نصفَ العمل.

    **والمبلغُ مكتوبٌ أو يُرفض.** خانةُ v1 تقول «اتركه فارغاً = أعلى عرض»،
    فتُقيَّد دفعةٌ على رقمٍ لم يكتبه أحد — وأثرُها مقيسٌ في الشاشة المجاورة:
    «خرج 29,990 مقابل مدفوع 20,000». وهي الخانةُ نفسُها التي أُسقطت من «خصم
    مباشر».
    """
    back = redirect("console:partner-payments-approve")
    vehicle = Vehicle.objects.filter(pk=request.POST.get("vehicle") or 0).first()
    if vehicle is None:
        messages.error(request, "مركبةٌ غير معروفة.")
        return back

    invoice = (
        Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
    )
    if invoice is None:
        messages.error(
            request, f"لوط {vehicle.lot_number}: لا فاتورةَ عليها بعد — تُفوتَر أوّلاً."
        )
        return back

    raw = (request.POST.get("amount") or "").strip()
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        messages.error(request, "المبلغ مطلوبٌ ويُكتب رقماً — ولا يُفترض من أعلى عرض.")
        return back

    note = (request.POST.get("note") or "").strip()[:120]

    # **صورةُ الحوالة — خانةُ v1 في هذه النافذة، اختياريّة.** وتُفحص قبل
    # القيد: ملفٌّ أكبرُ من الحدّ يُردّ **ولا تُقيَّد دفعتُه**، فلا يبقى قيدٌ
    # في الدفتر بلا الإيصال الذي قُصد أن يُرفَق به.
    receipt = request.FILES.get("receipt")
    if receipt is not None and receipt.size > MAX_RECEIPT_BYTES:
        messages.error(request, "الإيصالُ أكبر من ثمانية ميجابايت — لم يُقيَّد شيء.")
        return back

    # مرجعٌ يُميّز هذا القيدَ ويمنع تكرارَه بالضغط مرّتين على الزرّ نفسِه.
    reference = f"approve:{vehicle.pk}:{request.POST.get('paid_at') or ''}:{amount}"

    try:
        with transaction.atomic():
            settlement.record_vehicle_payment(
                invoice=invoice,
                amount=amount,
                source=InvoicePaymentSource.CASH,
                reference=reference,
                by=request.user,
            )
    except Exception as refusal:
        messages.error(request, f"لوط {vehicle.lot_number}: {refusal}")
        return back

    if receipt is not None:
        vehicle.payment_receipt = receipt
        vehicle.save(update_fields=["payment_receipt"])

    audit.record(
        action="console.partner_payment_approved",
        entity=vehicle,
        actor=request.user,
        before={},
        after={"amount": str(amount), "invoice": invoice.number},
        note=note or "اعتماد سداد من شاشة مدفوعات الشريك",
    )
    messages.success(
        request, f"قُيّد {amount} على الفاتورة {invoice.number} (لوط {vehicle.lot_number})."
    )
    return back


def _reverse_one(request):
    """اعكِس حركةً واحدةً من السجلّ — عمودُ «حذف» في v1، بما يقع هنا.

    v1 يحذف صفَّ الدفعة من جدوله فتختفي من صفحة الشريك. وحذفُ صفِّ دفعةٍ من
    دفترٍ **محوُ تدقيق**: يبقى المبلغُ في حساب العميل ولا يبقى ما يفسّره.

    فالعكسُ قيدٌ مرآةٌ (`money.services.reverse`): الأصلُ كما هو، وفوقه عكسُه
    ومن عكس ومتى — وذلك ما يُعيد بناءَ رصيدٍ متنازَعٍ عليه بعد شهور.
    """
    from apps.money import services as money
    from apps.money.models import Transaction

    back = redirect("console:partner-payments-approve")
    txn = Transaction.objects.filter(pk=request.POST.get("txn") or 0).first()
    if txn is None:
        messages.error(request, "حركةٌ غير معروفة.")
        return back

    try:
        with transaction.atomic():
            mirror = money.reverse(txn, reason="إلغاء اعتماد السداد", by=request.user)
    except Exception as refusal:
        messages.error(request, str(refusal))
        return back

    audit.record(
        action="console.partner_payment_reversed",
        entity=txn,
        actor=request.user,
        before={},
        after={"reversal": mirror.pk},
        note="عكسُ قيدِ سدادٍ من سجلّ مدفوعات الشريك",
    )
    messages.success(
        request, f"قُيّد عكسُ الحركة {txn.pk} بالحركة {mirror.pk} — والأصلُ باقٍ."
    )
    return back


def _mark_one(request):
    """**علّم سيارةً واحدة يدويّاً** — بطاقةُ v1 الثانية، بزرَّيها.

    v1 يضعها بجوار بطاقة الرفع: يُكتب رقمُ السيارة ويُضغط «✔ مسددة» أو
    «✕ غير مسددة». وهي لمن بيده رقمُ سيارةٍ واحدة ولا يبني لها ملفّاً.

    **و«غير مسددة» عكسُ قيدٍ لا محوُ علم.** في v1 العلمُ عمودٌ يُطفأ فتختفي
    السيارةُ من صفحة الشريك ولا يبقى أثرٌ لما كان. وهنا الدفعةُ حركةٌ في
    الدفتر، فإلغاؤها **يُقيَّد عكسُها** (`money.services.reverse`): يبقى
    القيدان ومعهما من عكس ومتى ولماذا. وذلك ما يُسأل عنه بعد شهر.

    **والمبلغُ مكتوبٌ أو يُرفض** — خانةُ v1 «اتركه فارغاً = أعلى عرض»
    أُسقطت، وأثرُها مقيسٌ في الشاشة المجاورة: «خرج 29,990 مقابل مدفوع
    20,000».
    """
    back = redirect("console:partner-payments-approve")
    raw_id = (request.POST.get("vehicle_no") or "").strip()
    vehicle = None
    if raw_id.isdigit():
        vehicle = Vehicle.objects.filter(pk=int(raw_id)).first()
    if vehicle is None and raw_id:
        # ورقمُ اللوط أو المطالبة يُقبلان كذلك: من بيده ورقةٌ لا يعرف معرّفَنا.
        vehicle = Vehicle.objects.filter(
            Q(claim_number=raw_id)
            | (Q(lot_number=int(raw_id)) if raw_id.isdigit() else Q(pk=None))
        ).first()
    if vehicle is None:
        messages.error(request, f"لا مركبةَ بالرقم «{raw_id}».")
        return back
    if vehicle.owner_company_id is None:
        messages.error(request, f"المركبة {vehicle.pk} ليست سيارةَ تسويق.")
        return back

    invoice = (
        Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
    )
    if invoice is None:
        messages.error(request, f"المركبة {vehicle.pk}: لا فاتورةَ عليها بعد.")
        return back

    if request.POST.get("paid") == "0":
        return _unmark(request, vehicle, invoice, back)

    raw = (request.POST.get("amount") or "").strip()
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError):
        messages.error(request, "المبلغ مطلوبٌ ويُكتب رقماً — ولا يُفترض من أعلى عرض.")
        return back

    note = (request.POST.get("note") or "").strip()[:120]
    try:
        with transaction.atomic():
            settlement.record_vehicle_payment(
                invoice=invoice,
                amount=amount,
                source=InvoicePaymentSource.CASH,
                reference=f"mark:{vehicle.pk}:{amount}",
                by=request.user,
            )
    except Exception as refusal:
        messages.error(request, f"المركبة {vehicle.pk}: {refusal}")
        return back

    audit.record(
        action="console.partner_payment_marked",
        entity=vehicle,
        actor=request.user,
        before={},
        after={"amount": str(amount), "invoice": invoice.number},
        note=note or "تعليمٌ يدويّ من شاشة مدفوعات الشريك",
    )
    messages.success(request, f"قُيّد {amount} على الفاتورة {invoice.number}.")
    return back


def _unmark(request, vehicle, invoice, back):
    """«✕ غير مسددة» — يُعكَس ما قُيّد، ولا يُحذف.

    v1 يطفئ عموداً فتختفي السيارةُ من صفحة الشريك بلا أثر. وهنا تُعكَس
    **كلُّ** دفعاتِ هذه الفاتورة، ويبقى الأصلُ وعكسُه ومن عكس.
    """
    from apps.money import services as money

    txns = payments.recorded().filter(
        Q(idempotency_key__startswith=f"{payments.KEY_BY_PK}{invoice.pk}:")
        | Q(idempotency_key__startswith=f"{payments.KEY_BY_NUMBER}{invoice.number}:")
    )
    done, failed = 0, ""
    for txn in txns:
        try:
            with transaction.atomic():
                money.reverse(txn, reason="إلغاء اعتماد السداد", by=request.user)
            done += 1
        except Exception as refusal:
            failed = failed or str(refusal)

    if not done:
        messages.error(request, failed or "لا دفعاتٍ مقيَّدةٌ على هذه الفاتورة.")
        return back

    audit.record(
        action="console.partner_payment_unmarked",
        entity=vehicle,
        actor=request.user,
        before={},
        after={"reversed": done, "invoice": invoice.number},
        note="إلغاء اعتماد السداد — عكسُ قيدٍ لا حذف",
    )
    messages.success(
        request, f"عُكست {done} دفعةً على الفاتورة {invoice.number} — والأصلُ باقٍ."
    )
    return back


def _upload(request):
    """اقرأ الملفّ وقيّد صفوفه — أو ارفضه كلَّه."""
    upload = request.FILES.get("sheet")
    if upload is None:
        messages.error(request, "لم يُرفَع ملفّ.")
        return redirect("console:partner-payments-approve")
    if upload.size > MAX_UPLOAD_BYTES:
        messages.error(request, "الملفّ أكبر من خمسة ميجابايت.")
        return redirect("console:partner-payments-approve")

    # **إيصالُ الحوالة — خانةُ v1 الثانية.** اختياريٌّ، وواحدٌ يُرفَق بكلّ
    # صفوف هذه الدفعة. وحدُّه ثمانيةُ ميجابايت كـ v1: صورةُ حوالةٍ من هاتفٍ
    # تبلغ خمسةً، والملفُّ الذي يبلغ عشرين ليس إيصالاً.
    receipt = request.FILES.get("receipt")
    if receipt is not None and receipt.size > MAX_RECEIPT_BYTES:
        messages.error(request, "الإيصالُ أكبر من ثمانية ميجابايت.")
        return redirect("console:partner-payments-approve")

    data = upload.read()
    digest = hashlib.sha256(data).hexdigest()

    # البصمة أوّلاً، قبل القراءة: الرفع الثاني للملفّ نفسه يُرفض ولا يُقرأ منه
    # صفّ. وهذا ما كان تحذيراً في v1.
    already = PaymentSheet.objects.filter(digest=digest).first()
    if already is not None:
        messages.error(
            request,
            f"هذا الملفّ مرفوعٌ من قبل في {already.uploaded_at:%Y-%m-%d} "
            f"({already.rows_posted} صفّاً) — لم يُقيَّد شيء.",
        )
        return redirect("console:partner-payments-approve")

    try:
        sheet = Sheet.read(data)
        good, skipped = read_rows(sheet)
    except SheetError as bad:
        messages.error(request, str(bad))
        return redirect("console:partner-payments-approve")

    posted, more_skipped, total = _post_rows(good, digest, request.user)
    skipped += more_skipped

    record = PaymentSheet.objects.create(
        digest=digest,
        filename=upload.name[:255],
        uploaded_by=request.user,
        rows_read=len(sheet.rows),
        rows_posted=len(posted),
        rows_skipped=len(skipped),
        total=total,
        # وإيصالُ الحوالة على صفّ الملفّ لا على كلّ دفعة: واحدٌ يُرفَق بكلّ
        # صفوفه، وهو ما يقوله سطرُ v1 تحت الخانة.
        receipt=receipt or "",
    )
    audit.record(
        action="console.partner_payments_upload",
        entity=record,
        actor=request.user,
        note=f"{len(posted)} قُيّد · {len(skipped)} تُخطّي · {total}",
    )

    if posted:
        messages.success(request, f"قُيّد {len(posted)} صفّاً بإجمالي {total}.")
    for row in skipped[:20]:
        messages.error(request, f"السطر {row['line']} ({row['key']}): {row['why']}")
    if len(skipped) > 20:
        messages.error(request, f"وتُخطّي {len(skipped) - 20} صفّاً آخر.")

    return redirect("console:partner-payments-approve")


def _post_rows(rows: list[dict], digest: str, by) -> tuple[list, list[dict], Decimal]:
    """قيّد ما يمكن تقييده، واذكر ما لا يمكن ولماذا.

    كلُّ صفٍّ في معاملته: صفٌّ يفشل لا يُسقط ما قبله. وv1 يقول «الصفوف تُضاف
    إلى المعتمد سابقاً ولا تحلّ محلّه» — وهو الشيء نفسه، غير أن الفشل هنا
    يُسمّى.
    """
    posted: list = []
    skipped: list[dict] = []
    total = ZERO

    for row in rows:
        vehicle = _vehicle_for(row["key"])
        if vehicle is None:
            skipped.append({**row, "why": "لا مركبةً مرساةً واحدةً بهذا المفتاح"})
            continue

        invoice = (
            Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
        )
        if invoice is None:
            skipped.append({**row, "why": "المركبة رست ولم تُفوتَر بعد"})
            continue

        # المرجع يحمل بصمة الملفّ وسطرَه: فصفٌّ في ملفَّين مختلفين يُقيَّد
        # مرّةً بمفتاح `record_payment` نفسه، وسطران في ملفٍّ واحدٍ يُقيَّدان
        # مرّتين — وهما دفعتان فعلاً.
        reference = f"sheet:{digest[:12]}:{row['line']}"
        try:
            with transaction.atomic():
                # `settlement.record_vehicle_payment` لا `money.record_payment`:
                # الدفعةُ نفسُها، ومعها نقلُ المركبة إلى «مسدَّدة» فتدخل طابورَ
                # الخروج. الدالّتان تُقيّدان الدفترَ بالمفتاح نفسِه، والفرقُ أن
                # هذه تُلحق المركبةَ بفاتورتها في المعاملة ذاتها — وبدونها
                # سُدِّد ملفُّ شريكٍ كاملاً وبقيت كلُّ سيّارةٍ فيه `invoiced`.
                txn = settlement.record_vehicle_payment(
                    invoice=invoice,
                    amount=row["amount"],
                    source=InvoicePaymentSource.CASH,
                    reference=reference,
                    by=by,
                )
        except Exception as refusal:
            skipped.append({**row, "why": str(refusal)})
            continue

        posted.append(txn)
        total += row["amount"]

    return posted, skipped, total
