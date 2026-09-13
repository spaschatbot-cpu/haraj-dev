"""Interpreting what the payment gateway said, separately from receiving it.

The sibling of `apps.odoo.processing`, and deliberately shaped like it. The two
boundaries share one table (`odoo.InboundMessage`) and nothing else: they read
different field names, they trust different secrets, and neither may interpret
the other's bodies — that last one is T913's third finding, and it is checked
here as it is checked there.

Why this is a module and not a method on `PaymentCallbackView`
--------------------------------------------------------------
Because a stored message has to be interpretable **again**. When it lived on the
view there was exactly one caller — the HTTP request that first delivered the
body — so a gateway message that failed had no way back at all: the retry cron
filters on Odoo's source, and the console's only button called Odoo's
interpreter, which answers a foreign source with `ignored`. `ignored` is
terminal. A real payment could reach the gateway, fail here on a lock timeout,
and then be *ended* by the one button support was given.

So interpretation is a function anything may call on a stored row, and the three
callers — the callback, the console button, and `tasks.retry_failed_gateway` —
all call this one. Same rule as the Odoo boundary: not a copy, not a variant
that skips a check because a human asked this time.

الحمولةُ الموقّعة ليست مصدرَ الحقيقة
------------------------------------
كانت هي المصدرَ الوحيد هنا: يُقرأ منها المبلغُ والحالةُ والمرجع، ويُقيَّد على
أساسها. وv1 — الذي أخطأ في كل شيءٍ تقريباً في هذا المسار — **لا يفعل ذلك
أبداً**: في `moyasar_webhook.php` سطرٌ بعنوان «Fetch من Moyasar (مصدر الحقيقة)»،
وفي `wallet_topup_card_done.php` تعليقٌ يقول السبب: «Use the amount Moyasar
confirmed (in SAR) to avoid tampering».

والتوقيعُ يُثبت شيئاً واحداً: أن من أرسل يعرف السرّ. لا يُثبت أن ما في الجسم هو
ما جرى عند البوّابة، ولا أنه لم يُعَد إرسالُ رسالةٍ قديمةٍ صحيحةِ التوقيع. لذلك
صار كلُّ تفسيرٍ يبدأ باستعلامٍ تأكيديّ (:func:`apps.money.moyasar.fetch_payment`)،
وما يُقرأ منه هو **ردُّ البوّابة** لا الحمولة.

وحين لا يكون الاستعلامُ ممكناً — لا مفتاحَ سرّيّاً في هذه البيئة — **لا يُقيَّد
من الحمولة وحدها**: تُكتب الرسالةُ `failed` بالسبب وتنتظر في طابور الإعادة
(المادة ٢-٢). وذلك يرفض ولا يخمّن، والتخمينُ هنا مالٌ يدخل الدفتر.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from apps.odoo.models import InboundMessage, InboundState

from . import moyasar, services, units
from .models import PaymentIntent

log = logging.getLogger(__name__)

#: The only source whose messages this module may interpret. See the module
#: docstring, and `apps.odoo.processing.INTERPRETED_SOURCE` for the mirror.
INTERPRETED_SOURCE = "payment_gateway"

#: The states a message can be interpreted *from*. `received` is the first
#: delivery; `failed` is the retry queue. Everything else is either terminal or
#: evidence nobody vouched for.
INTERPRETABLE = (InboundState.RECEIVED, InboundState.FAILED)


class Unconfirmed(Exception):
    """لم نستطع أن نقرأ من البوّابة ما جرى. لا يُقيَّد شيءٌ على الظنّ."""


def payment_id_of(payload: dict) -> str:
    """رقمُ الدفعة من أيٍّ من الأشكال الثلاثة التي ترسلها Moyasar.

    الثلاثةُ منقولةٌ من `moyasar_webhook.php` حرفيّاً: `data.id` (شكلُ الحدث
    الحديث) و`payment.id` و`id` (الدفعةُ عاريةً). v1 يجرّبها بالترتيب لأنه رأى
    الثلاثة فعلاً — وقراءةُ شكلٍ واحدٍ فقط تعني رسالةً بلا رقمٍ ثم «missing
    payment id» على دفعةٍ حقيقيّة.
    """
    for candidate in (
        (payload.get("data") or {}).get("id"),
        (payload.get("payment") or {}).get("id"),
        payload.get("id"),
    ):
        if isinstance(candidate, str) and candidate:
            return candidate
    return ""


def _body_of(payload: dict) -> dict:
    """جسمُ الدفعة داخل الحمولة — مغلَّفاً كان أو عارياً."""
    for key in ("data", "payment"):
        nested = payload.get(key)
        if isinstance(nested, dict) and nested:
            return nested
    return payload


def confirm(payload: dict) -> tuple[dict, str]:
    """ما تقوله البوّابةُ عن هذه الدفعة، ومن أين عرفناه.

    يُعاد الزوجُ (جسمُ الدفعة، سطرٌ يُكتب في ملاحظة الرسالة) — والسطرُ الثاني
    ليس زينة: بعد شهرٍ يكون الفرقُ بين «قُيِّدت باستعلامٍ من البوّابة» و«قُيِّدت
    من حمولةٍ موقّعة» هو كلَّ ما يُجيب سؤال «على أيّ دليلٍ دخل هذا المال؟».
    """
    payment_id = payment_id_of(payload)
    confirming = bool(getattr(settings, "PAYMENT_CONFIRM_WITH_GATEWAY", True))
    is_moyasar = str(settings.PAYMENT_GATEWAY).strip().lower() == "moyasar"

    if not confirming:
        # إعلانُ مشغّلٍ صريحٌ بأن بوّابةَ هذه البيئة بلا واجهةِ استعلام. يُكتب
        # في الملاحظة ولا يُسكت عنه.
        return _body_of(payload), "المصدر: الحمولة الموقّعة (الاستعلام التأكيدي مطفأ)"

    if not is_moyasar:
        raise Unconfirmed(
            f"الاستعلام التأكيدي غير مُنفَّذ لبوّابة {settings.PAYMENT_GATEWAY!r} — "
            "اضبط PAYMENT_CONFIRM_WITH_GATEWAY=False صراحةً إن كانت بلا واجهة استعلام"
        )

    if not moyasar.is_configured():
        raise Unconfirmed(
            "مفتاح Moyasar السرّي غير مضبوط؛ لا يُقيَّد من الحمولة وحدها"
        )

    try:
        payment = moyasar.fetch_payment(payment_id)
    except moyasar.MoyasarUnreachable as exc:
        # المادة ٢-٤: عدمُ الوصول ليس دليلاً على شيء. `failed` طابورُ إعادةٍ
        # لا قبر، والمحاولةُ التالية بتراجعٍ أسّيّ في `tasks.retry_failed_gateway`.
        raise Unconfirmed(f"تعذّر الاستعلام من البوّابة: {exc}") from exc
    except (moyasar.MoyasarRejected, moyasar.MoyasarDisabled) as exc:
        raise Unconfirmed(f"البوّابة رفضت الاستعلام: {exc}") from exc

    return payment, "المصدر: استعلام تأكيدي من البوّابة"


def reference_in(payment: dict, payload: dict) -> str:
    """مرجعُ النيّة الذي تُسنَد به هذه الدفعة، بثلاث محاولاتٍ بترتيب الثقة.

    ١. `metadata.reference` في **ردّ البوّابة** — ما كتبناه نحن عند الإنشاء.
    ٢. `invoice_id` — فاتورتُنا المستضافة، ومنها النيّةُ عبر
       `gateway_checkout_id`. لازمةٌ لأن انتقال `metadata` من الفاتورة إلى
       الدفعة **غير مقيسٍ عندنا** (لم تُنادَ Moyasar الحقيقيّة بعد)، وبناءُ
       الإسناد على افتراضٍ لم يُشاهَد هو ما صنع دفعاتِ v1 الـ~٢١٠٠ بلا صاحب.
    ٣. `metadata.reference` في الحمولة — آخرُ ما يُسأل لأنه أضعفُ دليلٍ هنا.

    ولا يخترع هذا الغيابُ مالاً: مرجعٌ فارغٌ يعني نيّةً غيرَ معروفة، و
    `apply_gateway_payment` تحفظ المبلغ كاملاً في الحساب المعلَّق بانتظار إنسان.
    """
    reference = str((payment.get("metadata") or {}).get("reference") or "").strip()
    if reference:
        return reference

    invoice_id = str(payment.get("invoice_id") or "").strip()
    if invoice_id:
        intent = PaymentIntent.objects.filter(
            gateway_checkout_id=invoice_id
        ).first()
        if intent is not None:
            return intent.reference

    return str((payload.get("metadata") or {}).get("reference") or "").strip()


def succeeded_by(status_raw: str) -> bool:
    """هل هذه الكلمةُ من كلمات النجاح؟ — بعد تطبيعٍ في الطرفين.

    كانت المقارنةُ حرفيّةً على النصّ الخام، فـ`"Paid"` و`" paid"` تُقرآن **فشلاً**
    ثم تُكتب النيّةُ `failed` ويُترك مالٌ محصَّلٌ بلا قيد. والكلماتُ تبقى إعداداً
    لا شيفرة: كلمةُ نجاحٍ جديدةٌ من البوّابة يجب ألّا تُقرأ نجاحاً بالمصادفة.
    """
    words = {str(word).strip().lower() for word in settings.PAYMENT_SUCCESS_STATUSES}
    return status_raw.strip().lower() in words


def interpret(message: InboundMessage) -> InboundMessage:
    """Read one stored gateway notification and record what came of it.

    Safe to call again on anything, and safe to call on a row that is not ours.
    Two refusals, and both leave the row **exactly as it was**:

    * a message from any other source. Marking it would be the very bug this
      module exists to fix, in the other direction: an Odoo row ended here is an
      Odoo row `apps.odoo.tasks.due_messages` never offers again.
    * a message whose signature did not verify. It is stored (Article 2-2) and
      interpreted by nothing — T913. A replay button is not an exemption.

    A row that already reached `processed` or `ignored` is returned untouched,
    which is what lets the callback, the console button and the retry task share
    this call.
    """
    if message.source != INTERPRETED_SOURCE:
        log.warning(
            "gateway interpret: refused message %s from source %r",
            message.pk,
            message.source,
        )
        return message

    if message.state == InboundState.REJECTED_SIGNATURE:
        log.warning("gateway interpret: refused unsigned message %s", message.pk)
        return message

    if message.state not in INTERPRETABLE:
        log.info("gateway interpret: message %s already %s", message.pk, message.state)
        return message

    # The stored payload, not the caller's copy of it. The row is the record —
    # on a duplicate delivery the caller holds a body that never became this
    # message, and interpreting that instead would credit against evidence
    # nobody can read back.
    payload = message.payload or {}

    try:
        payment, provenance = confirm(payload)
    except Unconfirmed as exc:
        # لا يُقيَّد شيء، ولا تُسقَط الرسالة. طابورُ الإعادة يعاود المحاولة،
        # والملاحظةُ تقول لماذا فشلت — المادة ٢-٢.
        message.state = InboundState.FAILED
        message.note = str(exc)
        return _seal(message)

    reference = reference_in(payment, payload)
    status_raw = str(payment.get("status", ""))
    # عملةُ البوّابة لا عملتُنا: المقسومُ عليه يتبع العملة، وقراءةُ دينارٍ كويتيّ
    # بأُسّ الريال تعطي عشرةَ أضعافه. وغيابُها يعني عملةَ المنصّة.
    currency = str(payment.get("currency") or settings.CURRENCY)

    try:
        # **بالتحويل، لا بالقراءة الخام.** Moyasar ترسل الهللة، وقراءتُها ريالاً
        # كانت تُنتج مئةَ ضعفِ المبلغ في كل دفعة.
        amount = units.from_gateway(payment.get("amount"), currency)
    except units.AmountUnreadable as exc:
        amount = None
        unreadable = str(exc)

    if amount is None or amount <= 0:
        message.state = InboundState.FAILED
        message.note = (
            unreadable
            if amount is None
            else f"مبلغ غير موجب في الرسالة: {payment.get('amount')!r}"
        )
        return _seal(message)

    try:
        outcome = services.apply_gateway_payment(
            reference=reference,
            payment_id=str(payment.get("id") or payment_id_of(payload)),
            amount=amount,
            currency=currency,
            status_raw=status_raw,
            succeeded=succeeded_by(status_raw),
        )
    except Exception as exc:  # noqa: BLE001 — a failure here is data
        # Article 2-2: a raise that escapes leaves the row with an empty
        # note and nothing looking at it. `failed` is now a queue rather
        # than a grave, which is the whole point of this module.
        log.exception("gateway interpret: message %s raised", message.pk)
        message.state = InboundState.FAILED
        message.note = f"{type(exc).__name__}: {exc}"
        return _seal(message)

    message.state = {
        "credited": InboundState.PROCESSED,
        "suspense": InboundState.PROCESSED,
        "ignored": InboundState.IGNORED,
    }.get(outcome.disposition, InboundState.FAILED)
    message.note = f"{outcome.note} — {provenance}"
    message.resulting_transaction = outcome.transaction
    return _seal(message)


def _seal(message: InboundMessage) -> InboundMessage:
    """اكتب نتيجةَ المحاولة على الصفّ. مخرجٌ واحدٌ لكل الفروع.

    كان كلُّ فرعٍ يسقط إلى نفس كتلة الحفظ في آخر الدالّة، فإضافةُ فرعٍ جديدٍ
    (الاستعلامُ التأكيديّ) كانت تعني إمّا تعشيقاً أعمق وإمّا `return` ينسى
    زيادةَ `attempts` — ورسالةٌ لا تُعدّ محاولاتها لا تخرج من طابور الإعادة أبداً.
    """
    message.attempts += 1
    message.processed_at = timezone.now()
    message.save(
        update_fields=[
            "state",
            "note",
            "resulting_transaction",
            "attempts",
            "processed_at",
        ]
    )
    log.info("gateway interpret: message %s -> %s", message.pk, message.state)
    return message


__all__ = [
    "INTERPRETED_SOURCE",
    "Unconfirmed",
    "confirm",
    "interpret",
    "payment_id_of",
    "reference_in",
    "succeeded_by",
]
