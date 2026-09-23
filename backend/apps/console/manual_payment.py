"""إنشاء دفعة — قيدُ سدادٍ على فاتورةٍ بيد موظّف. T832.

**أخطرُ كتابةٍ في اللوحة كلِّها.** كلُّ ما عداها يُحرّك مالاً موجوداً: المصادرةُ
تأخذ من حجزٍ قائم، والشحنُ اليدويّ يقابله إيداعٌ في `external_cash`، والتصحيحُ
قيدٌ عاكسٌ لقيد. وهذه تقول للدفتر إن **مالاً وصل** — ولا بوّابةَ دفعٍ ولا كشفَ
بنكٍ ولا `verify_ledger` يستطيع أن يؤكّد ذلك. صدقُ الصفّ من صدق الموظّف وحده،
ولذلك كلُّ حارسٍ هنا يقابل شيئاً غائباً في v1.

ما تفعله v1، ولماذا لا يُنقل
=============================
`PaymentController::store` (`admin_v2/payments/store`):

* **حارسُها صلاحيةُ عرض.** الشرطُ هناك
  `hasPermission('payments_manage') || hasPermission('invoices_list') || hasRole('owner')`
  — أي أن **`invoices_list`، وهي صلاحيةُ رؤية الفواتير، تكفي لإنشاء دفعةٍ
  وقلبِ حالة فاتورة**. وهنا قدرةٌ خاصّة: `payments.record`، وليست تحت
  `money.act` (السببُ مكتوبٌ في `apps/core/permissions.py` عند تعريفها).
* **لا هويّةَ فاعل ولا تدقيق.** لا `admin_id` في الحمولة ولا في الجدولين، و
  `financialLog()` هو `error_log` إلى ملفّ PHP **وفي الفشل وحده** — النجاحُ لا
  يُسجَّل أبداً. فلا يمكن معرفة أيُّ موظّفٍ قيّد أيَّ دفعة. وهنا: `AuditLog`
  بالفاعل والمبلغ والسبب، **والسببُ إجباريّ**.
* **لا سبب أصلاً.** حقلُ `memo` هناك `readonly` ويُولَّد آلياً من الفاتورة،
  فلا تُفرَّق بعد شهرٍ دفعةٌ حقيقيّةٌ من تصحيحِ خطأ.
* **لا مفتاحَ تفرّدٍ حقيقيّ.** `payments_odoo` بلا `UNIQUE`، والحمايةُ قفلُ
  `GET_LOCK` لحظيٌّ وقاعدةُ «المجموع ≤ قيمة الفاتورة» — فدفعتان جزئيّتان
  متطابقتان تمرّان. وهنا المرجعُ هو المفتاح: `payment:{invoice}:{reference}`
  في `money.services.record_payment`، والقيدُ في القاعدة.
* **`float` على مسار مال**، بهامشٍ يدويّ `+ 0.0001` في المقارنة، وخانةُ إدخالٍ
  `type="text"` بلا تحقّق. وهنا `Decimal` في كلّ خطوة (المادة ٣-٢).
* **نداءُ أودو داخل المعاملة**: إن أنشأت أودو الدفعةَ ثمّ فشل الـ`commit`
  بقيت دفعةٌ عندهم بلا قيدٍ عندنا. وهنا لا نداءَ شبكيّ إطلاقاً — يُكتب في
  صندوق الصادر (`apps.odoo.outbox`) والإرسالُ شأنٌ آخر.

أين يقع البابُ — وهو القرار
============================
`apps.money.services` هو كاتبُ الأرصدة الوحيد، ولا يُكتب رصيدٌ حوله. لكنّ
`money.record_payment` ليست البابَ الصحيح لهذه الشاشة: **كلُّ فاتورةٍ في هذا
النظام فاتورةُ فوزٍ بمركبة**، وحالةُ المركبة تتبع حالةَ فاتورتها. ولذلك وُصلت
مساراتُ الدفع كلُّها أمس ببابٍ واحد —
:func:`apps.bidding.settlement.record_vehicle_payment` — وهو غلافٌ رقيقٌ يقيّد
الدفعةَ **ثمّ يُلحق المركبةَ بها في المعاملة نفسها**. فالبابُ هنا هو ذاك، ولم
يُمسّ في `settlement.py` سطرٌ واحد.

وأودو
=====
`record_payment` **لا** تُخبر أودو، وتعليقُها يقول لماذا: مناديها الوحيد حتى
اليوم هو معالجُ الويبهوك — أي أن الدفعةَ جاءت **منهم**، وإعادتُها إليهم صدى
HR-10. وهذه الشاشةُ هي الاستثناء: دفعةٌ وُلدت **عندنا** ولا طريقَ لأودو أن
تعرفها. فتُدرَج هنا لا هناك، حتى لا ينقلب شرطُ الصدى على كلّ دفعةٍ واردة.
و«الإدراجُ ليس إرسالاً»: `ODOO_ENABLED` مطفأةٌ في كلّ بيئةٍ افتراضياً.

والحجب (`sensitive.py`)
=======================
`payments.record` لا تحمل معها `users.view` ولا `money.view`. فما هو **موضوع
الشاشة** يُعرَض — رقمُ الفاتورة ومبلغُها وباقيها، وهو ما يُقيَّد عليه — وما
يظهر **عَرَضاً** يمرّ بالحارس: جوّالُ العميل خلف `Shown.customer`، وأرصدةُ
تأمينه خلف `Shown.wallet`. والمحوُ في الخادم قبل القالب، لا في CSS.
"""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.accounts.services import display_name, find_by_phone
from apps.bidding import settlement
from apps.core import audit
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import UNPAID_INVOICE_STATES, Invoice, InvoicePaymentSource

from . import sensitive
from .views import console_page

log = logging.getLogger(__name__)

ZERO = Decimal("0.00")

#: كم فاتورةً تُعرَض من البحث. الشاشةُ تُفتح على فاتورةٍ بعينها في يد الموظّف
#: (إيصالٌ أو حوالة)، لا لتصفَّح — وقائمةٌ طويلة هنا تعني أن الكاتب لم يضيّق.
FOUND = 15


def find_invoices(text: str):
    """الفواتيرُ **غيرُ المسدَّدة** التي تطابق ما كُتب — أو لا شيء قبل الكتابة.

    وغيرُ المسدَّدة وحدها: `record_payment` ترفض الزائدَ على المستحقّ أصلاً،
    فعرضُ فاتورةٍ مسدَّدةٍ بزرِّ «قيّد» هو زرٌّ جوابُه رفضٌ دائماً — وذاك يُعلّم
    قارئَه أن اللوحة معطوبة.

    وخمسةُ مداخل لأنها ما تصل به الورقةُ إلى المكتب: رقمُ الفاتورة من الإيصال،
    واسمُ العميل، ولوحةُ المركبة أو رقمُ هيكلها، وجوّالُه حين لا يحمل ورقة.
    """
    text = (text or "").strip()
    if not text:
        return None

    matches = search_q(
        text,
        "number",
        "customer__full_name",
        "vehicle__plate_number",
        "vehicle__vin",
    )
    person = find_by_phone(text)
    if person is not None:
        matches |= Q(customer=person)

    return (
        Invoice.objects.filter(state__in=list(UNPAID_INVOICE_STATES))
        .filter(matches)
        .select_related("customer", "vehicle")
        .order_by("-issued_at")[:FOUND]
    )


def _amount(raw: str) -> Decimal | None:
    """المبلغ كما كُتب، أو `None` لما ليس مبلغاً موجباً.

    `Decimal` من السلسلة مباشرةً ولا `float` في الطريق — المادة ٣-٢. وv1 يقرأ
    `(float) $_POST['amount']` ثمّ يقارن بهامشٍ يدويّ `+ 0.0001`، وذلك الهامشُ
    نفسُه اعترافٌ بأن المقارنة صارت تقريبيّة على مسار مال.
    """
    try:
        value = Decimal((raw or "").strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value > ZERO else None


@console_page("console:payment-create")
def payment_create(request):
    """ابحث عن فاتورةٍ غير مسدَّدة، ثمّ قيّد عليها دفعةً بمرجعٍ وسبب."""
    if request.method == "POST":
        return record_payment(request)

    text = request.GET.get("q", "")
    found = find_invoices(text)
    seen = sensitive.shown_to(request.user)

    rows = []
    for invoice in found or []:
        rows.append(
            {
                "invoice": invoice,
                "name": display_name(invoice.customer),
                # الجوّالُ عَرَضٌ على هذه الشاشة لا موضوعُها — فيمرّ بالحارس.
                "phone": invoice.customer.phone if seen.customer else "",
                # وأرصدةُ التأمين كذلك، خلف `money.view`. **ولا تجيب «أله رصيدٌ
                # يكفي بدل النقد؟»** — كان ذلك سببَ عرضها، وأسقطه قرارُ المالك
                # (T954: التأمينُ لا يسدّد فاتورة). تُعرض لتقول ما المقفولُ على
                # هذه الفاتورة وما يعود متاحاً بعد سدادها.
                #
                # **قاموسٌ بأسماء الدلاء** من `wallet_snapshot().buckets`. كان
                # القالبُ يقرأ `wallet.insurance_free.balance` — شكلٌ قديمٌ للّقطة
                # لم يعد موجوداً، فكانت الخانتان تُرسمان **فارغتين** بلا خطأ.
                # قِيس على الخادم في ٢٤ سبتمبر ٢٠٢٦ على فاتورة V-12976-202609.
                "wallet": (
                    {
                        bucket.kind: bucket.amount
                        for bucket in money.wallet_snapshot(invoice.customer).buckets
                    }
                    if seen.wallet
                    else None
                ),
            }
        )

    return render(
        request,
        "console/payment_create.html",
        {
            "q": text,
            "rows": rows,
            "searched": found is not None,
            "seen": seen,
        },
    )


def record_payment(request):
    """القيدُ نفسه — يمرّ بالباب الواحد في `settlement` وحده.

    **عامّةٌ لأن لها بابين**: صفحةُ «إنشاء دفعة» (بقيت لمن يفتح رابطها)،
    ونافذةُ «إدارة المدفوعات» التي دُمجت فيها (T932). والمنطقُ واحدٌ في
    الموضعين — والرفضُ والتدقيقُ والمرجعُ المانع من القيد مرّتين معه.
    """
    back = f"{request.path}?q={request.POST.get('q', '')}"
    invoice = (
        Invoice.objects.select_related("customer", "vehicle")
        .filter(pk=request.POST.get("invoice"))
        .first()
    )
    amount = _amount(request.POST.get("amount", ""))
    reference = (request.POST.get("reference") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    if invoice is None:
        messages.error(request, "لم تُختَر فاتورة.")
        return redirect(back)
    if amount is None:
        messages.error(request, "المبلغ يجب أن يكون رقماً موجباً.")
        return redirect(back)
    if not reference:
        # المرجعُ هو مفتاح التفرُّد (`payment:{invoice}:{reference}`)، لا خانةً
        # للتوثيق. وبدونه تصير ضغطتان دفعتين — وهو ما يفعله v1 بالضبط.
        messages.error(
            request, "مرجع الإيصال أو الحوالة مطلوب — وهو ما يمنع القيد مرّتين."
        )
        return redirect(back)
    if not reason:
        messages.error(request, "سببُ القيد مطلوب — ويدخل سجلَّ التدقيق.")
        return redirect(back)

    already = money.find_transaction(f"payment:{invoice.pk}:{reference}")
    if already is not None:
        messages.error(
            request,
            f"هذا المرجع مقيَّدٌ على الفاتورة {invoice.number} من قبل "
            f"(حركة {already.pk}) — لم يُقيَّد شيء.",
        )
        return redirect(back)

    # اللقطةُ **قبل** النداء، لا بعده: `record_payment` تكتب على صفّها المقفول
    # و`refresh_from_db` تحت تجلب الجديد — فقراءةُ `state` بعدها كانت تكتب
    # الحالةَ الجديدة في خانة «قبل»، وقيدُ تدقيقٍ طرفاه متساويان لا يقول شيئاً.
    before = audit.snapshot(invoice, ["amount_paid", "state"])
    try:
        txn = settlement.record_vehicle_payment(
            invoice=invoice,
            amount=amount,
            source=InvoicePaymentSource.CASH,
            reference=reference,
            by=request.user,
        )
    except Exception as refusal:  # noqa: BLE001
        # جملةُ الخدمة نفسها: هي تفرّق بين «الفاتورة ملغاة» و«المبلغ أكبر من
        # المستحقّ» و«البطاقة لا تُسدّد بها سيارة»، وإعادةُ صياغتها هنا
        # تُضيّع ذلك الفرق.
        #
        # و`user_message` قبل `str`: `DomainError` يمرّر النصَّ الإنجليزيّ إلى
        # `Exception` حين يُعطى الاثنان، فيقرأ الموظّفُ سطرَ مطوِّرٍ لا جملةً.
        messages.error(request, getattr(refusal, "user_message", "") or str(refusal))
        return redirect(back)

    invoice.refresh_from_db()

    audit.record(
        action="console.record_payment",
        entity=invoice,
        actor=request.user,
        before=before,
        after=audit.snapshot(invoice, ["amount_paid", "state"]),
        note=(
            f"{amount} نقداً على الفاتورة {invoice.number} — {reason} — "
            f"مرجع {reference} — حركة {txn.pk}"
        ),
    )

    _tell_odoo(invoice, amount, txn)

    messages.success(
        request,
        f"قُيِّد {amount} على الفاتورة {invoice.number} (حركة {txn.pk}) — "
        f"الباقي {invoice.outstanding}.",
    )
    return redirect(back)


def _tell_odoo(invoice: Invoice, amount: Decimal, txn) -> None:
    """أدرِج الدفعةَ في صندوق صادر أودو — **كتابةٌ لا إرسال**.

    هي هنا لا في `money.record_payment` لأن تلك يناديها معالجُ الويبهوك: دفعةٌ
    جاءت من أودو تُعاد إليهم صدىً (HR-10). وهذه وُلدت في مكتبنا ولا طريقَ
    لأودو أن تعرفها، فهي الحالةُ الوحيدة التي يجب أن تُدرَج.

    وفاتورةٌ لا يعرفها أودو (`odoo_invoice_id` فارغ) لا تُدرَج: إخبارُهم بدفعةٍ
    على مستندٍ ليس عندهم هو الدَّينُ الوهميّ من الاتجاه الآخر.

    ويفشل بهدوء: صندوقُ الصادر ليس شرطاً لصحّة القيد، وقيدٌ صحيحٌ يُلغى لأن
    كتابةً في صندوقٍ تعثّرت هو أسوأُ من رسالةٍ ناقصةٍ تُعاد يدوياً.
    """
    if not invoice.odoo_invoice_id:
        return
    try:
        from apps.odoo import outbox

        outbox.queue_payment(invoice, amount, source_transaction=txn)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not queue odoo payment for %s: %s", invoice.number, exc)


__all__ = ["find_invoices", "payment_create"]
