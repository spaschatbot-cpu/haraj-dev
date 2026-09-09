"""شاشتا المزايدات — الجارية الآن، وكلُّها بمركباتها. T890.

v1 يفرّقهما كذلك: `BillController::activeBids` يعرض **أعلى مزايدة لكل مزادٍ
منتهٍ** ليقرّر فيها، و`AuctionBidsAdminController::index` يعرض **مزايدي كل
سيارة** في مزادٍ واحد. وهنا الشاشتان بالمعنى نفسه، وفارقان مقصودان:

* **المزاد الجاري يُقرأ من المحرّك لا من عمود.** v1 يسأل
  `end_time <= CONVERT_TZ(NOW(),…)` في كلّ استعلام، فالساعةُ تُحسب في SQL
  ومنطقةُ التوقيت تُكتب بيدٍ في كل موضع. وهنا `engine.phase` مصدرٌ واحد.
* **البحثُ يطبّع العربية.** v1 يقارن حرفياً، فمن كتب «تويوتا» بألفٍ ممدودة
  لا يجد سيارته.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.shortcuts import render

from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid

from .archive import _bid_state
from .exports import export, wants_export
from .vehicle_filters import normalize
from .views import console_page

PAGE_SIZE = 50

#: أعمدةُ المركبة التي يبحث فيها الموظّف — نفسُ ما يسأل عنه العميل بالهاتف.
_SEARCH_FIELDS = ("make", "model", "plate_number", "vin")


def _searched(rows, text: str):
    """رشِّح بنصٍّ واحد: لوحة أو شاصٍ أو ماركة أو طراز أو لوت أو اسم مزايد.

    الرقمُ الصرف يُقارن باللوت ورقم المزاد أيضاً — من يكتب ١٠٠٨١٣٣ يقصد لوتاً
    لا اسماً. والتطبيعُ عربيٌّ (`normalize`) فلا تحجب ألفٌ ممدودةٌ سيارة.
    """
    text = (text or "").strip()
    if not text:
        return rows

    clause = Q()
    for field in _SEARCH_FIELDS:
        clause |= Q(**{f"vehicle__{field}__icontains": text})
    clause |= Q(bidder__full_name__icontains=text)
    clause |= Q(bidder__phone__icontains=text)
    if text.isdigit():
        clause |= Q(vehicle__lot_number=int(text)) | Q(
            vehicle__auction__number=int(text)
        )
    return rows.filter(clause)


def _rows(*, auction=None, search=""):
    """المزايدات مع مركبتها ومزايدها ومزادها — استعلامٌ واحد لكل الصفحة."""
    rows = Bid.objects.select_related(
        "bidder", "vehicle", "vehicle__auction", "vehicle__owner_company"
    ).order_by("-placed_at", "-id")
    if auction is not None:
        rows = rows.filter(vehicle__auction=auction)
    return _searched(rows, search)


def _export_headers():
    return [
        "المزاد", "اللوت", "المركبة", "السنة", "اللوحة", "الشاصي", "اللون",
        "الحالة الفنية", "سعر الوقوف", "المزايد", "الجوال", "المبلغ",
        "حالة المزايدة", "الوقت",
    ]


def _export_cell(row):
    v = row.vehicle
    return [
        v.auction.number, v.lot_number, f"{v.make} {v.model}", v.year,
        v.plate_number, v.vin, v.get_colour_display(), v.get_condition_display(),
        v.reserve_price, row.bidder.full_name, row.bidder.phone, row.amount,
        _bid_state(row), row.placed_at,
    ]


@console_page("console:live-bids")
def live_bids(request):
    """مزايدات المزاد الجاري الآن — الشاشة التي تُفتح والمزاد مفتوح.

    «الجاري» من `engine.phase` لا من عمود الحالة وحده: عاملُ Celery قد يتأخّر،
    ولا يحتمل الموظّف أن يفتح الشاشة فيراها فارغةً ومزادٌ يعمل منذ دقيقتين.
    """
    live = [
        a
        for a in Auction.objects.filter(
            state__in=(AuctionState.LIVE, AuctionState.SCHEDULED)
        ).order_by("-starts_at")
        if engine.phase(a) in engine.BIDDABLE_PHASES
    ]

    search = request.GET.get("q", "")
    rows = _rows(search=search).filter(vehicle__auction__in=live) if live else Bid.objects.none()

    if wants_export(request):
        return export(rows, name="مزايدات-المزاد-الجاري",
                      headers=_export_headers(), cell=_export_cell)

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "console/live_bids.html", {
        "page": page, "q": search, "live": live,
        # روابطُ التصفّح تحمل البحث معها: «التالي» بدونه يعود بالجدول كلّه
        # والقارئُ يظنّ نفسه داخل نتيجته.
        "keep": f"q={search}&" if search else "",
        "bidders": rows.values("bidder_id").distinct().count(),
        "highest": rows.aggregate(top=Max("amount"))["top"],
    })


@console_page("console:vehicle-bids")
def vehicle_bids(request):
    """كل المزايدات على مركبات المزادات — بفلتر مزادٍ وبحثٍ وبيانات المركبة.

    الجدولُ يحمل بيانات المركبة كاملةً لا رقمَها ولوحتها فقط: من يقرأ مزايدةً
    يسأل «على أي سيارة؟» فوراً، وجوابُه في الصفّ لا في نقرةٍ ثانية.
    """
    number = (request.GET.get("auction") or "").strip()
    auction = (
        Auction.objects.filter(number=int(number)).first() if number.isdigit() else None
    )
    search = request.GET.get("q", "")
    rows = _rows(auction=auction, search=search)

    if wants_export(request):
        return export(rows, name="مزايدات-السيارات",
                      headers=_export_headers(), cell=_export_cell)

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    keep = "".join(
        f"{k}={v}&" for k, v in (("auction", number), ("q", search)) if v
    )
    return render(request, "console/vehicle_bids.html", {
        "page": page, "q": search, "auction": auction, "number": number, "keep": keep,
        "auctions": Auction.objects.order_by("-starts_at").values(
            "number", "title"
        )[:200],
        "vehicles": rows.values("vehicle_id").distinct().count(),
    })
