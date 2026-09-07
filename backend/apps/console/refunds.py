"""الاستردادات، وطابور العجز، ومزايدات حسب المزاد. T826 · T830ل · T835.

شاشتان من قائمتين مختلفتين، وتجمعهما ملاحظةٌ واحدة: كلتاهما في v1 **تعرض
رقماً لا يطابق شاشةً أخرى تعرض الشيء نفسه**.

الاستردادات — ثلاثةُ أرقامٍ لشيءٍ واحد
======================================
في إنتاج v1:

* «لوحة التقارير» تقول **طلبات الاسترداد `3,342`**
* «إدارة الطلبات ← استرداد» تقول **`500`**
* «الاستردادات» نفسها تقول **`0`**

ولا واحدةٌ منها تقول أي مرشّحٍ تطبّق. فمن يسأل «كم طلبَ استردادٍ عندنا؟» يجد
ثلاثة أجوبةٍ ولا يعرف أيَّها يقول للمحاسب.

وهنا مصدرٌ واحد: :class:`~apps.money.models.RefundRequest`، وحالاتُه خمسٌ
مسمّاة. والشاشةُ تعرض **العددَ لكل حالة** بدل رقمٍ واحدٍ لا يُعرف ما يعدّه —
فالسؤال يصير «كم مُقدَّماً وكم نُفِّذ» وله جوابٌ واحد.

و«ما زال يكلّفنا» ليس تصنيفاً بل مجموعة: `RefundRequestState.open_states()`
تُسمّيها مرّةً، ويقرأها القيدُ في القاعدة وهذه الشاشة معاً.

مزايدات حسب المزاد
==================
في v1 مدخلان مختلفان (`owners_console` و`managepage`) يشيران إلى **المسار
نفسه** — أحدُ سبعة تكرارات في جدول الكروت (الشاشة ٣٧-ب). وهي شاشةُ اختيار:
اختر مزاداً لترى مزايداته.

و`console:auction-bids` مبنيّةٌ منذ T835 وتعرض مزايدات مزادٍ بعينه بحالة كلٍّ
منها. فما ينقص مدخلُها: قائمةٌ تُختار منها. وهذا ما هنا.


طابور العجز
===========
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

from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auctions.models import Auction
from apps.bidding.models import Bid
from apps.core import audit
from apps.money.models import RefundRequest, RefundRequestState
from apps.odoo.models import RefundShortfall

from .exports import export, wants_export
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50


def refund_rows(*, text: str = "", state: str = ""):
    """طلبات الاسترداد — مصدرٌ واحد، وحالاتٌ مسمّاة."""
    rows = RefundRequest.objects.select_related("user").order_by("-created_at", "-id")

    text = (text or "").strip()
    if text:
        rows = rows.filter(
            Q(user__full_name__icontains=text)
            | Q(user__phone__icontains=text)
            | Q(reference__icontains=text)
        )

    if (state or "").strip() in RefundRequestState.values:
        rows = rows.filter(state=state)
    return rows


def refund_counts() -> list[dict]:
    """العددُ لكل حالة — بدل رقمٍ واحدٍ لا يُعرف ما يعدّه.

    وv1 يعرض رقماً واحداً في ثلاث شاشات بثلاث قيم. والقائمة هنا تُبنى من
    `RefundRequestState` نفسها، فحالةٌ تُضاف تظهر ولا تُنسى.
    """
    counted = {
        row["state"]: row["n"]
        for row in RefundRequest.objects.values("state").annotate(n=Count("id"))
    }
    return [
        {
            "value": value,
            "label": RefundRequestState(value).label,
            "count": counted.get(value, 0),
            # «ما زال يكلّفنا» تُقرأ من `open_states` لا تُكتب ثانيةً: القيدُ
            # في القاعدة يقرأ المجموعة نفسها (المادة ٤-٥).
            "open": value in RefundRequestState.open_states(),
        }
        for value in RefundRequestState.values
    ]


@console_page("console:refunds")
def refunds(request):
    """الاستردادات: كم طلباً وفي أي حالة — ومصدرٌ واحد لكلّها."""
    text = request.GET.get("q", "")
    state = request.GET.get("state", "")
    rows = refund_rows(text=text, state=state)

    if wants_export(request):
        return export(
            rows,
            name="الاستردادات",
            headers=["المرجع", "العميل", "الجوال", "المبلغ", "الحالة", "قُدِّم"],
            cell=lambda row: [
                row.reference,
                row.user.full_name,
                row.user.phone,
                row.amount,
                row.get_state_display(),
                row.created_at,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    still_open = RefundRequest.objects.filter(state__in=RefundRequestState.open_states())

    return render(
        request,
        "console/refunds.html",
        {
            "page": page,
            "counts": refund_counts(),
            "open_count": still_open.count(),
            "open_value": still_open.aggregate(t=Sum("amount"))["t"] or ZERO,
            "q": text,
            "state": state,
        },
    )


def auctions_with_bids(text: str = ""):
    """المزادات ومعها عددُ مزايداتها ومزايديها — قائمةُ اختيار."""
    rows = Auction.objects.annotate(
        bids=Count("vehicles__bids", distinct=True),
        bidders=Count("vehicles__bids__bidder", distinct=True),
        cars=Count("vehicles", distinct=True),
    ).order_by("-starts_at", "-number")

    text = (text or "").strip()
    if text:
        matches = Q(title__icontains=text)
        if text.isdigit():
            matches |= Q(number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:auction-bids-index")
def auction_bids_index(request):
    """مزايدات حسب المزاد: اختر مزاداً لتفتح مزايداته.

    و`console:auction-bids` هي التي تعرضها، وهي مبنيّةٌ منذ T835 بحالة كل
    مزايدة — مسحوبةً ومستبدَلةً وقائمة. فما ينقص هو المدخل، وهو هذا.
    """
    rows = auctions_with_bids(request.GET.get("q", ""))
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    return render(
        request,
        "console/auction_bids_index.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "total": Bid.objects.count(),
        },
    )


# -------------------------------------------------------------------------
# طابور العجز — الرقم في اللوحة له باب. T826
# -------------------------------------------------------------------------

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
