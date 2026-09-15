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

import datetime as dt
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import display_name
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import UNPAID_INVOICE_STATES, Hold, HoldState, Invoice

from . import sensitive
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
        .filter(search_q(text, "full_name", "phone"))
        .order_by("full_name", "id")[:FOUND]
    )


def _amount(raw: str) -> Decimal | None:
    """المبلغ كما كُتب، أو `None` لما ليس مبلغاً — بلا استثناءٍ يصعد."""
    try:
        value = Decimal((raw or "").strip())
    except (InvalidOperation, ValueError):
        return None
    return value if value > ZERO else None


def _a_date(raw: str):
    """تاريخُ التحويل كما كُتب، أو `None` — ولا استثناءَ يصعد.

    و`None` لا تُسقِط الاعتماد: التاريخُ سندُ مطابقةٍ لا شرطَ قيد، وردُّ
    استمارةٍ كاملةٍ لأن الموظّف لم يقرأ تاريخاً في الكشف يجعله يكتب تاريخاً
    مخترَعاً — وحقلٌ مخترَعٌ أسوأ من حقلٍ فارغ.
    """
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        return None


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


@console_page("console:bank-topups")
def bank_topups(request):
    """طابورُ الشحن البنكيّ: يُطابَق بكشف الحساب، ثم يُعتمد **بما وصل**. T919.

    وهي «إدارة الطلبات» التي في قائمة v1 — لا شاشةٌ ثانية. القياسُ من دَمب
    الإنتاج: ٢٣٢ صفّاً في `transfer_requests`، **كلُّها** `wallet_topup`
    بـ`payment_method='bank'`، وصفرُ طلبِ نقلِ ملكيّة رغم أن اسمَ الجدول
    والافتراضيَّ فيه يقولان `ownership_transfer`. فالاسمُ هناك يَعِد بخمسة
    أقسامٍ ويعمل واحدٌ منها، والقسمُ العامل هو هذا.

    والمراجعةُ فعلٌ ماليّ، والصفحةُ عرضٌ — فالقدرتان مختلفتان
    ========================================================
    الصفحةُ خلف `money.view` (`navigation.py`)، و«اعتماد/رفض» خلف
    `money.act`. ولا تكفي واحدةٌ للاثنين: من يقرأ الطابور ليعرف أين وصل طلبُ
    عميلٍ ليس بالضرورة من يقيّد في الدفتر، وقدرةٌ واحدةٌ تجعل كلَّ قارئٍ كاتباً.

    ولا يُكتب رصيدٌ هنا: :mod:`apps.money.services` كاتبُ الأرصدة الوحيد، وهذه
    الشاشة تجمع ما كُتب في الاستمارة وتُسلّمه لها.
    """
    if request.method == "POST":
        return _review_topup(request)
    return _queue(request)


def _queue(request, *, revealed=None):
    """الطابورُ مرسوماً — ومنه يُخرَج بعد `POST` أيضاً حين لا يُعاد التوجيه."""
    from django.core.paginator import Paginator

    from apps.money.models import BankTopupRequest, BankTopupState

    state = (request.GET.get("state") or "").strip()
    seen = sensitive.shown_to(request.user)
    # و`resulting_transaction` في نفس الاستعلام: «أين وقع المال؟» يُسأل لكلّ
    # صفٍّ معتمَد، وخمسون صفّاً بلا هذا خمسون رحلةً إلى القاعدة.
    rows = BankTopupRequest.objects.select_related(
        "user", "resulting_transaction"
    ).order_by("-created_at", "-id")
    if state:
        rows = rows.filter(state=state)

    counts = [
        {
            "value": s.value,
            "label": s.label,
            "n": rows.model.objects.filter(state=s.value).count(),
        }
        for s in BankTopupState
    ]
    open_count = BankTopupRequest.objects.filter(
        state__in=BankTopupState.open_states()
    ).count()

    page = Paginator(rows, 50).get_page(request.GET.get("page"))
    _dress(page.object_list, seen, revealed=revealed)
    return render(
        request,
        "console/bank_topups.html",
        {
            "page": page,
            "counts": counts,
            "open_count": open_count,
            "state": state,
            "seen": seen,
            "may_act": can(request.user, Capability.MONEY_ACT),
            "today": timezone.localdate(),
        },
    )


def _dress(rows, seen: sensitive.Shown, *, revealed=None) -> None:
    """امحُ من الصفوف ما لا يحقُّ لقارئها — قبل أن تصل القالبَ.

    واسمُ العميل وجوّالُه كانا يُقرآن من `row.user` في القالب مباشرةً بلا
    شرط، والصفحةُ خلف `money.view` وحدها — فدورٌ بـ`money.view` بلا
    `users.view` كان يأخذ اسمَ كلِّ من شحن وجوّالَه من هذه الشاشة. وهو نظيرُ
    ما أُصلح في الكتالوج حرفياً (`sensitive.py`).
    """
    from apps.money.models import TransactionKind

    sensitive.person_on(rows, seen, field="user")
    sensitive.bank_match_on(rows, seen, revealed=revealed)
    for row in rows:
        # **أين وقع المال**، صفّاً صفّاً. وعنوانُ الحالة لا يقوله: «اعتُمد
        # وقُيِّد» صادقةٌ في الحالتين، والفرقُ بينهما هو ما يسأل عنه العميل
        # حين لا يرى رصيدَه ارتفع. ومبلغٌ ليس مضاعفاً للوديعة يجلس في
        # «المعلّق» (HR-03) — محفوظاً ومعدوداً، لا ضائعاً.
        txn = row.resulting_transaction
        row.landed = (
            ""
            if txn is None
            else (
                "أُضيف لتأمينه"
                if txn.kind == TransactionKind.INSURANCE_TOPUP
                else "في المعلّق — لم يصل رصيدَه"
            )
        )


def _review_topup(request):
    """«اعتماد» أو «رفض» أو «اكشف الآيبان» — والثلاثة أفعالٌ تُقيَّد."""
    from apps.money.models import BankTopupRequest

    action = (request.POST.get("action") or "").strip()
    topup = BankTopupRequest.objects.filter(pk=request.POST.get("topup")).first()
    back = f"{request.path}?state={request.POST.get('state', '')}"

    if topup is None:
        messages.error(request, "لم يُختَر طلب.")
        return redirect(back)

    if action == "reveal":
        return _reveal_iban(request, topup)

    if not can(request.user, Capability.MONEY_ACT):
        # الصفحةُ مفتوحةٌ بـ`money.view`، والفعلُ خلف `money.act` — والحارسُ
        # هنا لا في القالب: زرٌّ مخفيٌّ ليس حارساً، و`POST` يُصنَع بيد.
        raise PermissionDenied("money.act غير مسموحة لهذا المستخدم")

    note = (request.POST.get("note") or "").strip()

    if action == "reject":
        try:
            money.reject_bank_topup(topup=topup, by=request.user, note=note)
        except Exception as refusal:
            messages.error(request, str(refusal))
            return redirect(back)
        messages.success(request, f"رُفض الطلب {topup.reference} — والسبب مكتوب.")
        return redirect(back)

    if action != "approve":
        messages.error(request, "فعلٌ غير معروف.")
        return redirect(back)

    amount = _amount(request.POST.get("approved", ""))
    if amount is None:
        messages.error(request, "المبلغ المعتمَد يجب أن يكون رقماً موجباً.")
        return redirect(back)

    try:
        topup, txn = money.approve_bank_topup(
            topup=topup,
            by=request.user,
            amount=amount,
            sender_name=request.POST.get("sender", ""),
            transfer_date=_a_date(request.POST.get("transfer_date", "")),
            iban=request.POST.get("iban", ""),
            note=note,
        )
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect(back)

    # وأين وقع المالُ يُقال، لا «تم بنجاح»: مبلغٌ ليس مضاعفاً للوديعة يجلس في
    # «المعلّق» ولا يصير تأميناً (HR-03)، والموظّفُ الذي يقرأ «اعتُمد» وحدها
    # يظنّ أن رصيد العميل ارتفع — وهو لم يرتفع.
    landed = (
        "وأُضيف إلى تأمين العميل"
        if txn.kind == "insurance_topup"
        else (
            "وجلس في «المعلّق» — ليس مضاعفاً للوديعة، فلا يصير تأميناً "
            "حتى يُكمل العميل الفرق"
        )
    )
    messages.success(
        request,
        f"اعتُمد {amount} من أصل {topup.amount} مُدَّعىً (حركة {txn.pk}) {landed}.",
    )
    return redirect(back)


def _reveal_iban(request, topup):
    """اكشف آيبانَ صفٍّ واحد — بقيدٍ في `AuditLog`، ثمّ ارسم الصفحة.

    ولا إعادةَ توجيه بعده: الوجهةُ كانت ستحمل المفتاحَ في الرابط، فيصير
    الكشفُ قابلاً للنسخ والمشاركة — وهو ما يُفرغ القيدَ من معناه. والاستمارةُ
    في القالب ترسل إلى `?{{ request.GET.urlencode }}`، فتبقى التصفيةُ والصفحةُ
    كما كانتا بعد الكشف.
    """
    if not can(request.user, sensitive.CUSTOMER):
        raise PermissionDenied("users.view غير مسموحة لهذا المستخدم")
    audit.record(
        action="console.bank_topup_iban_revealed",
        entity=topup,
        actor=request.user,
        note=f"آيبان طلب {topup.reference} — العميل {topup.user_id}",
    )
    return _queue(request, revealed=topup.pk)
