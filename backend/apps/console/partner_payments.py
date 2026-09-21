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
from django.db.models import Q, Sum
from django.shortcuts import redirect, render

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import VehicleState
from apps.bidding import settlement
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.sheets import Sheet, SheetError
from apps.money.models import Invoice, InvoicePaymentSource, PaymentSheet

from . import payments
from .icons import path_of
from .views import console_page

ZERO = Decimal("0.00")

#: ما يقبله الرفع. أكبرُ من ذلك خطأٌ — جدولُ الأسطول كلّه، أو صورةٌ أُعيدت
#: تسميتها — وقراءتُه في الذاكرة لاكتشاف ذلك هي كيف تسقط لوحة.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

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
        if request.POST.get("op") == "pay":
            return _pay_one(request)
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


def _decorate_cars(rows) -> None:
    """أضِف لكلّ مركبةٍ فاتورتَها وصورتَها وما بقي عليها — استعلامان للصفحة."""
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

    for car in rows:
        invoice = invoices.get(car.pk)
        car.invoice = invoice
        car.cover = covers.get(car.pk)
        car.paid_amount = invoice.amount_paid if invoice else ZERO
        car.due = invoice.outstanding if invoice else (car.awarded_price or ZERO)
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
    for row in rows:
        row.vehicle = cars.get(row.invoice.vehicle_id) if row.invoice else None
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


def _upload(request):
    """اقرأ الملفّ وقيّد صفوفه — أو ارفضه كلَّه."""
    upload = request.FILES.get("sheet")
    if upload is None:
        messages.error(request, "لم يُرفَع ملفّ.")
        return redirect("console:partner-payments-approve")
    if upload.size > MAX_UPLOAD_BYTES:
        messages.error(request, "الملفّ أكبر من خمسة ميجابايت.")
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
