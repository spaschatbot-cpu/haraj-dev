"""إشعاراتُ التطبيق (FCM) — الحالةُ والأجهزةُ وتسليمُ الطابور. T943.

قرارُ المالك (١٨ سبتمبر ٢٠٢٦): «عايز الطريقة بتاعة FCM… نربط حساب الـFCM
بالتطبيق، ونربط إن إحنا يتم إدارته من هنا يعني من الـadmin dashboard».

## ما يُدار من هنا، وما لا يُدار — والفرقُ مقصود

**يُدار:** هل الربطُ حيٌّ الآن، وأيُّ مشروع، وأيُّ حسابِ خدمة، وكم جهازاً
مسجَّلاً وبأيّ نظام، وكم إشعاراً ينتظر في الطابور — و**زرٌّ يُسلّمه**، وزرٌّ
يُجرّب الإرسال إلى جهازٍ واحدٍ قبل أن يُبثَّ إلى الآلاف.

**لا يُدار من هنا: المفتاحُ الخاصّ.** يُوضَع في بيئة الخادم
(`FCM_SERVICE_ACCOUNT_JSON` أو `FCM_SERVICE_ACCOUNT_PATH`)، وسببُه مكتوبٌ في
`apps/notifications/push.py`: نسخةُ القاعدة تُؤخذ للتطوير وتحمل كلَّ صفّ،
ومفتاحٌ في صفٍّ يخرج مع أوّل نسخة. والشاشةُ تقول **بالحرف** ما يُكتب وأين،
فالربطُ يُدار من هنا وإن كان السرُّ محفوظاً هناك.

## والتسليمُ بضغطةِ إنسان

المادة ٥-٢: لا إنفاقَ مجدولٌ بلا موافقةٍ صريحة. والإشعارُ إلى الجهاز لا
يُحاسَب بالرسالة، لكنّ رسالةً تصل في الثالثة فجراً بلا أن يقرّرها أحدٌ هي
الإنفاقُ نفسُه بعملةٍ أخرى. فالزرُّ هنا، ولا كرون.
"""

from __future__ import annotations

from django.contrib import messages
from django.db.models import Count

from apps.core import audit
from apps.core.permissions import Capability, can
from apps.notifications import delivery, push
from apps.notifications.models import (
    Channel,
    DeliveryState,
    Device,
    Notification,
)

#: كم جهازاً يُعرض في الجدول. الشاشةُ تجيب «هل يصل الربطُ أجهزةً فعلاً»، لا
#: تُتصفَّح — والعددُ فوقها هو الجواب، والصفوفُ عيّنةٌ تُطمئن.
SAMPLE = 25


def shape() -> dict:
    """حالةُ الربط والأجهزةُ والطابور — كلُّ ما تعرضه الشاشة."""
    by_platform = dict(
        Device.objects.values_list("platform")
        .annotate(n=Count("id"))
        .values_list("platform", "n")
    )
    queue = dict(
        Notification.objects.filter(channel=Channel.PUSH)
        .values_list("state")
        .annotate(n=Count("id"))
        .values_list("state", "n")
    )
    return {
        "fcm": push.status(),
        "devices": sum(by_platform.values()),
        "by_platform": [
            {"name": dict(Device._meta.get_field("platform").choices).get(key, key),
             "count": value}
            for key, value in sorted(by_platform.items())
        ],
        "sample": list(
            Device.objects.select_related("user").order_by("-last_seen_at")[:SAMPLE]
        ),
        "queued": queue.get(DeliveryState.QUEUED, 0),
        "sent": queue.get(DeliveryState.SENT, 0) + queue.get(DeliveryState.DELIVERED, 0),
        "failed": queue.get(DeliveryState.FAILED, 0),
    }


def act(request):
    """زرّا الشاشة: «سلِّم الطابور» و«جرِّب على جهازي». يعودان برسالة.

    وكلاهما خلف `notifications.send` — التسليمُ إخراجٌ إلى أجهزة الناس،
    والقراءةُ (`notifications.view`) لا تكفي له. والحارسُ هنا صراحةً لأن
    الصفحةَ تُفتح بالقدرة الأدنى.
    """
    if not can(request.user, Capability.NOTIFICATIONS_SEND):
        from django.core.exceptions import PermissionDenied

        raise PermissionDenied("notifications.send غير مسموحة لهذا المستخدم")

    op = (request.POST.get("op") or "").strip()

    if op == "test":
        return _test(request)
    if op != "deliver":
        messages.error(request, "فعلٌ غير معروف.")
        return

    result = delivery.deliver()
    if result.get("blocked"):
        messages.error(request, result["blocked"])
        return

    audit.record(
        action="console.push_deliver",
        entity_type="notifications.notification",
        entity_id="queue",
        actor=request.user,
        note=f"سُلّم {result['sent']} وفشل {result['failed']}",
    )
    if not result["taken"]:
        messages.info(request, "لا شيءَ في الطابور.")
        return
    messages.success(
        request,
        f"سُلّم {result['sent']} إشعاراً وفشل {result['failed']}"
        + (
            f" — وحُذف {result['devices_removed']} جهازاً رفضه FCM."
            if result.get("devices_removed")
            else "."
        ),
    )


def _test(request):
    """أرسِل إشعارَ تجربةٍ إلى أجهزة **المرسِل نفسِه**. لا إلى أحدٍ غيره.

    وإلى نفسه لا إلى جوّالٍ يُكتب في خانة: خانةٌ حرّةٌ تعني أن تجربةً واحدةً
    تصل عميلاً حقيقيّاً بنصٍّ مكتوبٍ على عجل. ومن يريد أن يرى الإشعارَ يسجّل
    جهازَه في التطبيق بحسابه.
    """
    tokens = list(
        Device.objects.filter(user=request.user).values_list("token", flat=True)
    )
    if not tokens:
        messages.error(
            request,
            "لا جهازَ مسجَّلٌ بحسابك. افتح التطبيقَ بهذا الحساب ليُسجَّل جهازُك، ثمّ جرّب.",
        )
        return

    try:
        outcome = push.send_to_tokens(
            title="تجربة — حراج",
            body="هذه رسالةُ تجربةٍ من لوحة الإدارة. إن وصلتك فالربطُ يعمل.",
            tokens=tokens,
            data={"kind": "console_test"},
        )
    except push.PushNotConfigured as refusal:
        messages.error(request, str(refusal))
        return

    audit.record(
        action="console.push_test",
        entity_type="notifications.device",
        entity_id=str(request.user.pk),
        actor=request.user,
        note=f"وصل {outcome.sent} وفشل {outcome.failed}",
    )
    if outcome.sent:
        messages.success(
            request,
            f"قبِل FCM الرسالةَ لـ{outcome.sent} من أجهزتك"
            + (f" وفشل {outcome.failed}." if outcome.failed else "."),
        )
    else:
        messages.error(
            request,
            "لم يقبلها FCM: " + "; ".join(outcome.errors.values())[:300],
        )


__all__ = ["act", "shape"]
