"""إرسال إشعار — الجمهورُ يُعَدّ، والكلفةُ تُعرَض، ثمّ يُضغط الزرّ. T832.

عطلُ v1 بحرفه: خيارُ «جميع المستخدمين» هو **أوّلُ عنصرٍ في القائمة المنسدلة**
— أي المختارُ افتراضياً — واستعلامُه `SELECT … FROM userss` بلا `WHERE` ولا
`LIMIT`. فعنوانٌ ونصٌّ وضغطةٌ واحدة = بثٌّ إلى القاعدة كلِّها، بلا عدٍّ مسبقٍ
ولا تأكيدٍ ولا كلفةٍ معروضة. والعددُ يظهر **بعد** التنفيذ: «تم تنفيذ الإشعار
الجماعي لعدد N مستخدم». وفي `haraj2_t307` اليوم **٤٤٬٠٣٦ عميلاً**.

فهذه الشاشة تقلب الترتيب في ثلاث خطواتٍ لا واحدة:

١. **تُوصَف** — مرشّحاتٌ في `apps.notifications.audience`.
٢. **تُعاين** — العددُ والكلفةُ وحالةُ البوّابة، ورمزٌ يُمنح للخطوة الثالثة.
٣. **تُنفَّذ** — ولا تُنفَّذ إلا برمزٍ من الخطوة الثانية.

والقناتان لا تُخلطان
====================
`in_app` صفٌّ في جدولنا لا يكلّف هللة؛ و`sms` **تُحاسَب بالرسالة ولا تُسترد**.
فالاختيارُ صريحٌ في الواجهة، والكلفةُ تُعرَض للثانية وحدها، والبوّابةُ تُسأل
للثانية وحدها.

والتأكيدُ علمٌ في الطلب لا في المتصفّح
=====================================
الخطوةُ الثالثة تحمل `confirmed_count` — الرقمَ الذي رآه الموظّف — ويقارنه
الخادمُ بما يعدّه هو الآن. تأكيدٌ في الجافاسكربت يُلتفّ عليه بطلبٍ مباشر؛
ورقمٌ يجب أن يطابق لا يُلتفّ عليه بحذف خانةٍ من الاستمارة (الغيابُ يعني
`None`، و`None != 469`).

ولا شيء يُرسَل من هنا
=====================
المنظرُ يكتب صفَّ القرار ويحجز المهمّة. والمهمّةُ تُدرج صفوف `Notification`
بحالة `queued`. و**لا شيءَ في v2 يأخذ صفّاً `queued` ويسلّمه إلى مزوّد** —
فـ«أُدرج» ليست «وصل»، والشاشةُ تقولها بنصّها كي لا يُقرأ غير ذلك.
"""

from __future__ import annotations

import uuid

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core import audit
from apps.notifications import broadcast as service
from apps.notifications import tasks as notification_tasks
from apps.notifications.audience import (
    ACCOUNT_TYPES,
    AUCTION_LINKS,
    STATUSES,
    Audience,
)
from apps.notifications.models import Broadcast, Channel

#: إلى أين يعود الإرسالُ بعد كلّ قرار — تبويبُه في «الإشعارات».
BACK = "/console/notifications/"

#: القنواتُ التي تُعرَض للاختيار.
#:
#: **و`push` دخلت في T943** — كان مكتوباً هنا «يوم تُسجَّل أجهزة يُضاف السطر»،
#: وقد بُني المسلكُ كلُّه: `apps.notifications.push` يسلّم عبر FCM،
#: و`delivery` يأخذ الطابور، وتبويبُ «ربط التطبيق» يقول أحيٌّ هو وكم جهازاً
#: مسجَّلاً. ومن يبثُّ إلى صفرِ جهازٍ يقرأ الصفرَ في التبويب قبل أن يضغط.
CHANNELS = (
    (Channel.IN_APP, "داخل التطبيق — لا يكلّف شيئاً"),
    (Channel.PUSH, "إشعارٌ على الجهاز (FCM) — لا يكلّف بالرسالة"),
    (Channel.SMS, "رسالة نصّيّة — تُحاسَب بالرسالة"),
)

#: كم بثّاً سابقاً يُعرَض أسفل الشاشة. السجلُّ يُقرأ بحثاً عن «ماذا أرسلنا
#: الأسبوع الماضي»، لا تصفُّحاً.
HISTORY = 20


def _channel(raw: str) -> str:
    """القناةُ المختارة، والافتراضُ **الأرخص**.

    وهو عكسُ v1 حرفياً: هناك الافتراضُ أوسعُ جمهورٍ ممكن، وهنا أقلُّ قناةٍ
    كلفةً. والافتراضاتُ في شاشةِ إنفاقٍ ليست تفصيلاً — هي ما يقع حين لا يقرّر
    أحدٌ شيئاً.
    """
    allowed = {value for value, _ in CHANNELS}
    raw = (raw or "").strip()
    return raw if raw in allowed else Channel.IN_APP


def _form(request, data, *, plan=None, token: str = "") -> dict:
    """ما يُرسَم على الشاشة — المرشّحُ كما كُتب، والخطّةُ إن حُسبت."""
    return {
        "account_types": ACCOUNT_TYPES,
        "statuses": STATUSES,
        "auction_links": AUCTION_LINKS,
        "channels": CHANNELS,
        "confirm_above": service.CONFIRM_ABOVE,
        "form": {
            "channel": _channel(data.get("channel", "")),
            "account_type": data.get("account_type", ""),
            "status": data.get("status", ""),
            "auction": data.get("auction", ""),
            "auction_link": data.get("auction_link", ""),
            "with_dues": str(data.get("with_dues", "")) in ("1", "on", "true"),
            "title": data.get("title", ""),
            "body": data.get("body", ""),
            "reason": data.get("reason", ""),
        },
        "plan": plan,
        "token": token,
        "history": Broadcast.objects.select_related("created_by")[:HISTORY],
        # حالةُ البوّابة معروضةٌ دائماً لا عند الرفض وحده: من يفتح الشاشة
        # ليرسل رسالةً نصّيّة يجب أن يعرف قبل أن يكتب نصّاً أن البوّابة مقفلة.
        "sms_refusal": service.gateway_refusal(Channel.SMS),
        "sms_detail": service.gateway_detail(Channel.SMS),
        "unit_cost": service.unit_cost(),
    }


def broadcast(request, shell: dict | None = None):
    """تبويبُ الإرسال: وصفٌ، ثمّ معاينةٌ بالعدد والكلفة، ثمّ تنفيذٌ برمز.

    **ليست صفحةً بعد T941**: دُمجت في «الإشعارات» تبويباً، فالحارسُ صار على
    الفعل لا على الباب (`apps.console.alerts`). والمنطقُ لم يُمسّ سطراً —
    الخطواتُ الثلاث والرمزُ ومطابقةُ العدد كما هي.
    """
    shell = shell or {
        "which": "log",
        "may_send": True,
        "may_remind": False,
        "opens": "notifySend",
    }

    if request.method != "POST":
        return render(
            request, "console/notifications.html", shell | _form(request, request.GET)
        )

    step = (request.POST.get("step") or "").strip()
    audience = Audience.from_request(request.POST)
    channel = _channel(request.POST.get("channel", ""))

    if step != "send":
        # المعاينة: تُعَدّ وتُقدَّر ولا تكتب صفّاً. والرمزُ يُمنح هنا — وهو
        # هويّةُ الحدث التي يُشتقّ منها مفتاحُ التفرّد، فمعاينةٌ واحدةٌ لا
        # تُنتج بثّين مهما ضُغط «إرسال».
        plan = service.plan(channel=channel, audience=audience)
        return render(
            request,
            "console/notifications.html",
            shell | _form(request, request.POST, plan=plan, token=uuid.uuid4().hex),
        )

    token = (request.POST.get("token") or "").strip()
    if not token:
        messages.error(request, "لا رمزَ معاينة — أعِد المعاينة قبل الإرسال.")
        return redirect(BACK)

    raw_confirmed = (request.POST.get("confirmed_count") or "").strip()
    confirmed = int(raw_confirmed) if raw_confirmed.isdigit() else None

    try:
        row, created = service.queue(
            token=token,
            channel=channel,
            audience=audience,
            title=request.POST.get("title", ""),
            body=request.POST.get("body", ""),
            reason=request.POST.get("reason", ""),
            actor=request.user,
            confirmed_count=confirmed,
        )
    except service.BroadcastRefused as refusal:
        messages.error(request, str(refusal))
        return render(
            request,
            "console/notifications.html",
            shell
            | _form(
                request,
                request.POST,
                plan=service.plan(channel=channel, audience=audience),
                token=token,
            ),
        )

    if not created:
        # الرمزُ نفسُه وصل مرّتين: ضغطتان، أو إعادةُ تحميلٍ بعد `POST`. الصفُّ
        # واحد، ولا يُحجَز له عملٌ ثانٍ.
        messages.warning(
            request,
            f"هذا البثّ مسجَّلٌ من قبل (بثّ {row.pk}) — لم يُدرَج شيءٌ جديد.",
        )
        return redirect(BACK)

    audit.record(
        action="console.broadcast",
        entity=row,
        actor=request.user,
        note=(
            f"{row.get_channel_display()} إلى {row.recipient_count} مستلماً "
            f"({row.audience_label}) — {row.reason}"
            + (f" — كلفةٌ مقدَّرة {row.estimated_cost}" if row.estimated_cost else "")
        ),
    )

    booked = notification_tasks.dispatch(row)
    if booked is None:
        # لا وسيط. القرارُ مكتوبٌ والصفُّ قائم، والإدراجُ يُعاد حجزُه — ولا
        # يُقال «أُدرج» لشيءٍ لم يُدرَج.
        messages.warning(
            request,
            f"سُجّل البثّ {row.pk} إلى {row.recipient_count} مستلماً، "
            "ولم يُحجَز التنفيذ — لا وسيطَ مهامّ يعمل الآن.",
        )
    else:
        messages.success(
            request,
            f"سُجّل البثّ {row.pk} وحُجز إدراجُه لـ{row.recipient_count} مستلماً "
            "— أُدرج في الطابور، ولم يصل أحداً بعد.",
        )
    return redirect(BACK)


__all__ = ["broadcast"]
