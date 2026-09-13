"""ترجمةُ ما يقوله أودو إلى ما يفهمه هذا النظام — كلمةً كلمة.

## العطل الذي وُجدت هذه الوحدة لإغلاقه

كان :func:`apps.odoo.processing._interpret` يوجّه بمطابقةٍ **حرفيّة** لخمس
كلماتٍ منقوطة اخترعناها نحن — ``payment.posted`` وأخواتها — و:mod:`apps.odoo.views`
يخزّن ``payload["event"]`` كما وصل بلا تطبيعٍ إطلاقاً.

**وأودو لا يتكلّم بهذه اللغة.** عقدُه الحقيقيّ — الموثَّق بيد v1 في
``OdooWebhookApiController::extractEvent``، وهي ستّون سطراً مبنيّةً على ٨٥٦ حدثاً
مسجَّلاً في الإنتاج — يرسل فعلاً مجرّداً بلا اسم موضوعه: ``posted`` · ``created``
· ``updated`` · ``cancelled`` · **أو فارغاً**. والموضوعُ (دفعة؟ فاتورة؟ استرداد؟)
يُعرف عند v1 من **المسار** (``/odoo/cash-receipt`` · ``/odoo/invoice-created`` ·
``/odoo/refund-updated``)، ونحن نستقبل على نقطةٍ واحدة — فيُعرف هنا من الحقول.

فكلُّ رسالةٍ حقيقيّةٍ كانت ستسقط في ``handler is None`` ⇒ ``ignored``.
و``ignored`` **نهائيّة**: لا يلتقطها طابورُ إعادة المحاولة، ولا زرُّ الإعادة
يُخرجها منها. أي أن المال يصل ولا يُقيَّد، **بصمتٍ وبلا إنذار، إلى الأبد** — وهو
عينُ العطل الذي وُجد الفيز ٠٠٣ كلُّه ليمنعه.

## لماذا وحدةٌ مستقلّة لا دالّةٌ في `views`

لأن لها ثلاثة قرّاء: الاستقبال (يختم الاسم القانونيّ على الصفّ)، وإعادةُ التفسير
لصفٍّ قديم، وأيُّ فحصٍ يريد أن يسأل «ماذا كانت هذه الرسالة تعني؟» بلا أن يستقبل
شيئاً. وقاعدةٌ واحدةٌ في مكانٍ واحد (المادة ٤-٥) — لا نسخةٌ في كلِّ موضع.

## ما لم يُنقل من v1 عمداً

v1 يرفع إنذاراً حين يتكرّر **الحدثُ المجهولُ نفسه** لمعرّف دفعةٍ واحد أكثر من
مرّة — «الكناريّ» الذي يقول إن مفردات أودو انزاحت. لم يُبنَ هنا: هو نظامُ تنبيهٍ
لا ترجمة، ومحلُّه صندوقُ الوارد. والمجهولُ هنا **يحتفظ باسمه الخام** في عمود
``event`` فيُقرأ في الصندوق ويُعدّ، وذلك ما يجعل بناءه لاحقاً استعلاماً لا تنقيباً.
"""

from __future__ import annotations

__all__ = ["TOPICS", "VERBS", "canonical_event", "topic_of", "verb_of"]

#: الأفعال بعد التطبيع. `unknown` ليست فعلاً — هي اعترافٌ بأن المفردة انزاحت.
VERBS = ("posted", "created", "updated", "cancelled", "unknown")

#: المواضيع التي لهذا النظام فروعٌ فيها.
TOPICS = ("payment", "invoice", "refund")

#: كلماتُ أودو للتأكيد. منقولةٌ حرفيّاً عن `extractEvent` في v1 — وكلُّ واحدةٍ
#: منها وصلت فعلاً في الإنتاج، فلا تُختصر القائمةُ «تبسيطاً».
_POSTED_WORDS = frozenset(
    {"posted", "paid", "done", "confirmed", "approved", "reconciled", "completed"}
)

#: وكلماتُه للإلغاء والعكس. `reversed`/`reversal` هنا لأن عكسَ قيدٍ في أودو
#: **لا يصل كـ`cancelled`**: يصل كـ`updated` وحالتُه `posted` — والحقيقةُ في
#: `payment_state` وحده (حادثة `INV/2026/03708`، ٢٠٢٦-٠٨-٠٣ في v1).
_CANCEL_WORDS = frozenset(
    {"cancel", "cancelled", "canceled", "reversed", "reversal", "rejected", "void"}
)

#: خريطةُ (موضوع، فعل) → اسم الفرع في :mod:`apps.odoo.processing`.
#:
#: ليست تطابقاً واحداً لواحد، ولكلِّ انحرافٍ سببُه:
#:
#: * ``invoice.created`` → ``invoice.updated``: الفرعُ واحدٌ يُنشئ إن لم يجد،
#:   فاسمان لمسلكٍ واحد كذبةٌ صغيرة تُقرأ في السجلّ على أنها فرعان.
#: * ``refund.posted`` → ``refund.confirmed``: «مرحَّل» عند أودو هو «نُفِّذ»
#:   عندنا، وهو الاسم الذي كُتب به الفرع قبل هذه الوحدة ولا يُعاد تسميته لأجلها.
#: * ``refund.created/updated`` → ``refund.pending``: v1 يجعل كلَّ ما ليس
#:   مرحَّلاً ولا ملغى «معلّقاً» ولا يحرّك به فلساً. فرعٌ يقولها ويتوقّف.
_ROUTE = {
    ("payment", "posted"): "payment.posted",
    ("payment", "updated"): "payment.updated",
    ("payment", "created"): "payment.created",
    ("payment", "cancelled"): "payment.cancelled",
    ("invoice", "posted"): "invoice.posted",
    ("invoice", "updated"): "invoice.updated",
    ("invoice", "created"): "invoice.updated",
    ("invoice", "cancelled"): "invoice.cancelled",
    ("refund", "posted"): "refund.confirmed",
    ("refund", "cancelled"): "refund.rejected",
    ("refund", "created"): "refund.pending",
    ("refund", "updated"): "refund.pending",
}

#: الأسماءُ القانونيّة كما هي. رسالةٌ تحملها أصلاً تمرّ بلا ترجمة — فاختباراتُنا
#: وأدواتُنا وصفوفُنا المخزَّنة تبقى صالحة، ولا تصير هذه الوحدة كسراً للقديم.
_CANONICAL = frozenset(_ROUTE.values())


def _low(value) -> str:
    return str(value or "").strip().lower()


def verb_of(payload: dict) -> str:
    """الفعلُ الذي تعنيه الرسالة، مطبَّعاً على مفردات v1 الستّين سطراً.

    الترتيب هو القاعدة، لا تفصيلٌ في التنفيذ — وكلُّ خطوةٍ فيه أُضيفت في v1 بعد
    حادثة:

    1. ``payment_state`` بكلمةِ إلغاءٍ **يغلب كلَّ شيء**. عكسُ القيد يصل بفعلٍ
       يقول ``updated`` وحالةٍ تقول ``posted``؛ ولو قُرئ بهما لبقيت وديعةٌ
       مقيَّدةٌ لمالٍ لم يعد عند أودو.
    2. فعلٌ فارغ ⇒ يُستنتج من ``state``. أودو يرسل الحالة بلا فعلٍ أحياناً.
    3. ``updated`` + حالةٌ مؤكِّدة ⇒ ``posted``. هذه هي الرسالةُ الثالثة التي
       تحمل ربطَ الفاتورة، والتي ابتلعها v1 مرّةً فبقيت وديعةٌ مسوّاةٌ تُعرض
       قابلةً للاسترداد أسبوعين.
    4. ``updated`` + حالةُ إلغاء ⇒ ``cancelled``. الثغرةُ المرآة، سُدّت في v1
       يوم ٢٠٢٦-٠٨-٠٣: إلغاءٌ بلا حقل ``payment_state`` كان يمرّ «تحديثاً
       روتينيّاً» فيُرمى.
    5. وما بقي مجهولاً يُسمّى ``unknown`` ولا يُخمَّن.
    """
    raw_event = _low(payload.get("event") or payload.get("type"))
    raw_state = _low(
        payload.get("state") or payload.get("payment_state") or payload.get("status")
    )

    # (1) — الأقوى، ويسبق كلَّ شيءٍ آخر.
    if _low(payload.get("payment_state")) in _CANCEL_WORDS:
        return "cancelled"

    event = raw_event
    if not event:  # (2)
        if raw_state in _CANCEL_WORDS:
            event = "cancelled"
        elif raw_state in _POSTED_WORDS:
            event = "posted"
        elif raw_state == "draft":
            event = "created"

    if event == "updated":
        if raw_state in _POSTED_WORDS:  # (3)
            event = "posted"
        elif raw_state in _CANCEL_WORDS:  # (4)
            event = "cancelled"

    if event in _CANCEL_WORDS:
        return "cancelled"
    if event in _POSTED_WORDS:
        return "posted"
    if event in ("created", "updated"):
        return event
    return "unknown"  # (5)


def topic_of(payload: dict) -> str:
    """عمَّ تتكلّم الرسالة: دفعة أم فاتورة أم استرداد.

    v1 يعرفها من المسار (أربعةُ مسارات)، ونحن نستقبل على نقطةٍ واحدة فنقرؤها من
    الحقول. **والترتيب لازم:**

    * **الاسترداد أوّلاً**، لأن الاسترداد في أودو دفعةٌ أيضاً ويحمل
      ``payment_id``؛ فلو سُئل عن الدفعة قبله لصار كلُّ استردادٍ ائتماناً.
    * **ثم الدفعة قبل الفاتورة**، لأن رسالة الدفعة الثانية تحمل ``invoice_id``
      معها — وهي الرسالةُ التي تربط الدفعةَ بفاتورتها، ولو قُرئت «فاتورة»
      لضاع الربطُ الذي جاءت لأجله.
    """
    hint = " ".join(
        _low(payload.get(key)) for key in ("event", "type", "model")
    )

    if (
        payload.get("refund_id")
        or "refund" in hint
        or _low(payload.get("move_type")) == "out_refund"
    ):
        return "refund"
    if payload.get("payment_id") or "payment" in hint:
        return "payment"
    if payload.get("invoice_id") or "invoice" in hint or "account.move" in hint:
        return "invoice"
    return ""


def canonical_event(payload: dict) -> str:
    """اسمُ الفرع الذي يعالج هذه الرسالة، أو اسمُها الخامّ إن لم يُفهم.

    لا يُرجع فارغاً أبداً حين يكون في الحمولة ما يُسمّى: رسالةٌ لا نفهمها تحتفظ
    بكلمتها كما أرسلها أودو، فيقول :func:`apps.odoo.processing._interpret`
    «حدث غير معروف: 'sale.order.confirmed'» — لا «حدث غير معروف: ''». والفرقُ
    بينهما هو الفرقُ بين بلاغٍ يُقرأ وبلاغٍ يُهمَل.
    """
    raw = str(payload.get("event") or "").strip()
    if raw in _CANONICAL:
        return raw

    route = _ROUTE.get((topic_of(payload), verb_of(payload)))
    if route is not None:
        return route
    return raw[:64]
