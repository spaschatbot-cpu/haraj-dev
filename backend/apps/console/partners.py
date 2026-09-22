"""Partner decisions and choosing an offer. T807.

The screen v1 had no equivalent of. There, a car whose highest bid fell below
the reserve simply sat in the vehicle list in lot order, and the partner was
told about it by telephone — so "which cars are waiting on a decision?" was
answered by somebody scrolling.

Three things this screen does that the vehicle list cannot:

* **Orders by situation, not by lot.** A car waiting on its owner is at the top
  because nobody is being paid for it while it waits.
* **Shows every bidder, not the top one.** A partner refusing 45,000 usually
  wants to know what the second offer was. In v1 that meant a database query.
* **Awards to any of them in one click.** The partner's answer is often "take
  the second one" — and there was no way to do that at all, so an operator
  cancelled the auction and relisted the car.

**The accepted offer is shown, never the highest.** Once a car is awarded, the
number on this screen is what it was awarded for. In v1 the screen recomputed
the maximum bid every time it rendered, so a car awarded to the second bidder
displayed the first bidder's number — and that number went into the invoice
conversation.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import (
    Case,
    Count,
    IntegerField,
    Max,
    OuterRef,
    Subquery,
    Value,
    When,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import urlencode

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.auctions.states import VehicleState
from apps.bidding import settlement
from apps.bidding.models import Bid
from apps.core import audit
from apps.money import services as money
from apps.money.models import ZERO

from .archive import ARCHIVED
from .exports import export, wants_export
from .partner_console import _scoped
from .icons import path_of
from .tones import with_tones
from .views import console_page

#: The states a partner decision is actually pending on. `awarded` is here
#: because an award can still be moved to another bidder (T510) — a partner who
#: changes their mind after the fact is a real Tuesday, and v1's answer was to
#: cancel the whole auction.
DECIDABLE = (VehicleState.AWAITING_DECISION, VehicleState.AWARDED)


@console_page("console:partner-decisions")
def decisions(request):
    """Cars waiting on a partner, oldest wait first.

    Sorted by how long the car has been waiting rather than by lot number: the
    question this page answers is "what has been sitting the longest", and a lot
    number answers nothing about that.
    """
    # **النطاقُ نطاقُ v1: كلُّ مركبةٍ في مزادٍ منتهٍ.** كان `state__in=DECIDABLE`
    # — ثلاثةُ صفوفٍ من تسعة على قاعدة التطوير — فتُخفى عن الشريك مركباتٌ
    # انتهى مزادُها ولم يزايد عليها أحد. وتلك بالضبط ما يحتاج أن يحكم فيها
    # بالرفض: `rejectVehicle` في v1 لها حالةٌ خاصّة «لا عروضَ قائمة — يُسجَّل
    # الرفض» كي تتوقّف شاشةُ المالك عن انتظاره.
    #
    # ولا يُحذف الترتيبُ بالإلحاح، بل يصير **ثانياً** بعد اللوط.
    rows = (
        Vehicle.objects.filter(auction__state__in=ARCHIVED)
        .select_related("auction", "owner_company", "awarded_to")
        .annotate(
            urgency=Case(
                When(state=VehicleState.AWAITING_DECISION, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            bidders=Count("bids__bidder", distinct=True),
            top_amount=Max("bids__amount"),
            top_bidder=Subquery(
                Bid.objects.live()
                .filter(vehicle=OuterRef("pk"))
                .order_by("-amount", "placed_at")
                .values("bidder__full_name")[:1]
            ),
        )
        # **الترتيبُ برقم اللوط.** قاله مالكُ v1 في ٢٠٢٦-٠٨-٢٢: «الشريك يمشي في
        # الحوش بالترتيب، فالصفحة تُقرأ بجانب السيارات». وفي v1 العمودُ نصّيٌّ
        # فترتيبُه النصّيّ يعطي ١٤ ثم ١٤٩ ثم ١٥٧ ثم ٣٤ ثم ٨ — ترتيبٌ لا يقابل
        # شيئاً على الأرض. وهنا العمودُ عدديٌّ أصلاً فالمشكلةُ لا تنشأ.
        .order_by("auction__number", "lot_number", "urgency")
    )

    # **ونطاقُها الشركاءُ وحدَهم.** كان الترشيحُ بالشريك يقع فقط حين يُمرَّر
    # `?partner=`، فتعرض شاشةٌ اسمُها «اتخاذ القرار للشريك» كلَّ مركبةٍ في
    # مزادٍ منتهٍ — ومنها سياراتُ الشركة نفسِها التي لا شريكَ لها. قِيس على
    # سيرفر التجربة: البطاقاتُ تقول **١٢٬٩٦٣** مركبةً في **٥٤** مزاداً،
    # وv1 على البيانات نفسِها يقول مئاتٍ في مزادين — لأن نطاقَه علمٌ على
    # الصفّ (`av.is_marketing = 1`). والنظيرُ هنا `_scoped`: شريكٌ بعينه إن
    # اختير، وإلّا **كلُّ من له شركة** لا كلُّ شيء.
    partner = request.GET.get("partner")
    rows = _scoped(rows, partner or "")

    # ترشيحٌ على مزادٍ واحد — البابُ الذي يفتحه زرُّ «مراجعة العروض» من صفّ
    # المزاد. T860
    #
    # وv1 يبني لهذا **نافذةً ثانية** بجلبٍ خاصّ وقائمةٍ خاصّة وزرَّي موافقةٍ
    # ورفض مكتوبين فيها من جديد. فصار للقرار الواحد مساران: نافذةُ الصفّ
    # وشاشةُ القرارات — وأحدهما لا يعرف بالآخر. وهنا شرطٌ واحد على الاستعلام
    # نفسه: الشاشةُ هي هي، بأزرارها وبوّابتها وسجلِّ تدقيقها، مضيَّقةً.
    auction = request.GET.get("auction")
    auction_row = None
    if auction and auction.isdigit():
        rows = rows.filter(auction_id=int(auction))
        auction_row = Auction.objects.filter(pk=int(auction)).first()

    if wants_export(request):
        return export(
            rows,
            name="partner-decisions",
            headers=[
                "المزاد",
                "الموقف",
                "السيارة",
                "اللوحة",
                "رقم المطالبة",
                "المبلغ المعتمد",
                "شامل الضريبة",
                "عدد المزايدين",
                "القرار",
                "تاريخ القرار",
                "الشريك",
            ],
            cell=lambda v: [
                v.auction.number,
                v.lot_number,
                f"{v.make} {v.model} {v.year}",
                v.plate_number or "",
                v.claim_number or "",
                v.awarded_price or v.top_amount,
                money.tax_added_to(v.awarded_price or v.top_amount).total
                if (v.awarded_price or v.top_amount)
                else None,
                v.bidders,
                v.get_partner_decision_display()
                if v.partner_decided_at
                else "بانتظار قراره",
                v.partner_decided_at,
                v.partner_name,
            ],
        )

    cars = list(rows)
    with_tones(cars)

    # **صورةُ المركبة — عمودُ v1 الثالث.** استعلامٌ واحدٌ للصفحة: الغلافُ
    # أوّلاً ثم أوّلُ صورةٍ بالترتيب.
    covers: dict[int, object] = {}
    for shot in VehicleImage.objects.filter(vehicle__in=cars).order_by(
        "vehicle_id", "-is_cover", "position", "id"
    ):
        covers.setdefault(shot.vehicle_id, shot)

    # **«شامل الضريبة» جنبَ المبلغ — عمودُ v1.** والمبلغُ هو المعتمَد: ما
    # رستْ به إن رستْ، وإلّا أعلى عرضٍ قائم. ولا تُضرب النسبةُ هنا:
    # `money.tax_added_to` هي الموضعُ الوحيد الذي يضرب في المشروع.
    for vehicle in cars:
        amount = vehicle.awarded_price or vehicle.top_amount
        vehicle.amount_with_vat = money.tax_added_to(amount).total if amount else None
        vehicle.cover = covers.get(vehicle.pk)

    return render(
        request,
        "console/partner_decisions.html",
        {
            "groups": _group_by_auction(cars),
            "total": len(cars),
            # **ثلاثةُ أرقامِ v1 فوق الصفحة**: كم ينتظر قراراً، وكم سيارةً في
            # مزاداتٍ منتهية، وفي كم مزاد. وهي على **الطابور كلِّه** لا على
            # الصفحة — من يسأل «كم بقي عليّ» يسأل عن الكلّ.
            "kpi": {
                "pending": rows.filter(partner_decided_at__isnull=True).count(),
                "vehicles": rows.count(),
                "auctions": rows.values("auction").distinct().count(),
            },
            "partner": partner or "",
            # نسبةُ الضريبة في رأس العمود كـ v1 — تُقرأ من `money` لا تُكتب
            # رقماً في القالب: النسبةُ تتغيّر بقرارٍ حكوميّ، ورقمٌ مكتوبٌ في
            # قالبٍ يبقى ١٥٪ بعد أن يصير غيرَه.
            "vat_label": f"{(money.vat_rate() * 100).normalize()}%",
            "auction_filter": auction_row,
            # المرشّحاتُ كما هي، ليعود إليها بعد كلّ حكم: الشريك يحكم على
            # أربعين مركبةً في مزادٍ واحد، وعودةٌ إلى الصفحة عاريةً تعني بحثاً
            # جديداً بعد كلّ واحدة.
            "filters": urlencode(
                {
                    "partner": partner or "",
                    "auction": request.GET.get("auction", ""),
                }
            ),
            # رسومُ الحكم — من `icons.py` لا إيموجي (T837). والقبولُ والرفضُ
            # فعلان لا رجعةَ لهما في الشاشة، فيُقرآن بالرسم قبل النصّ: العينُ
            # تلتقط «✓» و«⃠» أسرعَ من كلمتين متجاورتين بالطول نفسه.
            "icon_export": path_of("download"),
            "icon_yes": path_of("check"),
            "icon_no": path_of("ban"),
            "icon_offers": path_of("eye"),
            "icon_detail": path_of("file"),
            "icon_bids": path_of("users"),
        },
    )


def _group_by_auction(vehicles) -> list[dict]:
    """اجمع صفوفَ الصفحة تحت مزاداتها، ومع كلٍّ إحصاؤه — تجميعُ v1.

    **ولماذا تجميعٌ وقد كان جدولاً مسطّحاً يقول الشيءَ نفسَه.** لأن القرار
    يُتّخذ **بالمزاد لا بالسيارة**: الشريك يفتح الصفحةَ بعد أن يُقفل مزادٌ
    بعينه، ويريد أن يعرف «كم بقي عليّ في هذا المزاد» — وهو رقمٌ لا يقوله جدولٌ
    مسطّحٌ إلا بالعدّ باليد. وv1 يجمعها كذلك ويضع تحت كلّ مزادٍ عدّادَه.

    والتجميعُ على **صفوف الصفحة المعروضة** لا على الاستعلام كلِّه: الترتيبُ
    بالمزاد ثم اللوط يجعل مزاداً واحداً متّصلاً، وصفحةٌ قد تقطعه — وذلك مقبول،
    أمّا استعلامٌ ثانٍ ليجمع فلا.
    """
    groups: list[dict] = []
    for vehicle in vehicles:
        if not groups or groups[-1]["auction"].pk != vehicle.auction_id:
            groups.append(
                {
                    "auction": vehicle.auction,
                    "rows": [],
                    "pending": 0,
                    # إحصاءُ رأس المجموعة في v1: معلّق · مقبول · مرفوض،
                    # ومجموعُ ما شملَ الضريبة. وثلاثةُ أعدادٍ تقول أين وصل
                    # المزادُ بنظرةٍ — والواحدُ («ينتظر قرارَه N») يقول ما بقي
                    # ولا يقول ماذا جرى.
                    "accepted": 0,
                    "rejected": 0,
                    "sum_net": ZERO,
                    "sum_vat": ZERO,
                }
            )
        group = groups[-1]
        group["rows"].append(vehicle)
        if vehicle.partner_decided_at is None:
            group["pending"] += 1
        elif vehicle.partner_decision == "accepted":
            group["accepted"] += 1
        else:
            group["rejected"] += 1
        group["sum_net"] += vehicle.awarded_price or vehicle.top_amount or ZERO
        group["sum_vat"] += getattr(vehicle, "amount_with_vat", None) or ZERO
    return groups


@console_page("console:partner-decide-many")
def decide_many(request):
    """اقبل أو ارفض **المحدَّد** — أزرارُ v1 الجماعيّة فوق الجدول.

    الشريكُ يحكم على أربعين مركبةً بعد كلّ مزاد. وv1 يضع فوق الجدول «قبول
    المحدَّد» و«رفض المحدَّد» ومربّعَ تحديدٍ في كلّ صفّ، ورأسَ عمودٍ يحدّد
    مزاداً كاملاً — وبدونها أربعون نقرةً وأربعون إعادةَ تحميل.

    **وكلُّ مركبةٍ تمرّ بالبابِ المفردِ نفسِه** (`award_top` و`reject`)، لا
    بمسارٍ ثانٍ يكتب في القاعدة: شرطٌ يُفحص في أحدهما ويُنسى في الآخر هو كيف
    تُرسى مركبةٌ في مزادٍ لم ينتهِ. فالجماعيُّ حلقةٌ على المفرد.

    **ولا معاملةٌ واحدةٌ تضمّ الأربعين.** فشلُ المركبة السابعة لا يُلغي ستّاً
    صحيحة — والشريكُ الذي ضغط «قبول» على أربعين يريد التسعةَ والثلاثين التي
    تمرّ، ويريد أن يُقال له أيُّها لم تمرّ ولماذا. وv1 يفعلها كذلك (`Promise`
    لكلّ صفّ).

    والحصيلةُ سطرٌ واحد: كم مرّ وكم رُدّ ولماذا رُدَّ أوّلُها.
    """
    back = redirect(_back(request))
    if request.method != "POST":
        return back

    action = (request.POST.get("op") or "").strip()
    if action not in ("accept", "reject"):
        messages.error(request, "فعلٌ غير معروف.")
        return back

    pks = [p for p in request.POST.getlist("pick") if p.isdigit()]
    if not pks:
        messages.error(request, "لم تُحدَّد مركبة.")
        return back

    rows = Vehicle.objects.select_related("auction").filter(pk__in=pks)
    done, failed, first_why = 0, 0, ""
    for vehicle in rows:
        try:
            if action == "accept":
                _award_top_one(vehicle, request.user)
            else:
                _reject_one(vehicle, request.user)
            done += 1
        except Exception as refusal:
            failed += 1
            first_why = first_why or f"{vehicle.lot_number}: {refusal}"

    word = "قُبلت" if action == "accept" else "رُفضت"
    if done:
        messages.success(request, f"{word} {done} مركبة.")
    if failed:
        messages.error(request, f"وردّت {failed} — أوّلُها {first_why}")
    return back


def _award_top_one(vehicle, actor) -> None:
    """قبولُ أعلى عرضٍ على مركبةٍ واحدة — جسمُ `award_top` بلا طلبٍ ولا رسائل."""
    top = (
        Bid.objects.live()
        .filter(vehicle=vehicle)
        .order_by("-amount", "placed_at")
        .first()
    )
    if top is None:
        raise ValueError("لا عرضَ قائمٌ عليها — الرفضُ هو القرار")

    before = audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"])
    # **الختمُ قبل النقلة، والاثنان في معاملةٍ واحدة.** كان العكس، وكانت
    # الشاشةُ لا تحكم على شيء: `move_vehicle` تسأل `partner_lock_reason`
    # فتجد `partner_decided_at` خالياً فترفض بـ«هذه السيارة للتسويق
    # وبانتظار قرار التعاونية» — والشاشةُ **هي** موضعُ قرار الشريك. قِيس
    # على سيرفر التجربة: «وردّت ٢ — أوّلُها 1: هذه السيارة للتسويق…».
    #
    # والمعاملةُ تجمعهما لأن ختماً بلا نقلةٍ حكمٌ مسجَّلٌ على مركبةٍ لم
    # تتحرّك، ولا يُختَم مرّةً ثانيةً بعده.
    with transaction.atomic():
        _stamp(vehicle, "accepted", top, actor)
        settlement.award_to(vehicle, bidder=top.bidder, price=top.amount)
    vehicle.refresh_from_db()
    audit.record(
        action="console.award_vehicle",
        entity=vehicle,
        actor=actor,
        before=before,
        after=audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"]),
        note="قبول أعلى عرض — فعلٌ جماعيّ من شاشة القرار",
    )
    settlement.try_close(vehicle.auction)


def _reject_one(vehicle, actor) -> None:
    """رفضُ مركبةٍ واحدة — جسمُ `reject` بلا طلبٍ ولا رسائل."""
    from apps.auctions.services import reject as reject_vehicle

    before = audit.snapshot(vehicle, ["state"])
    # **الختمُ قبل النقلة، والاثنان في معاملةٍ واحدة.** كان العكس، وكانت
    # الشاشةُ لا تحكم على شيء: `move_vehicle` تسأل `partner_lock_reason`
    # فتجد `partner_decided_at` خالياً فترفض بـ«هذه السيارة للتسويق
    # وبانتظار قرار التعاونية» — والشاشةُ **هي** موضعُ قرار الشريك. قِيس
    # على سيرفر التجربة: «وردّت ٢ — أوّلُها 1: هذه السيارة للتسويق…».
    #
    # والمعاملةُ تجمعهما لأن ختماً بلا نقلةٍ حكمٌ مسجَّلٌ على مركبةٍ لم
    # تتحرّك، ولا يُختَم مرّةً ثانيةً بعده.
    with transaction.atomic():
        _stamp(vehicle, "rejected", None, actor)
        reject_vehicle(vehicle)
    vehicle.refresh_from_db()
    audit.record(
        action="console.reject_vehicle",
        entity=vehicle,
        actor=actor,
        before=before,
        after=audit.snapshot(vehicle, ["state"]),
        note="رفض — فعلٌ جماعيّ من شاشة القرار",
    )


@console_page("console:partner-award-top")
def award_top(request, pk: int):
    """اقبل **أعلى عرضٍ قائم** على المركبة من صفّها — زرُّ v1 في الجدول.

    v1 يضع القبولَ والرفضَ في الصفّ نفسِه، وهنا كانا في صفحةٍ ثانيةٍ لكلّ
    مركبة. والفرق ليس نقرةً: الشريك يحكم على أربعين سيارةً بعد كلّ مزاد،
    فأربعون فتحةَ صفحةٍ ورجوعاً تجعل الشاشةَ قائمةَ عرضٍ لا شاشةَ قرار — وهو
    ما قرأه المالكُ حين قال إنها «تفتح صفحة كل سياراتي».

    **وأعلى عرضٍ لا عرضٌ يُختار**: الاختيار بين المزايدين يبقى في صفحة العروض
    حيث يُرى الثاني والثالث. وهذا الزرُّ للحالة الغالبة — «خذ الأعلى» — ويردّ
    من لا عرضَ له إلى الرفض.
    """
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)
    if request.method != "POST":
        return redirect("console:partner-decisions")

    top = (
        Bid.objects.live()
        .filter(vehicle=vehicle)
        .order_by("-amount", "placed_at")
        .first()
    )
    if top is None:
        messages.error(request, "لا عرضَ قائمٌ على هذه المركبة — الرفضُ هو القرار.")
        return redirect(_back(request))

    before = audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"])
    # **الختمُ قبل النقلة، والاثنان في معاملةٍ واحدة.** كان العكس، وكانت
    # الشاشةُ لا تحكم على شيء: `move_vehicle` تسأل `partner_lock_reason`
    # فتجد `partner_decided_at` خالياً فترفض بـ«هذه السيارة للتسويق
    # وبانتظار قرار التعاونية» — والشاشةُ **هي** موضعُ قرار الشريك. قِيس
    # على سيرفر التجربة: «وردّت ٢ — أوّلُها 1: هذه السيارة للتسويق…».
    #
    # والمعاملةُ تجمعهما لأن ختماً بلا نقلةٍ حكمٌ مسجَّلٌ على مركبةٍ لم
    # تتحرّك، ولا يُختَم مرّةً ثانيةً بعده.
    try:
        with transaction.atomic():
            _stamp(vehicle, "accepted", top, request.user)
            settlement.award_to(vehicle, bidder=top.bidder, price=top.amount)
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect(_back(request))

    vehicle.refresh_from_db()
    audit.record(
        action="console.award_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"]),
        note="قبول أعلى عرض من شاشة القرار",
    )
    settlement.try_close(vehicle.auction)
    messages.success(request, f"رست على {top.bidder.full_name} بمبلغ {top.amount}.")
    return redirect(_back(request))


def _stamp(vehicle, decision: str, bid, actor) -> None:
    """اختم قرارَ الشريك على المركبة — نظيرُ `stampDecision` في v1.

    وبلا هذا الختم لا تعرف شاشةُ المالك أن الشريك حكم، فتبقى تنتظره على مركبةٍ
    حُسم أمرُها. وv1 يختمه في `partner_decided_at` ويقرؤه في شاشة قراره.

    **ويمرّ بالخدمة لا يكتب الأعمدة بيده** حين تكون المركبةُ للتسويق:
    `record_partner_ruling` تقفل الصفَّ وترفض ختماً ثانياً («الحكمُ الأوّل
    يبقى») وترفض الحكمَ قبل انتهاء المزاد. وكتابةٌ مباشرةٌ هنا تتخطّى
    الثلاثة، وتترك ضغطتين متتاليتين تكتبان حكمين.

    والمركبةُ التي ليست للتسويق لا شريكَ لها يحكم، فالخدمةُ ترفضها بحقّ —
    ويبقى العمودُ ختماً لمن حسم من هذه الشاشة، فيُكتب هنا.
    """
    from apps.auctions.services import record_partner_ruling

    if vehicle.is_marketing:
        record_partner_ruling(
            vehicle,
            decision=decision,
            actor=actor if getattr(actor, "pk", None) else None,
            bid=bid,
        )
        return

    vehicle.partner_decision = decision
    vehicle.partner_decided_at = timezone.now()
    vehicle.partner_decided_by = actor if getattr(actor, "pk", None) else None
    vehicle.partner_decision_bid = bid
    vehicle.save(
        update_fields=[
            "partner_decision",
            "partner_decided_at",
            "partner_decided_by",
            "partner_decision_bid",
        ]
    )


def _back(request) -> str:
    """يعود إلى شاشة القرار بمرشّحاتها — لا إلى رأسها."""
    query = request.POST.get("back", "")
    return f"/console/partners/?{query}" if query else "/console/partners/"


def _back_or_offers(request, pk: int) -> str:
    """إلى الشاشة التي أُرسلت منها الاستمارة، وإلّا إلى صفحة العروض."""
    query = (request.POST.get("back") or "").strip()
    return f"/console/partners/?{query}" if query else f"/console/partners/{pk}/"


@console_page("console:partner-offers")
def offers(request, pk: int):
    """Every live bid on one car, highest first, with the accepted one marked.

    The accepted offer is read off the award, not recomputed. A car awarded to
    the second bidder must not display the first bidder's number — in v1 it did,
    and that number reached the invoice conversation.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company", "awarded_to"), pk=pk
    )

    bids = (
        Bid.objects.live()
        .filter(vehicle=vehicle)
        .select_related("bidder")
        .order_by("-amount", "placed_at")
    )

    # **قطعةٌ للنافذة، أو الصفحةُ كاملة — من العرض نفسِه.** T966
    #
    # طلبُ المالك: «قائمة المزايدين عايزها بوباب يعرض قائمة المزايدين بس».
    # وقالبٌ ثانٍ يقرأ استعلاماً ثانياً كان سيتفارق مع الصفحة عند أوّل إصلاح
    # — وهو عطلُ T922 بعينه. فالاستعلامُ واحدٌ والقالبان وجهان له.
    from .sensitive import shown_to

    seen = shown_to(request.user)
    modal = request.GET.get("modal") == "1" or request.headers.get(
        "X-Requested-With"
    ) == "fetch"

    return render(
        request,
        "console/_partner_offers_modal.html" if modal else "console/partner_offers.html",
        {
            "vehicle": vehicle,
            "bids": bids,
            "show_money": seen.money,
            "show_customer": seen.customer,
            # The number the partner is being asked about. Absent until there
            # is an award — an unawarded car has no accepted offer, and showing
            # the highest bid in that slot is exactly the v1 confusion.
            "accepted": vehicle.awarded_price,
            # **الرجوعُ إلى من فتح النافذة.** كانت الترسيةُ تردّ دائماً إلى
            # صفحة العروض، فمن رسَّ من نافذةٍ في «اتخاذ القرار» خرج من
            # الشاشة ومن مرشّحاتها ومن موضعه في أربعين صفّاً — وهو بعينه ما
            # فُتحت النافذةُ لتمنعه.
            "back": request.GET.get("back", ""),
            "reserve_met": [
                bid
                for bid in bids
                if vehicle.reserve_price is None or bid.amount >= vehicle.reserve_price
            ],
        },
    )


@console_page("console:partner-award")
def award(request, pk: int):
    """Award the car to a chosen bidder, or move an award to another.

    One entry point for both, because they are the same decision made at two
    moments and the money differs: awarding fresh is a settlement move, moving
    an existing award is `replace_winner`, which cancels the first invoice and
    frees the first winner's lock in the same transaction.

    Choosing which of the two to call is this view's only decision, and it reads
    it off the car rather than off the form — a form field saying "this is a
    replacement" is a form field somebody sets wrongly.
    """
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)

    if request.method != "POST":
        return redirect("console:partner-offers", pk=pk)

    reason = (request.POST.get("reason") or "").strip()

    bid = Bid.objects.live().filter(pk=request.POST.get("bid"), vehicle=vehicle).first()
    if bid is None:
        messages.error(request, "المزايدة المختارة لم تعد قائمة.")
        return redirect("console:partner-offers", pk=pk)

    # **والسببُ يُركَّب من الواقعة حين لا يُكتب.** خانةُ السبب شيلت من نافذة
    # المزايدين بقرار المالكة، وv1 بلا خانةٍ أصلاً. و`replace_winner` تشترط
    # `reason` لأن «ترسيةً نُقلت بلا سببٍ مسجَّل صفٌّ لا يُشرح لأيّ من
    # العميلين» — والجملةُ المركَّبةُ هنا تقول مَن ومَن وبكم، وهي أصدقُ
    # ممّا يُكتب بعجلةٍ في خانةٍ ضيّقة.
    if not reason and vehicle.awarded_to_id and vehicle.awarded_to_id != bid.bidder_id:
        was = vehicle.awarded_to.full_name if vehicle.awarded_to else "—"
        reason = (
            f"نُقلت الترسيةُ من {was} ({vehicle.awarded_price}) "
            f"إلى {bid.bidder.full_name} ({bid.amount}) من قائمة المزايدين."
        )

    before = audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"])

    try:
        with transaction.atomic():
            # **الختمُ قبل الترسية، كما في `award_top`.** كان هذا البابُ بلا
            # ختمٍ أصلاً، فالقبولُ من نافذة المزايدين على سيارة شريكٍ يردّه
            # `partner_lock_reason` بـ«هذه السيارة للتسويق وبانتظار قرار
            # التعاونية» — والنافذةُ هي بابُ اختيار العرض الثاني، أي أنّ
            # «أرسِ على غير الأعلى» كان لا يعمل على سيارات الشريك كلِّها.
            #
            # ولا يُختَم مرّتين: نقلُ ترسيةٍ قائمةٍ حكمٌ ثانٍ على مركبةٍ حُكم
            # فيها، و`record_partner_ruling` ترفضه — فيُسأل عن الختم قبله.
            if vehicle.partner_decided_at is None:
                _stamp(vehicle, "accepted", bid, request.user)
            if vehicle.awarded_to_id is None:
                settlement.award_to(vehicle, bidder=bid.bidder, price=bid.amount)
            else:
                settlement.replace_winner(
                    vehicle, new_winner=bid.bidder, price=bid.amount, reason=reason
                )
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect(_back_or_offers(request, pk))

    vehicle.refresh_from_db()
    audit.record(
        action="console.award_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state", "awarded_to_id", "awarded_price"]),
        note=reason,
    )
    # قرارٌ على مركبةٍ قد يكون آخرَ ما كان ينتظره المزاد — فيُسأل عن الإغلاق
    # هنا، لا في استطلاعٍ يمرّ على كل مزادٍ منتهٍ كلَّ دقيقة. والدالةُ تصمت إن
    # بقي غيرُها.
    settlement.try_close(vehicle.auction)
    messages.success(request, f"رست على {bid.bidder.full_name} بمبلغ {bid.amount}.")
    return redirect(_back_or_offers(request, pk))


@console_page("console:partner-reject")
def reject(request, pk: int):
    """The partner refused every offer. The car is rejected, not withdrawn.

    Two different facts, and v1 lost the distinction: "nobody offered enough"
    and "the owner pulled it" have opposite next steps — the first goes back
    into a later cycle, the second does not.
    """
    vehicle = get_object_or_404(Vehicle.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:partner-offers", pk=pk)

    reason = (request.POST.get("reason") or "").strip()

    from apps.auctions.services import reject as reject_vehicle

    before = audit.snapshot(vehicle, ["state"])
    # **الختمُ قبل النقلة، والاثنان في معاملةٍ واحدة.** كان العكس، وكانت
    # الشاشةُ لا تحكم على شيء: `move_vehicle` تسأل `partner_lock_reason`
    # فتجد `partner_decided_at` خالياً فترفض بـ«هذه السيارة للتسويق
    # وبانتظار قرار التعاونية» — والشاشةُ **هي** موضعُ قرار الشريك. قِيس
    # على سيرفر التجربة: «وردّت ٢ — أوّلُها 1: هذه السيارة للتسويق…».
    #
    # والمعاملةُ تجمعهما لأن ختماً بلا نقلةٍ حكمٌ مسجَّلٌ على مركبةٍ لم
    # تتحرّك، ولا يُختَم مرّةً ثانيةً بعده.
    try:
        with transaction.atomic():
            # v1 يختم الرفضَ حتى حين **لا عرضَ قائمٌ أصلاً**: «لا توجد عروض —
            # تم تسجيل الرفض»، لأن الشريك حكم وإن لم يكن ثمّ ما يُرفض.
            _stamp(vehicle, "rejected", None, request.user)
            reject_vehicle(vehicle)
    except Exception as refusal:
        messages.error(request, str(refusal))
        return redirect(_back_or_offers(request, pk))

    vehicle.refresh_from_db()
    audit.record(
        action="console.reject_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(vehicle, ["state"]),
        note=reason,
    )
    # قرارٌ على مركبةٍ قد يكون آخرَ ما كان ينتظره المزاد — فيُسأل عن الإغلاق
    # هنا، لا في استطلاعٍ يمرّ على كل مزادٍ منتهٍ كلَّ دقيقة. والدالةُ تصمت إن
    # بقي غيرُها.
    settlement.try_close(vehicle.auction)
    messages.success(request, "سُجّل الرفض.")
    asked_back = request.POST.get("back") is not None
    return redirect(_back(request) if asked_back else f"/console/partners/{pk}/")


def _amount(raw: str) -> Decimal | None:
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return None


__all__ = ["DECIDABLE", "award", "decisions", "offers", "reject"]
