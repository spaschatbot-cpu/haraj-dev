"""The decorator every console page wears.

The guard takes a **page name**, not a capability, so the rule that admits a
caller and the rule that shows the link are the same row in
:mod:`apps.console.navigation` rather than two strings that agree today.

This module held `console:home` too, back when the root was a grid of cards
explaining each screen. The root is the analytics board now — as it is in v1 —
and the explaining line lives on each sidebar link, so the grid is gone and
what is left here is the guard alone.
"""

from __future__ import annotations

from functools import wraps
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.shortcuts import redirect
from django.utils import timezone

from apps.core.permissions import can

from .navigation import capability_for


def console_page(url_name: str):
    """Guard a view with the capability its page is listed under.

    Naming the page rather than the capability is the point. A decorator taking
    a capability would be a second place to write it down, and v1's console
    broke precisely because the menu's copy and the guard's copy drifted.

    An unknown page name raises at import time. A guard that silently allows
    everything because somebody mistyped its name is worse than no guard, and
    the mistype is exactly what a typo-prone string invites.
    """
    capability = capability_for(url_name)
    if capability is None:
        raise ImproperlyConfigured(f"{url_name} is not in apps.console.navigation.PAGES")

    def decorate(view):
        @wraps(view)
        @login_required
        def guarded(request, *args, **kwargs):
            # كلمةٌ كتبها غيرُه تُغيَّر قبل أي شيء (T848). ويُستثنى مسارُ
            # التغيير نفسه وإلّا دار على نفسه، والخروجُ ليس صفحةً هنا أصلاً.
            if (
                getattr(request.user, "must_change_password", False)
                and url_name != "console:password-change"
            ):
                return redirect("console:password-change")
            if not can(request.user, capability):
                raise PermissionDenied(f"{capability} غير مسموحة لهذا المستخدم")

            # ساعةُ الرياض على كلّ صفحةِ لوحة — T846.
            #
            # `TIME_ZONE = "UTC"` والتخزينُ بها، وهو الصواب. لكن لا شيء كان
            # يُفعّل منطقة العرض، فكلّ `{{ auction.starts_at }}` في القوالب
            # كان يُرسم **بتوقيت UTC**: مزادٌ يبدأ ١٢:٠٠ ظهراً يُقرأ ٩:٠٠
            # صباحاً. والعطل صامت — لا استثناء ولا اختبار يسقط، والموظّف
            # يقرأ رقماً معقولاً وهو خطأٌ بثلاث ساعات.
            #
            # والتفعيل هنا لا في وسيطٍ عامّ: العميلُ يقرأ من API بـUTC
            # ويحوّل عنده، وقلبُ المنطقة لكلّ طلبٍ في المشروع كان سيغيّر
            # مخرَج تلك النقاط أيضاً.
            timezone.activate(ZoneInfo(settings.DISPLAY_TIME_ZONE))
            try:
                response = view(request, *args, **kwargs)
                # لا bfcache على صفحات اللوحة: المتصفّح كان يخدم نسخةً محفوظة
                # بعد كلّ فعلٍ (تخصيصُ أعمدة، حفظُ فلتر)، فيبدو أن الحفظ لم
                # يقع والشاشةُ لم تتغيّر. `no-store` يمنع الحفظ في bfcache،
                # فكلُّ عودةٍ إلى صفحةٍ تُجلَب طازجةً بحالتها بعد الفعل.
                if hasattr(response, "headers"):
                    response.headers["Cache-Control"] = "no-store, must-revalidate"
                return response
            finally:
                # الخيوطُ يُعاد استعمالها: منطقةٌ مفعَّلةٌ لا تُعاد تُسرّب
                # ساعة الرياض إلى طلبٍ تالٍ ليس صفحةَ لوحة.
                timezone.deactivate()

        return guarded

    return decorate


def columns_save(request):
    """احفظ تخصيصَ أعمدةِ جدولٍ لهذا الموظّف، ثم أعِده إلى حيث كان.

    ليست `@console_page`: لا شاشةَ لها في الشريط ولا صفحةَ تُفتح — هي نقطةُ
    كتابةٍ يستدعيها مكوّنُ الأعمدة من أيّ جدول. وحارسُها `CONSOLE_ACCESS` وحده:
    من يفتح اللوحة يخصّص أعمدةَ ما يراه، والرؤيةُ نفسُها محروسةٌ في شاشة الجدول.
    """
    from django.contrib.auth.decorators import login_required as _login
    from django.shortcuts import redirect
    from django.utils.http import url_has_allowed_host_and_scheme

    from apps.core.permissions import Capability, can

    from . import columns

    if not request.user.is_authenticated:
        raise PermissionDenied
    if not can(request.user, Capability.CONSOLE_ACCESS):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied

    table_key = request.POST.get("table_key", "")
    if table_key not in columns.TABLES:
        raise PermissionDenied

    # `visible` تحمل ما بقي ظاهراً؛ المخفيُّ هو ما في السجلّ وليس فيها. وقراءةُ
    # «المخفيّ» من الطلب مباشرةً تثق بالمتصفّح في إرسال كل مفتاح، وحذفُ خانةٍ
    # من الطلب أسهلُ من قلبها — فنشتقّ المخفيَّ طرحاً لا استقبالاً.
    all_keys = [c.key for c in columns.TABLES[table_key]]
    visible = set(request.POST.getlist("visible"))
    hidden = [k for k in all_keys if k not in visible]
    ordering = request.POST.getlist("order")

    columns.save_layout(request.user, table_key, hidden=hidden, ordering=ordering)

    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect("console:home")
