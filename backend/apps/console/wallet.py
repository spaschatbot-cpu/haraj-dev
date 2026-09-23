"""إيداعٌ يدويّ في محفظة عميل — بمرجعٍ وسبب. T830ط، وأُعيد في ٢٤ سبتمبر ٢٠٢٦.

لماذا عاد
=========
أُلغي في ١٨ سبتمبر ٢٠٢٦ (`5093dcd`) بقرار المالك مع «طلبات الشحن البنكي» و
«الخصم المباشر»، وقِيس يومها أنه لم يُستعمل مرّةً على الإنتاج. وكُتب في
`navigation.py` ما يزول معه: **كان البابَ الوحيد في اللوحة لتقييد إيداعٍ نقديٍّ
أو بنكيّ بيد موظّف**.

ثم ظهر الثمن في اختبار المسار الكامل على `haraj.spas.sa`: عميلٌ لا يستطيع
المزايدةَ حتى يُودِع التأمين، وزرُّ الشحن بالبطاقة يمرّ ببوّابة دفع — فلم يبقَ
طريقٌ لإيداعٍ وصل نقداً أو بحوالة. فقال المالك: «رجّع الإيداع اليدوي».

وعاد **الإيداعُ وحده**. الخصمُ المباشر لم يعد: «اخصم مبلغاً» ليس فعلاً محاسبيّاً
(المصادرةُ والسدادُ والاستردادُ لكلٍّ بابُه)، والمصادرةُ باقيةٌ في «أفعال مالية».

ما تغيّر عن النسخة الأولى — وهو إصلاح
=====================================
كانت تقيّد بـ:func:`money.deposit_insurance`، وهي **مسجِّلٌ لا حَكَم**: لا تطبّق
قاعدةَ الوديعة الكاملة (HR-03)، وتعليقُها يقول ذلك صراحةً ويحيل إلى
:func:`money.credit_payment`. فكان موظّفٌ يستطيع إيداعَ ٤٬٨٥٠ ريالاً تأميناً —
وهي بعينها الوديعةُ الناقصة التي جعلت v1 يغطّي استردادَ عشرة آلافٍ بإيداعِ ريال.

والآن تمرّ بـ`credit_payment` (البابُ نفسه الذي يمرّ به اعتمادُ الشحن البنكيّ)،
**وتُرفض قبلها** المبالغُ التي ليست مضاعفاً للوديعة، بجملةٍ تسمّي الوديعة. لأن
`credit_payment` لا ترفضها بل **تركنها في المعلّق** — صوابٌ لحوالةٍ وصلت فعلاً
ولا تُردّ، وخطأٌ لموظّفٍ كتب رقماً في خانة: يضغط «أودِع» ويقرأ «تمّ» ولا يجد
العميلُ تأميناً.

وثلاثةٌ لا يشترطها v1
====================
١. **مرجعٌ** — هو مفتاحُ التفرّد (`deposit_key`). الضغطُ مرّتين يقيّد مرّة، و
   إعادةُ الحوالة نفسِها غداً تُرفض بجملة.
٢. **سببٌ** يدخل مذكّرةَ القيد و`AuditLog`: «من أودع ولماذا» يُسأل بعد شهر.
٣. **بحثٌ لا قائمة**: v1 قائمةٌ منسدلة «تُخفي السجلّات غيرَ المكتملة»، وهنا
   يُبحَث بالاسم أو الجوّال فيظهر الصفُّ الناقص ويُصلَح بدل أن يختفي.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.accounts.services import display_name
from apps.core import audit
from apps.core.arabic import search_q
from apps.money import services as money

from .views import console_page

ZERO = Decimal("0.00")

#: كم عميلاً يُعرض من البحث. البحثُ يضيّق، ومئتا صفٍّ تعني أن الكاتب لم يضيّق.
FOUND = 20


def people(text: str = ""):
    """عملاءُ يطابقون ما كُتب — أو `None` قبل أن يُكتب شيء."""
    text = (text or "").strip()
    if not text:
        return None
    return (
        User.objects.filter(is_staff=False)
        .filter(search_q(text, "full_name", "phone"))
        .order_by("full_name", "id")[:FOUND]
    )


def _amount(raw: str) -> Decimal | None:
    """المبلغُ كما كُتب، أو `None` لما ليس مبلغاً موجباً — بلا استثناءٍ يصعد."""
    try:
        value = Decimal((raw or "").strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value > ZERO else None


def _buckets(person) -> dict[str, Decimal]:
    """أرصدةُ العميل بأسماء الدلاء — من `wallet_snapshot` وحدها."""
    return {bucket.kind: bucket.amount for bucket in money.wallet_snapshot(person).buckets}


@console_page("console:wallet-credit")
def wallet_credit(request):
    """ابحث عن العميل، ثم أودِع بمرجعٍ وسبب."""
    if request.method == "POST":
        return _do_credit(request)

    text = request.GET.get("q", "")
    found = people(text)
    rows = [{"person": person, "buckets": _buckets(person)} for person in found or []]

    return render(
        request,
        "console/wallet_credit.html",
        {
            "q": text,
            "rows": rows,
            "searched": found is not None,
            "unit": money.deposit_amount_for(),
        },
    )


def _do_credit(request):
    """القيدُ نفسه — يمرّ بـ`money.credit_payment` وحدها."""
    person = User.objects.filter(pk=request.POST.get("customer"), is_staff=False).first()
    amount = _amount(request.POST.get("amount", ""))
    reference = (request.POST.get("reference") or "").strip()
    reason = (request.POST.get("reason") or "").strip()
    back = f"{request.path}?q={request.POST.get('q', '')}"

    if person is None:
        messages.error(request, "لم يُختَر عميل.")
        return redirect(back)
    if amount is None:
        messages.error(request, "المبلغ يجب أن يكون رقماً موجباً.")
        return redirect(back)
    if money.whole_deposits_in(amount) is None:
        unit = money.deposit_amount_for()
        messages.error(
            request,
            f"التأمينُ وديعةٌ كاملة: {unit} ريال أو مضاعفاتُها. "
            f"المبلغ {amount} لا يصير تأميناً — لم يُقيَّد شيء.",
        )
        return redirect(back)
    if not reference:
        messages.error(request, "مرجع الإيداع مطلوب — وهو ما يمنع التقييد مرّتين.")
        return redirect(back)

    already = money.find_transaction(money.deposit_key("cash", reference))
    if already is not None:
        messages.error(request, f"هذا المرجع مقيَّدٌ من قبل (حركة {already.pk}) — لم يُقيَّد شيء.")
        return redirect(back)

    memo = f"إيداع يدويّ — مرجع {reference}" + (f" — {reason}" if reason else "")
    try:
        txn = money.credit_payment(
            user=person,
            amount=amount,
            source="cash",
            reference=reference,
            memo=memo,
        )
    except Exception as refusal:  # noqa: BLE001
        # جملةُ الخدمة نفسها: تفرّق بين الأسباب، وإعادةُ صياغتها تُضيّع الفرق.
        messages.error(request, str(refusal))
        return redirect(back)

    audit.record(
        action="console.wallet_credit",
        entity=person,
        actor=request.user,
        note=f"{amount} — مرجع {reference} — حركة {txn.pk}" + (f" — {reason}" if reason else ""),
    )
    messages.success(request, f"أُودع {amount} تأميناً لـ{display_name(person)} (حركة {txn.pk}).")
    return redirect(back)
