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
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import localtime

from apps.auctions import exits as exit_services
from apps.auctions.exits import ExitReason, ExitStage, ExitType, VehicleExit
from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can

from .exports import export_table, wants_export
from .icons import path_of
from .sensitive import CUSTOMER, columns_for, person_on, shown_to
from .views import console_page

PAGE_SIZE = 30

#: ما يجوز إنشاءُ أمرِ خروجٍ له: بيع وسُدِّد. الخروجُ تسليمٌ، والتسليمُ بعد المال.
EXITABLE = (VehicleState.PAID, VehicleState.RELEASED)


def _stamp(moment) -> str:
    """وقتٌ للتصدير، والفراغُ فراغاً.

    مكتوبةٌ مرّةً لأن الصيغةَ كانت منسوخةً في أربعة مواضع — وأحدُها تجاوز
    حدَّ السطر بحرفٍ واحد فأسقط `ruff` على `main`. وصيغةٌ منسوخةٌ تتفارق:
    يُصلَح عمودٌ ويبقى أخوه.
    """
    return localtime(moment).strftime("%Y-%m-%d %H:%M") if moment else ""


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
        match = search_q(
            q,
            "plate_number",
            "vin",
            "make",
            "model",
            "awarded_to__full_name",
            "awarded_to__phone",
        )
        if q.isdigit():
            match |= Q(auction__number=int(q))
        create_rows = create_rows.filter(match)

    seen = shown_to(request.user)

    # لسانا المتابعة والأرشيف: أوامرُ الخروج بحسب مرحلتها.
    orders = VehicleExit.objects.select_related(
        "vehicle", "vehicle__auction", "vehicle__awarded_to"
    )
    follow_rows = orders.filter(stage=ExitStage.UNDER_TRANSFER).order_by(
        "warehouse_exit_at"
    )
    archive_rows = orders.filter(stage=ExitStage.ARCHIVED).order_by("-transfer_at")

    # **تصديرُ المرحلة كاملةً، لا ما تركه الفلتر.** شريطُ الفلترة في هذين
    # اللسانين يُخفي صفوفاً في المتصفّح ولا يحذفها، فملفٌّ يتبع الشاشةَ يُسلّم
    # جزءاً من الجواب بصمت — وهي حجّةُ v1 نفسُها (`scope=transfer|archive`).
    scope = (request.GET.get("scope", "") or "").strip()
    if wants_export(request) and scope in ("follow", "archive"):
        stage_rows = follow_rows if scope == "follow" else archive_rows
        return export_table(
            stage_rows,
            name="متابعة-نقل-الملكية" if scope == "follow" else "أرشيف-المنقولة",
            columns=columns_for(
                [
                    ("السيارة", lambda o: f"{o.vehicle.make} {o.vehicle.model}", None),
                    ("اللوحة", lambda o: o.vehicle.plate_number, None),
                    ("رقم المطالبة", lambda o: o.vehicle.claim_number, None),
                    ("الموديل", lambda o: o.vehicle.year, None),
                    (
                        "المشتري",
                        lambda o: o.vehicle.awarded_to.full_name
                        if o.vehicle.awarded_to
                        else "",
                        CUSTOMER,
                    ),
                    (
                        "الجوال",
                        lambda o: o.vehicle.awarded_to.phone
                        if o.vehicle.awarded_to
                        else "",
                        CUSTOMER,
                    ),
                    ("الغرض / الحالة", lambda o: o.purpose[0], None),
                    (
                        "تاريخ الخروج",
                        lambda o: _stamp(o.warehouse_exit_at),
                        None,
                    ),
                    (
                        "تاريخ النقل",
                        lambda o: _stamp(o.transfer_at),
                        None,
                    ),
                    ("المؤقّت", lambda o: o.timer[0], None),
                    ("ملاحظات المتابعة", lambda o: o.notes, None),
                ],
                seen,
            ),
        )

    if wants_export(request):
        # **والملفُّ يرث حارسَ الشاشة**: المشتري وجوّالُه خلف `users.view`
        # بالقاعدة نفسِها التي تحجبهما في الجدول (`sensitive.py`). ومن يفتح
        # الشاشة كان يضغط «تصدير Excel» فيأخذ في ملفٍّ واحدٍ عمودَ الجوّال
        # كاملاً — وعمودٌ يخرج في ملفٍّ ولا يظهر على شاشةٍ هو بابُ التسريب
        # نفسُه من الخلف.
        return export_table(
            create_rows,
            name="الخروج-ونقل-الملكية",
            columns=columns_for(
                [
                    ("المزاد", lambda c: c.auction.number, None),
                    ("السيارة", lambda c: f"{c.make} {c.model}", None),
                    ("اللوحة", lambda c: c.plate_number, None),
                    ("الموديل", lambda c: c.year, None),
                    (
                        "المشتري",
                        lambda c: c.awarded_to.full_name if c.awarded_to else "",
                        CUSTOMER,
                    ),
                    (
                        "الجوال",
                        lambda c: c.awarded_to.phone if c.awarded_to else "",
                        CUSTOMER,
                    ),
                    (
                        "حالة الخروج",
                        lambda c: c.exit_order.get_stage_display()
                        if hasattr(c, "exit_order") and c.exit_order
                        else "لم يُنشأ",
                        None,
                    ),
                ],
                seen,
            ),
        )

    page = Paginator(create_rows, PAGE_SIZE).get_page(request.GET.get("page"))

    follow = list(follow_rows)
    archive = list(archive_rows)

    # **المحجوبُ يُمحى هنا، قبل القالب.** كانت الألسنةُ الثلاثةُ تضع اسمَ
    # المشتري وجوّالَه في **مصدر الصفحة** لكلّ صفّ، والشاشةُ `auctions.view`
    # وحدَها — وهي البياناتُ نفسُها التي أُغلقت في الكتالوج و«ما بعد البيع».
    # والقاعدةُ واحدةٌ في `sensitive.py`.
    #
    # ولسانا المتابعة والأرشيف صفوفُهما `VehicleExit` لا `Vehicle`، والشخصُ
    # على مركبتها — فتُمرَّر المركباتُ أنفسُها، ويقرأ القالبُ
    # `o.vehicle.buyer_phone`. لا حارسٌ ثانٍ لشكلِ صفٍّ ثانٍ.
    person_on(page.object_list, seen)
    person_on([order.vehicle for order in follow], seen)
    person_on([order.vehicle for order in archive], seen)

    # ومن لا يملك `auctions.manage` لا يُبنى له زرُّ كتابة: `_guard` تردّ كلَّ
    # أفعال هذه الشاشة إليه بتحويلٍ صامت، **وزرُّ «تعديل» كان يحمل في مصدر
    # الصفحة اسمَ المستلِم ورقمَ هويّته وجوّالَه** في `data-*` لمن لا يملك
    # الفعلَ أصلاً. فالزرُّ الذي لا يعمل ليس عموداً يُحجَب محتواه — هو زرٌّ
    # لا يُكتب.
    manage = _guard(request)

    return render(
        request,
        "console/vehicle_exit.html",
        {
            "page": page,
            "q": q,
            "follow": follow,
            "archive": archive,
            "show_customer": seen.customer,
            "manage": manage,
            "export_url": f"?export=xlsx&q={q}",
            # مفرداتُ النوع والسبب من التعداد لا من القالب: خانةٌ تُكتب بيدها
            # في HTML تنجو من أي تغييرٍ في الموديل بلا أن تشتكي، فتُرسل قيمةً
            # يردّها `set_papers` ولا يفهم المستخدمُ لماذا.
            "exit_types": ExitType.choices,
            "exit_reasons": ExitReason.choices,
            "after_transfer": ExitType.AFTER_TRANSFER.value,
            "counts": {
                "create": Vehicle.objects.filter(
                    state__in=EXITABLE, exit_order__isnull=True
                ).count(),
                "follow": len(follow),
                "archive": len(archive),
            },
            # رسومُ الألسنة الأربعة والأفعال — من `icons.py` لا محارفَ في
            # القالب. كانت `📤` `🔄` `🗄️` `🚧` `✅`، وواحدةٌ منها (`🚧`)
            # تقول المعنى الخطأ أصلاً: «أعمالٌ جارية» لا «بوّابةُ حارس».
            # ذيلُ T837.
            "tab_icons": {
                "create": path_of("upload"),
                "follow": path_of("refresh"),
                "archive": path_of("archive"),
                "gate": path_of("gate"),
            },
            "confirm_icon": path_of("check"),
            # رسومُ أفعال الصفّ — من `icons.py` لا مسارات `d` مكتوبةً بيدٍ في
            # القالب. كانت الثلاثةُ الأولى مرسومةً هناك سطراً سطراً، فخرجت
            # بسماكاتٍ وزوايا لا تشبه بقيّة اللوحة (T837: ما يجعلها مجموعةً
            # واحدة هو التطابقُ في السُمك لا التشابهُ في الموضوع).
            "row_icons": {
                "declaration": path_of("printer"),
                "papers": path_of("upload"),
                "edit": path_of("pencil-line"),
                "create": path_of("exit-door"),
                "export": path_of("download"),
                "camera": path_of("camera"),
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
        # رسمُ «طباعة» من `icons.py` — كان `🖨️` ومعه `U+FE0F` الخفيّ. وهي
        # صفحةٌ تُطبَع: الطابعةُ تُخرج الإيموجي بأسلوب نظام التشغيل، فيخرج
        # الإقرارُ الرسميُّ برسمٍ ملوَّن بجوار نصٍّ أسود. ذيلُ T837.
        {"vehicle": vehicle, "order": order, "print_icon": path_of("printer")},
    )


def exit_gate_lookup(request):
    """بحثٌ بالباركود قبل التأكيد — نظيرُ `gate-lookup` في v1.

    كانت البوّابةُ هنا خانةً واحدة: يُكتَب الرمزُ فيُؤكَّد الخروجُ فوراً. وذلك
    **فعلٌ بلا قراءة**: الحارسُ لا يرى أيَّ سيارةٍ يُفرج عنها ولا لمن، ولا يُنبَّه
    أن خروجَها أُكِّد أمس. وباركودٌ خاطئٌ ممسوحٌ في زحمة الساحة يُخرج سيارةً
    أخرى، ولا رجوعَ من `warehouse_exit_at` بشاشة.

    فالقراءةُ أولاً: ستُّ حقائقَ تُطابَق بالعين على الورقة التي بيد السائق
    (السيارة · اللوحة · الموديل · اللوت · المستلِم · نوع الخروج)، ثم التأكيد.
    """
    if not _guard(request):
        return JsonResponse({"ok": False, "message": "لا صلاحية."}, status=403)

    code = (request.GET.get("code", "") or "").strip().upper()
    if not code:
        return JsonResponse({"ok": False, "message": "أدخل الباركود."})

    order = (
        VehicleExit.objects.select_related("vehicle")
        .filter(barcode=code)
        .first()
    )
    if order is None:
        return JsonResponse({"ok": False, "message": f"باركود غير معروف: {code}"})

    car = order.vehicle
    # «خرجت سلفاً» من الطابع لا من المرحلة وحدها: الطابعُ هو ما يُكتب عند
    # البوّابة، ومرحلةٌ تُغيَّر بيدٍ يوماً ما لا تُغيّر أن السيارة غادرت.
    already = order.warehouse_exit_at is not None or order.stage in (
        ExitStage.UNDER_TRANSFER,
        ExitStage.ARCHIVED,
    )
    return JsonResponse(
        {
            "ok": True,
            "code": order.barcode,
            "car": f"{car.make} {car.model}",
            "plate": car.plate_number or "—",
            "model": car.year,
            "lot": car.lot_number,
            "recipient": order.recipient_name or "—",
            "exit_type": order.get_exit_type_display() or "لم يُحدَّد",
            "stage": order.get_stage_display(),
            "already": already,
            "exited_at": (
                localtime(order.warehouse_exit_at).strftime("%Y-%m-%d %H:%M")
                if order.warehouse_exit_at
                else ""
            ),
            "confirm_url": reverse("console:exit-gate"),
        }
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

    # مركبةٌ خرجت سلفاً تُردّ برسالةٍ لا تُختَم مرّةً ثانية — كـ v1 (409). وبلا
    # هذا الردّ يمسح الحارسُ الورقةَ نفسَها مرّتين فتعود المركبةُ من الأرشيف إلى
    # طابور المتابعة، أو يُكتَب لها تاريخُ خروجٍ ثانٍ يُصفّر مؤقّتَ تأخّرها.
    if order.warehouse_exit_at is not None:
        messages.error(
            request,
            f"تم تأكيد خروج هذه المركبة مسبقاً — "
            f"{localtime(order.warehouse_exit_at).strftime('%Y-%m-%d %H:%M')}.",
        )
        return redirect(_back(request))

    exit_services.confirm_gate(order)
    audit.record(
        action="console.exit_gate_confirm",
        entity=order.vehicle,
        actor=request.user,
        after={"barcode": order.barcode, "routed": order.stage},
        note="تأكيد الخروج من البوابة",
    )
    # الوجهةُ تُقال في الرسالة: حارسُ البوّابة يمسح ثم يرفع بصره، والسطرُ هو
    # كلُّ ما يخبره أذهبت السيارةُ إلى الأرشيف أم إلى طابور المتابعة.
    where = (
        "أُرشِف مباشرةً (خروجٌ بعد النقل)"
        if order.stage == ExitStage.ARCHIVED
        else "صار قيد متابعة النقل"
    )
    messages.success(
        request,
        f"أُكِّد خروجُ {order.vehicle.make} {order.vehicle.model} (لوت "
        f"{order.vehicle.lot_number}) — {where}.",
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
    """أوراقُ الخروج: نوعٌ وسببٌ وإقرارٌ موقّع — ثم إلى البوابة. نظيرُ «رفع الموقّع».

    كانت تحفظ الملفَّ وحده، فلا يُكتب نوعُ خروجٍ أبداً وتوجيهُ البوابة معطَّل.
    والتحقّقُ كلُّه في `apps.auctions.exits.set_papers` — الكاتبُ الواحد — وهنا
    عرضُ سببِ الرفض لا تكرارُ شروطه.
    """
    if not _guard(request):
        return redirect("console:vehicle-exit")
    order = get_object_or_404(VehicleExit.objects.select_related("vehicle"), pk=pk)
    try:
        exit_services.set_papers(
            order,
            exit_type=(request.POST.get("exit_type", "") or "").strip(),
            exit_reason=(request.POST.get("exit_reason", "") or "").strip(),
            signed=request.FILES.get("signed"),
            proof=request.FILES.get("proof"),
        )
    except ValueError as why:
        messages.error(request, str(why))
        return redirect(_back(request))

    audit.record(
        action="console.exit_upload_signed",
        entity=order.vehicle,
        actor=request.user,
        after={"exit_type": order.exit_type, "exit_reason": order.exit_reason},
        note="أوراق الخروج والإرسال إلى البوابة",
    )
    messages.success(
        request,
        f"حُفظت أوراقُ الخروج ({order.get_exit_type_display()}) — "
        f"الباركود {order.barcode} بانتظار البوابة.",
    )
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
