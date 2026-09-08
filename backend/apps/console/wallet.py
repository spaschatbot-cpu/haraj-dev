"""شحن يدوي، والخصم المباشر. T830ط.

شاشتان من قسم «المحفظة» في v1، وهما **الشاشتان اللتان يقيس أثرَهما v1 على
نفسه**: «صحّة المحفظة» هناك تعرض تسعين بلاغ «إلغاء بلا سبب» وبلاغَي «خصم زائد»
بـ٩٬٩٩١ ريالاً، أحدهما «خرج 29,990 مقابل مدفوع 20,000».

فما يلي ليس تشدّداً — هو ما ينتج تلك البلاغات إن غاب.

الشحن اليدوي
============
شاشة v1: قائمةٌ منسدلة بالعملاء، وتحتها سطرٌ يقول «تظهر فقط السجلات المكتملة:
اسم واضح + رقم جوال صحيح، **مع إخفاء السجلات التجريبية أو غير المكتملة**».

وذلك السطر اعترافٌ: القاعدة فيها صفوفٌ لا اسمَ لها ولا جوّال، والحلُّ هناك
إخفاؤها من قائمةٍ واحدة. وهنا لا تُخفى — **يُبحَث**: قائمةٌ منسدلة بأربعةٍ
وأربعين ألف عميلٍ ليست قائمة، والبحثُ بالجوال يجد الصفَّ الناقص أيضاً فيُصلَح
بدل أن يختفي.

**وثلاثة أشياء يشترطها هذا الشحن ولا يشترطها v1:**

١. **مرجعٌ للحوالة** — وهو مفتاح التفرُّد (`deposit_key`). فالضغط مرّتين على
   الزرّ يقيّد مرّةً، وإعادةُ إدخال الحوالة نفسها غداً تُرفض. وv1 يقيّد مرّتين.
٢. **سببٌ مكتوب** يدخل مذكّرة القيد و`AuditLog`. «من شحن ولماذا» سؤالٌ يُسأل
   بعد شهر، ولا يُجاب بمبلغٍ وتاريخ.
٣. **مبلغٌ موجب** — والقاعدة ترفض غيره أصلاً، لكن الرسالة هنا تصل بجوار
   الخانة لا في صفحة خطأ.

الخصم المباشر — ولماذا لا خانةَ مبلغٍ حرّة
==========================================
شاشة v1: صفُّ نتائج بحثٍ، وفيه خانةُ مبلغٍ وزرُّ «خصم الآن». بلا سببٍ، وبلا
تأكيد، وبلا سقفٍ إلا الرصيد. وأثرُها مقيسٌ في شاشتها المجاورة.

**والمشكلة ليست في غياب التأكيد — هي في أن «اخصم مبلغاً» ليس فعلاً محاسبياً.**
المال لا «يُخصَم»؛ هو ينتقل من حسابٍ إلى حساب، والسؤال هو **إلى أين**:

* إلى **إيرادات المنصّة** لأن العميل أخلَّ ← تلك **مصادرة**، ولها
  `money.services.confiscate` بسببٍ إلزاميّ ومنفّذٍ مسمّى وقيدٍ في `AuditLog`،
  وتقع على **حجزٍ بعينه** لا على رصيدٍ عائم.
* إلى **سداد فاتورة** ← تلك `pay_invoice_from_balance`، وتصرف قفل الفاتورة
  أولاً ثم المتاح، فلا تأخذ أكثر من المستحقّ.
* إلى **العميل نفسه** ← ذلك استردادٌ، وله `refund_insurance`.

فهذه الشاشة تعرض الثلاثة **مسمّاةً بمقاديرها**، ولا تعرض خانةً حرّة. وخانةُ
المبلغ الحرّة هي بعينها ما يُنتج «خرج 29,990 مقابل مدفوع 20,000»: رقمٌ يُكتب
بيد، ولا شيء يقابله بشيء.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.accounts.services import display_name
from apps.core import audit
from apps.money import services as money
from apps.money.models import UNPAID_INVOICE_STATES, Hold, HoldState, Invoice

from .views import console_page

ZERO = Decimal("0.00")

#: كم عميلاً يُعرض من البحث. البحث يضيّق، والقائمة الطويلة تعني أن الكاتب لم
#: يضيّق بعد — فيُطلب منه لا يُعرض له مئتان.
FOUND = 20


def people(text: str = ""):
    """عملاءُ يطابقون ما كُتب — أو لا شيء قبل أن يُكتب.

    ولا يُخفى الصفُّ الناقص: v1 يخفي «السجلات التجريبية أو غير المكتملة» من
    قائمته، فيبقى الصفُّ في القاعدة ولا يراه أحد. والبحثُ بالجوال يجده،
    وظهورُه هو ما يجعله يُصلَح.
    """
    text = (text or "").strip()
    if not text:
        return None
    return (
        User.objects.filter(is_staff=False)
        .filter(Q(full_name__icontains=text) | Q(phone__icontains=text))
        .order_by("full_name", "id")[:FOUND]
    )


def _amount(raw: str) -> Decimal | None:
    """المبلغ كما كُتب، أو `None` لما ليس مبلغاً — بلا استثناءٍ يصعد."""
    try:
        value = Decimal((raw or "").strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value > ZERO else None


@console_page("console:wallet-credit")
def wallet_credit(request):
    """شحن يدوي: ابحث عن العميل، ثم اشحن بمرجعٍ وسبب."""
    if request.method == "POST":
        return _do_credit(request)

    text = request.GET.get("q", "")
    found = people(text)
    rows = []
    for person in found or []:
        rows.append({"person": person, "wallet": money.wallet_snapshot(person)})

    return render(
        request,
        "console/wallet_credit.html",
        {"q": text, "rows": rows, "searched": found is not None},
    )


def _do_credit(request):
    """القيد نفسه — يمرّ بـ`money.services` وحدها."""
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
    if not reference:
        # المرجع ليس تزييناً: هو مفتاح التفرُّد، وبدونه يقيّد الضغطُ مرّتين
        # مرّتين — وهو ما يفعله v1.
        messages.error(request, "مرجع الحوالة مطلوب — وهو ما يمنع التقييد مرّتين.")
        return redirect(back)

    already = money.find_transaction(money.deposit_key("cash", reference))
    if already is not None:
        messages.error(
            request,
            f"هذا المرجع مقيَّدٌ من قبل (حركة {already.pk}) — لم يُشحن شيء.",
        )
        return redirect(back)

    try:
        txn = money.deposit_insurance(
            user=person,
            amount=amount,
            source="cash",
            reference=reference,
            memo=reason,
        )
    except Exception as refusal:
        # جملةُ الخدمة نفسها: هي تفرّق بين «مصدر غير معروف» و«مبلغ غير صالح»،
        # وإعادةُ صياغتها هنا تُضيّع ذلك الفرق.
        messages.error(request, str(refusal))
        return redirect(back)

    audit.record(
        action="console.wallet_credit",
        entity=person,
        actor=request.user,
        note=f"{amount} — {reason} — مرجع {reference} — حركة {txn.pk}",
    )
    messages.success(request, f"شُحن {amount} لـ{display_name(person)} (حركة {txn.pk}).")
    return redirect(back)


@console_page("console:direct-deduct")
def direct_deduct(request):
    """الخصم المباشر: ما يمكن أن يخرج من رصيد العميل، **مسمّىً بمقداره**.

    ولا خانةَ مبلغٍ حرّة — انظر رأس الملف. الثلاثةُ المعروضة هنا هي كلُّ
    الطرق التي يخرج بها مالٌ من رصيد عميلٍ في هذا النظام، ولكلٍّ منها خدمتُها
    وقيدُها.
    """
    text = request.GET.get("q", "")
    found = people(text)

    rows = []
    for person in found or []:
        holds = (
            Hold.objects.filter(owner=person, state=HoldState.ACTIVE)
            .select_related("auction", "invoice")
            .order_by("-created_at")
        )
        dues = Invoice.objects.filter(
            customer=person, state__in=list(UNPAID_INVOICE_STATES)
        ).order_by("issued_at")
        rows.append(
            {
                "person": person,
                "name": display_name(person),
                "wallet": money.wallet_snapshot(person),
                "holds": holds,
                "dues": dues,
            }
        )

    return render(
        request,
        "console/direct_deduct.html",
        {"q": text, "rows": rows, "searched": found is not None},
    )
