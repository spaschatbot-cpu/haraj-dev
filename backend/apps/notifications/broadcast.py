"""بثُّ رسالةٍ إلى جمهور — الكاتبُ الوحيد لـ:class:`Broadcast`. T832.

ثلاثةُ أشياءٍ تقع هنا وحدها، ولكلٍّ منها عطلٌ في v1 وُضعت لأجله:

١ — **البوّابةُ تُسأل قبل أن يُوعَد أحدٌ بشيء**
===============================================
`SMS_BACKEND` في هذه البيئة `console_backend`: يكتب الرسالةَ في سجلّ التطبيق
ولا يرسلها. وبوّابةٌ حقيقيّةٌ بلا `OURSMS_TOKEN` أسوأ — `apps.accounts.checks`
تمسكها بـ`accounts.E004`، وقبلها `E005` للمسار الذي لا يُستورَد أصلاً. فالشاشةُ
ترفض بالعربيّة **وتسمّي ما ينقص**، ولا تقول «تمّ» لبثٍّ ذهب إلى سجلّ.

والمعرفةُ تُقرأ من `apps.accounts.checks` نفسِها (`CONSOLE_BACKEND` و
`REAL_SMS_GATEWAYS`) ولا تُكرَّر هنا: قائمةٌ ثانيةٌ بمزوّدين ومتغيّراتِهم تعني
أن إضافةَ مزوّدٍ تُصلَح في موضعٍ وتُنسى في الآخر، فتمرّ الشاشةُ بينما يرفض
`check --deploy` — أو العكس، وهو الأسوأ.

٢ — **الكلفةُ تُعرَض قبل الزرّ، أو يُقال إنها غير معروفة**
==========================================================
`SMS_COST_PER_MESSAGE` بلا قيمةٍ افتراضيّة (انظر `config/settings/base.py`).
فإمّا رقمٌ من المالك، وإمّا جملةٌ تقول إنه ناقص — ولا رقمَ ثالثٌ نخترعه.
و`Decimal` في كلّ خطوة: المادة ٣-٢ لا تستثني تقديراً.

٣ — **مفتاحُ تفرُّدٍ يمنع الإرسال مرّتين**
==========================================
النمطُ من `apps.money.services.post` حرفياً: مفتاحٌ يُشتقّ من **هويّة الحدث**،
والقيدُ في القاعدة هو الحارس لا فحصٌ قبل الكتابة. وهويّةُ الحدث هنا هي **رمزُ
المعاينة**: الشاشةُ الأولى تعدّ الجمهور وتمنح رمزاً، والشاشةُ الثانية تُرسل
الرمزَ معها. فضغطتان على «إرسال» أو إعادةُ تحميلٍ بعد `POST` تحملان الرمزَ
نفسه ⇐ صفٌّ واحد؛ وبثٌّ ثانٍ مقصودٌ بالنصّ نفسه يمرّ بالمعاينة فيأخذ رمزاً
جديداً ⇐ صفٌّ ثانٍ. وهذا هو الفرقُ الذي يضيع حين يُشتقّ المفتاح من النصّ.

ولا يُرسَل شيءٌ من هنا
======================
هذه الوحدةُ تكتب صفَّ القرار وتحجز المهمّة، ثمّ تنتهي. والفانوسُ (`tasks.py`)
هو الذي يُدرج صفوفَ `Notification` بحالة `queued`. والتسليمُ إلى المزوّد ليس
مبنيّاً في v2 أصلاً — فلا شيء في هذا المستودع يأخذ صفّاً `queued` ويسلّمه —
وهو مكتوبٌ هنا كي لا يقرأ أحدٌ «أُدرج» على أنه «وصل».
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction as db_transaction

from .audience import Audience
from .models import Broadcast, BroadcastState, Channel

log = logging.getLogger(__name__)

#: فوق هذا العدد لا يمرّ البثُّ بلا تأكيدٍ صريحٍ **في الطلب**. T832.
#:
#: ولماذا خمسمئة بالذات: أكبرُ جمهورٍ «طبيعيٍّ» في هذه القاعدة هو مزايدو مزادٍ
#: واحد — قِيس على `haraj2_t307` في ١٤ سبتمبر ٢٠٢٦: أكثرُ مزادٍ فيه **٤٦٩**
#: مزايداً مختلفاً، وإجماليُّ المزايدين في القاعدة كلِّها ١٬٨٠٥ من أصل ٤٤٬٠٣٦
#: عميلاً. فتحت هذا الحدّ يكون الجمهورُ **مجموعةً يمكن تسميتها** («من زايد في
#: مزاد ٤٨»)، وفوقه يصير «كلّ من يطابق مرشّحاً» — وهي عتبةٌ في نوع القرار لا
#: في حجمه.
#:
#: ومن يريد تغييرَه يغيّر رقماً واحداً هنا، لا شرطاً في منظرٍ وآخرَ في قالب.
CONFIRM_ABOVE = 500

#: كم صفَّ إشعارٍ يُكتب في الدفعة الواحدة داخل المهمّة المؤجَّلة.
#: `bulk_create` بأربعةٍ وأربعين ألف كائنٍ دفعةً واحدة يبني القائمةَ كلَّها في
#: الذاكرة أولاً؛ وألفٌ هو ما يستعمله `queue_auction_reminder` أصلاً.
BATCH = 1000


class BroadcastRefused(Exception):
    """رفضٌ يُعرَض للموظّف كما هو — بالعربية، ويسمّي ما ينقص."""


# ---------------------------------------------------------------------------
# البوّابة
# ---------------------------------------------------------------------------


def gateway_refusal(channel: str) -> str:
    """ما الذي يمنع هذه القناة من الإرسال اليوم — أو `""` إن لم يمنعها شيء.

    القنواتُ المجّانيّة (`in_app` و`push`) تكتب في جدولنا ولا تعبر بوّابة، فلا
    شيء يمنعها. و`sms` وحدها تُسأل، لأنها وحدها تُكلّف.
    """
    if channel != Channel.SMS:
        return ""

    from django.utils.module_loading import import_string

    from apps.accounts.checks import CONSOLE_BACKEND, REAL_SMS_GATEWAYS

    backend = str(getattr(settings, "SMS_BACKEND", "") or "").strip()
    if not backend:
        return "لا بوّابةَ رسائل مضبوطة: `SMS_BACKEND` فارغ."
    if backend == CONSOLE_BACKEND:
        return (
            "بوّابةُ الرسائل في هذه البيئة هي بوّابةُ السجلّ "
            f"(`SMS_BACKEND={backend}`): تكتب نصَّ الرسالة في سجلّ التطبيق "
            "ولا تُرسلها إلى أحد. اضبط `SMS_BACKEND` على مزوّدٍ حقيقيّ "
            "(`apps.accounts.sms.oursms_backend`) قبل البثّ."
        )
    try:
        import_string(backend)
    except ImportError:
        # نفسُ ما يمسكه `accounts.E005`: خطأٌ إملائيٌّ لا يظهر عند الإقلاع،
        # لأن `import_string` تُنادى **لحظةَ الإرسال** — أي بعد أن يكون
        # الموظّف قد ضغط وقُرئ له «تمّ».
        return f"`SMS_BACKEND` هو {backend!r} ولا يمكن استيراده (accounts.E005)."

    missing = [
        name
        for name in REAL_SMS_GATEWAYS.get(backend, ())
        if not str(getattr(settings, name, "") or "").strip()
    ]
    if missing:
        return (
            f"البوّابة حقيقيّة ({backend}) و{'، '.join(missing)} فارغ "
            "(accounts.E004) — أوّلُ إرسالٍ يرفع `SmsSendFailed` ولا تخرج رسالة."
        )
    return ""


# ---------------------------------------------------------------------------
# الكلفة
# ---------------------------------------------------------------------------


def unit_cost() -> Decimal | None:
    """كلفةُ الرسالة الواحدة من الإعدادات، أو `None` حين لا قيمةَ لها.

    `None` تعني «لا يُعرف» ولا تعني صفراً، والفرقُ هو كلُّ ما في الأمر.
    """
    raw = str(getattr(settings, "SMS_COST_PER_MESSAGE", "") or "").strip()
    if not raw:
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        log.warning("SMS_COST_PER_MESSAGE is not a number: %r", raw)
        return None
    return value if value >= 0 else None


@dataclass(frozen=True)
class Plan:
    """ما سيقع لو ضُغط الزرّ — يُعرَض كاملاً **قبل** أن يُضغط."""

    channel: str
    audience: Audience
    recipients: int
    unit_cost: Decimal | None
    estimated_cost: Decimal | None
    refusal: str
    #: أيحتاج تأكيداً صريحاً؟ انظر :data:`CONFIRM_ABOVE`.
    needs_confirmation: bool

    @property
    def costs_money(self) -> bool:
        return self.channel == Channel.SMS

    @property
    def cost_unknown(self) -> bool:
        """قناةٌ تُكلّف ولا نعرف كم. تُقال، ولا يُخترع لها رقم."""
        return self.costs_money and self.estimated_cost is None


def plan(*, channel: str, audience: Audience) -> Plan:
    """عُدّ الجمهور، وقدّر الكلفة، واسأل البوّابة — بلا كتابةِ صفٍّ واحد."""
    recipients = audience.count()
    cost = unit_cost()
    total = None
    if channel == Channel.SMS and cost is not None:
        total = (cost * recipients).quantize(Decimal("0.01"))
    return Plan(
        channel=channel,
        audience=audience,
        recipients=recipients,
        unit_cost=cost if channel == Channel.SMS else None,
        estimated_cost=total,
        refusal=gateway_refusal(channel),
        needs_confirmation=recipients > CONFIRM_ABOVE,
    )


# ---------------------------------------------------------------------------
# القرار
# ---------------------------------------------------------------------------


@db_transaction.atomic
def queue(
    *,
    token: str,
    channel: str,
    audience: Audience,
    title: str,
    body: str,
    reason: str,
    actor,
    confirmed_count: int | None = None,
) -> tuple[Broadcast, bool]:
    """اكتب قرارَ البثّ مرّةً واحدة. يُرجع الصفَّ و«أجديدٌ هو؟».

    الترتيبُ هنا هو التصميم:

    ١. الرمزُ المكرّر يقصُر الطريقَ قبل أيّ عدٍّ أو تحقّق — ضغطتان على «إرسال»
       أو إعادةُ تحميلٍ بعد `POST` تُرجعان الصفَّ الأوّل ولا تعدّان جمهوراً؛
    ٢. ثمّ يُرفض ما يُرفض، ولا صفَّ قد كُتب بعد؛
    ٣. **ثمّ يُعاد العدُّ على الخادم**، ولا يُصدَّق العددُ الذي عاد من المتصفّح
       — الرقمُ الذي في الاستمارة **مُدَّعىً** يقول «هذا ما رأيتُه»، ويُقارَن
       بما يقوله الخادمُ الآن؛ فإن اختلفا رُفض البثُّ وأُعيدت المعاينة. (وذلك
       هو معنى «التأكيدُ علمٌ في الطلب»: تأكيدٌ في الجافاسكربت يُلتفّ عليه
       بطلبٍ مباشر، ورقمٌ يجب أن يطابق لا يُلتفّ عليه بحذف خانة.)
    """
    key = f"broadcast:{token}"
    existing = Broadcast.objects.filter(idempotency_key=key).first()
    if existing is not None:
        log.info("broadcast: %s already recorded as %s", key, existing.pk)
        return existing, False

    body = (body or "").strip()
    if not body:
        raise BroadcastRefused("نصُّ الرسالة مطلوب.")
    if not (reason or "").strip():
        # السببُ إجباريٌّ للسبب نفسه الذي جعله إجبارياً في أفعال المال:
        # «من بثَّ ولماذا» سؤالٌ يُسأل بعد شهر، ولا يُجاب بنصِّ الرسالة وتاريخ.
        raise BroadcastRefused("سببُ البثّ مطلوب — ويدخل سجلَّ التدقيق.")

    refusal = gateway_refusal(channel)
    if refusal:
        raise BroadcastRefused(refusal)

    fresh = plan(channel=channel, audience=audience)
    if fresh.recipients == 0:
        raise BroadcastRefused("لا أحدَ يطابق هذا المرشّح — لم يُدرَج شيء.")

    if fresh.needs_confirmation or confirmed_count is not None:
        if confirmed_count is None:
            raise BroadcastRefused(
                f"هذا البثّ إلى {fresh.recipients} مستلماً ولم يصل تأكيدُ العدد "
                "— أعِد المعاينة واكتب العدد لتأكيد أنك قرأته."
            )
        if confirmed_count != fresh.recipients:
            raise BroadcastRefused(
                f"العددُ تغيّر منذ المعاينة: أكّدتَ {confirmed_count} والجمهورُ "
                f"الآن {fresh.recipients}. راجِع الجمهورَ ثمّ أكِّد."
            )

    try:
        row = Broadcast.objects.create(
            channel=channel,
            title=(title or "").strip(),
            body=body,
            audience=audience.as_dict(),
            audience_label=audience.describe(),
            recipient_count=fresh.recipients,
            unit_cost=fresh.unit_cost,
            estimated_cost=fresh.estimated_cost,
            idempotency_key=key,
            created_by=actor,
            reason=reason.strip(),
        )
    except IntegrityError:
        # سباقٌ على الرمز نفسه: طلبان في نفس عشراتِ الميلي‑ثانية مرّا الفحصَ
        # الأوّل معاً. القيدُ في القاعدة هو الحارس، والخاسرُ يقرأ صفَّ الفائز
        # — لأن من ضغط مرّتين له بثٌّ واحد، لا خطأ.
        winner = Broadcast.objects.get(idempotency_key=key)
        return winner, False

    return row, True


# ---------------------------------------------------------------------------
# الإدراج — يُنادى من المهمّة المؤجَّلة وحدها
# ---------------------------------------------------------------------------


def fan_out(broadcast: Broadcast) -> dict:
    """اكتب صفَّ إشعارٍ لكلّ مستلم. **لا يُرسل، ولا يعبر بوّابة.**

    v1 يفعل هذا **داخل دورة الطلب**: `INSERT` منفصلٌ لكلّ مستخدم (تعليقُ الكود
    هناك يقول «~34k rows»)، أو طلبُ HTTPS لكلّ توكن في FCM بلا تجزئةٍ ولا مهلة.
    وأربعةٌ وأربعون ألفَ صفٍّ في طلبٍ واحد تُسقط الخادم أو تنتهي مهلتُه في
    منتصفها — فيبقى نصفُ الجمهور مرسَلاً إليه ونصفُه لا، بلا ما يُستأنف منه.

    وهنا تقع في مهمّةٍ مؤجَّلة، على دفعاتٍ من :data:`BATCH`، و`ignore_conflicts`
    ليست هنا عمداً: `Notification` بلا قيد تفرّدٍ على (مستخدم، بثّ)، والحارسُ
    ضدّ التكرار هو مفتاحُ :class:`Broadcast` نفسُه — بثٌّ واحدٌ لا يُنشأ مرّتين،
    فلا تُدرَج صفوفُه مرّتين.
    """
    from django.utils import timezone

    from .models import Notification

    if broadcast.state in (BroadcastState.DONE, BroadcastState.RUNNING):
        return {"skipped": f"broadcast {broadcast.pk} is {broadcast.state}"}

    broadcast.state = BroadcastState.RUNNING
    broadcast.started_at = timezone.now()
    broadcast.save(update_fields=["state", "started_at"])

    audience = Audience.from_dict(broadcast.audience)
    ids = list(audience.queryset().values_list("id", flat=True))

    written = 0
    for start in range(0, len(ids), BATCH):
        chunk = ids[start : start + BATCH]
        Notification.objects.bulk_create(
            [
                Notification(
                    user_id=uid,
                    channel=broadcast.channel,
                    template="console_broadcast",
                    body=broadcast.body,
                    data={"broadcast": broadcast.pk, "title": broadcast.title},
                )
                for uid in chunk
            ],
            batch_size=BATCH,
        )
        written += len(chunk)

    broadcast.queued_count = written
    # الفرقُ بين ما عُرض وما أُدرج يُكتب ولا يُبتلع: مرشّحٌ يعطي عدداً وقتَ
    # المعاينة وعدداً آخرَ وقتَ التنفيذ (حسابٌ عُطّل، فاتورةٌ سُدّدت) حقيقةٌ
    # يجب أن تُقرأ في الصفّ، لا أن تُخفى بمساواة العمودين.
    broadcast.failed_count = max(broadcast.recipient_count - written, 0)
    broadcast.state = BroadcastState.DONE
    broadcast.finished_at = timezone.now()
    broadcast.save(
        update_fields=["queued_count", "failed_count", "state", "finished_at"]
    )
    log.info("broadcast %s: queued %s notifications", broadcast.pk, written)
    return {"broadcast": broadcast.pk, "queued": written}


__all__ = [
    "BATCH",
    "CONFIRM_ABOVE",
    "BroadcastRefused",
    "Plan",
    "fan_out",
    "gateway_refusal",
    "plan",
    "queue",
    "unit_cost",
]
