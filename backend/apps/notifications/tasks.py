"""إدراجُ البثّ في الطابور — مهمّةٌ مؤجَّلة لا دورةُ طلب. T832.

⚠️ **لا شيءَ هنا مجدوَل.** المهمّةُ تُحجَز بحدَثٍ — ضغطةُ إنسانٍ على «إرسال» —
لا بنبضةِ كرون. والمادة ٥-٢ تمنع مهمّةً مجدولةً تُنفق بلا موافقةٍ صريحة، وهذه
لا تُجدوَل أصلاً. والنمطُ نفسُه في `apps/odoo/tasks.py::dispatch`.

ولماذا مؤجَّلةٌ أصلاً
====================
لأن v1 يفعلها في الطلب: `foreach ($users as $user) { insertNotificationRecord(...) }`
— أي `INSERT` منفصلٌ لكلّ واحدٍ من أربعةٍ وأربعين ألفاً، في طلب HTTP واحد. وهو
إمّا يُسقط الخادم وإمّا تنتهي مهلتُه في المنتصف، فيُرسَل إلى نصف الجمهور ولا
يعرف أحدٌ أيُّ نصف — ولا `attempts` ولا استئناف.

والقفلُ (المادة ٥-١): بثٌّ واحدٌ يُدرَج مرّةً واحدة، ولو وصل حجزان.
"""

from __future__ import annotations

import logging

from celery import shared_task

from apps.core.locks import single_instance

from . import broadcast as service
from . import delivery
from .models import Broadcast, BroadcastState

log = logging.getLogger(__name__)


@shared_task(name="notifications.run_broadcast")
def run_broadcast(broadcast_id: int) -> dict:
    """أدرِج صفوفَ إشعارِ بثٍّ واحد. **لا تُسلَّم إلى مزوّد.**

    والقفلُ باسم البثّ لا باسم المهمّة: مهمّتان لبثّين مختلفين تعملان معاً،
    ومهمّتان لبثٍّ واحد لا. وقفلٌ باسم المهمّة وحدها كان سيجعل بثّاً ينتظر
    بثّاً آخرَ بلا سبب.
    """
    row = Broadcast.objects.filter(pk=broadcast_id).first()
    if row is None:
        return {"skipped": f"broadcast {broadcast_id} is gone"}

    with single_instance(f"notifications.broadcast:{row.pk}") as acquired:
        if not acquired:
            log.info("broadcast %s: another instance holds the lock", row.pk)
            return {"skipped": "another instance holds the lock"}
        try:
            return service.fan_out(row)
        except Exception as exc:  # noqa: BLE001 — يُكتب في الصفّ ثم يُرفع
            # الفشلُ يُكتب في الصفّ قبل أن يصعد: بثٌّ عالقٌ في `running` بلا
            # سببٍ مكتوب هو بالضبط ما لا تجيب عنه شاشةُ v1.
            Broadcast.objects.filter(pk=row.pk).update(
                state=BroadcastState.FAILED, error=str(exc)[:2000]
            )
            log.exception("broadcast %s failed", row.pk)
            raise


@shared_task(name="notifications.deliver_push")
def deliver_push(limit: int = delivery.BATCH) -> dict:
    """سلِّم ما في طابور إشعارات التطبيق إلى أجهزتها. T943.

    **ولا تُجدوَل** — كسابقتها وللمادة ٥-٢ نفسِها: تُحجَز بضغطةِ إنسانٍ على
    «سلِّم الطابور». والإرسالُ إلى الأجهزة لا يُحاسَب بالرسالة، لكنّ إشعاراً
    يصل في الثالثة فجراً بلا أن يقرّره أحدٌ هو الإنفاقُ نفسُه بعملةٍ أخرى.

    والقفلُ واحدٌ للطابور كلِّه لا لكلّ صفّ: مهمّتان تأخذان الدفعةَ نفسَها
    تُرسلان الإشعارَ مرّتين إلى الجهاز نفسِه.
    """
    with single_instance("notifications.deliver_push") as acquired:
        if not acquired:
            log.info("push delivery: another instance holds the lock")
            return {"skipped": "another instance holds the lock"}
        return delivery.deliver(limit)


def dispatch(broadcast: Broadcast) -> str | None:
    """احجز إدراجَ هذا البثّ فور كتابة قراره. يفشل بهدوءٍ بلا وسيط.

    بهدوءٍ لأن التطوير يعمل بلا Redis غالباً، ولا يجوز أن يسقط **قرارُ** البثّ
    لأن الحجز تعذّر — الصفُّ مكتوبٌ وقابلٌ لإعادة الحجز، والصامتُ الخطِر هو
    العكس: قرارٌ ضاع ومهمّةٌ تعمل.
    """
    try:
        result = run_broadcast.apply_async(args=[broadcast.pk])
    except Exception as exc:  # noqa: BLE001 — وسيطٌ غائب لا يُسقط القرار
        log.warning("could not dispatch broadcast %s: %s", broadcast.pk, exc)
        return None
    log.info("booked broadcast %s", broadcast.pk)
    return result.id


__all__ = ["deliver_push", "dispatch", "run_broadcast"]
