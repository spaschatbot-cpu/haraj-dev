"""الخروج ونقل الملكية — دورةُ حياةٍ كاملة، نظيرُ v1.

أربعةُ ألسنة على شاشةٍ واحدة، وكلٌّ سؤالٌ:

| اللسان | السؤال |
|---|---|
| إنشاء الخروج | ما بيع وسُدِّد ولم يُنشأ له أمرُ خروج؟ |
| متابعة نقل الملكية | ما خرج من الساحة ولم تُنقَل ملكيّتُه؟ |
| أرشيف المنقولة | ما تمّ نقلُه؟ |
| البوابة | امسح الباركود لتأكيد الخروج |

الكتابةُ كلُّها عبر `apps.auctions.exits` — الخدمةُ الوحيدة التي تكتب المراحل،
فلا يُملأ تاريخُ خروجٍ إلا في البوابة ولا تاريخُ نقلٍ إلا عند النقل.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.auctions import exits as exit_services
from apps.auctions.exits import ExitStage, VehicleExit
from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core import audit
from apps.core.permissions import Capability, can

from .exports import export, wants_export
from .views import console_page

PAGE_SIZE = 30

#: ما يجوز إنشاءُ أمرِ خروجٍ له: بيع وسُدِّد. الخروجُ تسليمٌ، والتسليمُ بعد المال.
EXITABLE = (VehicleState.PAID, VehicleState.RELEASED)


def _guard(request):
    """صلاحيةُ إدارة المزادات تحرس الكتابة. عرضٌ بلا صلاحيةٍ يُردّ."""
    return request.user.is_authenticated and can(
        request.user, Capability.AUCTIONS_MANAGE
    )


@console_page("console:vehicle-exit")
def vehicle_exit(request):
    """الشاشةُ الرئيسية بألسنتها الأربعة، وأعدادُها في التبويبات."""
    q = (request.GET.get("q", "") or "").strip()

    # لسانُ الإنشاء: المباعُ المسدَّد، ومعه أمرُ خروجه إن وُجد (لعرض حالته).
    create_rows = (
        Vehicle.objects.filter(state__in=EXITABLE)
        .select_related("auction", "awarded_to", "exit_order")
        .order_by("-awarded_at", "-id")
    )
    if q:
        match = (
            Q(plate_number__icontains=q)
            | Q(vin__icontains=q)
            | Q(make__icontains=q)
            | Q(model__icontains=q)
            | Q(awarded_to__full_name__icontains=q)
            | Q(awarded_to__phone__icontains=q)
        )
        if q.isdigit():
            match |= Q(auction__number=int(q))
        create_rows = create_rows.filter(match)

    if wants_export(request):
        return export(
            create_rows,
            name="الخروج-ونقل-الملكية",
            headers=["المزاد", "السيارة", "اللوحة", "الموديل", "المشتري", "الجوال", "حالة الخروج"],
            cell=lambda c: [
                c.auction.number,
                f"{c.make} {c.model}",
                c.plate_number,
                c.year,
                c.awarded_to.full_name if c.awarded_to else "",
                c.awarded_to.phone if c.awarded_to else "",
                c.exit_order.get_stage_display() if hasattr(c, "exit_order") and c.exit_order else "لم يُنشأ",
            ],
        )

    page = Paginator(create_rows, PAGE_SIZE).get_page(request.GET.get("page"))

    # لسانا المتابعة والأرشيف: أوامرُ الخروج بحسب مرحلتها.
    orders = VehicleExit.objects.select_related(
        "vehicle", "vehicle__auction", "vehicle__awarded_to"
    )
    follow = list(orders.filter(stage=ExitStage.UNDER_TRANSFER).order_by("warehouse_exit_at"))
    archive = list(orders.filter(stage=ExitStage.ARCHIVED).order_by("-transfer_at"))

    return render(
        request,
        "console/vehicle_exit.html",
        {
            "page": page,
            "q": q,
            "follow": follow,
            "archive": archive,
            "export_url": f"?export=xlsx&q={q}",
            "counts": {
                "create": Vehicle.objects.filter(
                    state__in=EXITABLE, exit_order__isnull=True
                ).count(),
                "follow": len(follow),
                "archive": len(archive),
            },
        },
    )


def exit_create(request, pk: int):
    """أنشئ أمرَ خروجٍ لمركبةٍ مسدَّدة — نظيرُ «إنشاء الخروج» في v1."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)
    try:
        order = exit_services.create_exit(
            vehicle,
            actor=request.user,
            exit_reason=request.POST.get("exit_reason", "").strip(),
            recipient_name=request.POST.get("recipient_name", "").strip(),
            recipient_id=request.POST.get("recipient_id", "").strip(),
            recipient_phone=request.POST.get("recipient_phone", "").strip(),
            recipient_id_image=request.FILES.get("recipient_id_image"),
        )
    except ValueError as why:
        messages.error(request, str(why))
        return redirect("console:vehicle-exit")

    audit.record(
        action="console.exit_create",
        entity=vehicle,
        actor=request.user,
        after={"barcode": order.barcode},
        note="إنشاء أمر خروج",
    )
    messages.success(request, f"أُنشئ أمرُ الخروج — الباركود {order.barcode}.")
    # يفتح الإقرارَ مباشرةً كي يُطبَع ويُرسَل مع السيارة إلى البوابة.
    return redirect("console:exit-declaration", pk=vehicle.pk)


def exit_declaration(request, pk: int):
    """إقرارُ الخروج بالباركود — صفحةٌ تُطبَع وتُسلَّم مع السيارة إلى البوابة.

    صفحةٌ فرعيةٌ لا تُسجَّل في التنقّل (تُفتح من زرّ في الشاشة)، فتُحرَس يدوياً
    بالصلاحية نفسِها لا بـ`@console_page` الذي يقرأ القدرةَ من `PAGES`.
    """
    if not _guard(request):
        return redirect("console:vehicle-exit")
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("auction", "awarded_to"), pk=pk
    )
    order = get_object_or_404(VehicleExit, vehicle=vehicle)
    return render(
        request,
        "console/exit_declaration.html",
        {"vehicle": vehicle, "order": order},
    )


def exit_gate(request):
    """البوابة: باركودٌ يُمسَح → يُؤكَّد خروجُ السيارة من الساحة."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    code = (request.POST.get("barcode", "") or "").strip().upper()
    order = VehicleExit.objects.select_related("vehicle").filter(barcode=code).first()
    if order is None:
        messages.error(request, f"لا أمرَ خروجٍ بالباركود «{code}».")
        return redirect(_back(request))

    exit_services.confirm_gate(order)
    audit.record(
        action="console.exit_gate_confirm",
        entity=order.vehicle,
        actor=request.user,
        after={"barcode": order.barcode},
        note="تأكيد الخروج من البوابة",
    )
    messages.success(
        request,
        f"أُكِّد خروجُ {order.vehicle.make} {order.vehicle.model} (لوت "
        f"{order.vehicle.lot_number}) — صار قيد متابعة النقل.",
    )
    return redirect(_back(request))


def exit_transfer(request, pk: int):
    """تأكيدُ نقل الملكية — يُؤرشَف الأمرُ، مع إثباتٍ إن رُفع."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    exit_services.mark_transferred(order, proof=request.FILES.get("proof"))
    audit.record(
        action="console.exit_transfer",
        entity=order.vehicle,
        actor=request.user,
        after={"barcode": order.barcode},
        note="نقل الملكية",
    )
    messages.success(request, "تمّ نقلُ الملكية وأُرشِف الأمر.")
    return redirect(_back(request))


def exit_lift_ban(request, pk: int):
    """رفعُ الحظر عن خروجٍ بلا لوحات — يُؤرَّخ فيُتابَع النقلُ بعده."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    exit_services.lift_ban(order)
    audit.record(
        action="console.exit_lift_ban",
        entity=order.vehicle,
        actor=request.user,
        note="رفع الحظر",
    )
    messages.success(request, "رُفع الحظر.")
    return redirect(_back(request))


def exit_upload(request, pk: int):
    """رفعُ الإقرار الموقّع — يُخزَّن في `declaration_file`. نظيرُ «📎 رفع الموقّع»."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    signed = request.FILES.get("signed")
    if signed is None:
        messages.error(request, "لم يُختَر ملفّ.")
        return redirect(_back(request))
    order.declaration_file = signed
    order.save(update_fields=["declaration_file", "updated_at"])
    audit.record(
        action="console.exit_upload_signed",
        entity=order.vehicle,
        actor=request.user,
        note="رفع الإقرار الموقّع",
    )
    messages.success(request, "رُفع الإقرار الموقّع.")
    return redirect(_back(request))


def exit_edit(request, pk: int):
    """تعديلُ بيانات المستلِم — الاسم والهوية والجوّال. نظيرُ «✏️ تعديل» في v1."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    order.recipient_name = (request.POST.get("recipient_name", "") or "").strip()
    order.recipient_id = (request.POST.get("recipient_id", "") or "").strip()
    order.recipient_phone = (request.POST.get("recipient_phone", "") or "").strip()
    fields = ["recipient_name", "recipient_id", "recipient_phone", "updated_at"]
    decl = (request.POST.get("declaration_date", "") or "").strip()
    order.declaration_date = decl or None
    fields.append("declaration_date")
    # صورةُ تفويض/هوية جديدة للاستبدال — اختياريّة.
    new_image = request.FILES.get("recipient_id_image")
    if new_image is not None:
        order.recipient_id_image = new_image
        fields.append("recipient_id_image")
    order.save(update_fields=fields)
    audit.record(
        action="console.exit_edit_recipient",
        entity=order.vehicle,
        actor=request.user,
        note="تعديل بيانات المستلِم",
    )
    messages.success(request, "حُفظت بيانات المستلِم.")
    return redirect(_back(request))


def exit_note(request, pk: int):
    """حفظُ ملاحظةِ متابعةٍ على أمر الخروج."""
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    order.notes = (request.POST.get("notes", "") or "").strip()
    order.save(update_fields=["notes", "updated_at"])
    messages.success(request, "حُفظت الملاحظة.")
    return redirect(_back(request))


def _back(request) -> str:
    """يعود إلى شاشة الخروج على اللسان الذي جاء منه (`?tab=`)."""
    tab = request.POST.get("tab", "")
    base = "/console/vehicle-exit/"
    return f"{base}?tab={tab}" if tab else base
