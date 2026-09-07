"""أرشيف المزادات، ومزايدات مزادٍ بعينه. T835.

الشاشتان من لوحة v1 (`/auction-archive` و`/auctions/{id}/bids`)، وهما شاشتا
**قراءةٍ محضة**: لا زرَّ يكتب، ولا نقلةَ حالةٍ تُطلَق. النقلات كلها في
`auction_moves.py` وحده، وذلك مقصود — `ops/checks/auction_state_single_writer.py`
يرفض كتابة حالةٍ خارج `auctions.services`، وشاشةٌ تعرض التاريخ لا يجوز أن
تكون بابَ تغييرٍ فيه.

لماذا ملفٌّ ثالث لا إضافةٌ إلى `auctions.py`
=============================================
للسبب نفسه الذي أخرج `auction_moves.py`: `ops/checks/one_eligibility_gate.py`
يحرس كل وحدةٍ تستورد من `apps.bidding`، وشاشة المزايدات تستوردها بالضرورة.
إدخالُها في `auctions.py` كان سيُدخل ملفَّ القوائم كلَّه في نطاق الحارس، وهو
ما وقع مرّةً في T823. الملفُّ الذي يقرأ المزايدات غيرُ الملفِّ الذي يرسم
قوائم المزادات.

ما يختلف عن v1
==============
**الإجمالي مشتقٌّ لا مخزَّن.** v1 يقرأ «إجمالي المبيعات» من عمودٍ في `auctions`؛
هنا يُجمَع من أسعار المركبات المرساة في المزاد نفسه. جرد T302 وجد ثلاثة أعمدة
رصيدٍ مشتقّة في v1 وكلها تُهمَل — ورقمٌ مخزَّنٌ لا يعرف أحدٌ متى حُسب هو رقمٌ
لا يُبنى عليه (المادة ١-٦).

**والمزايدة المسحوبة والمستبدَلة تُعرَضان ويُقالان.** v1 يعرض الصفَّ الأخير
وحده، فيسأل الدعم «أين مزايدته؟» ولا جواب. هنا تُعرض كلها وحالةُ كلٍّ مكتوبة،
لأن الشاشة تُفتح أصلاً حين يكون هناك خلاف.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, render

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid

from .exports import export, wants_export
from .tones import with_tones
from .views import console_page

#: صفوفٌ في الصفحة. الأرشيف يُقرأ بحثاً عن مزادٍ بعينه لا تصفّحاً، فالصفحة
#: الطويلة تخدم `Ctrl+F` أكثر مما تخدمه صفحاتٌ قصيرة كثيرة.
PAGE_SIZE = 50

#: ما يُعدّ «منتهياً» فيدخل الأرشيف. المسودّة والمجدول والجاري ليست تاريخاً —
#: هي عملٌ قائم، ومكانها `console:auctions`.
ARCHIVED = (AuctionState.ENDED, AuctionState.SETTLED, AuctionState.CANCELLED)

#: المركبة التي انتهت إلى بيع. تُجمَع أسعارها فتكون «إجمالي المبيعات».
#: `AWARDED` داخلة لأن الترسية بيعٌ وقع؛ ما بعدها (فاتورة، سداد، تسليم) خطوات
#: تحصيل لا خطوات بيع — فإخراجها كان سيجعل مزاداً سُدِّد كاملاً يبدو بلا مبيعات.
SOLD = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)

ZERO = Decimal("0.00")


def archived(*, text: str = "", state: str = ""):
    """المزادات المنتهية، مع عدد مركباتها وما بيع منها وإجماليه.

    مفصولةٌ عن العرض ليسألها الاختبار مباشرةً: الادّعاء أن «الإجمالي مشتقٌّ من
    المركبات» خاصيّةُ هذه الدالّة لا خاصيّةُ صفحةٍ من HTML.
    """
    rows = Auction.objects.filter(state__in=ARCHIVED)

    state = (state or "").strip()
    if state in ARCHIVED:
        rows = rows.filter(state=state)

    text = (text or "").strip()
    if text:
        # الرقم أو الاسم: الاثنان ما يُتذكَّر من مزادٍ مضى، ولا يُعرف أيّهما
        # في يد السائل. و`number` رقمٌ فيُطابَق تماماً لا جزئياً.
        matches = Q(title__icontains=text)
        if text.isdigit():
            matches |= Q(number=int(text))
        rows = rows.filter(matches)

    return rows.annotate(
        vehicle_count=Count("vehicles", distinct=True),
        sold_count=Count("vehicles", filter=Q(vehicles__state__in=SOLD), distinct=True),
        sold_total=Sum("vehicles__awarded_price", filter=Q(vehicles__state__in=SOLD)),
    ).order_by("-ends_at", "-number")


@console_page("console:auction-archive")
def auction_archive(request):
    """قائمة المزادات المنتهية — وكل صفٍّ بابٌ إلى مزايداته."""
    rows = archived(
        text=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="ارشيف-المزادات",
            headers=[
                "الرقم",
                "الاسم",
                "الحالة",
                "بدأ",
                "انتهى",
                "المركبات",
                "المباعة",
                "إجمالي المبيعات",
            ],
            cell=lambda row: [
                row.number,
                row.title,
                row.get_state_display(),
                row.starts_at,
                row.ends_at,
                row.vehicle_count,
                row.sold_count,
                row.sold_total or ZERO,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/auction_archive.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "states": [(value, AuctionState(value).label) for value in ARCHIVED],
        },
    )


def bids_of(auction: Auction):
    """كل مزايدات مزادٍ واحد، الأحدث أولاً — المسحوبة والمستبدَلة معها.

    `select_related` على الثلاثة لأن الجدول يعرض اسم المزايد وجوّاله ولوحة
    المركبة في كل صفّ: بدونها صفحةٌ من ٥٠ صفّاً تساوي ١٥١ استعلاماً.
    """
    return (
        Bid.objects.filter(vehicle__auction=auction)
        .select_related("bidder", "vehicle")
        .order_by("-placed_at")
    )


@console_page("console:auction-bids")
def auction_bids(request, pk: int):
    """مزايدات مزادٍ بعينه، وحالةُ كلٍّ منها مكتوبةٌ لا مستنتَجة."""
    auction = get_object_or_404(Auction, pk=pk)
    rows = bids_of(auction)

    if wants_export(request):
        return export(
            rows,
            name=f"مزايدات-مزاد-{auction.number}",
            headers=[
                "المركبة",
                "اللوحة",
                "المزايد",
                "الجوال",
                "المبلغ",
                "الحالة",
                "الوقت",
            ],
            cell=lambda row: [
                row.vehicle_id,
                row.vehicle.plate_number,
                row.bidder.full_name,
                row.bidder.phone,
                row.amount,
                _bid_state(row),
                row.placed_at,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    # الحالة تُعلَّق على صفوف هذه الصفحة وحدها. القالب لا يحسبها (المادة ٤-٤)،
    # ولا تُحسب لكل الصفوف: صفحةٌ من ٥٠ لا تحتاج حالةَ ٥٠٠٠.
    for bid in page.object_list:
        bid.state_word = _bid_state(bid)
        # لا حقلَ `state` على المزايدة — حالتها محسوبةٌ من علمين. فالنغمة
        # تُشتقّ من العلمين مباشرةً لا من خريطة `tones`، وتلك خريطةُ حالاتٍ
        # مخزَّنة لا حالاتٍ محسوبة.
        bid.tone = "bad" if bid.is_withdrawn else ("" if bid.is_superseded else "ok")

    return render(
        request,
        "console/auction_bids.html",
        {
            "auction": auction,
            "page": page,
            "total": rows.count(),
            "vehicles": Vehicle.objects.filter(auction=auction).count(),
        },
    )


def _bid_state(bid: Bid) -> str:
    """حالة المزايدة كلمةً واحدة.

    محسوبةٌ هنا لا في القالب: القالب يحسب حالةً هو مكانٌ ثانٍ للقاعدة ولا
    يُختبَر (المادة ٤-٤). والترتيب مقصود — المسحوبة تبقى مسحوبةً وإن استُبدلت
    بعدها، لأن السؤال الذي يُفتح لأجله هذا الجدول هو «لماذا لم تُحتسب؟».
    """
    if bid.is_withdrawn:
        return "مسحوبة"
    if bid.is_superseded:
        return "مستبدَلة بأعلى"
    return "قائمة"
