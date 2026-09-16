"""الدعم الفني — محادثاتُ العملاء بأقسامها. T924.

مقابلُها في v1 `support_panel/admin_chat.php` (٧١١ سطراً) ومعه
`conversation_action.php` (٤٣٩) و`admin_poll.php` — **لوحةٌ ثانيةٌ كاملة**
خارج لوحة الإدارة: بابُ دخولٍ خاصٌّ بها (`admin_login.php`)، وجدولُ موظّفين
خاصٌّ بها (`haraj_chat_staff`)، وحارسٌ خاصٌّ بها. وهذه الشاشةُ تُدخلها إلى
اللوحة: نفسُ الحساب، ونفسُ القدرات، ونفسُ سجلّ التدقيق.

الشكلُ نفسُه: ثلاثةُ أعمدة
=========================
الأقسامُ يميناً، وقائمةُ المحادثات، ثم النصّ. وهو تخطيطُ v1 حرفاً — ولم
يُغيَّر لأنه صحيح: الموظّفُ يعمل بثلاثِ نظراتٍ (أيُّ قسم · أيُّ محادثة ·
ماذا قال)، وشاشةُ قائمةٍ ثم صفحةُ تفصيلٍ تجعل كلَّ محادثةٍ رحلتين.

وما تغيّر ثلاثةٌ، وكلُّها من قياسٍ على دَمب الإنتاج:

١. **ترقيمُ صفحاتٍ بدل `LIMIT 50`.** استعلامُ v1 يقصّ عند خمسين بلا صفحةٍ
   ثانية — و`support` وحدَه فيه **٨٩٬١٨٠ محادثة**. أي أن ٩٩٫٩٪ منها لا
   طريقَ إليها من الشاشة إلا بأن تصعد إلى رأس القائمة بكلامٍ جديد.
٢. **مرشّحُ الحالة يبدأ بـ«الكلّ» لا بـ«المفتوحة».** الافتراضُ في v1
   «المفتوحة» — و**٩٣٬٢٩٤ من ٩٣٬٢٩٥ مفتوحة**، فالمرشّحُ يُخفي صفّاً واحداً
   ويوهم أنه يرشّح.
٣. **البحثُ يشمل الجوّالَ ورقمَ المحادثة ونصَّ الرسائل.** بحثُ v1
   ``user_name LIKE ? OR id = ?`` وحده، و`id` يُقرأ بـ`(int)` — فمن كتب
   «أحمد» صار شرطُه `id = 0`.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, OuterRef, Q, Subquery
from django.shortcuts import redirect, render

from apps.accounts.models import User
from apps.core import audit
from apps.core.errors import DomainError
from apps.core.permissions import Capability, can
from apps.support import services
from apps.support.models import Conversation, Department, Message, SenderKind

from .views import atomic_write, console_page, row_for_write

#: خمسٌ وعشرون في الصفحة. القائمةُ عمودٌ ضيّقٌ بجانب النصّ لا جدولٌ عريض،
#: وخمسون صفّاً فيه تمريرٌ لا يُقرأ — وهو عددُ v1 نفسُه غير أن له صفحةً ثانية.
PAGE_SIZE = 25

#: ما يُعرَض من نصّ الرسالة الأخيرة في القائمة.
PREVIEW = 120


class ReplyForm(forms.Form):
    """ردُّ موظّف. حقلٌ واحدٌ إلزاميّ، وسببُ الإغلاق اختياريّ.

    **وسببُ الإغلاق هو زرُّ «إغلاق بعد الرد» نفسُه** — في v1 مربّعُ اختيارٍ
    بلا سبب، فتُغلَق المحادثةُ ولا يبقى لماذا. وهنا: نصٌّ مكتوبٌ يُغلق، وفراغٌ
    يترك المحادثةَ مفتوحة.
    """

    body = forms.CharField(
        label="الردّ",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "اكتب ردّك…"}),
        max_length=4000,
    )
    close_reason = forms.CharField(
        label="أغلق بعد الردّ (اكتب السبب)",
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "اتُّفق مع العميل هاتفياً…"}),
    )

    def clean_body(self):
        text = (self.cleaned_data.get("body") or "").strip()
        if not text:
            raise forms.ValidationError("لا يُرسَل ردٌّ بلا نصّ.")
        return text


def _departments():
    """الأقسامُ ومعها عدّادان — باستعلامٍ واحد.

    v1 يستعلم ثلاثَ مرّات لهذا الشريط: عدُّ المفتوح، وعدُّ الموظّفين
    المتّصلين، ثم `GROUP BY department_code` على وصلٍ بين الجدولين — وكلُّها
    تُعاد **كلَّ أربع ثوانٍ** من `admin_poll.php`.
    """
    unread = Q(
        conversations__messages__sender_kind=SenderKind.CUSTOMER,
        conversations__messages__read_at__isnull=True,
    )
    return Department.objects.annotate(
        open_count=Count(
            "conversations",
            filter=Q(conversations__closed_at__isnull=True),
            distinct=True,
        ),
        unread_count=Count("conversations__messages", filter=unread),
    ).order_by("position", "id")


def _filtered(request, department):
    """قائمةُ المحادثات بعد المرشّحات — ومعها معاينةُ آخرِ كلام."""
    rows = Conversation.objects.filter(department=department)

    state = request.GET.get("status", "all")
    if state == "open":
        rows = rows.filter(closed_at__isnull=True)
    elif state == "closed":
        rows = rows.filter(closed_at__isnull=False)

    term = (request.GET.get("q") or "").strip()
    if term:
        # رقمُ المحادثة **إن كان رقماً** — لا `(int)` صامتة تجعل كلَّ بحثٍ
        # نصّيٍّ شرطاً على `id = 0` كما في v1.
        matches = (
            Q(guest_name__icontains=term)
            | Q(customer__full_name__icontains=term)
            | Q(customer__phone__icontains=term)
            | Q(messages__body__icontains=term)
        )
        if term.isdigit():
            matches |= Q(pk=int(term))
        # `distinct` لأن الشرطَ الأخير يصل الرسائل: محادثةٌ فيها الكلمةُ
        # ثلاثَ مرّاتٍ كانت ستظهر ثلاثةَ صفوف.
        rows = rows.filter(matches).distinct()

    last = Message.objects.filter(conversation=OuterRef("pk")).order_by("-id")
    return (
        rows.select_related("customer", "assigned_to")
        .annotate(
            unread=Count(
                "messages",
                filter=Q(
                    messages__sender_kind=SenderKind.CUSTOMER,
                    messages__read_at__isnull=True,
                ),
            ),
            preview=Subquery(last.values("body")[:1]),
            preview_kind=Subquery(last.values("sender_kind")[:1]),
        )
        .order_by("-last_message_at", "-id")
    )


def _require(request, capability: Capability) -> None:
    """يرفع الرفضَ نفسَه الذي يرفعه حارسُ الصفحة، بالكلام نفسِه."""
    if not can(request.user, capability):
        raise PermissionDenied(f"{capability} غير مسموحة لهذا المستخدم")


@console_page("console:support")
@atomic_write
def support(request):
    """الشاشةُ كلُّها — الأقسامُ والقائمةُ والنصُّ والأفعال.

    ومسارٌ واحدٌ لا ستّة: كلُّ فعلٍ `POST` عليه يميّزه حقلُ `op`، ثم يُعيد
    التوجيه إلى الرابط نفسِه بمعاملاته — فمن ردَّ يبقى حيث كان، بقسمِه
    ومرشّحِه وصفحتِه. (نفسُ قرار `news` و`packages` في T921.)
    """
    departments = list(_departments())
    if not departments:
        return render(
            request,
            "console/support.html",
            {"departments": [], "conversation": None, "page": None},
        )

    wanted = request.GET.get("dept") or request.POST.get("dept") or ""
    current = next((row for row in departments if row.code == wanted), departments[0])

    if request.method == "POST":
        return _act(request, current)

    rows = _filtered(request, current)
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    conversation = None
    thread: list[Message] = []
    raw = request.GET.get("conversation_id") or ""
    if raw.isdigit():
        conversation = (
            Conversation.objects.select_related(
                "customer", "department", "assigned_to", "closed_by"
            )
            .filter(pk=int(raw))
            .first()
        )
        if conversation is not None:
            thread = list(conversation.messages.select_related("author").order_by("id"))

    return render(
        request,
        "console/support.html",
        {
            "departments": departments,
            "current": current,
            "page": page,
            "conversation": conversation,
            "thread": thread,
            "form": ReplyForm(),
            "preview_length": PREVIEW,
            "state": request.GET.get("status", "all"),
            "term": (request.GET.get("q") or "").strip(),
            "may_reply": can(request.user, Capability.SUPPORT_REPLY),
            "may_departments": can(request.user, Capability.SUPPORT_DEPARTMENTS),
            "targets": [row for row in departments if row.pk != current.pk],
            "staff_choices": _staff_choices(),
        },
    )


def _staff_choices():
    """من يمكن أن تُسنَد إليه محادثة: من يحمل `support.reply` فعلاً.

    v1 يعرض كلَّ صفٍّ في `haraj_chat_staff` — وهو جدولٌ لا علاقةَ له بمن
    يستطيع الردّ؛ صفّاه الحيّان بلا كلمةِ مرورٍ أصلاً، أي أنهما لا يدخلان.
    """
    return [
        person
        for person in User.objects.filter(is_staff=True, is_active=True).order_by(
            "full_name"
        )
        if can(person, Capability.SUPPORT_REPLY)
    ]


def _back(request, department, **extra):
    """يعود إلى الشاشة بنفس ما كان معروضاً — لا إلى رأسها."""
    keep = {"dept": department.code}
    for name in ("q", "status", "page", "conversation_id"):
        value = request.POST.get(name) or ""
        if value:
            keep[name] = value
    keep.update({k: v for k, v in extra.items() if v})
    query = "&".join(f"{k}={v}" for k, v in keep.items())
    return redirect(f"{request.path}?{query}")


def _act(request, department):
    """الأفعالُ الستّة. وكلُّها تمرّ على `apps.support.services` لا على ORM."""
    op = request.POST.get("op", "")

    # فتحُ قسمٍ وإغلاقُه لا يحتاج محادثةً — ويُحرَس بقدرته وحدَه.
    if op == "toggle-department":
        _require(request, Capability.SUPPORT_DEPARTMENTS)
        row = row_for_write(request, Department.objects.all(), pk=request.POST.get("pk"))
        before = {"is_open": row.is_open}
        row.is_open = not row.is_open
        row.save(update_fields=["is_open", "updated_at"])
        audit.record(
            action="console.support_department",
            entity=row,
            actor=request.user,
            before=before,
            after={"is_open": row.is_open},
            note=request.POST.get("reason", "").strip(),
        )
        messages.success(
            request,
            f"قسم «{row.name_ar}» "
            + ("يستقبل المحادثات الآن." if row.is_open else "توقّف عن الاستقبال."),
        )
        return _back(request, department)

    conversation = row_for_write(
        request, Conversation.objects.all(), pk=request.POST.get("conversation_id")
    )

    try:
        if op == "reply":
            _require(request, Capability.SUPPORT_REPLY)
            form = ReplyForm(request.POST)
            if not form.is_valid():
                # الرفضُ يُقال بجانب الحقل، لا في شريطٍ أعلى الصفحة يبتلعه
                # التمرير — وحقلٌ واحدٌ لا يستحقّ إعادةَ بناء الشاشة كلِّها.
                messages.error(request, form.errors["body"][0])
                return _back(request, department)
            services.reply(
                conversation=conversation,
                staff=request.user,
                body=form.cleaned_data["body"],
                close_reason=form.cleaned_data["close_reason"],
            )
            messages.success(request, "أُرسل الردّ.")

        elif op == "close":
            _require(request, Capability.SUPPORT_REPLY)
            services.close(
                conversation=conversation,
                staff=request.user,
                reason=request.POST.get("reason", ""),
            )
            messages.success(request, "أُغلقت المحادثة.")

        elif op == "reopen":
            _require(request, Capability.SUPPORT_REPLY)
            services.reopen(
                conversation=conversation,
                staff=request.user,
                reason=request.POST.get("reason", ""),
            )
            messages.success(request, "أُعيد فتحُ المحادثة.")

        elif op == "transfer":
            _require(request, Capability.SUPPORT_REPLY)
            target = Department.objects.filter(
                pk=request.POST.get("department") or 0
            ).first()
            if target is None:
                messages.error(request, "القسمُ المطلوب غير موجود.")
                return _back(request, department)
            services.transfer(
                conversation=conversation,
                staff=request.user,
                department=target,
                reason=request.POST.get("reason", ""),
            )
            messages.success(request, f"حُوِّلت المحادثة إلى «{target.name_ar}».")
            # والعودةُ إلى القسم الجديد: البقاءُ في القديم يعني شاشةً تقول
            # «حُوِّلت» ثم لا تجد المحادثةَ في قائمتها.
            return _back(request, target)

        elif op == "assign":
            _require(request, Capability.SUPPORT_REPLY)
            chosen = User.objects.filter(pk=request.POST.get("staff") or 0).first()
            services.assign(
                conversation=conversation, staff=request.user, assignee=chosen
            )
            messages.success(
                request,
                f"أُسندت إلى {chosen.full_name}." if chosen else "رُفع الإسناد.",
            )

        elif op == "read":
            # **الختمُ فعلٌ صريحٌ بزرّ، لا أثرٌ جانبيٌّ لفتح الصفحة.**
            #
            # ختمُه على `GET` كان أسهل، وثمنُه أن كلَّ فتحٍ للرابط يكتب في
            # القاعدة: معاينةُ رابطٍ في محادثةٍ بين موظّفين، وزرُّ «رجوع»،
            # وزاحفُ فحصٍ يطلب الصفحات كلَّها — ثلاثتُها تختم رسائلَ عميلٍ
            # «مقروءةً» ولم يقرأها إنسان. والردُّ يختم وحدَه (`services.reply`)
            # لأن من ردّ قرأ قطعاً.
            _require(request, Capability.SUPPORT_REPLY)
            count = services.mark_read(conversation=conversation, staff=request.user)
            messages.success(request, f"خُتمت {count} رسالةً كمقروءة.")

        else:
            messages.error(request, "طلبٌ لا يقول ماذا يريد.")

    except DomainError as refusal:
        messages.error(request, refusal.user_message)

    return _back(request, department, conversation_id=str(conversation.pk))


__all__ = ["ReplyForm", "support"]
