"""تسليمُ ما في الطابور إلى الأجهزة. T943.

## ما كان ناقصاً

`broadcast.fan_out` يكتب صفَّ `Notification` بحالة `queued` لكلّ مستلم، **ولا
شيءَ في v2 كان يأخذ صفّاً `queued` ويسلّمه إلى مزوّد** — وصدرُ
`apps/console/broadcast.py` يقولها بنصّها. فالشاشةُ صادقةٌ حين تقول «أُدرج ولم
يصل أحداً بعد»، والوعدُ ناقص.

وهذا هو الجزءُ الناقص: يأخذ الطابورَ، ويجمع أجهزةَ كلِّ مستلم، ويُسلّم عبر
:mod:`apps.notifications.push`، ويكتب في الصفّ **ما جرى** — `sent` بمرجع
المزوّد، أو `failed` بسببه.

## والحالةُ تُكتب من جواب المزوّد لا من نيّتنا

`sent` تعني «قبِلها FCM»، لا «رآها صاحبُها». و`delivered` لا تُكتب هنا أبداً:
إقرارُ الوصول يأتي من التطبيق حين يفتح الإشعار، وكتابتُها عند الإرسال تجعل
السجلَّ يقول «وصلت» لجهازٍ مطفأٍ منذ أسبوع — وهو بعينه ما يجعل جوابَ الدعم
كذبةً مهذّبة.

## ومن لا جهازَ له يُقال عنه ذلك

إشعارٌ `push` لمستخدمٍ بلا جهازٍ مسجَّل لا يُترك في الطابور إلى الأبد: يُكتب
`failed` وسببُه «لا جهاز». والطابورُ الذي يحمل ما لا يمكن تسليمُه أبداً هو
طابورٌ لا يُقرأ.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from . import push
from .models import Channel, DeliveryState, Device, Notification

log = logging.getLogger(__name__)

#: كم إشعاراً يُؤخذ في الدفعة الواحدة. مهلةُ الشبكة عشرُ ثوانٍ لكلّ جهاز في
#: أسوأ الحالات، فدفعةٌ كبيرةٌ تعني مهمّةً تعمل ساعة. والباقي يُؤخذ في التالية.
BATCH = 200


def pending(limit: int = BATCH):
    """إشعاراتُ التطبيق التي لم تُسلَّم بعد — الأقدمُ أوّلاً.

    الأقدمُ أوّلاً لأن الطابورَ طابور: بثٌّ جديدٌ لا يتخطّى بثّاً ينتظر، وإلّا
    بقي القديمُ إلى الأبد كلّما جاء أحدث.
    """
    return (
        Notification.objects.filter(
            channel=Channel.PUSH, state=DeliveryState.QUEUED
        )
        .select_related("user")
        .order_by("created_at", "id")[:limit]
    )


def deliver(limit: int = BATCH) -> dict:
    """سلِّم دفعةً، واكتب في كلّ صفٍّ ما جرى له. يُرجع الأرقام.

    **ولا يُرفع خطأٌ لغياب الإعداد**: تُرجَع الأرقامُ ومعها السبب، فالشاشةُ
    تقوله للموظّف بدل صفحة خطأ، والمهمّةُ المؤجَّلة لا تُعيد المحاولة أبداً
    على شيءٍ لن يتغيّر حتى يضبطه إنسان.
    """
    rows = list(pending(limit))
    if not rows:
        return {"taken": 0, "sent": 0, "failed": 0}

    if not push.is_configured():
        return {
            "taken": 0,
            "sent": 0,
            "failed": 0,
            "blocked": "FCM غير مضبوط — لم يُلمس الطابور.",
        }

    # أجهزةُ المستلمين دفعةً واحدة: استعلامٌ لكلّ صفٍّ يعني مئتي رحلةٍ إلى
    # القاعدة قبل أوّل رحلةٍ إلى جوجل.
    owners = {row.user_id for row in rows}
    devices: dict[int, list[str]] = defaultdict(list)
    for user_id, token in Device.objects.filter(user_id__in=owners).values_list(
        "user_id", "token"
    ):
        devices[user_id].append(token)

    sent = failed = 0
    dead: set[str] = set()
    now = timezone.now()

    for row in rows:
        tokens = devices.get(row.user_id, [])
        title = str((row.data or {}).get("title", "")) or "حراج"

        if not tokens:
            row.state = DeliveryState.FAILED
            row.error = "لا جهازَ مسجَّلاً لهذا المستخدم."
            failed += 1
            continue

        try:
            outcome = push.send_to_tokens(
                title=title, body=row.body, tokens=tokens, data=row.data or {}
            )
        except push.PushNotConfigured as refusal:
            # ضُبط ثم فسد بين الفحص والإرسال — يُترك في الطابور، لا يُحرق.
            log.warning("push delivery halted: %s", refusal)
            break

        dead.update(outcome.dead)
        if outcome.sent:
            row.state = DeliveryState.SENT
            row.sent_at = now
            row.provider_reference = next(iter(outcome.names.values()), "")[:200]
            row.error = ""
            sent += 1
        else:
            row.state = DeliveryState.FAILED
            row.error = "; ".join(outcome.errors.values())[:2000]
            failed += 1

    touched = [r for r in rows if r.state != DeliveryState.QUEUED]
    with transaction.atomic():
        if touched:
            Notification.objects.bulk_update(
                touched,
                ["state", "sent_at", "provider_reference", "error"],
                batch_size=BATCH,
            )
        # التوكناتُ الميّتة تُحذف **بعد** كتابة النتائج: لو سقط الحذفُ بقيت
        # النتائجُ مكتوبةً، والعكسُ يعيد إرسالَ ما أُرسل.
        removed = Device.objects.filter(token__in=dead).delete()[0] if dead else 0

    return {
        "taken": len(touched),
        "sent": sent,
        "failed": failed,
        "devices_removed": removed,
    }


__all__ = ["BATCH", "deliver", "pending"]
