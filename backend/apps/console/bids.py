"""شاشتا المزايدات — الجارية الآن، وكلُّها بمركباتها. T890.

v1 يفرّقهما كذلك: `BillController::activeBids` يعرض **أعلى مزايدة لكل مزادٍ
منتهٍ** ليقرّر فيها، و`AuctionBidsAdminController::index` يعرض **مزايدي كل
سيارة** في مزادٍ واحد. وهنا الشاشتان بالمعنى نفسه، وفارقان مقصودان:

* **المزاد الجاري يُقرأ من المحرّك لا من عمود.** v1 يسأل
  `end_time <= CONVERT_TZ(NOW(),…)` في كلّ استعلام، فالساعةُ تُحسب في SQL
  ومنطقةُ التوقيت تُكتب بيدٍ في كل موضع. وهنا `engine.phase` مصدرٌ واحد.
* **والبحثُ صار يطبّع العربية فعلاً — T897.** كان مكتوباً هنا أنه يطبّع وهو
  غيرُ واقع (كشفه `ruff` بـ`F401`: استيرادٌ لا يُستدعى)، فصُحِّحت الجملةُ
  وفُتح بندٌ للسلوك. والآن التطبيعُ في `apps.core.arabic` وتستعمله كلُّ شاشات
  اللوحة، وتفصيلُ تنفيذِه هنا في `_searched`.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.shortcuts import render

from apps.accounts.models import User
from apps.auctions import engine
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid
from apps.core.arabic import search_q

from .archive import _bid_state
from .exports import export_table, wants_export
from .sensitive import (
    CUSTOMER,
    amounts_on,
    cell_amount,
    columns_for,
    person_on,
    shown_to,
    sold,
)
from .views import console_page

PAGE_SIZE = 50

#: أعمدةُ المركبة التي يبحث فيها الموظّف — نفسُ ما يسأل عنه العميل بالهاتف.
_SEARCH_FIELDS = ("make", "model", "plate_number", "vin")

#: وأعمدةُ المزايد: الاسمُ والجوّال، والجوّالُ أوّلُ ما يُقال في المكالمة.
_BIDDER_FIELDS = ("full_name", "phone")


def _searched(rows, text: str):
    """رشِّح بنصٍّ واحد: لوحة أو شاصٍ أو ماركة أو طراز أو لوت أو اسم مزايد.

    الرقمُ الصرف يُقارن باللوت ورقم المزاد أيضاً — من يكتب ١٠٠٨١٣٣ يقصد لوتاً
    لا اسماً. و«١٠٠٨١٣٣» بالأرقام العربية-الهندية تعمل كذلك: `int` في بايثون
    يقرؤها، و`isdigit` يقبلها.

    **والمطابقةُ تطبّع العربية** (`apps.core.arabic`): «شاحنه» تجد «شاحنة»
    و«دطق1265» تجد «د ط ق 1265». وكان مكتوباً هنا مرّةً أنها تطبّع وهي لا
    تطبّع — فالسطرُ اليوم مقيسٌ لا موعود.

    **والبحثُ يُحلّ على الجدولين الصغيرين ثم يُربط بالمفتاح المفهرس**، ولا
    يُطبَّق على ١٦٣٬٢٨٣ مزايدة صفّاً صفّاً. والفرقُ مقيسٌ على القاعدة
    المُرحَّلة: «لكزس اي اس» كانت ١٢٤٢ms بـ`icontains` على المزايدات وصارت
    ٧٤٤ms، و«شاحنه» ٩٦٥ms ← ٥١٠ms. أي أن التطبيعَ هنا **أسرعُ** ممّا حلّ
    محلَّه، لأن التعبيرَ النمطيَّ يُقيَّم ١٢٬٩٨١ + ٤٤٬٠٣٦ مرّةً بدل
    ١٦٣٬٢٨٣ × ٦. ومن يعيدها إلى `Q(vehicle__make__iregex=…)` مباشرةً يضاعف
    الزمن — جُرّب وقيس: ١٤٣٢ms.
    """
    text = (text or "").strip()
    if not text:
        return rows

    vehicles = Vehicle.objects.filter(search_q(text, *_SEARCH_FIELDS)).values("pk")
    bidders = User.objects.filter(search_q(text, *_BIDDER_FIELDS)).values("pk")
    clause = Q(vehicle__in=vehicles) | Q(bidder__in=bidders)
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


def _export_columns(seen):
    """أعمدةُ ملفّ المزايدات — **والملفُّ يرث حارسَ الشاشة**. T901.

    الملفُّ الواحد يخدم الشاشتين (الجاري، وكلّ السيارات) كما يخدمهما الجدول،
    وكان ينزّل «المزايد» و«الجوال» و«المبلغ» لمن يملك `auctions.view` وحدَها —
    أي أن من حُجب عنه الجوّالُ على الشاشة كان يأخذه في ملفٍّ بضغطةٍ واحدة.

    وعمودُ «المبلغ» يبقى ويُحجَب **صفّاً صفّاً** لا عموداً كاملاً: انظر
    :func:`~apps.console.sensitive.cell_amount` — الملفُّ يخلط مركبةً رست
    وأخرى في مزادٍ مفتوح، وسعرُ الوقوف يبقى في الحالتين (سؤالُ تشغيلٍ لا مال).
    """
    return columns_for(
        [
            ("المزاد", lambda row: row.vehicle.auction.number, None),
            ("اللوت", lambda row: row.vehicle.lot_number, None),
            ("المركبة", lambda row: f"{row.vehicle.make} {row.vehicle.model}", None),
            ("السنة", lambda row: row.vehicle.year, None),
            ("اللوحة", lambda row: row.vehicle.plate_number, None),
            ("الشاصي", lambda row: row.vehicle.vin, None),
            ("اللون", lambda row: row.vehicle.get_colour_display(), None),
            ("الحالة الفنية", lambda row: row.vehicle.get_condition_display(), None),
            ("سعر الوقوف", lambda row: row.vehicle.reserve_price, None),
            ("المزايد", lambda row: row.bidder.full_name, CUSTOMER),
            ("الجوال", lambda row: row.bidder.phone, CUSTOMER),
            ("المبلغ", lambda row: cell_amount(row, seen), None),
            ("حالة المزايدة", lambda row: _bid_state(row), None),
            ("الوقت", lambda row: row.placed_at, None),
        ],
        seen,
    )


@console_page("console:live-bids")
def live_bids(request):
    """مزايدات المزاد الجاري الآن — الشاشة التي تُفتح والمزاد مفتوح.

    «الجاري» من `engine.phase` لا من عمود الحالة وحده: عاملُ Celery قد يتأخّر،
    ولا يحتمل الموظّف أن يفتح الشاشة فيراها فارغةً ومزادٌ يعمل منذ دقيقتين.
    """
    # نبضةُ دورة الحياة قبل القراءة — كما تفعل قائمةُ المزادات. عاملُ Celery
    # يتوقّف، ولا يحتمل الموظّفُ أن يفتح «الجاري» فيراها فارغةً ومزادٌ حان
    # وقتُه قبل دقيقتين. وهي تنادي `services` نفسها فالكاتبُ يبقى واحداً.
    engine.tick()

    candidates = list(
        Auction.objects.filter(
            state__in=(AuctionState.LIVE, AuctionState.SCHEDULED)
        ).order_by("-starts_at")
    )
    live = [a for a in candidates if engine.phase(a) in engine.BIDDABLE_PHASES]

    # ما تخلّف عنه العامل يُقال صراحةً: صفحةٌ فارغةٌ بلا سببٍ تُقرأ «لا مزايدات»،
    # وهي في الحقيقة «مزادٌ كان يجب أن يبدأ ولم يبدأ».
    late = [
        (a, engine.phase(a))
        for a in candidates
        if engine.phase(a) in (engine.Phase.OVERDUE_START, engine.Phase.OVERDUE_END)
    ]

    search = request.GET.get("q", "")
    rows = (
        _rows(search=search).filter(vehicle__auction__in=live)
        if live
        else Bid.objects.none()
    )

    # جوّالُ المزايد خلف `users.view` هنا كما في كلّ جدولٍ آخر. ومبلغُه يبقى
    # ظاهراً في المعتاد: مركباتُ مزادٍ **مفتوح** لم تَرسُ، ومزايدةٌ على مركبةٍ
    # لم تَرسُ رقمُ سوقٍ لا مالُ أحد — و`cell_amount` تسأل المركبةَ لا الشاشة،
    # فلو دخل الجدولَ صفٌّ لمركبةٍ رست حُجب مبلغُه وحدَه.
    seen = shown_to(request.user)

    if wants_export(request):
        return export_table(rows, name="مزايدات-المزاد-الجاري",
                            columns=_export_columns(seen))

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    person_on(page.object_list, seen, field="bidder")
    amounts_on(page.object_list, seen)
    return render(request, "console/live_bids.html", {
        "page": page, "q": search, "live": live, "late": late,
        "show_money": seen.money, "show_customer": seen.customer,
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

    # الشاشةُ `auctions.view`، وكانت تضع في **مصدرها** خمسين جوّالاً وأربعةً
    # وخمسين مبلغاً في الصفحة الواحدة، وملفُّها أربعةَ عشرَ عموداً فيها
    # «المزايد» و«الجوال». والقاعدةُ في `sensitive.py` لا هنا.
    seen = shown_to(request.user)

    if wants_export(request):
        return export_table(rows, name="مزايدات-السيارات",
                            columns=_export_columns(seen))

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    person_on(page.object_list, seen, field="bidder")
    # والمبلغُ يُسأل عن **مركبته**: هذا الجدول يخلط المزادات، فصفٌّ لمركبةٍ
    # رست تحته صفٌّ لمركبةٍ في مزادٍ جارٍ. والأوّلُ سعرُ رسوٍّ بغطاءِ كلمة
    # «مزايدة»، والثاني رقمُ سوق.
    amounts_on(page.object_list, seen)
    keep = "".join(
        f"{k}={v}&" for k, v in (("auction", number), ("q", search)) if v
    )
    return render(request, "console/vehicle_bids.html", {
        "page": page, "q": search, "auction": auction, "number": number, "keep": keep,
        "show_money": seen.money, "show_customer": seen.customer,
        "auctions": Auction.objects.order_by("-starts_at").values(
            "number", "title"
        )[:200],
        "vehicles": rows.values("vehicle_id").distinct().count(),
    })


@console_page("console:vehicle-bid-list")
def vehicle_bid_list(request, pk: int):
    """مزايداتُ مركبةٍ واحدة — قِطعةٌ تُحقَن في نافذة، لا صفحةٌ كاملة.

    الصفُّ في جدول المزايدات يقول مزايدةً واحدة، والسؤالُ الذي يليه دائماً:
    «ومن غيره زايد عليها؟». وفتحُ صفحةٍ للجواب يفقد الموظّفُ مكانَه في جدولٍ
    من مئة ألف صفّ — فالجوابُ يأتي إليه.

    وتُعرض **كلُّها** لا الحيّة وحدها: «كم مرّةً رفع هذا الرقم؟» سؤالٌ عن
    التاريخ، وإخفاءُ المستبدَلة يجعل الجدولَ يكذب بالحذف.
    """
    from django.shortcuts import get_object_or_404

    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company"), pk=pk
    )
    rows = list(
        Bid.objects.filter(vehicle=vehicle)
        .select_related("bidder")
        .order_by("-amount", "placed_at")
    )

    # **أثقلُ تسريبٍ في الجولة**: مئةٌ وثمانيةَ عشرَ جوّالاً ومئةٌ وتسعةَ عشرَ
    # مبلغاً لمركبةٍ واحدة، في مصدر قِطعةٍ تُفتح من زرٍّ في كارت الأرشيف —
    # وهي `auctions.view` وحدَها. والقِطعةُ لا ترث حارسَ الصفحة التي تُحقَن
    # فيها: `fetch` طلبٌ مستقلٌّ يمرّ بحارسه هو، فلو اكتُفي بحجب الجدول خلفها
    # لبقي البابُ مفتوحاً بعنوانٍ يُكتب في شريط المتصفّح.
    seen = shown_to(request.user)
    person_on(rows, seen, field="bidder")
    # و`vehicle=` لأن المركبةَ في اليد أصلاً: بدونها `bid.vehicle` استعلامٌ
    # لكلّ صفٍّ من مئةٍ وتسعة عشر — و`select_related` هنا على المزايد وحده.
    amounts_on(rows, seen, vehicle=vehicle)

    # وأعلى مبلغٍ في الترويسة يُحجَب بالشرط نفسِه: على مركبةٍ رست **هو** سعرُ
    # رسوّها بالهللة، فحجبُ مئةٍ وتسعةَ عشرَ صفّاً وإبقاؤه في سطرٍ فوقها ليس
    # حجباً. ويُحسب على الصفوف المحمَّلة لا باستعلامِ تجميعٍ ثانٍ.
    top = max((bid.amount for bid in rows), default=None)

    return render(
        request,
        "console/_vehicle_bid_list.html",
        {
            "vehicle": vehicle,
            "rows": rows,
            "live": sum(
                1 for bid in rows if not bid.is_superseded and not bid.is_withdrawn
            ),
            "top": None if not seen.money and sold(vehicle) else top,
            "show_money": seen.money,
            "show_customer": seen.customer,
            # ورايةٌ إلى جانب `top` لأن `None` هنا جوابان: «لا مزايدات على
            # هذه المركبة» و«لا يحقُّ لك الرقم». والقالبُ يقول أيَّهما، فلا
            # يُقرأ الحجبُ فراغاً في القاعدة.
            "hide_top": not seen.money and sold(vehicle),
        },
    )
