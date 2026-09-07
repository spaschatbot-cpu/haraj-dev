"""اعتماد مدفوعات الشريك — ملفٌّ يُقيَّد في الدفتر، لا جدولٌ موازٍ. T830ي.

شاشة v1 المقابلة تكتب عطلَها على نفسها، بالحرف:

    «الشريك لا يرى أي حالة سداد من النظام المحاسبي — لا فواتير ولا مدفوعات
     ولا مستحقّات. صفحته تقرأ **هذا الجدول فقط**، ومصدره الوحيد هو ملفك.»

أي أن الملفّ المرفوع **جدولٌ ثانٍ للحقيقة**: «مسدَّدة» فيه لا تمسّ دفتراً ولا
فاتورةً ولا حساباً. فللسداد حقيقتان، ولا شيء يوفّق بينهما.

**وهنا الملفّ مصدرُ استيرادٍ لا مصدرُ حقيقة.** كلُّ صفٍّ يُقيَّد دفعةً على
فاتورة المركبة عبر `money.services.record_payment`، فيظهر في هذه الشاشة وفي
حساب العميل وفي صحّة المال وفي صفحات الشريك — **رقمٌ واحد**.

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

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core import audit
from apps.core.sheets import Sheet, SheetError
from apps.money import services as money
from apps.money.models import Invoice, InvoicePaymentSource, PaymentSheet

from .views import console_page

ZERO = Decimal("0.00")

#: ما يقبله الرفع. أكبرُ من ذلك خطأٌ — جدولُ الأسطول كلّه، أو صورةٌ أُعيدت
#: تسميتها — وقراءتُه في الذاكرة لاكتشاف ذلك هي كيف تسقط لوحة.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

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
    """اعتماد مدفوعات الشريك: ارفع الملفّ، فيُقيَّد كلُّ صفٍّ في الدفتر."""
    if request.method == "POST":
        return _upload(request)

    sheets = PaymentSheet.objects.select_related("uploaded_by")[:20]
    posted = Invoice.objects.filter(
        vehicle__owner_company__isnull=False, amount_paid__gt=ZERO
    )
    return render(
        request,
        "console/partner_payments_approve.html",
        {
            "sheets": sheets,
            "total": posted.aggregate(t=Sum("amount_paid"))["t"] or ZERO,
            "count": posted.count(),
        },
    )


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
                txn = money.record_payment(
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
