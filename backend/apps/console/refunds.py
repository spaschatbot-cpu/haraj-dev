"""طابور عجز الاسترداد — الشاشة التي لم تكن. T826.

`HR-09` بنى `odoo.RefundShortfall`: أودو يطلب سحب وديعةٍ مرهونة، فيُفتح صفٌّ
يقول كم طُلب وكم كان متاحاً وكم العجز، ولا يُنفَّذ شيء آلياً. ومُسجَّلٌ في
`tasks.md` أن **«لا شاشة للطابور بعد»** — أي أن الصفّ يُكتب ولا يبلغه موظّف،
والعميل يسأل «أين استردادي؟» وجوابه مكتوبٌ عندنا في جدولٍ لا باب له.

**والقراءة والإغلاق صلاحيتان لا واحدة.** المستودع يقسم المال ثلاثاً — قراءةُ
الدفتر، والفعل فيه، ومنحُ استثناء — لأن v1 جمعها في علمٍ واحد «فمن يقرأ رصيداً
كان يستطيع مصادرته». والقراءة هنا تشخيصٌ يحتاجه الدعم ليجيب العميل؛ والإغلاق
قرارٌ يقول «لا استرداد» أو «صُرف بطريقةٍ أخرى»، وهو من ثقة `money.act`.

**ولا يُصلَح شيءٌ آلياً هنا،** لنفس سبب `BalanceCheck`: حسابُ المنصّة لا يقرّر
هل سُلّمت السيارة. يقرّر إنسانٌ، ويقول كيف.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core import audit
from apps.odoo.models import RefundShortfall

from .views import console_page

#: كم صفّاً يُعرض. الطابور معناه أن يكون قصيراً؛ وصفحةٌ منه علامةُ عطلٍ لا
#: علامةُ حاجةٍ إلى ترقيم صفحات.
LIMIT = 200


@console_page("console:refund-queue")
def refund_queue(request):
    """ما ينتظر قراراً، أطولُه انتظاراً أوّلاً.

    الترتيب بالانتظار لا بالمعرّف: السؤال الذي تجيبه هذه الصفحة هو «من ينتظر
    استرداده منذ متى»، والمعرّف لا يقول شيئاً عن ذلك. نظير ترتيب
    `partner-decisions` بالسبب نفسه.
    """
    open_cases = (
        RefundShortfall.objects.filter(resolved_at__isnull=True)
        .select_related("user", "message")
        .order_by("opened_at")[:LIMIT]
    )
    closed = (
        RefundShortfall.objects.filter(resolved_at__isnull=False)
        .select_related("user", "resolved_by")
        .order_by("-resolved_at")[:20]
    )
    return render(
        request,
        "console/refund_queue.html",
        {"cases": open_cases, "closed": closed},
    )


@console_page("console:refund-resolve")
def refund_resolve(request, pk: int):
    """أغلق قضيةً بقرارٍ مكتوب. الكتابة الوحيدة على هذه الشاشة."""
    case = get_object_or_404(RefundShortfall.objects.select_related("user"), pk=pk)

    if request.method != "POST":
        return redirect("console:refund-queue")

    resolution = (request.POST.get("resolution") or "").strip()
    if not resolution:
        # القيد `a_closed_shortfall_names_its_decision` يمنع الفارغ في القاعدة،
        # لكن بلوغه من شاشةٍ صفحةُ خطأ لا جملةٌ بجانب الخانة. ومسافاتٌ بيضاء
        # تمرّ من `CHECK` وليست قراراً.
        messages.error(request, "قرار الإغلاق مطلوب.")
        return redirect("console:refund-queue")

    if case.resolved_at is not None:
        # إغلاقٌ ثانٍ يمحو اسم من أغلق أولاً وقراره — وهو ما يُسأل عنه لاحقاً.
        # والرفض هنا لا في القاعدة: لا قيدَ يمنعه، ولأن صفحتين مفتوحتين على
        # الطابور حالةٌ عاديّة لا نادرة.
        messages.error(request, "هذه القضية مُغلقة، ولها قرارٌ واسم من أغلقها.")
        return redirect("console:refund-queue")

    before = audit.snapshot(case, ["resolved_at", "resolution", "shortfall"])

    case.resolved_at = timezone.now()
    case.resolution = resolution
    case.resolved_by = request.user
    case.save(update_fields=["resolved_at", "resolution", "resolved_by"])

    audit.record(
        action="console.resolve_refund_shortfall",
        entity=case,
        actor=request.user,
        before=before,
        after=audit.snapshot(case, ["resolved_at", "resolution", "shortfall"]),
        note=resolution,
    )
    messages.success(request, "أُغلقت القضية.")
    return redirect("console:refund-queue")
