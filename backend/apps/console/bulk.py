"""عمليات مجمعة — والرقم الذي بُنيت الشاشة لتمنعه. T830م.

شاشة v1 المقابلة تعرض أربعة أرقام، واثنان منها لا يجتمعان:

    مزادات نشطة        0
    مزايدات نشطة  81,475

**والمزايدة النشطة مزايدةٌ على مزادٍ نشط.** فإمّا أن حالة المزايدة لا تُغلق
حين يُغلق مزادُها، أو أن «نشط» في الجدولين تعني شيئين. والأول هو الأرجح —
لأن الزرَّ الثاني في تلك الشاشة موجودٌ أصلاً:

    «إيقاف جميع المزايدات النشطة — سيتم تحويل حالة كل المزايدات (81,475)
     من active إلى not_active. ⚠ عملية لا يمكن التراجع عنها بسهولة.»

أي أن **الفعل الجماعي وُجد ليُصلح يدوياً ما كان يجب أن يُغلق تلقائياً**. وهو
ليس أداةً — هو عرَض.

ما تفعله هذه الشاشة بدلاً منه
=============================
**١. لا زرَّ «أوقف كل المزايدات».** إنهاءُ المزاد في v2 نقلةٌ في
`auctions.services.end`، وهي تُغلق مزايداته في المعاملة نفسها. وزرٌّ يغلق
المزايدات وحدها يعني أن هناك حالتين للشيء الواحد.

**٢. وعدّادٌ يقول إن ذلك لا يقع.** «مزايدات قائمة على مزادات منتهية» رقمٌ
**يجب أن يكون صفراً دائماً**، وهو معروضٌ في الرأس. وغيرُ الصفر هنا ليس عملاً
جماعياً يُطلَق — هو عطلٌ يُفتَح له تاسك.

**٣. والإنهاء الجماعي يمرّ بالخدمة، مزاداً مزاداً، بسببٍ واحدٍ مكتوب.**
`move_auction` هي الوحيدة التي تكتب حالة مزاد (`ops/checks/
auction_state_single_writer.py`)، وهي التي ترفض النقلة المستحيلة. فالجماعيُّ
هنا حلقةٌ على الفرديِّ لا مسارٌ ثانٍ — وما يُرفض منها يُذكر باسمه.

وv1 يقول «⚠ عملية لا يمكن التراجع عنها بسهولة» ثم ينفّذها بضغطة. وهنا تُطلب
**قائمةٌ مختارة** وسببٌ مكتوب: «أوقف الكلّ» ليس اختياراً، هو غيابُه.
"""

from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.auctions import services as auctions
from apps.auctions.models import (
    Auction,
    FuelType,
    PlateType,
    Vehicle,
    VehicleCondition,
)
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid
from apps.core import audit
from apps.core.permissions import Capability, can
from apps.core.uploads import UploadRejected

#: المزادات التي انتهت. تُقرأ من `archive` لا تُكتب ثانيةً.
from .archive import ARCHIVED  # noqa: E402
from .views import console_page


def dangling_bids():
    """مزايداتٌ قائمة على مزاداتٍ منتهية — **ويجب أن تكون صفراً**.

    وهي بعينها ما يعدّه v1 «مزايدات نشطة 81,475» بجوار «مزادات نشطة 0».
    فمعروضةٌ هنا عدّاداً: صفرٌ يعني أن الإغلاق يعمل، وغيرُ الصفر عطلٌ في
    `auctions.services.end` لا عملٌ جماعيٌّ يُطلَق.
    """
    return Bid.objects.filter(
        vehicle__auction__state__in=ARCHIVED,
        is_withdrawn=False,
        is_superseded=False,
    )


def movable():
    """المزادات التي يمكن إنهاؤها الآن — الجارية وحدها."""
    return (
        Auction.objects.filter(state=AuctionState.LIVE)
        .annotate(
            cars=Count("vehicles", distinct=True),
            bids=Count("vehicles__bids", distinct=True),
        )
        .order_by("-starts_at", "-number")
    )


@console_page("console:auctions-bulk")
def bulk(request):
    """عمليات مجمعة: إنهاءُ مزاداتٍ مختارة، وعدّادٌ يقول إن الإغلاق يعمل."""
    if request.method == "POST":
        return _end_selected(request)

    stale = dangling_bids()
    return render(
        request,
        "console/auctions_bulk.html",
        {
            "live": movable(),
            "auctions": Auction.objects.count(),
            "bids": Bid.objects.count(),
            "dangling": stale.count(),
            # أوّلُ خمسةٍ منها إن وُجدت: عدّادٌ بلا صفوفٍ لا يُتصرَّف فيه.
            "dangling_rows": stale.select_related("vehicle", "vehicle__auction")[:5],
        },
    )


def _end_selected(request):
    """أنهِ ما اختير — مزاداً مزاداً، بالخدمة، وبسببٍ مكتوب."""
    chosen = request.POST.getlist("auction")
    reason = (request.POST.get("reason") or "").strip()

    if not chosen:
        messages.error(request, "لم يُختَر مزاد. «أوقف الكلّ» ليس اختياراً.")
        return redirect("console:auctions-bulk")

    ended, refused = [], []
    for auction in Auction.objects.filter(pk__in=chosen):
        try:
            # الخدمةُ وحدها تكتب الحالة، وهي التي تُغلق المزايدات في
            # المعاملة نفسها — فلا زرَّ ثانياً يفعل نصفَ ذلك.
            auctions.end(auction)
        except Exception as refusal:
            refused.append((auction, str(refusal)))
            continue

        ended.append(auction)
        audit.record(
            action="console.auction_end_bulk",
            entity=auction,
            actor=request.user,
            note=reason,
        )

    if ended:
        numbers = "، ".join(str(auction.number) for auction in ended)
        messages.success(request, f"أُنهي {len(ended)} مزاداً: {numbers}.")
    for auction, why in refused:
        messages.error(request, f"المزاد {auction.number}: {why}")

    return redirect("console:auctions-bulk")


def quick_edit_targets(text: str = ""):
    """المزادات التي يُفتح منها التعديل السريع — بعدد سياراتها.

    شاشة v1 «⚡ اختر مزاد — تعديل سريع» بطاقاتٌ لكل مزاد، ومنها ما فيه
    **صفرُ سيارات** (`#1005 المطبخ · 0 سيارة`). وبطاقةٌ تُفتح على لا شيء ليست
    اختصاراً؛ فالصفرُ يُعرض هنا في عموده ويُقرأ قبل الضغط.
    """
    rows = Auction.objects.annotate(cars=Count("vehicles", distinct=True)).order_by(
        "-starts_at", "-number"
    )
    text = (text or "").strip()
    if text:
        matches = Q(title__icontains=text)
        if text.isdigit():
            matches |= Q(number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:auctions-manage")
def manage(request):
    """إدارة مزاد + سياراته: اختر مزاداً لتفتح صفحته وسياراته.

    v1 يفصل «إدارة مزاد + سياراته» عن «تعديل سريع للعدادات» عن «قائمة
    المزادات» — ثلاثةُ مداخل إلى الاختيار نفسه. وهي هنا مدخلٌ واحد يقول ما
    يمكن فعله بكل مزاد، لأن ما يليه (صفحة المزاد) هو نفسه في الثلاثة.
    """
    rows = quick_edit_targets(request.GET.get("q", ""))
    return render(
        request,
        "console/auctions_manage.html",
        {"rows": rows[:100], "q": request.GET.get("q", ""), "total": rows.count()},
    )


# ---------------------------------------------------------------------------
# تعديل سريع للعدادات — صفٌّ واحد لكل سيارة، وقيدٌ لكل تغيير. T830م
# ---------------------------------------------------------------------------
#
# شاشة v1: اختر مزاداً، ثم عدِّل عدّادات سياراته في جدولٍ واحد. والفكرة صحيحة
# — الساحةُ تقيس العدّادات دفعةً واحدة، وفتحُ صفحةِ تعديلٍ لكل سيارةٍ من ثلاثمئة
# عملٌ لا يُنجَز.
#
# وثلاثة أشياء تُضاف هنا:
#
# **١. ما تغيّر وحده يُكتب.** الحلقةُ تقارن القيمة الجديدة بالقديمة وتتخطّى
# المتساوية، فحفظُ الجدول بلا تعديلٍ لا يكتب ثلاثمئة صفّ ولا ثلاثمئة قيد.
#
# **٢. وكلُّ تغييرٍ قيدٌ في `AuditLog` بقيمته قبلُ وبعد.** «كم كان العدّاد؟»
# سؤالٌ يُسأل حين يشكو مشترٍ، ولا يُجاب بالقيمة الحالية.
#
# **٣. والقيمةُ غيرُ الرقمية تُذكر ولا تُسقِط الجدول.** تحت
# `STRICT_TRANS_TABLES` كان v1 يُجهض التحديث كلَّه لقيمةٍ واحدة لا تناسب
# عمودها، فيخسر الموظّفُ ما أدخله كلَّه (T808). وهنا الصفُّ الخطأ يُذكر باسمه
# والباقي يُحفظ.


#: القيمُ المعروضة كشرائح في «حالة المحرك» و«المفتاح» — نصٌّ حرٌّ في v2
#: (`varchar`)، فالشريحةُ اختصارٌ للقيمة الشائعة و«أخرى» تفتح كتابةً حرّة،
#: تماماً كما في v1 (`$optField`).
RUNS_PRESETS = ["تعمل", "لا تعمل"]
KEY_PRESETS = ["يوجد", "لا يوجد"]


def _qe_record(car: Vehicle) -> dict:
    """سجلٌّ مضغوطٌ لكل سيارة — تُبنى منه الكروتُ كسولاً بالجافاسكربت.

    v1 يشحن كل سيارةٍ HTMLاً جاهزاً (٨٧ ألف عقدة DOM لـ٨٩٤ سيارة فتتجمّد
    الصفحة)، ثم صار يشحن سجلّاتٍ مضغوطة ويبني دفعةً كلَّ تمرير. المثلُ هنا.
    """
    return {
        "id": car.pk,
        "lot": car.lot_number,
        "name": f"{car.make} {car.model} {car.year}".strip(),
        "plate": car.plate_number or "",
        "vin": car.vin or "",
        "claim": car.claim_number or "",
        "odo": car.odometer_km if car.odometer_km is not None else "",
        "pt": car.plate_type or "",
        "ft": car.fuel_type or "",
        "cond": car.condition or "",
        "runs": car.runs_status or "",
        "key": car.key_status or "",
        # حقلُ بحثٍ واحدٌ يجمع ما يُبحث به — لوحة/شاصي/مطالبة/اسم/موقف.
        "s": " ".join(
            [
                car.plate_number or "",
                car.vin or "",
                car.claim_number or "",
                car.make,
                car.model,
                str(car.lot_number),
            ]
        ).lower(),
    }


@console_page("console:auctions-quick-edit")
def quick_edit(request):
    """تعديل سريع للعدادات — نظيرُ شاشتَي v1 (`quickEditChooser` ثم
    `quickEditVehicles`): بلا مزادٍ مختار كروتُ اختيار، ومعه كروتُ سياراتٍ
    يُحرَّر كلٌّ منها في مكانه ويحفظ وحده.

    الترتيبُ والحقولُ كما في v1: رقم الموقف، العدّاد وصورتُه، نوع اللوحة،
    الوقود، حالة المركبة، حالة المحرك، المفتاح. والشاصي للقراءة فقط. وما
    تغيّر وحده يُكتب، ولكل تغييرٍ قيدٌ في التدقيق (`vehicle_quick_update`).
    """
    number = request.GET.get("number", "").strip()
    auction = None
    if number.isdigit():
        auction = Auction.objects.filter(number=int(number)).first()

    # وضعُ الاختيار: كروتُ المزادات — نظيرُ `renderAuctionChooser`.
    if auction is None:
        rows = quick_edit_targets(request.GET.get("q", ""))
        return render(
            request,
            "console/quick_edit_pick.html",
            {
                "rows": rows[:100],
                "q": request.GET.get("q", ""),
                "total": rows.count(),
            },
        )

    # وضعُ التحرير: سجلّاتٌ مضغوطة + قوائمُ الخيارات بلصائقها من النموذج.
    cars = Vehicle.objects.filter(auction=auction).order_by("lot_number", "id")
    records = [_qe_record(c) for c in cars]
    return render(
        request,
        "console/auctions_quick_edit.html",
        {
            "auction": auction,
            "records": records,
            "count": len(records),
            "plate_choices": PlateType.choices,
            "fuel_choices": FuelType.choices,
            "condition_choices": VehicleCondition.choices,
            "runs_presets": RUNS_PRESETS,
            "key_presets": KEY_PRESETS,
        },
    )


def vehicle_quick_update(request, pk: int):
    """حفظُ سيارةٍ واحدة من كارت التعديل السريع — نظيرُ `quickUpdateVehicle` في v1.

    يُستدعى بـAJAX (حفظٌ تلقائيٌّ لكل كارت). يكتب ما أُرسل فقط، ويتخطّى
    الفارغَ كي لا يمحو قيمةً قائمة — كقاعدة v1 نفسِها. وكلُّ تغييرٍ قيدٌ يحمل
    القيمة قبلُ وبعد. وصورةُ العدّاد تدخل معرضَ السيارة عبر الخدمة المُعقَّمة.
    """
    if not request.user.is_authenticated or not can(
        request.user, Capability.AUCTIONS_MANAGE
    ):
        return JsonResponse({"ok": False, "message": "لا صلاحية."}, status=403)
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST فقط."}, status=405)

    car = get_object_or_404(Vehicle.objects.all(), pk=pk)
    changes: dict[str, tuple] = {}

    # العدّاد — رقمٌ صحيحٌ غير سالب، أو فراغٌ يعني «لم يُقَس».
    if "odometer_km" in request.POST:
        raw = request.POST.get("odometer_km", "").strip()
        if raw == "":
            new_odo = None
        elif raw.isdigit():
            new_odo = int(raw)
        else:
            return JsonResponse(
                {"ok": False, "message": "العدّاد يجب أن يكون رقماً صحيحاً."}, status=422
            )
        if new_odo != car.odometer_km:
            changes["odometer_km"] = (car.odometer_km, new_odo)
            car.odometer_km = new_odo

    # رقم الموقف — لوتٌ موجب. الفارغُ يُترك، فلا يُمحى موقفٌ قائم.
    if "lot_number" in request.POST:
        raw = request.POST.get("lot_number", "").strip()
        if raw != "":
            if not raw.isdigit() or int(raw) <= 0:
                return JsonResponse(
                    {"ok": False, "message": "رقم الموقف يجب أن يكون رقماً موجباً."},
                    status=422,
                )
            new_lot = int(raw)
            if new_lot != car.lot_number:
                changes["lot_number"] = (car.lot_number, new_lot)
                car.lot_number = new_lot

    # الحقولُ ذاتُ التعداد المغلق — تُقبل القيمةُ إن كانت من القائمة فقط.
    enum_fields = {
        "plate_type": {v for v, _ in PlateType.choices},
        "fuel_type": {v for v, _ in FuelType.choices},
        "condition": {v for v, _ in VehicleCondition.choices},
    }
    for field, valid in enum_fields.items():
        if field in request.POST:
            val = request.POST.get(field, "").strip()
            if val and val in valid and val != getattr(car, field):
                changes[field] = (getattr(car, field), val)
                setattr(car, field, val)

    # حالة المحرك والمفتاح — نصٌّ حرٌّ في v2؛ الفارغُ لا يمحو.
    for field in ("runs_status", "key_status"):
        if field in request.POST:
            val = request.POST.get(field, "").strip()
            if val and val != getattr(car, field):
                changes[field] = (getattr(car, field), val)
                setattr(car, field, val)

    # صورةُ العدّاد — تدخل المعرضَ صورةً عادية (لا غلافاً)، عبر الخدمة الوحيدة.
    image_id = 0
    image_error = None
    photo = request.FILES.get("meter_image")
    if photo is not None:
        try:
            image_id = auctions.add_image(car, photo, cover=False).pk
        except UploadRejected as refusal:
            image_error = str(refusal)

    if not changes and image_id == 0 and image_error is None:
        return JsonResponse({"ok": False, "message": "لا تغيير."}, status=422)

    if changes:
        try:
            car.save(update_fields=[*changes.keys(), "updated_at"])
        except IntegrityError:
            return JsonResponse(
                {"ok": False, "message": "رقم الموقف مستعمَل في هذا المزاد."},
                status=409,
            )
        for field, (before, after) in changes.items():
            audit.record(
                action="console.quick_edit_field",
                entity=car,
                actor=request.user,
                before={field: before},
                after={field: after},
                note=f"{field}: {before} ← {after}",
            )
    if image_id:
        audit.record(
            action="console.quick_edit_meter_photo",
            entity=car,
            actor=request.user,
            after={"image": image_id},
            note="صورةُ عدّاد من التعديل السريع",
        )

    resp = {"ok": True, "image_id": image_id, "saved": list(changes.keys())}
    if image_error:
        resp["image_error"] = image_error
    return JsonResponse(resp)
