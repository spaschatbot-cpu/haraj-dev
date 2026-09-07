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

from django import forms
from django.contrib import messages
from django.contrib.auth.password_validation import validate_password
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import ConsoleRole, User
from apps.core import audit
from apps.core.permissions import (
    Capability,
    Role,
    assign_role,
    bundle_for,
    filter_by_role,
    is_built_in,
    is_last_active_owner,
    is_owner_account,
    role_choices,
    role_label,
    role_of,
)

from .dashboard import Stat
from .exports import export, wants_export
from .icons import path_of
from .views import console_page

PAGE_SIZE = 25

#: معرّفُ دور المالك، مقروءاً مرّةً — والمقارنةُ به مقارنةُ نصٍّ لا سؤالُ إذن.
OWNER_ROLE = Role.OWNER.value


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


#: لسانا هذه الشاشة. **صفحةٌ واحدة لا اثنتان** (T852): «الأدوار» كانت مدخلاً
#: مستقلاً، ولا تُفتح إلا من هنا عملياً — ومن يعدّل دوراً يريد أن يرى من يحمله
#: في النفَس نفسه، ومن يقرأ قائمة المشرفين يسأل «وما الذي يعنيه هذا الدور؟».
VIEWS = (("staff", "المشرفون"), ("roles", "الأدوار والصلاحيات"))


#: رسومُ بطاقات هذه الشاشة. مكتوبةٌ هنا لأن `test_no_icon_is_drawn_for_nobody`
#: يمسح `PAGES` و`PLANNED` وبطاقاتِ اللوحة وحدها — ورسمٌ تستعمله بطاقةُ شاشةٍ
#: أخرى كان يُقرأ «بلا مستعمل» فيُحذف، ثم تُرسم الشاشة بفراغ. ويحرسها
#: `test_every_card_icon_is_declared` فلا تفترق عمّا تبنيه الدالّة.
CARD_ICONS = ("shield", "check", "lock", "key-refresh", "hourglass")


def staff_tallies() -> list[Stat]:
    """بطاقاتُ رأس الشاشة — بالشكل نفسه الذي تعرضه «إدارة المستخدمين».

    شاشتان في القسم الواحد يقرؤهما الموظّف نفسه، فاختلافُ الشكل بينهما يُقرأ
    نظامين لا شاشتين. والبطاقات هنا تجيب أسئلةَ هذه الشاشة: «كم يفتح اللوحة؟»
    و«كم حسابٍ متروكٍ مفعَّلاً؟» و«كم ينتظر تغيير كلمته؟».
    """
    counted = User.objects.filter(is_staff=True).aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        off=Count("id", filter=Q(is_active=False)),
        waiting=Count("id", filter=Q(must_change_password=True)),
        never=Count("id", filter=Q(last_login__isnull=True)),
    )
    return [
        Stat(
            label="إجمالي المشرفين",
            value=f"{counted['total']:,}",
            detail="من يفتح اللوحة بأي دور.",
            tone="people",
            icon="shield",
        ),
        Stat(
            label="مفعّل",
            value=f"{counted['active']:,}",
            detail="يدخل الآن.",
            icon="check",
        ),
        Stat(
            label="معطّل",
            value=f"{counted['off']:,}",
            detail="لا يدخل، واسمُه باقٍ على ما فعل.",
            tone="warn",
            icon="lock",
            href=f"{reverse('console:admins')}?state=off",
            action="اعرضهم",
        ),
        Stat(
            label="ينتظر تغيير الكلمة",
            value=f"{counted['waiting']:,}",
            detail="كلمةٌ كتبها غيرُه، وتبطل عند أوّل دخول.",
            tone="warn" if counted["waiting"] else "plain",
            icon="key-refresh",
        ),
        Stat(
            label="لم يدخل قطّ",
            value=f"{counted['never']:,}",
            detail="حسابٌ أُنشئ ولم يُستعمل — يُراجَع.",
            icon="hourglass",
        ),
    ]


@console_page("console:admins")
def admins(request):
    """المشرفون وأدوارهم — لسانان على شاشةٍ واحدة."""
    if request.GET.get("view") == "roles":
        return _roles_tab(request)
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
        # يُحسب هنا لا في القالب: سؤالُ الدور له قارئٌ واحد
        # (`ops/checks/one_permission_gate.py`)، وهذا سطرُ عرضٍ يخرج منه.
        person.is_owner = is_owner_account(person)
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
            # الرسمُ من `icons.py` لا محرف: `👑` يرسمه نظامُ التشغيل فيختلف
            # بين الأجهزة، ويسقط إلى مربّعٍ فارغ حين لا يجده الخطّ.
            "crown_icon": path_of("crown"),
            "views": VIEWS,
            "view": "staff",
            "cards": staff_tallies(),
        },
    )


def _roles_tab(request):
    """لسانُ الأدوار — نفسُ الشاشة، وحارسُها نفسه (`console:admins`).

    ولا `console_page` عليه: هو ليس صفحةً في السجلّ بل جسمُ لسانٍ في صفحة،
    والحارسُ وقع على `admins` قبل أن يصل هنا. وصفٌّ ثانٍ في السجلّ لعنوانٍ
    واحد هو ما يجعل قدرتين تحرسان الشيء نفسه ثم تفترقان.
    """
    form = RoleForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        role = form.save(commit=False)
        role.created_by = request.user
        role.full_clean()
        role.save()
        audit.record(
            action="console.create_role",
            entity=role,
            actor=request.user,
            after={"slug": role.slug, "capabilities": sorted(role.capabilities)},
            note=role.reason,
        )
        messages.success(request, f"أُضيف الدور «{role.label}».")
        return redirect(f"{reverse('console:admins')}?view=roles")

    return render(
        request,
        "console/roles.html",
        {
            "form": form,
            "rows": role_table(),
            "views": VIEWS,
            "view": "roles",
            "cards": staff_tallies(),
            # قائمةُ القدرات كما هي في التعداد: النافذةُ ترسمها مرّةً، ولا
            # تُكرَّر في كل صفّ — سبعةُ أدوارٍ × ثمانَ عشرةَ قدرة = مئةٌ
            # وستّةٌ وعشرون مربّعاً مخفيّاً في كل تحميل.
            "capability_choices": Capability.choices,
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


# ---------------------------------------------------------------------------
# الأدوار — دورٌ يُختار ويُضاف ويُحذف. T847
# ---------------------------------------------------------------------------
#
# قائمة v1 المنسدلة في «إضافة مشرف» فيها أحدَ عشرَ دوراً:
#
#     Owner (المالك) · Admin (مدير) · Manager (مدير قسم) · Supervisor (مشرف) ·
#     Data Entry (إدخال بيانات) · Company (شركة) · مدير (كل شيء عدا
#     الإحصائيات) · مدخل بيانات المزادات · الساحة/العدادات (تعديل سريع) ·
#     خدمات ما بعد البيع (اطلاع) · المالية
#
# **وأربعةٌ منها تكرارُ أربعةٍ أخرى بأسماءٍ مختلفة** — «Admin (مدير)» و«مدير
# (كل شيء عدا الإحصائيات)»، و«Data Entry (إدخال بيانات)» و«مدخل بيانات
# المزادات». وهذا ليس خطأً في التسمية: هو أثرُ أن كلَّ حاجةٍ جديدة كانت
# تُحلّ بدورٍ جديدٍ في الشيفرة، ثم لا يجرؤ أحدٌ على حذف القديم لأنه لا يعرف
# من يحمله.
#
# فالشاشة هنا تقول لكل دورٍ **كم مشرفاً يحمله**، وتحذفه حين لا يحمله أحد.
# وهو الفرق بين قائمةٍ تطول أبداً وقائمةٍ تُنظَّف.
#
# وأربعةُ أدوارٍ تبقى مكتوبةً في الشيفرة ولا تُحذف من هنا: حذفُ «المالك» يُقفل
# اللوحة على الجميع بلا طريقٍ للعودة، وذلك عطلٌ لا تُصلحه شاشة.


class RoleForm(forms.ModelForm):
    """دورٌ جديد: اسمٌ يُقرأ، ومعرّفٌ يُكتب في العمود، وقدراتٌ تُختار."""

    capabilities = forms.MultipleChoiceField(
        choices=Capability.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="القدرات",
        # `console.access` ليست مفروضةً هنا: دورٌ بلا دخولٍ إلى اللوحة قد يكون
        # مقصوداً (حسابٌ يُنشأ اليوم ويُفتح له الأسبوع القادم)، والشاشة تقوله
        # بدل أن تصحّحه بصمت.
        help_text="بلا «فتح اللوحة» لا يدخل حاملُ الدور أصلاً.",
    )

    class Meta:
        model = ConsoleRole
        fields = ("label", "slug", "capabilities", "reason")
        labels = {
            "label": "اسم الدور",
            "slug": "المعرّف (لاتينيّ)",
            "reason": "لماذا هذا الدور",
        }

    def clean_slug(self) -> str:
        """معرّفٌ يطابق دوراً مكتوباً في الشيفرة يُرفض — لأنه لن يُقرأ.

        `bundle_for` تقرأ المكتوب أولاً، فصفٌّ اسمُه `owner` لا أثر له إطلاقاً.
        وصفٌّ لا أثر له وهو معروضٌ في شاشةٍ أسوأ من رفضٍ صريح.
        """
        slug = (self.cleaned_data.get("slug") or "").strip()
        if is_built_in(slug):
            raise forms.ValidationError("هذا المعرّف لدورٍ مكتوبٍ في الشيفرة — اختر غيره.")
        return slug


def role_table() -> list[dict]:
    """كل دور، ومعه عددُ حامليه وعددُ قدراته — باستعلامين لا باستعلامٍ لكلٍّ."""
    held = {
        row["console_role"]: row["n"]
        for row in User.objects.filter(is_staff=True)
        .values("console_role")
        .annotate(n=Count("id"))
    }
    added = {row.slug: row for row in ConsoleRole.objects.all()}
    labels = dict(Capability.choices)

    table = []
    for slug, label in role_choices():
        row = added.get(slug)
        table.append(
            {
                "slug": slug,
                "label": label,
                "built_in": is_built_in(slug),
                "count": len(bundle_for(slug)),
                "held": held.get(slug, 0),
                "reason": row.reason if row else "",
                # قدراتُ الدور **مسمّاةً بالعربية** لا بمعرّفاتها: «١٢ قدرة»
                # رقمٌ لا يُراجَع، و`money.act` معرّفٌ للشيفرة — و«الأفعال
                # المالية الإدارية» هو ما يُقرأ حين يُسأل «لماذا يرى هذا
                # الشخص المال؟». وتُبنى هنا لا في القالب: بحثٌ في قاموس لا
                # يفعله قالبُ جانغو أصلاً، ومن يحاول يكتب مرشّحاً جديداً.
                "capabilities": sorted(
                    labels.get(name, name) for name in bundle_for(slug)
                ),
                # المعرّفاتُ الخام معها: النافذةُ تؤشّر بها، والجدولُ يعرض
                # الاسمَ العربيّ — ومصدرُهما `bundle_for` واحدةً لا اثنتين.
                "codes": ",".join(sorted(bundle_for(slug))),
            }
        )
    return table


@console_page("console:role-delete")
def role_delete(request, slug: str):
    """احذف دوراً لا يحمله أحد — أو اعرف من يحمله.

    والرفضُ مقصود: حذفُ دورٍ يحمله سبعةٌ يترك سبعةَ حساباتٍ بدورٍ لا وجود له،
    فتقرأ `bundle_for` مجموعةً فارغة ويخرج سبعةُ موظّفين من اللوحة في لحظةٍ
    واحدة بلا أن يقول لهم أحدٌ لماذا.
    """
    role = get_object_or_404(ConsoleRole, slug=slug)
    holders = User.objects.filter(is_staff=True, console_role=slug)

    if request.method == "POST" and not holders.exists():
        audit.record(
            action="console.delete_role",
            entity_type=ConsoleRole._meta.label_lower,
            entity_id=role.pk,
            actor=request.user,
            before={"slug": role.slug, "capabilities": sorted(role.capabilities)},
            note=(request.POST.get("reason") or "").strip(),
        )
        role.delete()
        messages.success(request, f"حُذف الدور «{role.label}».")
        return redirect(f"{reverse('console:admins')}?view=roles")

    return render(
        request,
        "console/role_delete.html",
        {
            "role": role,
            "holders": holders.order_by("full_name"),
            "capabilities": sorted(role.capabilities),
            "labels": dict(Capability.choices),
        },
    )


# ---------------------------------------------------------------------------
# إضافة مشرف جديد — والخانةُ التي تُبطل السجلّ. T848
# ---------------------------------------------------------------------------
#
# استمارة v1 أربعةُ حقول: اسم المستخدم، وكلمة المرور، ورقم الجوال، والدور،
# ومفتاحُ حالة الحساب. وهي منقولةٌ هنا كما هي — **إلا شيئين**.
#
# **١. كلمةُ المرور يكتبها موظّفٌ لموظّفٍ آخر.** أي أن الأول يعرف كلمة الثاني
# ويستطيع الدخول باسمه؛ فكلُّ قيدٍ يتركه الثاني في `AuditLog` يصير قابلاً
# للإنكار: «لم أفعل، فلانٌ يعرف كلمتي». وذلك لا يُفسد قيداً — يُبطل السجلَّ
# كلَّه، لأن حجّةَ الإنكار تصلح لكل صفٍّ فيه.
#
# فالكلمة هنا **مؤقّتة بحكم البناء**: `must_change_password` يُرفع مع الحساب،
# والحارس في `console_page` يحوّل حاملَه إلى شاشة التغيير قبل أيّ شاشةٍ أخرى.
# فما يعرفه المنشئ يبطل عند أوّل دخول، قبل أن يُفعل بالحساب شيء.
#
# **٢. والدور الافتراضيّ ليس «المالك».** في v1 القائمةُ المنسدلة تُفتح على
# `Owner (المالك)` مختاراً — أي أن الضغط على «تسجيل» بلا انتباهٍ يُنشئ مالكاً
# ثانياً. والافتراضُ هنا **لا شيء**، والاختيار مطلوب.
#
# ولا زرَّ حذفٍ في القائمة تحتها، وذلك قرارٌ سابق: حسابُ الموظّف هو الطرفُ في
# كل قيدٍ كتبه، فحذفُه محوُ التدقيق. والبديلُ `is_active`.


class NewAdminForm(forms.Form):
    """مشرفٌ جديد: اسمٌ وجوّالٌ ودورٌ وكلمةٌ مؤقّتة."""

    full_name = forms.CharField(label="اسم المستخدم", max_length=200)
    phone = forms.CharField(label="رقم الجوال", max_length=12)
    password = forms.CharField(
        label="كلمة مرور مؤقّتة",
        widget=forms.PasswordInput,
        help_text="تُطلب من حاملها مرّةً واحدة، ثم يغيّرها قبل أن يفتح أي شاشة.",
    )
    role = forms.ChoiceField(label="الدور (الصلاحية)", choices=())
    is_active = forms.BooleanField(label="الحساب مفعّل", required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # الخيارات تُقرأ عند الإنشاء لا عند الاستيراد: دورٌ يُضاف من شاشة
        # الأدوار يجب أن يظهر هنا في الطلب التالي، لا بعد إعادة تشغيل الخادم.
        #
        # و«— اختر الدور —» أوّلاً بلا قيمة: v1 يفتح على `Owner (المالك)`
        # مختاراً، فضغطةٌ بلا انتباه تُنشئ مالكاً ثانياً.
        self.fields["role"].choices = [("", "— اختر الدور —"), *role_choices()]

    def clean_phone(self) -> str:
        """جوّالٌ مستعملٌ يُرفض بالاسم، لا برسالة قاعدة بيانات.

        و`phone` مفتاحٌ فريد، فالحفظُ بلا هذا الفحص يرمي `IntegrityError`
        ويسقط الطلب كلَّه — وهو عطل T808 بعينه في شكلٍ آخر: قيمةٌ واحدة تُسقط
        ما أدخله الموظّف كلَّه.
        """
        phone = (self.cleaned_data.get("phone") or "").strip()
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("هذا الجوّال لحسابٍ قائم — افتحه بدل إنشاء ثانٍ.")
        return phone

    def clean_password(self) -> str:
        """مصادقاتُ جانغو لا شرطان مكتوبان بيد — كما في `console:password-change`."""
        password = self.cleaned_data.get("password") or ""
        validate_password(password)
        return password


@console_page("console:admin-new")
def admin_new(request):
    """أنشئ حساب مشرف — بكلمةٍ مؤقّتة تبطل عند أوّل دخول."""
    form = NewAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        person = User.objects.create_user(
            phone=form.cleaned_data["phone"],
            full_name=form.cleaned_data["full_name"],
            password=form.cleaned_data["password"],
        )
        person.is_staff = True
        person.is_active = form.cleaned_data["is_active"]
        person.must_change_password = True
        # الدورُ يُكتب بالبوّابة لا هنا: إسنادُ دورٍ قرارُ صلاحيات، وحقلُه له
        # كاتبٌ واحد كما له قارئٌ واحد (`one_permission_gate`). و`save=False`
        # ليكون الحفظُ واحداً لا اثنين على الصفّ نفسه.
        assign_role(person, form.cleaned_data["role"], save=False)
        person.save(
            update_fields=[
                "is_staff",
                "console_role",
                "is_active",
                "must_change_password",
            ]
        )
        audit.record(
            action="console.create_admin",
            entity=person,
            actor=request.user,
            after={
                "phone": person.phone,
                # اسمُ الدور لا قيمةُ الحقل: `role_label` تخرج من البوّابة
                # بدل قراءة `console_role` هنا، وهي أنفعُ في قيدٍ يُقرأ بعد
                # سنة — «الدعم» تُفهم و`support` تحتاج من يترجمها.
                "role": role_label(person),
                "is_active": person.is_active,
            },
            note=f"أنشأه {request.user.full_name}؛ كلمةٌ مؤقّتة تُغيَّر عند أوّل دخول.",
        )
        messages.success(
            request,
            f"أُنشئ حساب «{person.full_name}». يغيّر كلمته عند أوّل دخول.",
        )
        return redirect("console:admins")

    return render(request, "console/admin_new.html", {"form": form})


# ---------------------------------------------------------------------------
# تعديل مشرف — الشاشة التي لم تكن. T852
# ---------------------------------------------------------------------------
#
# قُرئت من مصدر v1: `src/Controllers/Admin/AdminUserController.php::update`
# و`src/Views/Admin/admins/index.php:307-360` (نافذةُ التعديل).
#
# هناك يُعدَّل المشرفُ من نافذةٍ في صفِّه بخمسة حقول: اسم المستخدم، والدور،
# والجوّال، وكلمةُ مرورٍ جديدة (اختيارية)، وحالةُ الحساب. **وعندنا لم يكن
# للدور بابٌ إطلاقاً**: `console:staff-grants` يمنح قدرةً فوق الدور ويسحبها،
# ولا يغيّر الدور نفسه — فمن أُسنِد إليه دورٌ خطأ يبقى عليه، أو تُمنح له
# قدراتٌ فرديّة تُحاكي الدور الصحيح، فتنمو الاستثناءات مكان التصحيح.
#
# وأربعُ حراساتٍ من v1 تُنقَل بأسبابها (`AdminUserController.php:150-175`
# و`213-217`):
#
# **١. لا تُعطّل نفسك.** هناك «لا يمكن حذف نفسك»؛ وهنا الإيقاف بديلُ الحذف،
# فالقاعدة تنتقل إليه: من يعطّل حسابه يخرج من اللوحة في منتصف الفعل ولا يبقى
# من يعكسه.
#
# **٢. لا تُغيّر دورك.** ليست في v1، وهي لازمةٌ هنا: `bundle_for` تقرأ الدور،
# فمن يخفض دوره بالخطأ يفقد الشاشة التي يصلحه منها. وv1 لا يحتاجها لأن
# `hasRole('owner')` تُجيب بنعم دائماً للمالك — وتلك حادثتُه لا حلُّه.
#
# **٣. آخرُ مالكٍ لا يُنزَع ولا يُعطَّل.** هناك «لا يمكن حذف مالك النظام»
# مطلقاً؛ وهو أشدُّ من اللازم — مالكان أحدُهما ترك العمل يجب أن يُعطَّل.
# فالقيدُ هنا على **الأخير**: لوحةٌ بلا مالكٍ فاعل لا يفتحها أحد، ولا شاشةَ
# تصلحها.
#
# **٤. والمالكُ وحده يعدّل مالكاً.** منقولةٌ كما هي.
#
# وكلمةُ المرور: **لا تُكتب هنا.** v1 يدع مشرفاً يكتب كلمةَ آخر (وذلك ما
# يُبطل السجلّ — T848)، فالزرُّ هنا **يُطلق إعادةَ تعيين**: يرفع
# `must_change_password`، فيغيّرها صاحبُها عند أوّل دخول.


class AdminEditForm(forms.Form):
    """ما يُعدَّل في مشرف: دورُه وجوّالُه وحالتُه. لا كلمةَ مرور."""

    full_name = forms.CharField(label="الاسم", max_length=200)
    phone = forms.CharField(label="رقم التواصل", max_length=12)
    role = forms.ChoiceField(label="الدور (الصلاحية)", choices=(), required=False)
    is_active = forms.BooleanField(label="الحساب مفعّل", required=False)
    reason = forms.CharField(
        label="السبب",
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="يدخل سجلّ التدقيق مع ما تغيّر قبلُ وبعد.",
    )

    def __init__(self, *args, person=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.person = person
        self.fields["role"].choices = [("", "— بلا دور —"), *role_choices()]

    def clean_phone(self) -> str:
        """جوّالٌ لحسابٍ آخر يُرفض بالاسم لا بـ`IntegrityError` يُسقط الحفظ."""
        phone = (self.cleaned_data.get("phone") or "").strip()
        clash = User.objects.filter(phone=phone)
        if self.person is not None:
            clash = clash.exclude(pk=self.person.pk)
        if clash.exists():
            raise forms.ValidationError("هذا الجوّال لحسابٍ آخر.")
        return phone


@console_page("console:admin-edit")
def admin_edit(request, pk: int):
    """عدّل مشرفاً: دورَه وجوّالَه وحالتَه — وأربعُ حراساتٍ تقول لماذا لا."""
    person = get_object_or_404(User.objects.filter(is_staff=True), pk=pk)

    is_self = person.pk == request.user.pk
    # «المالكُ وحده يعدّل مالكاً» في v1 ليست قاعدةً تُنقَل: الشاشةُ كلُّها خلف
    # `staff.grant`، فمن وصلها يملكها. والحراسةُ التي تنفع هي التي تحت — آخرُ
    # مالكٍ فاعل لا يُنزَع.
    only_owner_left = is_last_active_owner(person)
    current_role = role_of(person)

    form = AdminEditForm(
        request.POST or None,
        person=person,
        initial={
            "full_name": person.full_name,
            "phone": person.phone,
            "role": current_role,
            "is_active": person.is_active,
        },
    )

    if request.method == "POST" and form.is_valid():
        wanted_role = form.cleaned_data["role"]
        wanted_active = form.cleaned_data["is_active"]

        refusals = []
        if is_self and not wanted_active:
            refusals.append("لا تعطّل حسابك: تخرج من اللوحة ولا يبقى من يعيدك.")
        if is_self and wanted_role != current_role:
            refusals.append("لا تغيّر دورك من هنا: قد تفقد الشاشة التي تصلحه منها.")
        if only_owner_left and (not wanted_active or wanted_role != OWNER_ROLE):
            refusals.append("هذا آخرُ مالكٍ فاعل: لوحةٌ بلا مالك لا يفتحها أحد.")

        if refusals:
            for line in refusals:
                messages.error(request, line)
        else:
            watched = ["full_name", "phone", "console_role", "is_active"]
            before = audit.snapshot(User.objects.get(pk=pk), watched)
            person.full_name = form.cleaned_data["full_name"]
            person.phone = form.cleaned_data["phone"]
            person.is_active = wanted_active
            # الدورُ بالبوّابة: حقلُه له كاتبٌ واحد كما له قارئٌ واحد (T848).
            assign_role(person, wanted_role, save=False)
            person.save(update_fields=["full_name", "phone", "is_active", "console_role"])
            audit.record(
                action="console.edit_admin",
                entity=person,
                actor=request.user,
                before=before,
                after=audit.snapshot(person, watched),
                note=form.cleaned_data["reason"],
            )
            messages.success(request, "حُفظت بيانات المشرف.")
            return redirect("console:admins")

    return render(
        request,
        "console/admin_edit.html",
        {
            "person": person,
            "form": form,
            "is_self": is_self,
            "only_owner_left": only_owner_left,
            "role_name": role_label(person),
        },
    )


@console_page("console:admin-password-reset")
def admin_password_reset(request, pk: int):
    """أطلق إعادةَ تعيين كلمة مرور مشرف — بلا أن تكتبها أنت.

    v1 يدع مشرفاً يكتب كلمة مرور آخر في خانةٍ ويمضي. والأثر ليس حساباً مكشوفاً:
    كلُّ قيدٍ يتركه الثاني يصير قابلاً للإنكار («فلانٌ يعرف كلمتي»)، فيُبطل
    السجلُّ كلُّه (T848). فالزرُّ هنا يرفع `must_change_password` وحده:
    الكلمةُ الحالية تبقى صالحةً لدخولٍ واحد، وأوّلُ شاشةٍ تُطلب هي التغيير.
    """
    person = get_object_or_404(User.objects.filter(is_staff=True), pk=pk)

    if request.method == "POST":
        reason = (request.POST.get("reason") or "").strip()
        if not reason:
            messages.error(request, "السبب مطلوب — إعادةُ التعيين تُسأل عنها لاحقاً.")
            return redirect("console:admin-password-reset", pk=pk)

        person.must_change_password = True
        person.save(update_fields=["must_change_password"])
        audit.record(
            action="console.force_password_change",
            entity=person,
            actor=request.user,
            after={"must_change_password": True},
            note=reason,
        )
        messages.success(request, f"«{person.full_name}» سيغيّر كلمته عند أوّل دخول.")
        return redirect("console:admins")

    return render(request, "console/admin_password_reset.html", {"person": person})


@console_page("console:role-edit")
def role_edit(request, slug: str):
    """عدّل قدرات دورٍ مضاف — وقُل كم مشرفاً يمسّه التعديل قبل أن يقع. T852.

    وكانت الأدوار تُضاف وتُحذف ولا تُعدَّل، فمن أراد أن يزيد قدرةً واحدة على
    دورٍ يحمله سبعة كان أمامه طريقان: يحذف الدور ويصنع غيره (فيُخرج السبعةَ
    من اللوحة لحظةً)، أو يمنح القدرةَ لكلٍّ منهم فردياً (فتنمو الاستثناءات
    مكان التصحيح). وكلاهما أسوأ من التعديل.

    **والمكتوبُ في الشيفرة لا يُعدَّل من هنا.** `bundle_for` تقرأه قبل الجدول،
    فتعديلُ صفٍّ باسمه لا أثر له — وشاشةٌ تقبل تعديلاً بلا أثر أسوأ من شاشةٍ
    ترفضه.
    """
    role = get_object_or_404(ConsoleRole, slug=slug)
    holders = User.objects.filter(is_staff=True, console_role=slug)

    # اللقطةُ **قبل** بناء الاستمارة: `ModelForm` يكتب في `instance` أثناء
    # التحقّق، فقراءةُ `role.capabilities` بعده تقرأ الجديدَ وتكتبه في خانة
    # «قبل» — فيقول القيدُ إن شيئاً لم يتغيّر. وقيدٌ يقول ذلك أسوأ من غيابه:
    # يُقرأ إثباتاً على أن التغيير لم يقع.
    before = sorted(role.capabilities)

    # النافذةُ ترسل القدرات والسبب وحدهما — لا الاسمَ ولا المعرّف: هي شاشةُ
    # «إدارة الصلاحيات» لا شاشةُ إعادة تسمية. فيُكمَّل الناقصُ من الصفّ
    # القائم، ولو تُرك ناقصاً لرفضت الاستمارةُ الحفظَ على حقلٍ لم يُعرَض
    # أصلاً — وذلك رفضٌ لا يفهمه من يقرأ الشاشة.
    posted = request.POST.copy() if request.method == "POST" else None
    if posted is not None:
        posted.setdefault("label", role.label)
        posted.setdefault("slug", role.slug)

    form = RoleForm(posted, instance=role)
    # المعرّف لا يُعدَّل: هو ما يحمله عمودُ كل مشرفٍ على هذا الدور، وتغييرُه
    # يترك السبعةَ بدورٍ لا وجود له — وهو حذفٌ بلا اسمه.
    form.fields["slug"].disabled = True

    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.slug = role.slug
        saved.full_clean()
        saved.save()
        audit.record(
            action="console.edit_role",
            entity=saved,
            actor=request.user,
            before={"capabilities": before},
            after={"capabilities": sorted(saved.capabilities)},
            note=saved.reason,
        )
        messages.success(
            request,
            f"حُدِّث الدور «{saved.label}» — ويمسّ {holders.count()} مشرفاً.",
        )
        return redirect(f"{reverse('console:admins')}?view=roles")

    return render(
        request,
        "console/role_edit.html",
        {
            "role": role,
            "form": form,
            "holders": holders.order_by("full_name"),
        },
    )
