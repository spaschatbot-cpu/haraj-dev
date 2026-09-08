"""العمليّات المجمَّعة على مركبات مزادٍ واحد — نظيرُ شريط v1. T865.

شاشةُ v1 المقابلة (`/auctions/{id}/vehicles`) تحمل خانةَ اختيارٍ في كل صفّ
وشريطاً يظهر عند أوّل اختيار، وفيه أربعةُ أفعال: نقلُ الحالة، ونقلُ المركبات
إلى مزادٍ آخر، والتسويق تشغيلاً وإطفاءً، والحذف. وهي أفعالُ اليوم الواقعيّ:
مزادٌ من ثلاثمئة سيارة لا يُضبط سيارةً سيارة.

ما نُقل كما هو، وما لم يُنقل
============================
* **الحالة تمرّ بالخدمة.** :func:`apps.auctions.services.move_vehicle` هو
  الكاتبُ الوحيد لحالة المركبة (`auction_state_single_writer`)، فالفعلُ
  المجمَّع حلقةٌ عليه لا ``queryset.update(state=…)``. و``update`` كان أسرع
  وأخطر: يتخطّى آلة الحالات فيضع مركبةً «مباعة» بلا مزايدةٍ ولا فاتورة.

* **وما رُفض يُقال بعدده وباسمه.** v1 يمرّر ما يُمرَّر ويصمت عن الباقي، فيقرأ
  الموظّف «تم» ويظنّ الثلاثمئة قد تحرّكت. وهنا: نجح كذا، ورُفض كذا، **ولماذا**.

* **والحذفُ للمركبة التي لا أثرَ لها وحدها.** مركبةٌ عليها مزايدةٌ أو فاتورةٌ
  أو رست على مشترٍ لا تُحذف — والقاعدة تمنعه بـPROTECT، والرسالةُ هنا تقول
  العدد وتدلّ على البديل («اسحبها») بدل أن تُلقي خطأً في وجه الموظّف.

* **ولا نقلَ إلى مزادٍ بدأ.** نقلُ مركبةٍ إلى مزادٍ مفتوحٍ للمزايدة يُدخل
  سيارةً في منتصف الشوط، فمن دفع تأمينه على ما رآه يجد غيرَه. والوجهةُ
  تُقرأ من المحرّك (:func:`apps.auctions.engine.has_started`) لا بمقارنةٍ هنا.
"""

from __future__ import annotations

from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect

from apps.auctions import engine
from apps.auctions import services as auction_services
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import VehicleState
from apps.core import audit
from apps.money.models import Invoice, InvoiceState

from .views import console_page

#: النقلاتُ التي يعرضها الشريط. أسماءُ حالاتٍ لا أفعالٌ مخترعة — والقائمة
#: مغلقة، فقيمةٌ من الطلب لا تصل إلى `move_vehicle` إلا وهي منها.
BULK_STATES = (
    (VehicleState.LISTED, "معروضة للمزايدة"),
    (VehicleState.DRAFT, "مسودة — مخفيّة عن العملاء"),
    (VehicleState.REJECTED, "مرفوضة"),
)


def _chosen(request, auction: Auction):
    """المركباتُ المختارة **داخل هذا المزاد** — لا معرّفاً من خارجه.

    الترشيحُ على ``auction`` ليس تجميلاً: بدونه يكفي أن يُرسل معرّفٌ بيده
    ليتحرّك صفٌّ في مزادٍ آخر لا تُفتح شاشتُه أصلاً.
    """
    ids = [value for value in request.POST.getlist("vehicle") if value.isdigit()]
    return Vehicle.objects.filter(auction=auction, pk__in=ids)


@console_page("console:auction-vehicles-bulk")
def vehicles_bulk(request, pk: int):
    """نفِّذ فعلاً واحداً على ما اختير من مركبات هذا المزاد."""
    auction = get_object_or_404(Auction.objects.all(), pk=pk)
    back = redirect("console:auction-detail", pk=auction.pk)

    if request.method != "POST":
        return back

    reason = (request.POST.get("reason") or "").strip()

    rows = list(_chosen(request, auction))
    if not rows:
        messages.error(request, "لم تُختَر مركبة.")
        return back

    operation = request.POST.get("op", "")
    handlers = {
        "state": _move_state,
        "marketing": _marketing,
        "move": _move_auction,
        "delete": _delete,
    }
    handler = handlers.get(operation)
    if handler is None:
        messages.error(request, "فعلٌ غير معروف.")
        return back

    handler(request, auction, rows, reason)
    return back


def _move_state(request, auction: Auction, rows: list[Vehicle], reason: str) -> None:
    target = request.POST.get("state", "")
    allowed = {str(value) for value, _ in BULK_STATES}
    if target not in allowed:
        messages.error(request, "حالة غير معروفة.")
        return

    moved, refused = [], []
    for vehicle in rows:
        try:
            # الخدمةُ وحدها تكتب الحالة — لا `queryset.update`، فذاك يتخطّى
            # آلةَ الحالات ويضع نقلةً لا يسمح بها المسار.
            auction_services.move_vehicle(vehicle, target)
        except Exception as refusal:  # noqa: BLE001
            refused.append((vehicle, str(refusal)))
            continue
        moved.append(vehicle)

    if moved:
        label = dict((str(v), lbl) for v, lbl in BULK_STATES)[target]
        audit.record(
            action="console.vehicles_bulk_state",
            entity=auction,
            actor=request.user,
            after={"state": target, "count": len(moved)},
            note=reason,
        )
        messages.success(request, f"نُقلت {len(moved)} مركبة إلى «{label}».")
    _say_refusals(request, refused)


def _marketing(request, auction: Auction, rows: list[Vehicle], reason: str) -> None:
    on = request.POST.get("marketing") == "on"
    changed = Vehicle.objects.filter(pk__in=[v.pk for v in rows]).update(
        is_marketing=on
    )
    audit.record(
        action="console.vehicles_bulk_marketing",
        entity=auction,
        actor=request.user,
        after={"is_marketing": on, "count": changed},
        note=reason,
    )
    word = "شُغِّل" if on else "أُطفئ"
    messages.success(request, f"{word} التسويق على {changed} مركبة.")


def _move_auction(request, auction: Auction, rows: list[Vehicle], reason: str) -> None:
    target_id = request.POST.get("target", "")
    if not target_id.isdigit():
        messages.error(request, "لم يُختَر مزادٌ وجهة.")
        return

    target = Auction.objects.filter(pk=int(target_id)).first()
    if target is None:
        messages.error(request, "المزاد الوجهة غير موجود.")
        return
    if target.pk == auction.pk:
        messages.error(request, "المزاد الوجهة هو المزاد نفسه.")
        return
    # الساعةُ من المحرّك — مزادٌ بدأ لا تُدخَل إليه سيارةٌ في منتصف الشوط.
    if engine.has_started(target):
        messages.error(
            request,
            f"مزاد {target.number} بدأ بالفعل — نقلُ مركبةٍ إليه يُدخلها في "
            "منتصف الشوط بعد أن دفع المزايدون تأميناتهم على ما رأوه.",
        )
        return

    # مركبةٌ عليها فاتورةٌ حيّة لا تُنقَل نقلاً صامتاً: الفاتورةُ تؤشّر عليها
    # وقد دفع صاحبُها، ونقلُها إلى مزادٍ آخر يترك فاتورةً في مزادٍ وسيارةً في
    # آخر. وهو ما يقفله v1 صراحةً (`annotateVehicleInvoiceLock`)، وكان هنا
    # `update()` خاماً يمرّرها. فالمقفولةُ تُذكر باسمها وتُدَلُّ على الاسترجاع
    # (`vehicle_relist`) الذي يعكس الفاتورةَ والتأمين معها، والباقي يُنقَل.
    locked_ids = set(
        Invoice.objects.filter(vehicle__in=rows)
        .exclude(state=InvoiceState.CANCELLED)
        .values_list("vehicle_id", flat=True)
    )
    free = [v for v in rows if v.pk not in locked_ids]
    locked = [v for v in rows if v.pk in locked_ids]

    moved = 0
    if free:
        moved = Vehicle.objects.filter(pk__in=[v.pk for v in free]).update(
            auction=target
        )
        audit.record(
            action="console.vehicles_bulk_move",
            entity=auction,
            actor=request.user,
            after={"to_auction": target.number, "count": moved},
            note=reason,
        )
        messages.success(request, f"نُقلت {moved} مركبة إلى مزاد {target.number}.")
    if locked:
        names = "، ".join(str(v.lot_number or v.pk) for v in locked[:8])
        messages.error(
            request,
            f"{len(locked)} مركبة لم تُنقَل — عليها فاتورةٌ حيّة ({names}). "
            "استرجِعها أولاً: الاسترجاعُ يعكس الفاتورةَ ويحرّر التأمين، ثم تُنقَل.",
        )


def _delete(request, auction: Auction, rows: list[Vehicle], reason: str) -> None:
    gone, kept = 0, []
    for vehicle in rows:
        label = str(vehicle.lot_number or vehicle.pk)
        try:
            vehicle.delete()
        except ProtectedError:
            # مزايدةٌ أو فاتورةٌ تشير إليها. والقاعدة تمنع، والرسالةُ تدلّ
            # على البديل بدل أن تُلقي خطأً في وجه الموظّف.
            kept.append(label)
            continue
        gone += 1

    if gone:
        audit.record(
            action="console.vehicles_bulk_delete",
            entity=auction,
            actor=request.user,
            after={"count": gone},
            note=reason,
        )
        messages.success(request, f"حُذفت {gone} مركبة.")
    if kept:
        names = "، ".join(kept[:8])
        messages.error(
            request,
            f"{len(kept)} مركبة لم تُحذف — عليها مزايدةٌ أو فاتورة ({names}). "
            "اسحبها بدل حذفها: يبقى أثرُها كاملاً.",
        )


def _say_refusals(request, refused) -> None:
    """ما رُفض يُقال باسمه وسببه — لا يُبتلَع في «تمّ»."""
    for vehicle, why in refused[:8]:
        messages.error(request, f"لوت {vehicle.lot_number or vehicle.pk}: {why}")
    if len(refused) > 8:
        messages.error(request, f"و{len(refused) - 8} مركبةً أخرى رُفضت للسبب نفسه.")
