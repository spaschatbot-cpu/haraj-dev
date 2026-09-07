"""إدارة المشرفين — قائمةُ الطاقم الإداري وأدوارهم. T830ج.

الشاشة من قائمة v1 (`/admins`)، وهي هنا **قراءةٌ محضة** عمداً. وذلك أكبر فرقٍ
عنها، فيُقال أوّلاً.

لماذا لا حذفَ هنا
=================
شاشة v1 تعرض زرَّ «🗑 حذف» في كل صفّ، وتستثني اثنين بنصٍّ يحلّ محلّه:
«لا يمكن حذف مالك» و«حسابك الحالي». والاستثناءان صحيحان — لوحةٌ يحذف فيها
المالكُ نفسَه لوحةٌ بلا مالك — **والزرّ نفسه هو الخطأ**.

حسابُ الموظّف ليس صفّاً قائماً بذاته: هو الطرفُ في كل قيدٍ كتبه في
`AuditLog`، وفي كل `StaffGrant` مُنح له، وفي كل حركةٍ مالية سجّلها. وحذفُه
إمّا أن يفشل بقيد المفتاح الأجنبي (وهو الأفضل)، أو يجرَّ معه سجلَّ من فعل ماذا
— أي أن الزرَّ الذي يبدو تنظيفاً هو محوُ التدقيق.

**والبديل مبنيٌّ أصلاً:** `User.is_active`. الحساب المعطَّل لا يدخل، ويبقى
اسمُه على كل ما فعل. وهذا ما تعرضه هذه الشاشة في عمود الحالة.

وثلاثة أعمدةٍ تختلف عن v1
==========================
* **«نشط الآن» في سبعةٍ وثلاثين من سبعةٍ وثلاثين.** عمودٌ لا يحمل إلا قيمةً
  واحدة ليس عموداً. وهنا يُقرأ من `is_active` الحقيقي، ومعه **آخر دخول** —
  فالحساب الذي تُرك مفعَّلاً بعد أن ترك صاحبُه العمل هو ما يُمسَك بالتاريخ لا
  بمربّعٍ لا أحد يفكّه.
* **«غير متوفر» في أربعةٍ وعشرين من سبعةٍ وثلاثين جوّالاً.** الجوّال في v2
  هو **اسم الدخول** (`USERNAME_FIELD`) فلا يكون فارغاً أصلاً.
* **الدور صلاحيةٌ لا كارت.** v1 يعرض `Company (شركة)` و`مدخل بيانات المزادات`
  و`الساحة/العدادات (تعديل سريع)` — أربعةَ عشرَ دوراً، ثلاثةٌ منها إصلاحاتٌ
  لدورٍ سابق. وv2 أربعةٌ، ويُبنى فوقها `StaffGrant`: استثناءٌ **بسببٍ مكتوب
  وقيدٍ في `AuditLog`** بدل دورٍ خامسَ عشر. وعمود «الصفحات» هنا يفتحه.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from apps.accounts.models import User
from apps.core.permissions import filter_by_role, role_choices, role_label

from .exports import export, wants_export
from .views import console_page

PAGE_SIZE = 25


def staff_rows(*, text: str = "", role: str = "", state: str = ""):
    """الطاقم الإداري: كلُّ من يفتح اللوحة، بدوره وحالته وعدد استثناءاته.

    `is_staff` وحدها هي التعريف — لا `console_role`: موظّفٌ بلا دورٍ مكتوب
    **يوجد** (يفتح اللوحة بأدنى قدرة)، وإخفاؤه هنا كان سيجعل الشاشة تقول
    ستّةً والقاعدة تعرف سبعة. والصفُّ الذي لا يظهر هو الصفُّ الذي لا يُراجَع.
    """
    rows = User.objects.filter(is_staff=True).annotate(
        granted=Count("grants", filter=Q(grants__granted=True), distinct=True),
        revoked=Count("grants", filter=Q(grants__granted=False), distinct=True),
    )

    text = (text or "").strip()
    if text:
        rows = rows.filter(Q(full_name__icontains=text) | Q(phone__icontains=text))

    # المرشّح يمرّ بالبوابة: `console_role` له قارئٌ واحد في المستودع
    # (`ops/checks/one_permission_gate.py`)، وهذه شاشةُ عرضٍ لا بوابة.
    rows = filter_by_role(rows, (role or "").strip())

    # الحالة مرشَّحٌ صريح: السؤال الذي تُفتح الشاشة لأجله غالباً «من ما زال
    # يدخل؟»، وهو سؤالٌ لا يُجاب بقائمةٍ تخلط المعطَّل بالعامل.
    if state == "active":
        rows = rows.filter(is_active=True)
    elif state == "off":
        rows = rows.filter(is_active=False)

    return rows.order_by("-date_joined", "-id")


@console_page("console:admins")
def admins(request):
    """قائمة المشرفين — من يدخل اللوحة، بأي دور، ومتى دخل آخر مرّة."""
    rows = staff_rows(
        text=request.GET.get("q", ""),
        role=request.GET.get("role", ""),
        state=request.GET.get("state", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="المشرفون",
            headers=[
                "المعرّف",
                "الاسم",
                "الجوال",
                "الدور",
                "الحالة",
                "آخر دخول",
                "تاريخ الإنشاء",
                "قدرات ممنوحة فوق الدور",
                "قدرات مسحوبة من الدور",
            ],
            cell=lambda row: [
                row.pk,
                row.full_name,
                row.phone,
                role_label(row),
                "مفعّل" if row.is_active else "معطّل",
                row.last_login,
                row.date_joined,
                row.granted,
                row.revoked,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    for person in page.object_list:
        person.role_label = role_label(person)
        # يُحسب هنا لا في القالب: `{% if %}` على المساواة في قالبٍ يتكرّر في
        # كل صفٍّ ولا يُختبَر. و«حسابك الحالي» هو النصّ الذي يحلّ محلّ زرّ
        # الحذف في v1 — بقي وحده لأن الزرّ لم يُنقَل، ويبقى نافعاً: من يقرأ
        # قائمةً من سبعةٍ وثلاثين يريد أن يعرف أيُّها هو.
        person.is_you = person.pk == request.user.pk

    return render(
        request,
        "console/admins.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "role": request.GET.get("role", ""),
            "state": request.GET.get("state", ""),
            "roles": role_choices(),
        },
    )


@console_page("console:page-control")
def page_control(request):
    """التحكم في صفحات المستخدمين — الاستثناءات فوق الدور، **مسمّاةً**. T830ﻫ.

    شاشة v1 المقابلة تقول ما نقوله هنا حرفياً: «تجاوز فردي فوق دوره — لا يؤثر
    على باقي المستخدمين». وهذا `StaffGrant` بعينه، فالفكرة تُنقَل كما هي.

    **والفرق عمودٌ واحد.** هناك «صفحات مخفية: 46» رقمٌ لا يقول أيّ الصفحات ولا
    لماذا، ولا يفرّق بين ما مُنح وما سُحب. وأرقامُ الإنتاج تجعل السؤال ملحّاً:
    `مترك` مالكٌ وله **٤٦** صفحةً مخفية، و`Sameh Mansour` مشرفٌ وله ١٨،
    و`ezzat` مديرٌ وله ١٥. ومالكٌ خُفيت عنه ستٌّ وأربعون صفحة إمّا أنه ليس
    مالكاً فعلاً، أو أن أحداً أخفاها ولا أحد يذكر لماذا.

    فهنا يُعرض **ما** أُخفي و**ما** أُضيف، ولكلٍّ سببُه — `StaffGrant.reason`
    حقلٌ إلزاميّ، والقيدُ في `AuditLog` يقول من ومتى.
    """
    from apps.accounts.models import StaffGrant
    from apps.core.permissions import Capability

    rows = staff_rows(text=request.GET.get("q", ""), role=request.GET.get("role", ""))
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    # استعلامٌ واحد لكل الصفحة لا استعلامٌ لكل شخص: خمسةٌ وعشرون صفّاً بخمسةٍ
    # وعشرين استعلاماً هو ما يجعل شاشةً تُفتح في ثانيتين.
    people = list(page.object_list)
    grants = StaffGrant.objects.filter(user__in=people).select_related("granted_by")
    by_person: dict[int, list] = {}
    for grant in grants:
        by_person.setdefault(grant.user_id, []).append(grant)

    labels = {value: label for value, label in Capability.choices}
    for person in people:
        person.role_label = role_label(person)
        person.overrides = [
            {
                "label": labels.get(grant.capability, grant.capability),
                "granted": grant.granted,
                "reason": grant.reason,
                "by": grant.granted_by,
            }
            for grant in by_person.get(person.pk, [])
        ]

    return render(
        request,
        "console/page_control.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "role": request.GET.get("role", ""),
            "roles": role_choices(),
        },
    )


@console_page("console:settings")
def settings_page(request):
    """الإعدادات — الحساب والصلاحيات والمظهر، وما لكلٍّ منها من شاشة. T830ﻫ.

    وخمسةُ ألسنة v1 لا تُنسَخ هنا: ثلاثةٌ منها لها شاشاتٌ في اللوحة، فتُرابَط.
    ولسانٌ ينسخ شاشةً هو المكان الثاني الذي يفترق عنها.

    **وما تملكه أنت** قسمٌ ليس في v1 أصلاً، وهو أوضح جوابٍ عن السؤال الذي يصل
    الدعمَ أكثر من غيره: «لماذا لا أرى هذه الصفحة؟». وv1 يعرض المصفوفة كلّها
    لمن يملكها ولا شيء لمن لا يملكها — أي أنه يجيب من لا يسأل ولا يجيب السائل.
    """
    from apps.accounts.models import StaffGrant
    from apps.core.permissions import Capability, capabilities_of

    allowed = capabilities_of(request.user)
    labels = {value: label for value, label in Capability.choices}
    given = set(
        StaffGrant.objects.filter(user=request.user, granted=True).values_list(
            "capability", flat=True
        )
    )

    mine = [
        {
            "label": labels.get(name, name),
            "source": "grant" if name in given else "role",
        }
        for name in sorted(allowed, key=lambda name: labels.get(name, name))
    ]

    return render(
        request,
        "console/settings.html",
        {"role": role_label(request.user), "mine": mine},
    )


@console_page("console:password-change")
def password_change(request):
    """تغيير كلمة المرور — بمُصادقات جانغو لا بشرطين مكتوبين بيد.

    v1 يشترط «٨ أحرف على الأقل ومزيج من الأحرف والأرقام»، وهما أضعف من
    AUTH_PASSWORD_VALIDATORS الافتراضي (يرفض الشائعة، والمشابهة لاسم
    المستخدم، والرقمية بالكامل) — فلا يُنقلان.

    وupdate_session_auth_hash ليست تفصيلاً: بدونها يُخرِج تغييرُ كلمة
    المرور صاحبَها من جلسته فوراً، فيظنّ أن التغيير فشل ويحاول ثانيةً.
    """
    from django.contrib import messages
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.forms import PasswordChangeForm
    from django.shortcuts import redirect

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, form.user)
            messages.success(request, "غُيّرت كلمة المرور.")
            return redirect("console:settings")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "console/password_change.html", {"form": form})
