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

from apps.auctions import cards, engine
from apps.auctions import services as auction_services
from apps.auctions.listing import MAX_PAGE_SIZE, with_vehicle_counts
from apps.auctions.models import Auction, Showcase, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.auctions.visibility import visible_vehicles
from apps.core import audit
from apps.core.permissions import Capability, can

from . import icons
from .exports import export, wants_export
from .forms import AuctionForm, VehicleForm
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
ACTIONS = (
    ("cars", "سياراته", "car"),
    ("bids", "مزايداته", "gavel"),
    ("export", "تصدير سياراته", "file-excel"),
    ("fees", "الرسوم والتأمين", "coins"),
    ("reschedule", "إعادة جدولة", "calendar-clock"),
    ("end", "إنهاء فوري", "trash"),
    ("edit", "تعديل", "pencil"),
)


COLUMNS = (
    ("id", "الرقم"),
    ("auction", "المزاد"),
    ("preview", "المعاينة"),
    ("badge", "الحالة"),
    ("window", "الفترة الزمنية"),
    ("cars", "العربيات"),
    ("prices", "الأسعار"),
    ("ready", "التفعيل"),
    ("images", "الصور"),
    ("bids", "المشاركات"),
    ("park", "الموقع"),
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
                "الرقم",
                "المزاد",
                "المرحلة",
                "يبدأ",
                "ينتهي",
                "الموقع",
                "السيارات",
                "الماركات",
                "المعروضة",
                "بسعر مسجّل",
                "أقل سعر وقوف",
                "أعلى سعر وقوف",
                "سيارات لها صور",
                "الصور",
                "المزايدات",
                "المزايدون",
                "أعلى مزايدة",
                "التأمين",
                "الرسوم الإدارية",
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
                summaries[a.pk].with_reserve,
                summaries[a.pk].reserve_low,
                summaries[a.pk].reserve_high,
                summaries[a.pk].cars_with_images,
                summaries[a.pk].images,
                summaries[a.pk].bids,
                summaries[a.pk].bidders,
                summaries[a.pk].top_bid,
                a.deposit_required,
                a.admin_fee,
            ],
        )

    page = _page(request, rows)
    with_tones(page.object_list)
    # المرحلةُ على كل صفّ — بلا استعلامٍ إضافي (T843). القائمةُ كانت تعرض
    # العمود وحده، فمزادٌ انتهى وقتُه ولم يُغلَق يُقرأ «جارياً» في الصفّ الذي
    # يُفتَح منه، وهو الصفّ الذي يجب أن يُفتَح **أولاً**.
    engine.phases_of(page.object_list)
    for row in page.object_list:
        row.phase_tone = tone_of_phase(row.phase)
        # البادج بمفردات v1 الخمس، محسوباً من الحالة والساعة واللافتة.
        row.badge = engine.badge_of(row)
        row.badge_label = engine.Badge(row.badge).label
        row.badge_tone = engine.BADGE_TONES.get(row.badge, "")
    # أعمدةُ v1 كما طلبها المالك: «عايز نفس الحقول». أربعةُ استعلاماتٍ
    # مجمَّعة لصفوف **الصفحة** وحدها — وv1 كان يحسبها للمزادات كلّها في كل
    # تحميل، ثم يعدّ المزايدات المسحوبة ضمن النشاط.
    engine.summarise_onto(page.object_list)

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
            "showcases": Showcase.choices,
        },
    )


@console_page("console:auction-detail")
def auction_detail(request, pk: int):
    """المزاد كمُجمَّع: سياراتُه، ومن دخله وبأيّ تأمين، وما يجوز فعله به.

    المالك بالحرف: «مزاد مجمع وداخله مجموعة من السيارات… المزاد الواحد مطلوب
    عشان المشاركة فيه تأمين واحد للمزايدة فيه حتى لو هيزايد على كل السيارات
    اللي فيه… فواتير المزاد الواحد تتربط برده بنفس التأمين بتاعه».

    وهذه الشاشة هي المكان الذي يُرى فيه ذلك: صفٌّ لكل مشارك، فيه **تأمينٌ
    واحد** مهما بلغ عدد سياراته، وتحته سياراته وفواتيره. وقبل T843 كان
    الجوابُ موجوداً في القاعدة ولا شاشةَ تعرضه: الموظّف يفتح دفتر التأمينات
    ثم قائمة الفواتير ثم يربط بيده.

    ولا شيء هنا يقرّر. المرحلةُ والعمليّاتُ والمشاركون كلُّها من
    :mod:`apps.auctions.engine`، والكتابةُ من ``services`` و``settlement``.
    """
    auction = get_object_or_404(with_vehicle_counts(Auction.objects.all()), pk=pk)

    from django.db.models import Case, IntegerField, Value, When

    cars = (
        Vehicle.objects.filter(auction=auction)
        .select_related("owner_company", "awarded_to")
        .annotate(
            urgency=Case(
                When(state=VehicleState.AWAITING_DECISION, then=Value(0)),
                When(state=VehicleState.AWARDED, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("urgency", "lot_number")
    )

    # لقطةٌ واحدة بدل ستّة أسئلة موزّعة على القالب. والعمليّاتُ تأتي معها
    # محسوبةً من آلة الحالات — وكانت تُبنى هنا بيد، ويُبنى مثلُها في
    # `bulk.py` بشرطٍ مختلف.
    view = engine.snapshot(auction)
    page = _page(request, cars)
    with_tones(page.object_list)

    return render(
        request,
        "console/auction_detail.html",
        {
            "auction": auction,
            "page": page,
            "view": view,
            # النغمةُ تُحسب هنا لا في القالب: `tones.with_tones` يقول لماذا —
            # قالبٌ يحسب نغمةً مكانٌ ثانٍ للقاعدة ولا يُختبَر (المادة ٤-٤).
            "phase_tone": tone_of_phase(view.phase),
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

    return render(
        request,
        "console/vehicle_detail.html",
        {
            "vehicle": vehicle,
            "moves": moves,
            "shots": shots,
            "destinations": destinations,
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

    if not reason:
        messages.error(request, "سبب التغيير مطلوب.")
        return redirect("console:vehicle-detail", pk=pk)

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


AUCTION_FIELDS = ["number", "title", "starts_at", "ends_at", "deposit_required"]
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
def auction_new(request):
    """A new auction, born `draft`.

    The state is not a field and not a choice: an auction starts as a draft and
    reaches every other state through `apps.auctions.services`, whose guards
    refuse — among other things — scheduling one with no cars in it.
    """
    form = AuctionForm(request.POST or None)

    if request.method == "POST":
        auction = _save(
            request, form, action="console.create_auction", fields=AUCTION_FIELDS
        )
        if auction is not None:
            messages.success(request, f"أُنشئ المزاد {auction.number}.")
            return redirect("console:auction-detail", pk=auction.pk)

    return render(
        request,
        "console/auction_form.html",
        {"form": form, "auction": None},
    )


@console_page("console:auction-edit")
def auction_edit(request, pk: int):
    auction = get_object_or_404(Auction.objects.all(), pk=pk)
    form = AuctionForm(request.POST or None, instance=auction)

    if request.method == "POST":
        saved = _save(
            request,
            form,
            action="console.edit_auction",
            fields=AUCTION_FIELDS,
            instance=Auction.objects.get(pk=pk),
        )
        if saved is not None:
            messages.success(request, "حُفظت التعديلات.")
            return redirect("console:auction-detail", pk=pk)

    return render(
        request,
        "console/auction_form.html",
        {"form": form, "auction": auction},
    )


@console_page("console:vehicle-new")
def vehicle_new(request):
    """A new car, born `draft` and listed only through the service."""
    form = VehicleForm(request.POST or None)

    if request.method == "POST":
        vehicle = _save(
            request, form, action="console.create_vehicle", fields=VEHICLE_FIELDS
        )
        if vehicle is not None:
            messages.success(request, f"أُنشئت المركبة (لوت {vehicle.lot_number}).")
            return redirect("console:vehicle-detail", pk=vehicle.pk)

    return render(request, "console/vehicle_form.html", {"form": form, "vehicle": None})


@console_page("console:vehicle-edit")
def vehicle_edit(request, pk: int):
    """Edit a car's facts. Its state and its award are not among them.

    An award typed by hand is an award with no bid behind it and no money moved
    for it; correcting one is `bidding.settlement.replace_winner`, which moves
    the invoice and the deposit with it.
    """
    vehicle = get_object_or_404(Vehicle.objects.all(), pk=pk)
    form = VehicleForm(request.POST or None, instance=vehicle)

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
            return redirect("console:vehicle-detail", pk=pk)

    return render(
        request, "console/vehicle_form.html", {"form": form, "vehicle": vehicle}
    )
