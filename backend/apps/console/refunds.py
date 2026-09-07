"""الاستردادات، ومزايدات حسب المزاد. T830-ل.

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

و`console:auction-bids` مبنيّةٌ منذ T826 وتعرض مزايدات مزادٍ بعينه بحالة كلٍّ
منها. فما ينقص مدخلُها: قائمةٌ تُختار منها. وهذا ما هنا.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from apps.auctions.models import Auction
from apps.bidding.models import Bid
from apps.money.models import RefundRequest, RefundRequestState

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

    و`console:auction-bids` هي التي تعرضها، وهي مبنيّةٌ منذ T826 بحالة كل
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
