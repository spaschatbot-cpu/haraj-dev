"""The auctions and vehicles screens. T805.

Four pages, and each answers a question an operator actually asks:

* **المزادات** — what is running, what is coming, and how many cars in each.
* **تفاصيل المزاد** — this auction's cars, with the one that needs a decision
  visible rather than buried on page four.
* **المركبات** — find a car across auctions, by make or by lot.
* **تغيير حالة المركبة** — the quick edit, and the only write here.

Nothing on these pages decides anything. The listing comes from
`apps.auctions.listing`, which is the same code the customer API pages use, so
the console and the app cannot disagree about how many cars an auction holds.
State changes go through `apps.auctions.services` — `auction_state_single_writer`
fails the build if a screen ever writes a state column itself.

**Every write demands a reason.** Spec 009 §"قواعد المال في اللوحة" 2 asks it of
financial actions; this file asks it of state changes too, for the same reason:
a car that moved and nobody can say why is the row support cannot explain to the
partner who owned it.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from apps.auctions import cards, engine
from apps.auctions import services as auction_services
from apps.auctions.listing import MAX_PAGE_SIZE, with_vehicle_counts
from apps.auctions.models import Auction, Showcase, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import visible_vehicles
from apps.core import audit
from apps.core.permissions import Capability, can

from . import columns, icons, vehicle_bulk, vehicle_filters
from .exports import export, wants_export
from .forms import AuctionForm, AuctionIdentityForm, VehicleForm
from .tones import tone_of, tone_of_phase, with_tones
from .views import console_page

#: Rows per page. Twenty-five rather than the API's twenty: a console user is
#: scanning rather than scrolling a phone, and a page that ends after twenty
#: rows costs an operator a click on every auction.
PAGE_SIZE = 25


#: أعمدة الجدول لخانات «تخصيص الأعمدة» — المفتاح هو `data-col` نفسه.
#:
#: هنا لا في القالب: قائمةٌ في القالب تُنسخ ثانيةً في السكربت، فيبقى عمودٌ
#: بلا خانةٍ تُخفيه أو خانةٌ لا تُخفي شيئاً — ولا يُلاحَظ حتى يفتحها موظّف.
#: أيقوناتُ عمود التحكم — سبعةُ أفعالٍ في صفٍّ واحد.
#:
#: نصّاً كانت تلتفّ على أربعة أسطر وتمدّ الصفّ حتى يُقرأ الجدول أطولَ من
#: محتواه. والأيقونة **ليست بديلاً عن الاسم**: كلُّ زرٍّ يحمل `aria-label`
#: و`title` بالنصّ نفسه، فمن يقرأ بقارئ شاشة أو يقف بالفأرة يسمع/يرى الكلمة.
#: رسومُ صفِّ هذه الشاشة — المُعلنُ منها هو المستعمَل، ويحرسه
#: `test_every_row_icon_is_declared`. و`test_no_icon_is_drawn_for_nobody` يمسح
#: `PAGES` وبطاقاتِ اللوحة وحدها، فرسمٌ يقرؤه صفُّ جدولٍ كان يُعدّ «بلا مستعمل»
#: فيُحذف — ثم يُرسم الصفُّ بفراغ.
ROW_ICONS = (
    "flag",
    "car",
    "scale",
    "file-excel",
    "coins",
    "calendar-clock",
    "square",
    "pencil",
    "trash",
)

ACTIONS = (
    ("status", "تغيير الحالة", "flag"),
    ("cars", "السيارات", "car"),
    # «مراجعة العروض» — نظيرُ `bidReviewModal` في v1. T860
    #
    # هناك نافذةٌ تُجلَب بـAJAX وتُظهر سياراتِ المزاد ومزايديها وزرَّي موافقةٍ
    # ورفض. وهنا **الشاشةُ موجودةٌ أصلاً** — `partner-decisions` بأزرارها
    # وبوّابتها وسجلِّها — وكان ينقصها بابٌ من الصفّ. فالزرّ يوصل إليها مُرشَّحةً
    # على هذا المزاد، ولا يُبنى قرارٌ ثانٍ في نافذة.
    ("review", "مراجعة العروض", "scale"),
    ("export", "تصدير Excel", "file-excel"),
    # `coins` للرسوم لا `pencil`: القلمُ يقول «تعديل»، والرسومُ فعلٌ ماليّ
    # له وجهُه. وكان القلمُ عليها فظُنّ زرَّ التعديل، وزرُّ التعديل نفسُه
    # كان بلا أيقونة أصلاً — سقط في الدمج فرجعت النسخةُ القديمة صامتةً.
    ("fees", "الرسوم والتأمين", "coins"),
    ("reschedule", "إعادة جدولة", "calendar-clock"),
    ("end", "إنهاء المزاد", "square"),
    ("edit", "تعديل بيانات المزاد", "pencil"),
    ("delete", "حذف المزاد", "trash"),
)


COLUMNS = (
    ("id", "#"),
    ("auction", "المزاد والملخص"),
    ("preview", "المعاينة"),
    ("cars", "العربيات"),
    ("window", "الفترة الزمنية"),
    ("prices", "الأسعار"),
    ("ready", "التفعيل"),
    ("images", "الصور"),
    ("bids", "المشاركات"),
    ("park", "الموقع"),
    ("badge", "الحالة"),
    ("actions", "تحكم"),
)


def parks(limit: int = 60) -> list[str]:
    """الساحاتُ الموجودة فعلاً، لقائمة الفلترة.

    مقروءةٌ من الصفوف لا مكتوبةٌ في الشيفرة: قائمةٌ ثابتة تنسى ساحةً تُفتح
    غداً، ويبحث الموظّف عنها فلا يجدها ويظنّ أن لا مزاد فيها.
    """
    seen = (
        Auction.objects.exclude(location="")
        .values_list("location", flat=True)
        .distinct()
        .order_by("location")[:limit]
    )
    return list(seen)


def _page(request, queryset):
    """One page of ``queryset``, with the size bounded.

    `MAX_PAGE_SIZE` is shared with the customer API deliberately: `?limit=100000`
    is a table scan whoever asks for it, and an operator's session is not a
    reason to allow one.
    """
    try:
        size = min(int(request.GET.get("limit", PAGE_SIZE)), MAX_PAGE_SIZE)
    except (TypeError, ValueError):
        size = PAGE_SIZE

    return Paginator(queryset, max(size, 1)).get_page(request.GET.get("page"))


@console_page("console:auctions")
def auctions(request):
    """Every auction, newest first, with its counts.

    Staff see drafts and cancelled auctions; `apps.auctions.listing` already
    makes that distinction for the customer API, and this reuses the same
    annotation so the counts on both cannot drift.
    """
    # نبضةُ دورة الحياة قبل القراءة — T846. عاملُ Celery يتوقّف، ولا يحتمل
    # الموظّف أن يفتح الشاشة فيرى «قريباً» على مزادٍ بدأ قبل دقيقتين. وهي
    # تنادي `services` نفسها، فالكاتبُ يبقى واحداً، وتُكلّف استعلامين
    # يعودان فارغين في أغلب النداءات.
    engine.tick()

    rows = Auction.objects.all()

    state = request.GET.get("state", "")
    if state in AuctionState.values:
        rows = rows.filter(state=state)

    search = (request.GET.get("q") or "").strip()
    if search:
        # البحث يشمل الموقع أيضاً (T846): «ابحث بالاسم أو الساحة أو الرقم».
        rows = (
            rows.filter(Q(title__icontains=search) | Q(location__icontains=search))
            if not search.isdigit()
            else rows.filter(number=int(search))
        )

    # الفلترة المتقدّمة: مطابقةٌ حرفية لا احتواء — «رقم المزاد المطابق»
    # و«الساحة المطابقة». وهي غيرُ خانة البحث عمداً: من يعرف الرقم لا يريد
    # أن يجد معه ١٠١٤ و٢١٠١٤.
    exact = (request.GET.get("id_exact") or "").strip()
    if exact.isdigit():
        rows = rows.filter(number=int(exact))

    park = (request.GET.get("park_exact") or "").strip()
    if park:
        rows = rows.filter(location__iexact=park)

    # الأحدث أوّلاً — والرقم يفصل عند تساوي الموعد، وإلا اختلف ترتيب الصفحة
    # الثانية عن الأولى وتكرّر صفٌّ وغاب آخر.
    rows = with_vehicle_counts(rows).order_by("-starts_at", "-number")

    if wants_export(request):
        # التصدير يحمل ما تحمله الشاشة — وإلا صار ملفّان لا يتّفقان: موظّفٌ
        # يقرأ «٦٥١٨ مزايدة» على الشاشة و«٥٨٤٧» في الملفّ ولا يعرف أيّهما.
        # ولذلك يمرّ على المحرّك نفسه، لا على استعلامٍ ثانٍ.
        page_rows = list(rows)
        summaries = engine.summarise(page_rows)
        engine.phases_of(page_rows)
        return export(
            page_rows,
            name="auctions",
            headers=[
                "#",
                "المزاد",
                "الحالة",
                "يبدأ",
                "ينتهي",
                "الموقع",
                "السيارات",
                "الماركات",
                "المعروضة",
                "سيارات لها صور",
                "الصور",
                "المزايدات",
                "المزايدون",
            ],
            cell=lambda a: [
                a.number,
                a.title,
                a.phase_label,
                a.starts_at,
                a.ends_at,
                a.location,
                summaries[a.pk].cars,
                summaries[a.pk].makes,
                summaries[a.pk].offered,
                summaries[a.pk].cars_with_images,
                summaries[a.pk].images,
                summaries[a.pk].bids,
                summaries[a.pk].bidders,
            ],
        )

    page = _page(request, rows)
    with_tones(page.object_list)
    # المرحلةُ على كل صفّ — بلا استعلامٍ إضافي (T843).
    engine.phases_of(page.object_list)
    # أعمدةُ v1 كما طلبها المالك: «عايز نفس الحقول».
    engine.summarise_onto(page.object_list)
    # ختمُ HR-13 لكل صفّ، لتحمله نافذةُ التعديل. الاستمارةُ نفسها تحسبه —
    # حسبةٌ ثانية هنا كانت ستُنتج ختماً لا يطابق ما يفحصه الحفظ، فيُرفض كلُّ
    # حفظٍ صحيح.
    for row in page.object_list:
        row.row_stamp = AuctionIdentityForm(instance=row).initial.get("row_stamp", "")
    for row in page.object_list:
        row.phase_tone = tone_of_phase(row.phase)
        # البادج بمفردات v1 الخمس، محسوباً من الحالة والساعة واللافتة.
        row.badge = engine.badge_of(row)
        row.badge_label = engine.Badge(row.badge).label
        row.badge_tone = engine.BADGE_TONES.get(row.badge, "")

        # العنوان وحده تحته العددان — لا عيّنةَ سيارة.
        #
        # كان السطرُ يبدأ باسم عيّنةٍ فيقرأ الموظّف «تويوتا كامري تويوتا كامري
        # 2025» — تكرارٌ لأن `vehicle_name` في v1 مكتوبٌ في الماركة والطراز
        # معاً. والعيّنةُ لها عمودُها (العربيات)، ووجودُها هنا يدفع الرقمين
        # اللذين يفتح الموظّف الشاشة لأجلهما إلى آخر السطر.
        sample = row.summary.sample if (row.summary and row.summary.sample) else ""
        row.display_title = (row.title or "").strip() or sample or f"مزاد #{row.number}"
        row.cars_total = row.summary.cars if row.summary else 0
        row.cars_offered = row.summary.offered if row.summary else 0

    return render(
        request,
        "console/auctions.html",
        {
            "page": page,
            "states": AuctionState.choices,
            "state": state,
            "q": search,
            "id_exact": exact,
            "park_exact": park,
            "parks": parks(),
            "badges": engine.Badge.choices,
            "column_choices": COLUMNS,
            "action_icons": {
                key: (label, icons.path_of(name)) for key, label, name in ACTIONS
            },
            # الأزرار تُرسَم لمن يملك الإدارة فقط — لا تُرسَم ثم تُرفض.
            "can_manage": can(request.user, Capability.AUCTIONS_MANAGE),
            "can_delete": can(request.user, Capability.AUCTIONS_DELETE),
            "showcases": Showcase.choices,
        },
    )


@console_page("console:auction-detail")
def auction_detail(request, pk: int):
    """المزاد وسياراته — بحقول شاشة v1 المقابلة (`{id}/vehicles`)، لا أكثر.

    **وما ليس على هذه الشاشة مقصودٌ غيابُه.** لا سعرَ وقوفٍ ولا فائزَ ولا
    فاتورة: الأولُ يُحرَّر في شاشة تعديل المركبة، والأخيران **نتيجةُ بيعٍ
    ومالُها** ومكانُهما شاشاتُ ما بعد البيع. وشاشةُ v1 المقابلة لا تعرض
    واحداً منها — يفتحها من يملك `auctions.view`، وهو دورٌ لا يرى أموال
    العملاء.

    والأعمدةُ الثمانيةَ عشرَ في v1 قُرئت من `manage_vehicles.php:850-867`.
    خمسةٌ منها لا حقلَ لها عندنا (رقم المطالبة · شركة التأمين · حالة المحرّك ·
    المفاتيح · التسويق) — مذكورةٌ في `tasks.md` ولا تُخترَع.
    """
    auction = get_object_or_404(with_vehicle_counts(Auction.objects.all()), pk=pk)

    # الترشيحُ قبل فرع التصدير: الملفُّ يحمل **ما تراه الشاشة**. وتصديرٌ يتجاهل
    # الفلتر يعطي ثلاثمئة صفٍّ والشاشةُ أمام صاحبه تقول سبعة — ولا شيء في الملفّ
    # يقول أيَّهما الصحيح. وهو العطلُ نفسه الذي أُصلح في `0ad74b7` على مستوى
    # المزاد (كان يُنزّل الصفحة كلَّها لا سيّارات ذلك المزاد)، عائداً على مستوى
    # الفلتر.
    rows = vehicle_filters.apply(engine.vehicle_rows(auction), request.GET)

    if wants_export(request):
        from apps.auctions.importexport import export_vehicles

        from .exports import workbook_response

        return workbook_response(
            export_vehicles(rows),
            name=f"auction_{auction.number}_vehicles",
        )

    view = engine.snapshot(auction)
    page = _page(request, rows)
    with_tones(page.object_list)

    # صورةُ الغلاف لكل كارت — كأسلوب عرض v1 (`manage.php`): بطاقةُ السيارة
    # تحمل صورتَها. استعلامٌ واحد لكل الصفحة عبر `card_queryset` لا واحدٌ لكل
    # صفّ (النمطُ الذي جعل قائمة v1 تُحمَّل في ثوانٍ).
    ids = [row.pk for row in page.object_list]
    covers = {
        row.pk: cards.thumbnail_of(row)
        for row in cards.card_queryset(Vehicle.objects.filter(pk__in=ids))
    }
    for row in page.object_list:
        row.thumb = covers.get(row.pk)

    allowed_operations = [op for op in view.operations if op.allowed]
    blocked_operations = [op for op in view.operations if not op.allowed]

    return render(
        request,
        "console/auction_detail.html",
        {
            "auction": auction,
            "page": page,
            "filters": vehicle_filters.state(request.GET, auction),
            # تخصيصُ أعمدة الجدول — القائمةُ للمكوّن، والمخفيُّ للخلايا. T869
            "columns_layout": columns.layout_for(request.user, "auction_vehicles"),
            "columns_table_key": "auction_vehicles",
            "cols_hidden": columns.hidden_keys(request.user, "auction_vehicles"),
            "view": view,
            "allowed_operations": allowed_operations,
            "blocked_operations": blocked_operations,
            # النغمةُ تُحسب هنا لا في القالب: `tones.with_tones` يقول لماذا —
            # قالبٌ يحسب نغمةً مكانٌ ثانٍ للقاعدة ولا يُختبَر (المادة ٤-٤).
            "phase_tone": tone_of_phase(view.phase),
            "badge": engine.badge_of(auction),
            "badge_label": engine.Badge(engine.badge_of(auction)).label,
            "badge_tone": engine.BADGE_TONES.get(engine.badge_of(auction), ""),
            "can_manage": can(request.user, Capability.AUCTIONS_MANAGE),
            # ختمُ HR-13 لنافذة التعديل هنا كما في القائمة: المالك أراد
            # التعديلَ نافذةً في **كلّ** شاشة، والنافذةُ بلا ختمٍ تكتب فوق
            # تعديل زميلٍ صامتةً.
            "row_stamp": AuctionIdentityForm(instance=auction).initial.get(
                "row_stamp", ""
            ),
            # الشريطُ المجمَّع: حالاتُه من سجلٍّ مغلق، ووجهاتُ النقل مزاداتٌ
            # **لم تبدأ** — نقلُ مركبةٍ إلى مزادٍ جارٍ يُدخلها في منتصف الشوط.
            "bulk_states": vehicle_bulk.BULK_STATES,
            "move_targets": [
                row
                for row in Auction.objects.exclude(pk=auction.pk).order_by("-number")[
                    :50
                ]
                if not engine.has_started(row)
            ],
            "action_icons": {
                "view": icons.path_of("car"),
                "edit": icons.path_of("pencil"),
                "end": icons.path_of("square"),
                # أفعالُ الصفّ المفردة — نظيرُ عمود التحكّم في v1. T872
                "images": icons.path_of("eye"),
                "move": icons.path_of("layers"),
                "delete": icons.path_of("trash"),
                # إخفاء/إظهار — رؤيةُ السيارة عن العملاء. نظيرُ v1.
                "hide": icons.path_of("eye-off"),
                "show": icons.path_of("eye"),
            },
        },
    )


@console_page("console:vehicles")
def vehicles(request):
    """Find a car across auctions.

    The visibility rule is applied even here. Staff see everything through it —
    `visible_vehicles` already returns the full set for staff — but routing the
    console through the same function is what keeps "who may see this car" a
    single answer rather than two that agree until one is edited (T409).
    """
    rows = visible_vehicles(request.user).select_related("auction", "owner_company")

    search = (request.GET.get("q") or "").strip()
    if search:
        from django.db.models import Q

        terms = Q(make__icontains=search) | Q(model__icontains=search)
        if search.isdigit():
            terms = terms | Q(lot_number=int(search)) | Q(auction__number=int(search))
        rows = rows.filter(terms)

    state = request.GET.get("state", "")
    if state in VehicleState.values:
        rows = rows.filter(state=state)

    rows = rows.order_by("auction_id", "lot_number")

    if wants_export(request):
        # Delegated to phase 005's writer rather than given a second column
        # list here: the vehicle export is the *import's input* (T806), and a
        # second shape would produce a file that cannot be uploaded back.
        from apps.auctions.importexport import export_vehicles

        from .exports import workbook_response

        return workbook_response(export_vehicles(rows), name="vehicles")

    page = _page(request, rows)
    # الصورة والنغمة تُعلَّقان على صفوف **هذه الصفحة** وحدها.
    #
    # و`card_queryset` قبلهما لا بعدهما: بدونه يكلّف كل صفٍّ استعلامَ غلافٍ
    # خاصاً به — خمسون صفّاً، خمسون استعلاماً — وهو النمط الذي جعل هذه القائمة
    # في v1 تُحمَّل في ثوانٍ. وهي الدالّة نفسها التي يستعملها API العميل، فصورةُ
    # الغلاف في اللوحة هي صورةُ الغلاف في التطبيق بحكم البناء لا بحكم الاتفاق.
    ids = [row.pk for row in page.object_list]
    covers = {
        row.pk: cards.thumbnail_of(row)
        for row in cards.card_queryset(Vehicle.objects.filter(pk__in=ids))
    }
    for row in page.object_list:
        row.thumb = covers.get(row.pk)
        row.tone = tone_of(row.state)

    return render(
        request,
        "console/vehicles.html",
        {
            "page": page,
            "states": VehicleState.choices,
            "state": state,
            "q": search,
        },
    )


@console_page("console:vehicle-detail")

def _modal(request):
    """هل يُطلَب هذا العرضُ نافذةً؟ ولو نعم فأيُّ قالبِ أساسٍ يُستعمَل.

    `?modal=1` يأتي من زرٍّ في جدولٍ يفتح تفاصيلَ صفٍّ أو تعديلَه في مكانه.
    فيُرندَر المحتوى وحده (`_modal_base`) بلا شريطٍ جانبيٍّ ولا ترويسة، ويُحقَن
    في `<dialog>`. والطلبُ المباشر (رابطٌ مُشارَك، سجلّ متصفّح) يبقى صفحةً
    كاملة — فالوجهان من قالبٍ واحد.
    """
    is_modal = (
        request.GET.get("modal") == "1"
        or request.headers.get("X-Requested-With") == "fetch"
    )
    return is_modal, "console/_modal_base.html" if is_modal else "console/base.html"


def vehicle_detail(request, pk: int):
    """One car: what it is, where it stands, and where it may go next.

    The moves offered are computed from the state machine rather than listed in
    a template. A button for a transition the machine refuses is a button that
    produces an error message, and v1's screens were full of them.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company", "awarded_to"), pk=pk
    )

    from apps.auctions.states import VEHICLE_MOVES

    moves = [
        {"target": move.target, "label": VehicleState(move.target).label, "why": move.why}
        for move in VEHICLE_MOVES
        if move.source == vehicle.state
    ]

    # الصور: مرتّبةً بالغلاف أولاً ثم `position` — وهو ترتيب `VehicleImage.Meta`
    # نفسه، فلا ترتيبَ ثانٍ يفترق عنه. ولم تكن تُعرض في اللوحة أصلاً: سبعٌ
    # وعشرون صورة في قاعدة العرض ولا واحدةٌ منها على شاشة، بينما هي أسرع ما
    # يجيب «أهذه السيارة التي يتكلّم عنها العميل؟».
    shots = vehicle.images.order_by("-is_cover", "position", "pk")

    # وجهاتُ إعادة العرض: المزادات التي لم تبدأ بعد. الحيّ ليس منها — لوتٌ
    # يظهر بعد أن قرأ الناس القائمة هو مزادٌ تغيّر تحت من يزايد فيه (T828).
    from apps.auctions.states import VEHICLE_MOVE_INDEX

    may_relist = (vehicle.state, VehicleState.RELISTED) in VEHICLE_MOVE_INDEX
    destinations = (
        Auction.objects.filter(
            state__in=(AuctionState.DRAFT, AuctionState.SCHEDULED)
        ).order_by("starts_at")
        if may_relist
        else Auction.objects.none()
    )

    is_modal, base_template = _modal(request)
    return render(
        request,
        "console/vehicle_detail.html",
        {
            "vehicle": vehicle,
            "moves": moves,
            "shots": shots,
            "destinations": destinations,
            "base_template": base_template,
            "is_modal": is_modal,
        },
    )


@console_page("console:vehicle-state")
def vehicle_state(request, pk: int):
    """Move one car, with a reason. The only write on these screens.

    A reason is required and recorded. A car that changed state and nobody can
    say why is the row support cannot explain to the partner who owns it — and
    partners ask.
    """
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)

    if request.method != "POST":
        return redirect("console:vehicle-detail", pk=pk)

    target = request.POST.get("target", "")
    reason = (request.POST.get("reason") or "").strip()


    before = audit.snapshot(vehicle, ["state", "auction_id", "lot_number"])

    try:
        auction_services.move_vehicle(vehicle, target)
    except Exception as refusal:
        # The state machine's own sentence, shown as it is. It already says
        # whether the move does not exist or is merely not ready yet, and
        # rewording it here would lose that distinction.
        messages.error(request, str(refusal))
        return redirect("console:vehicle-detail", pk=pk)

    audit.record(
        action="console.move_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state", "auction_id", "lot_number"]),
        note=reason,
    )
    messages.success(request, f"المركبة صارت «{VehicleState(vehicle.state).label}».")
    # يعود إلى حيث جاء الطلب إن كان مساراً داخلياً آمناً (شاشةُ المزاد ترسل
    # `next`)، وإلا فصفحةُ المركبة. فزرُّ «إظهار/إخفاء» على الكارت يُبقي الموظّفَ
    # في المزاد الذي يبنيه لا يقذفه إلى صفحة مركبةٍ مفردة.
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts=None):
        return redirect(nxt)
    return redirect("console:vehicle-detail", pk=pk)


# ---------------------------------------------------------------------------
# Creating and editing. T805's other half.
# ---------------------------------------------------------------------------


def _save(request, form, *, action: str, fields: list[str], instance=None):
    """Validate, save, and record — in that order, once.

    Shared by the four editing views because the order is the rule and a rule
    written four times drifts. The audit entry is written **after** the save and
    inside no transaction of its own: the row exists by then, so a snapshot of
    it is a snapshot of what is actually stored.
    """
    if not form.is_valid():
        return None

    before = audit.snapshot(instance, fields) if instance is not None else None
    saved = form.save()

    audit.record(
        action=action,
        entity=saved,
        actor=request.user,
        before=before,
        after=audit.snapshot(saved, fields),
        note=form.cleaned_data["reason"],
    )
    return saved


AUCTION_FIELDS = [
    "number", "title", "location", "showcase",
    "starts_at", "ends_at", "sms_reminder_at",
    "deposit_required", "admin_fee",
]

#: ما تكتبه نافذةُ التعديل — هويّةُ المزاد وحدها. T859.
#:
#: الموعدُ تملكه «إعادة الجدولة» والتأمينُ تملكه «الرسوم»، وكانت هذه الاستمارة
#: تكتبهما أيضاً بقواعدَ أخفّ — فمن عدّل الموعد من هنا تخطّى التحقّق من النافذة
#: وتخطّى مسحَ مزايدات ما لم يُبَع. والقسمة الآن: لكلّ حقلٍ كاتبٌ واحد.
AUCTION_IDENTITY_FIELDS = ["number", "title", "location"]
VEHICLE_FIELDS = [
    "auction_id",
    "lot_number",
    "make",
    "model",
    "year",
    "reserve_price",
    "owner_company_id",
]


@console_page("console:auction-new")
def _absorb_selected(request, auction: Auction) -> int:
    """انقل السياراتِ المختارةَ من الكتالوج إلى مزادٍ وليد، وأعِد كم نُقل.

    المعرّفاتُ تصل في `vehicle_ids` (حقلٌ خفيّ حمله النموذجُ من `?vehicle_ids`
    في رابط «إنشاء مزاد من المحدد»). ما عليه فاتورةٌ حيّة لا يُنقَل صامتاً —
    نظيرُ قفل `vehicle_bulk`: الفاتورةُ تؤشّر على السيارة وقد دُفع عليها.
    """
    raw = request.POST.get("vehicle_ids", "")
    ids = [int(part) for part in raw.split(",") if part.strip().isdigit()]
    if not ids:
        return 0

    from apps.money.models import Invoice, InvoiceState

    rows = list(Vehicle.objects.filter(pk__in=ids))
    locked = set(
        Invoice.objects.filter(vehicle__in=rows)
        .exclude(state=InvoiceState.CANCELLED)
        .values_list("vehicle_id", flat=True)
    )
    free = [v.pk for v in rows if v.pk not in locked]
    if not free:
        if locked:
            messages.error(
                request,
                f"{len(locked)} مركبة عليها فاتورةٌ حيّة لم تُنقَل — استرجِعها أولاً.",
            )
        return 0

    moved = Vehicle.objects.filter(pk__in=free).update(auction=auction)
    audit.record(
        action="console.auction_absorb_selected",
        entity=auction,
        actor=request.user,
        after={"auction": auction.number, "count": moved},
        note="إنشاء مزاد من سياراتٍ مختارة في الكتالوج",
    )
    if locked:
        messages.error(
            request,
            f"{len(locked)} مركبة عليها فاتورةٌ حيّة لم تُنقَل — استرجِعها أولاً.",
        )
    return moved


def auction_new(request):
    """A new auction, born `draft`.

    The state is not a field and not a choice: an auction starts as a draft and
    reaches every other state through `apps.auctions.services`, whose guards
    refuse — among other things — scheduling one with no cars in it.
    """
    form = AuctionForm(request.POST or None)

    if request.method == "POST":
        # الرقمُ يُخصَّص في `AuctionForm.save` (max+1). سباقُ منشئَين قد يقع على
        # الرقم نفسه فيرفضه القيدُ الفريد — نعيد المحاولة، وكلُّ محاولةٍ تُعيد
        # حساب الرقم. القيدُ هو الحارس، وهذا مجرّد لطفٍ يتفادى صفحةَ خطأ.
        from django.db import IntegrityError

        auction = None
        if form.is_valid():
            for _attempt in range(6):
                try:
                    auction = _save(
                        request,
                        form,
                        action="console.create_auction",
                        fields=AUCTION_FIELDS,
                    )
                    break
                except IntegrityError:
                    form.instance.pk = None  # فشل الإدراج → أعِد الحساب والمحاولة
                    continue
        if auction is not None:
            # «إنشاء مزاد من المحدد» في الكتالوج: يصل بمعرّفات سياراتٍ مختارة،
            # فتُنقَل إلى المزاد الوليد. المزادُ فارغٌ فلا يصطدم لوتٌ مكرّر،
            # والمقفولةُ بفاتورةٍ حيّة تُذكر ولا تُنقَل — كنقل vehicle_bulk.
            absorbed = _absorb_selected(request, auction)
            step2 = (
                f"استوعب {absorbed} مركبة. راجعها وأضِف غيرَها والصور."
                if absorbed
                else "الخطوة ٢: أضِف السيارات والصور."
            )
            messages.success(
                request,
                f"أُنشئ المزاد {auction.number} (مسودّة). {step2}",
            )
            return redirect("console:auction-detail", pk=auction.pk)

    # الرقمُ التالي المعروض للموظّف — نفسُ حساب `AuctionForm.save` (max+1).
    # معاينةٌ لا التزام: قد يتغيّر لو أُنشئ مزادٌ بين العرض والحفظ، و`save`
    # يُعيد الحساب حينها. لكن عرضَ الرقم الفعليّ أوضحُ من «يُخصَّص تلقائياً».
    from django.db.models import Max

    next_number = (Auction.objects.aggregate(m=Max("number"))["m"] or 0) + 1

    # «إنشاء مزاد من المحدد»: تُعرَض السياراتُ المختارةُ في النموذج — لوحةً
    # وشاصياً وحالة — كما في مرشد v1، فيرى الموظّفُ ما سيُستوعَب قبل الحفظ.
    raw_ids = request.GET.get("vehicle_ids", "")
    ids = [int(part) for part in raw_ids.split(",") if part.strip().isdigit()]
    selected_vehicles = (
        list(Vehicle.objects.filter(pk__in=ids).select_related("auction"))
        if ids
        else []
    )

    return render(
        request,
        "console/auction_form.html",
        {
            "form": form,
            "auction": None,
            "next_number": next_number,
            # يُعاد حقلاً خفياً في النموذج كي يصل مع الـPOST فتُستوعَب بعد الحفظ.
            "vehicle_ids": raw_ids,
            "selected_vehicles": selected_vehicles,
        },
    )


@console_page("console:auction-edit")
def auction_edit(request, pk: int):
    """تعديلُ بيانات المزاد — **نافذةٌ من القائمة**، والصفحةُ احتياطٌ لا غير.

    المالك: «خلي زرار التعديل اللي في صفحة إدارة المزادات يكون بوب أب مش
    صفحة». وبقيت الصفحةُ تُرسم للطلب المباشر (`GET`) — رابطٌ يُفتح من سجلّ
    المتصفّح أو يُشارَك يجب أن يُعطي شيئاً.

    **ورفضُ الاستمارة يعود إلى القائمة برسائله**، لا إلى صفحةٍ ثانية: من
    فتح نافذةً على القائمة يتوقّع أن يرجع إليها. وأخطاءُ الحقول تُقال في
    `messages` لأن النافذةَ لا تحمل أخطاءَ حقلٍ بجانب حقلها.
    """
    auction = get_object_or_404(Auction.objects.all(), pk=pk)
    form = AuctionIdentityForm(request.POST or None, instance=auction)
    from_list = request.POST.get("back") == "list"

    if request.method == "POST":
        saved = _save(
            request,
            form,
            action="console.edit_auction",
            fields=AUCTION_IDENTITY_FIELDS,
            instance=Auction.objects.get(pk=pk),
        )
        if saved is not None:
            messages.success(request, f"حُفظت تعديلات مزاد {saved.number}.")
            if from_list:
                return redirect("console:auctions")
            return redirect("console:auction-detail", pk=pk)
        if from_list:
            for field, errors in form.errors.items():
                label = form.fields[field].label if field in form.fields else field
                messages.error(request, f"{label}: {' · '.join(errors)}")
            return redirect("console:auctions")

    return render(
        request,
        "console/auction_form.html",
        {"form": form, "auction": auction},
    )


@console_page("console:vehicle-new")
def vehicle_new(request):
    """A new car, born `draft` and listed only through the service.

    والزخرفةُ فوقها ليست تفصيلاً: سقطت في فرعٍ آخر، فصارت الصفحة **بلا حارسٍ
    إطلاقاً** — يفتحها أيُّ حسابٍ داخل، ويقبل `POST` منه، بما فيه حسابُ شركةٍ
    شريكة. وأمسكها `test_no_console_page_answers_a_partner` بـ200 مكان 403.
    وذلك بعينه ما بُني له `every_capability_guards_something`: صفحةٌ في السجلّ
    بقدرةٍ لا تحرسها الشيفرة هي صفحةٌ مفتوحة.
    """
    is_modal, base_template = _modal(request)

    # المزادُ الحاليُّ يأتي في `?auction=` حين تُفتح الإضافةُ من داخل صفحة
    # مزادٍ بعينه (زرُّ «إضافة مركبة» هناك)، فيُملأ به الحقلُ سلفاً — والموظّفُ
    # في مزاد ١٠٠٢ يضيف إليه لا يبحث عنه في قائمةٍ من خمسمئة. ويبقى الحقلُ
    # قابلاً للتغيير: إضافةٌ عامّةٌ من «مركبة جديدة» حالةٌ قائمة أيضاً.
    scope = request.GET.get("auction", "")
    scoped_auction = (
        Auction.objects.filter(pk=int(scope)).first() if scope.isdigit() else None
    )
    initial = {"auction": scoped_auction.pk} if scoped_auction else {}
    form = VehicleForm(request.POST or None, initial=initial)

    if request.method == "POST":
        vehicle = _save(
            request, form, action="console.create_vehicle", fields=VEHICLE_FIELDS
        )
        if vehicle is not None:
            messages.success(request, f"أُنشئت المركبة (لوت {vehicle.lot_number}).")
            # نافذةٌ حفظت: تُغلَق ويُعاد تحميلُ جدول المزاد خلفها (٢٠٤ كالتعديل).
            # والطلبُ المباشر يعود إلى صفحة مزاد المركبة لتُرى في سياقها، لا إلى
            # صفحةِ مركبةٍ مفردةٍ تُخرج الموظّفَ من المزاد الذي يبنيه.
            if is_modal:
                from django.http import HttpResponse

                return HttpResponse(status=204)
            return redirect("console:auction-detail", pk=vehicle.auction_id)

    return render(
        request,
        "console/vehicle_form.html",
        {"form": form, "vehicle": None, "base_template": base_template},
    )


@console_page("console:vehicle-edit")
def vehicle_edit(request, pk: int):
    """Edit a car's facts. Its state and its award are not among them.

    An award typed by hand is an award with no bid behind it and no money moved
    for it; correcting one is `bidding.settlement.replace_winner`, which moves
    the invoice and the deposit with it.
    """
    vehicle = get_object_or_404(Vehicle.objects.all(), pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)
    is_modal, base_template = _modal(request)

    if request.method == "POST":
        saved = _save(
            request,
            form,
            action="console.edit_vehicle",
            fields=VEHICLE_FIELDS,
            instance=Vehicle.objects.get(pk=pk),
        )
        if saved is not None:
            messages.success(request, "حُفظت التعديلات.")
            # نافذةٌ حفظت بنجاح: تُغلَق ويُعاد تحميلُ الجدول خلفها. الـview
            # يقول ذلك بـ204 (لا محتوى) بدل توجيهٍ إلى صفحةٍ كاملة تُبتلع في
            # `<dialog>`. والطلبُ المباشر يبقى توجيهاً.
            if is_modal:
                from django.http import HttpResponse

                return HttpResponse(status=204)
            return redirect("console:vehicle-detail", pk=pk)

    return render(
        request,
        "console/vehicle_form.html",
        {"form": form, "vehicle": vehicle, "base_template": base_template},
    )
