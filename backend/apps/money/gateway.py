"""أين يُرسَل العميل ليدفع — وهو سؤالٌ للخادم لا للعميل.

The contract had a hole and both channels fell into it: `start_topup` writes a
:class:`~apps.money.models.PaymentIntent` and returns it, but nothing in that
row said **where the customer goes to pay**. The web could create an intent and
not send anybody anywhere; phase 008's card top-up would have hit the same wall.

The shape this fills it with is deliberately not "a gateway url in the response"
-------------------------------------------------------------------------------
The obvious fix is to put the gateway's own address in the serialized intent.
It is the wrong one, for a reason that outlives whichever gateway is chosen:

* every gateway wants something different — a redirect for one, a form `POST`
  with signed fields for the next, a session token for a third. A field holding
  "the gateway url" is a field whose meaning changes when the gateway does, and
  **both clients would have to change with it**;
* and the shape would leak into two codebases that have no business knowing it.
  The web and the app would each grow a branch for "how do we hand off to
  Moyasar", which is a rule living in three places (Article 4-5).

So the intent carries a url on **our own** server, always the same shape, and
that endpoint is where the handoff is decided. Switching gateway is then a
change here and nowhere else — neither client is rebuilt, neither is redeployed,
and neither ever learns what a Moyasar is.

والفاتورةُ تُنشأ عند البوّابة، لا تُملأ في قالب
-----------------------------------------------
كان هذا الملفّ يملأ `PAYMENT_CHECKOUT_TEMPLATE` بالمرجع والمبلغ ويرسل العميل إلى
النصّ الناتج — **بلا استدعاءٍ صادرٍ واحدٍ إلى البوّابة في `apps/money` كلّه**. وهو
لا يعمل مع Moyasar أصلاً: لا يوجد رابطٌ ثابتٌ عندها يُملأ بقالب، الدفعةُ تُنشَأ
بنداء. فصار المسارُ الأول هو :func:`apps.money.moyasar.create_invoice`، والقالبُ
احتياطٌ لبوّابةٍ أخرى أو لبيئةٍ تختبر الشكل بلا شبكة.

والنداءُ لا يتكرّر: رقمُ الفاتورة ورابطُها يُحفظان على النيّة، فضغطتان على «ادفع»
لا تصيران فاتورتين قابلتين للدفع.

Off by default, like every other integration
--------------------------------------------
بلا `MOYASAR_SECRET_KEY` وبلا `PAYMENT_CHECKOUT_TEMPLATE` لا يُنتج هذا الملفّ
شيئاً وترفض النقطةُ بالعربيّة. وهو موقفُ عميل أودو ومسارِ الويبهوك نفسه:
تكاملٌ غيرُ مضبوطٍ يرفض ولا يخمّن، لأن التخمين هنا عميلٌ أُرسل إلى صفحةٍ مكسورةٍ
ومالُه في يده.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone

from . import moyasar, units
from .models import PaymentIntent, PaymentIntentState

log = logging.getLogger(__name__)

__all__ = [
    "CheckoutUnavailable",
    "available_for",
    "checkout_target",
    "is_configured",
    "is_payable",
]


class CheckoutUnavailable(Exception):
    """No gateway is configured, or this intent can no longer be paid.

    One exception for both, with the Arabic sentence chosen by the raiser: to a
    customer they are the same situation — this button will not take them
    anywhere — and to an operator the two are told apart by which sentence
    appears in the log.
    """

    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message


def is_payable(intent: PaymentIntent) -> bool:
    """Whether sending this customer to a gateway could still do anything.

    Only a `pending` intent. A succeeded one would take a second payment for a
    deposit already made; a failed or cancelled one is a row somebody would be
    paying against after the platform stopped expecting it. Both are cases where
    the *absence* of a button is the correct interface.

    **والمهلةُ تُقرأ من الساعة لا من العمود.** النيّةُ المنتهية قد تكون ما زالت
    `pending` في القاعدة لأن لا شيء مرّ عليها بعد (`services.expire_stale_intents`
    تُنادى عند بدء عمليّةٍ جديدةٍ لصاحبها، كما في v1 تماماً). فلو سألنا العمودَ
    وحده لبقي زرُّ الدفع حيّاً على نيّةٍ ماتت ساعتين — وهي الحالةُ التي كُتبت هذه
    المهلةُ من أجلها.
    """
    if intent.state != PaymentIntentState.PENDING:
        return False
    return intent.expires_at is None or intent.expires_at > timezone.now()


def is_configured() -> bool:
    """هل في هذه البيئة بوّابةٌ يمكن إرسالُ أحدٍ إليها أصلاً؟ سؤالٌ بلا شبكة."""
    return moyasar.is_configured() or bool(
        getattr(settings, "PAYMENT_CHECKOUT_TEMPLATE", "")
    )


def available_for(intent: PaymentIntent) -> bool:
    """هل يُعرَض زرُّ الدفع لهذه النيّة؟ **بلا أيّ نداءٍ شبكيّ.**

    مفصولةٌ عن :func:`checkout_target` لأن الأخيرة صارت تُنشئ فاتورةً عند
    البوّابة. وكان المُسلسِل (`PaymentIntentSerializer.get_checkout_url`) يستدعي
    `checkout_target` لمجرّد أن يعرف هل يعرض الزرّ — فصفحةُ «عمليّاتي» التي
    تُسلسِل عشرَ نيّاتٍ كانت ستُنشئ **عشرَ فواتيرَ** عند Moyasar في كل تحميل.
    """
    return is_payable(intent) and is_configured()


def _return_url(intent: PaymentIntent) -> str:
    """رابطُ عودة العميل بعد الدفع، أو فراغٌ إن لم تسمّه البيئة.

    والفراغُ ليس عطلاً: الويبهوكُ مستقلٌّ عن عودة العميل تماماً، وهو ما أصلح
    عطلَ v1 «الدفع نجح والعميل أغلق التطبيق ⇒ المال ضاع» (سببُ وجود الـbackstop،
    ٢٠٢٦-٠٦-٠٤). فالعودةُ راحةُ عينٍ لا مسارَ مال.
    """
    template = getattr(settings, "PAYMENT_RETURN_URL_TEMPLATE", "")
    if not template:
        return ""
    return template.format(reference=quote(intent.reference, safe=""))


def _amount_for_gateway(intent: PaymentIntent) -> str:
    try:
        return units.to_gateway(intent.amount, intent.currency)
    except units.AmountUnreadable as exc:
        # عملةٌ لا نعرف وحدتها الصغرى: يُرفض الإرسال ولا يُخمَّن المقسومُ عليه.
        # وجملةُ العميل عامّة — تفصيلُ العملة في السجلّ لا على شاشته.
        log.error("checkout: %s — %s", intent.reference, exc)
        raise CheckoutUnavailable("تعذّر تجهيز الدفع لهذه العملة.") from exc


def checkout_target(intent: PaymentIntent) -> str:
    """Where to send this customer, right now, to pay this intent.

    ثلاثةُ مساراتٍ بترتيبٍ مقصود:

    ١. **رابطٌ محفوظٌ على النيّة** — فاتورةٌ أُنشئت في ضغطةٍ سابقة. تُعاد كما هي،
       فلا تصير الضغطتان فاتورتين.
    ٢. **Moyasar** حين يكون مفتاحُها السرّيّ مضبوطاً: يُنشئ الخادمُ فاتورةً
       بمبلغِه هو ومرجعِه هو ومهلتِه هو، ويُعاد `url`ها. وأسبقيّتُها على القالب
       مقصودة: المفتاحُ السرّيّ موجودٌ في البيئة إعلانٌ صريحٌ من مشغّلٍ بأن
       البوّابةَ الحقيقيّة مشغّلة، والقالبُ سبقها في الزمن لا في الأولويّة.
    ٣. **القالب** `PAYMENT_CHECKOUT_TEMPLATE` لبوّابةٍ أخرى أو لفحص الشكل بلا
       شبكة. يسمّي ما يحتاج:

           PAYMENT_CHECKOUT_TEMPLATE="https://pay.example.com/{reference}?amount={amount}"

    ``reference`` هو المُعرِّف الوحيد الذي يعبر في كل المسارات. ملكُنا، ومبهَم،
    وبه تُسنَد الدفعةُ العائدة — ولا تعرف البوّابةُ مُعرِّفَ مستخدمٍ أبداً، وهو
    كلُّ سبب وجود `PaymentIntent` صفّاً يُكتب قبل أن يغادر العميل (v1 حاول
    استرجاع صاحب الدفعة من رابط العودة فضاعت منه دفعات).

    ``amount`` يخرج **بوحدة البوّابة** (:func:`apps.money.units.to_gateway`) — أي
    بالهللة لـMoyasar. وكان يُوضَع بالريال، فنموذجٌ مستضافٌ يقرؤه هللةً يطالب
    العميلَ بمئة ريالٍ بدل عشرة آلاف: مرآةُ عطلِ القراءة على مسار الدخول. ويبقى
    **نصّاً** في كل خطوة، فلا يصير `float` على مسار مالٍ (المادة ٣-٢).
    """
    if not is_payable(intent):
        raise CheckoutUnavailable("هذه العملية لم تعد قابلة للدفع.")

    if intent.gateway_checkout_url:
        return intent.gateway_checkout_url

    amount = _amount_for_gateway(intent)

    if moyasar.is_configured():
        try:
            invoice = moyasar.create_invoice(
                amount_minor=amount,
                currency=intent.currency,
                description=f"شحن تأمين ({intent.reference})",
                reference=intent.reference,
                callback_url=_return_url(intent),
                expires_at=intent.expires_at,
            )
        except moyasar.MoyasarDisabled as exc:  # pragma: no cover - حارسٌ منطقيّ
            log.error("checkout: %s — %s", intent.reference, exc)
            raise CheckoutUnavailable("الدفع بالبطاقة غير مفعّل في هذه البيئة.") from exc
        except (moyasar.MoyasarUnreachable, moyasar.MoyasarRejected) as exc:
            # **لا رابطَ مخمَّن.** بوّابةٌ لم تردّ تعني أننا لا نعرف رقم فاتورةٍ
            # ولا رابطاً؛ وإرسالُ العميل إلى عنوانٍ مبنيٍّ بالحدس هو إرسالُه
            # ليدفع في مكانٍ لا يعود منه شيء.
            log.error("checkout: %s — %s", intent.reference, exc)
            raise CheckoutUnavailable(
                "تعذّر تجهيز الدفع الآن. حاول بعد قليل."
            ) from exc

        url = str(invoice.get("url") or "")
        if not url:
            log.error("checkout: %s — فاتورةُ Moyasar بلا رابط", intent.reference)
            raise CheckoutUnavailable("تعذّر تجهيز الدفع الآن. حاول بعد قليل.")

        intent.gateway_checkout_id = str(invoice.get("id") or "")[:128]
        intent.gateway_checkout_url = url[:500]
        intent.save(
            update_fields=["gateway_checkout_id", "gateway_checkout_url", "updated_at"]
        )
        log.info(
            "checkout: intent %s -> moyasar invoice %s",
            intent.reference,
            intent.gateway_checkout_id,
        )
        return url

    template = getattr(settings, "PAYMENT_CHECKOUT_TEMPLATE", "")
    if not template:
        raise CheckoutUnavailable("الدفع بالبطاقة غير مفعّل في هذه البيئة.")

    # `quote` on every substituted value: a reference is generated by us and is
    # url-safe today, and a template that only works because of that is a
    # template that breaks the day a gateway wants a different reference format.
    return template.format(
        reference=quote(intent.reference, safe=""),
        amount=quote(amount, safe=""),
        currency=quote(intent.currency, safe=""),
    )
