"""معرضُ صور المركبة من صفِّ المزاد — نظيرُ نافذة v1. T866.

الشاشةُ المقابلة في v1 (`GET /auctions/{aid}/vehicles/{vid}/images`) نافذةٌ
تُفتح من عمود الصور في الجدول، وفيها **ثلاثةُ أفعالٍ لا أكثر**: العرض،
والتكبير، وحذفُ صورة. الرفعُ وتعيينُ الغلاف نقطتان موجودتان في v1 لكنّهما
تُنادَيان من شاشة المزاد (`manage.php`) لا من هذه الشاشة.

ما نُقل، وما زِيد، ولماذا
=========================
* **الرفعُ زِيد هنا.** في v1 يفتح الموظّف الجدول فيرى «بلا صور» ثم يغادر إلى
  شاشةٍ أخرى ليرفع — وهي الخطوةُ التي تُنسى، فتُشحن المزادات بسياراتٍ بلا
  صورة. والرفعُ يمرّ بـ:func:`apps.auctions.services.add_image` وحدها، فلا
  يقرأ هذا الملفُّ بايتاً ولا يسمّي ملفّاً (`ops/checks/one_upload_gate.py`).

* **وتعيينُ الغلاف زِيد كذلك.** v1 لا يستطيع ترقيةَ صورةٍ قائمة: يرفع نسخةً
  ثانيةً بالبايتات نفسها ويرفع عليها `is_primary`، فتظهر الصورةُ مرّتين. وهنا
  :func:`apps.auctions.services.set_cover` يرقّي القائمَ بلا تكرار.

* **والحذفُ لا يمسّ القرص** — كما في v1 بالضبط. القرارُ وسببُه في
  `services.remove_image`.

* **ولا فعلَ بلا سبب.** ثلاثتُها تكتب في سجلّ التدقيق باسم المنفّذ وسببه، وهو
  ما لا يفعله v1 في أيٍّ من نقاط الصور الخمس — ولا واحدةٌ منها تتحقّق من CSRF
  أصلاً (AuctionController.php:4507، 4555، 4608).
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.auctions import services as auction_services
from apps.auctions.models import Vehicle, VehicleImage
from apps.core import audit
from apps.core.uploads import UploadRejected

from .views import console_page

#: كم صورةً تُقبل في الرفعة الواحدة. v1 بلا حدٍّ إطلاقاً — لا للعدد ولا للحجم
#: (`uploadVehicleImages` يفحص ترويسةَ النوع وحدها) — ورفعُ مئةِ ملفٍّ في طلبٍ
#: واحد يشغّل مولّدَ الطبقتين مئةَ مرّة داخل الطلب نفسه فيسقط بمهلة الخادم،
#: **بعد** أن يكون بعضُها قد كُتب. فالحدُّ هنا يجعل الرفضَ يقع قبل أول كتابة.
BATCH = 20


def _gallery_of(vehicle: Vehicle):
    """صورُ المركبة بترتيب المعرض: الغلافُ أوّلاً، ثم `position`، ثم الأقدم.

    الترتيبُ نفسه في ثلاثة مواضع (هنا، و`api/views.py`، و`auctions.py:445`)،
    وهو تكرارٌ يستحقّ استخراجاً لو صار رابعاً — ولم يصر بعد.
    """
    return vehicle.images.order_by("-is_cover", "position", "pk")


@console_page("console:vehicle-images")
def gallery(request, pk: int):
    """معرضُ صور مركبةٍ واحدة، وأفعالُه الثلاثة — صفحةً أو نافذةً منبثقة.

    النافذةُ (`?modal=1` أو ترويسةُ fetch) تُفتح من كارت شاشة المزاد فتعرض
    المحتوى وحده. وأفعالُها ترجع المعرضَ محدَّثاً (200) لا تحويلاً، فتبقى
    مفتوحةً وتُظهر الأثر فوراً — بينما الصفحةُ الكاملة تُحوَّل بنمط PRG.
    """
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "owner_company"), pk=pk
    )
    is_modal = (
        request.GET.get("modal") == "1"
        or request.headers.get("X-Requested-With") == "fetch"
    )

    if request.method == "POST":
        operation = request.POST.get("op", "")
        if operation == "upload":
            _upload(request, vehicle)
        elif operation == "delete":
            _delete(request, vehicle)
        elif operation == "cover":
            _cover(request, vehicle)
        else:
            messages.error(request, "فعلٌ غير معروف.")
        if is_modal:
            return _render_gallery(request, vehicle, modal=True)
        return redirect("console:vehicle-images", pk=vehicle.pk)

    return _render_gallery(request, vehicle, modal=is_modal)


def _render_gallery(request, vehicle: Vehicle, *, modal: bool):
    """المعرضُ بوجهيه: جزئيةُ النافذة، أو الصفحةُ الكاملة."""
    template = (
        "console/_vehicle_images_modal.html" if modal else "console/vehicle_images.html"
    )
    return render(
        request,
        template,
        {
            "vehicle": vehicle,
            "auction": vehicle.auction,
            "shots": list(_gallery_of(vehicle)),
            "batch": BATCH,
        },
    )


def _upload(request, vehicle: Vehicle):
    files = request.FILES.getlist("images")
    if not files:
        messages.error(request, "لم يُختَر ملفّ.")
        return
    if len(files) > BATCH:
        messages.error(
            request, f"{len(files)} ملفّاً في رفعةٍ واحدة — الحدّ {BATCH}."
        )
        return

    # الموضعُ يتابع آخر ما في المعرض، ولا يبدأ من الصفر: صفران بالموضع نفسه
    # يجعلان الترتيب يعتمد على `pk` وحده، فتنتقل صورةٌ من مكانها بلا سبب.
    last = _gallery_of(vehicle).order_by("-position").values_list("position", flat=True)
    position = (last[0] + 1) if last else 0

    stored, refused = 0, []
    for index, upload in enumerate(files):
        try:
            # `cover=` أوّلُ صورةٍ لمركبةٍ لا غلافَ لها: بطاقةُ العميل تقرأ
            # الغلاف وحده، فرفعٌ بلا غلافٍ يترك السيارة بلا صورةٍ في القائمة
            # وصورُها مرفوعة — وهي الشكوى نفسها التي وُلد منها عمودُ الصور.
            auction_services.add_image(
                vehicle,
                upload,
                position=position + index,
                cover=(stored == 0 and not vehicle.images.filter(is_cover=True).exists()),
            )
        except UploadRejected as refusal:
            refused.append(f"{upload.name}: {refusal}")
            continue
        stored += 1

    if stored:
        audit.record(
            action="console.vehicle_images_upload",
            entity=vehicle,
            actor=request.user,
            after={"count": stored},
            note=f"رفعُ {stored} صورة",
        )
        messages.success(request, f"رُفعت {stored} صورة.")
    for line in refused:
        messages.error(request, f"رُفض — {line}")


def _delete(request, vehicle: Vehicle):
    image = _picked(request, vehicle)
    if image is None:
        return

    was_cover = image.is_cover
    auction_services.remove_image(image)
    audit.record(
        action="console.vehicle_image_delete",
        entity=vehicle,
        actor=request.user,
        before={"image": image.pk, "was_cover": was_cover},
        note="حذفُ صورة",
    )
    if was_cover:
        heir = _gallery_of(vehicle).first()
        messages.success(
            request,
            "حُذفت الصورة، وصارت التالية غلافاً."
            if heir is not None
            else "حُذفت الصورة، ولم يبقَ للمركبة غلاف.",
        )
    else:
        messages.success(request, "حُذفت الصورة.")


def _cover(request, vehicle: Vehicle):
    image = _picked(request, vehicle)
    if image is None:
        return

    auction_services.set_cover(image)
    audit.record(
        action="console.vehicle_image_cover",
        entity=vehicle,
        actor=request.user,
        after={"image": image.pk},
        note="تعيينُ غلاف",
    )
    messages.success(request, "صارت هذه صورةَ العرض.")


def _picked(request, vehicle: Vehicle) -> VehicleImage | None:
    """الصورةُ المطلوبة **من هذه المركبة** — لا معرّفاً من خارجها.

    الترشيحُ على `vehicle` هو ما يمنع أن يحذف معرّفٌ مكتوبٌ بيدٍ صورةَ مركبةٍ
    أخرى لا تُفتح شاشتُها أصلاً — نظيرُ ما يفعله `vehicle_bulk._chosen`.
    """
    raw = request.POST.get("image", "")
    if not raw.isdigit():
        messages.error(request, "لم تُختَر صورة.")
        return None
    image = VehicleImage.objects.filter(vehicle=vehicle, pk=int(raw)).first()
    if image is None:
        messages.error(request, "الصورة غير موجودة في هذه المركبة.")
        return None
    return image


def set_display_image(request, pk: int):
    """رفعُ **صورة العرض** لمركبةٍ بضغطةٍ من كارت شاشة المزاد — نظيرُ v1.

    v1 (`manage.php`): صورةُ الكارت نفسُها زرّ — الضغطُ عليها يفتح منتقيَ ملفٍّ،
    وأولُ اختيارٍ يُرفع فوراً ويصير «صورة العرض» (`set-display-image`). المثلُ
    هنا: طلبٌ واحد بملفٍّ واحد، يردّ JSON فتتحدّث الشاشةُ بلا مغادرة.

    والفارقُ عن v1 أن الصورة تمرّ بالخطّ المُعقَّم (`add_image`) ثم يرفعها
    `set_cover` غلافاً — وهو ينزل الغلافَ القديم في المعاملة نفسها، فلا يصطدم
    قيدُ `one_cover_image_per_vehicle` ولا تبقى المركبةُ بلا غلاف. وv1 كان
    يُدخل نسخةً ثانيةً من البايتات نفسها فتظهر الصورةُ مرّتين في المعرض.

    ليست `@console_page`: فعلٌ على كارتٍ لا صفحةٌ في الشريط — يُحرَس بالصلاحية
    مباشرةً ويردّ JSON دائماً.
    """
    from django.http import JsonResponse

    from apps.core.permissions import Capability, can

    if not request.user.is_authenticated or not can(request.user, Capability.AUCTIONS_MANAGE):
        return JsonResponse({"ok": False, "message": "لا صلاحية."}, status=403)
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST فقط."}, status=405)

    vehicle = get_object_or_404(Vehicle.objects.all(), pk=pk)
    uploaded = request.FILES.get("image")
    if uploaded is None:
        return JsonResponse({"ok": False, "message": "لم يُختَر ملف."}, status=400)

    try:
        image = auction_services.add_image(vehicle, uploaded, cover=False)
    except UploadRejected as refusal:
        return JsonResponse({"ok": False, "message": str(refusal)}, status=400)

    auction_services.set_cover(image)
    audit.record(
        action="console.vehicle_display_image",
        entity=vehicle,
        actor=request.user,
        after={"image": image.pk},
        note="رفعُ صورة العرض من شاشة المزاد",
    )
    return JsonResponse({"ok": True, "image": image.pk})
