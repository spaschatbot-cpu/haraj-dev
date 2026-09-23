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
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone, translation

from apps.core.permissions import can

from .navigation import capability_for


def internal_next(request) -> str | None:
    """الشاشةُ التي أُرسلت منها الاستمارة (`next`) — إن كانت داخل اللوحة.

    نقاطُ الكتابة يناديها أكثرُ من شاشة: الترسيةُ والرفضُ يناديهما «اتخاذ
    القرار» و«اتخاذ القرار للشريك» معاً، والفوترةُ يناديها «اتخاذ القرار»
    و«المزايدات المقبولة». فالشاشةُ تقول إلى أين تعود، وإلّا عادت كلُّ نقطةٍ
    إلى شاشتها هي — وخرج الموظّفُ من الشاشة التي كان يعمل فيها بعد كلّ ضغطة.

    ومسارٌ داخليٌّ وحدَه: `//host` و`\host` يقرؤهما المتصفّحُ عنواناً
    خارجيّاً، فتصير خانةُ نموذجٍ بابَ تحويلٍ إلى أيّ موقع. و`..` كذلك:
    `/console/../admin/` يمرّ البادئةَ ويحلّه المتصفّحُ خارجَها.
    """
    target = (request.POST.get("next") or "").strip()
    if (
        target.startswith("/console/")
        and "//" not in target
        and "\\" not in target
        and ".." not in target
    ):
        return target
    return None


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
            # ولغةُ اللوحة عربيّةٌ بقرارٍ لا بترويسةِ متصفّح — T839.
            #
            # كلُّ قالبٍ هنا يكتب `<html lang="ar" dir="rtl">` ثابتاً،
            # و`LocaleMiddleware` مع `LANGUAGES` فيها الإنجليزية كانت تختار
            # اللغة من `Accept-Language`. فمتصفّحُ ويندوز الافتراضيّ
            # (`en-US`) يجعل الصفحةَ **تدّعي العربية وتُرسم إنجليزيّة**: قِيس
            # على هذه القاعدة في ١٣ سبتمبر ٢٠٢٦ — تاريخُ التسجيل يُقرأ
            # «Sept. 13, 2026, 4:40 p.m.» وسط جدولٍ عربيّ، ورفضُ كلمةِ مرورٍ
            # ضعيفةٍ في «إضافة مشرف» يخرج «This password is too common.»
            # وحدها. وبترويسة `ar` تخرج الاثنتان عربيّتين — فالترجمةُ موجودة،
            # والمختارُ هو الخطأ.
            #
            # والتفعيلُ هنا لا في الإعدادات، للسبب نفسه الذي وُضعت له المنطقة
            # فوق: نقاطُ الـAPI يقرؤها العميلُ ويتفاوض عليها بلغته، وقلبُ
            # اللغة للمشروع كلِّه كان سيغيّر مخرَجها معها.
            translation.activate("ar")
            try:
                response = view(request, *args, **kwargs)
                # لا bfcache على صفحات اللوحة: المتصفّح كان يخدم نسخةً محفوظة
                # بعد كلّ فعلٍ (تخصيصُ أعمدة، حفظُ فلتر)، فيبدو أن الحفظ لم
                # يقع والشاشةُ لم تتغيّر. `no-store` يمنع الحفظ في bfcache،
                # فكلُّ عودةٍ إلى صفحةٍ تُجلَب طازجةً بحالتها بعد الفعل.
                if hasattr(response, "headers"):
                    response.headers["Cache-Control"] = "no-store, must-revalidate"
                    # `LocaleMiddleware` يكتب `Content-Language` بما تفاوض
                    # عليه (`setdefault`)، فيُعلن الردُّ إنجليزيّةً ومحتواه
                    # عربيّ. والمكتوبُ هنا يسبقه.
                    response.headers["Content-Language"] = "ar"
                return response
            finally:
                # الخيوطُ يُعاد استعمالها: منطقةٌ مفعَّلةٌ لا تُعاد تُسرّب
                # ساعة الرياض إلى طلبٍ تالٍ ليس صفحةَ لوحة. واللغةُ مثلها.
                timezone.deactivate()
                translation.deactivate()

        return guarded

    return decorate


def columns_save(request):
    """احفظ تخصيصَ أعمدةِ جدولٍ لهذا الموظّف، ثم أعِده إلى حيث كان.

    ليست `@console_page`: لا شاشةَ لها في الشريط ولا صفحةَ تُفتح — هي نقطةُ
    كتابةٍ يستدعيها مكوّنُ الأعمدة من أيّ جدول. وحارسُها `CONSOLE_ACCESS` وحده:
    من يفتح اللوحة يخصّص أعمدةَ ما يراه، والرؤيةُ نفسُها محروسةٌ في شاشة الجدول.
    """
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


# ---------------------------------------------------------------------------
# HR-13ج — «افحص ثم اكتب» تصير خطوةً واحدة
# ---------------------------------------------------------------------------
#
# `HR-13` أضاف ختمَ الصفّ (`ReasonMixin.row_stamp`) فأغلق النافذةَ الواسعة:
# موظّفان يفتحان الشاشة بدقائقَ بينهما، والثاني يُرفض. **وبقيت نافذةٌ ضيّقة**:
# الفحصُ في `clean` والكتابةُ في `save`، وبينهما لا قفلٌ ولا معاملة. طلبان
# يصلان في نفس عشراتِ الميلي‑ثانية يقرآن الصفَّ نفسه، فيتطابق ختماهما معاً،
# ويكتب الثاني فوق الأوّل — وهو عينُ العطل الذي وُجد `HR-13` ضدّه.
#
# والعلاجُ الذي يصفه التاسكُ بنصّه: «`atomic` على العرض و`select_for_update`
# عند تحميل الصفّ». وهما هنا **أداتان مشتركتان لا سطران في كلّ شاشة**: خمسُ
# نسخٍ من القفل هي خمسةُ مواضعَ تُنسى إحداها يومَ تُضاف شاشةٌ سادسة.
#
# **والقفلُ على الكتابة وحدها.** قفلُ صفٍّ لمن يقرأ صفحةً يجعل فتحَ ملفِّ عميلٍ
# يحجب تعديلَه من موظّفٍ آخر — ثمنٌ لا يشتري شيئاً، فالقارئ لا يدهس أحداً.


def atomic_write(view):
    """اجعل معالجةَ `POST` كلَّها معاملةً واحدة — من القراءة إلى الحفظ.

    و`GET` يمرّ بلا معاملة: هو قراءةٌ لا تدهس شيئاً، ومعاملةٌ حولها تحجز
    اتّصالاً بلا مقابل.
    """

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return view(request, *args, **kwargs)
        with transaction.atomic():
            return view(request, *args, **kwargs)

    return wrapper


def row_for_write(request, queryset, **lookup):
    """حمّل الصفَّ — مقفولاً إن كنّا نكتب، حرّاً إن كنّا نقرأ.

    يُستعمل **مع** :func:`atomic_write` وحدها: `select_for_update` خارج معاملةٍ
    يرمي `TransactionManagementError`، وذلك رفضٌ صريحٌ خيرٌ من قفلٍ صامتٍ لا
    يقفل — وهو ما يجعل نسيانَ الزينةِ الأولى عطلاً يظهر فوراً لا بعد شهور.
    """
    if request.method == "POST":
        queryset = queryset.select_for_update()
    return get_object_or_404(queryset, **lookup)
