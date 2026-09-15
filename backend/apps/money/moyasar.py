"""المكانُ الوحيد الذي يكلّم Moyasar عبر الشبكة.

## العطل

`apps/money` كلُّه كان فيه **صفرُ استدعاءٍ صادرٍ إلى البوّابة**. لا إنشاءَ دفعةٍ،
ولا نموذجاً مستضافاً، ولا استعلاماً تأكيديّاً. و`gateway.checkout_target` كان
يملأ قالباً نصّيّاً ويُرسل العميل إليه — أي أنّ «الدفع بالبطاقة» في v2 كان
عنواناً في `.env` لا تكاملاً.

## قراران مأخوذان من v1 حرفيّاً

**١) الخادمُ يُنشئ الدفعة، لا المتصفّح.** v1 يفتح `wallet_topup_card.php` وفيه
`Moyasar.init({amount: <?= $amountHalala ?>, ...})` — والمبلغُ هناك جاء من
`$_GET['amount']`، فالعميلُ هو من سمّى ما سيدفعه (السقفُ الوحيد ٥٠٠٬٠٠٠).
وv2 يرفض ذلك صراحةً في `TopupCreateSerializer`. فلو أعدنا بناء النموذج
المستضاف في المتصفّح لعاد المبلغُ إلى يد العميل من الباب الخلفيّ. لذلك
تُنشَأ **فاتورةُ Moyasar من الخادم** (`POST /v1/invoices`) ويُعاد `url`ها:
المبلغُ والمرجعُ والمهلةُ كلُّها كُتبت هنا، ولا يملك العميل إلا فتح الرابط.

**٢) `GET /v1/payments/{id}` مصدرُ الحقيقة، لا حمولةُ الويبهوك.** مكتوبةٌ بنصّها
في `moyasar_webhook.php`: «Fetch من Moyasar (مصدر الحقيقة)»، ويكرّرها
`wallet_topup_card_done.php` بتعليقٍ يقول لماذا: «Use the amount Moyasar
confirmed (in SAR) to avoid tampering». v1 لا يثق بحمولةٍ أبداً — لا في مسار
المتصفّح ولا في مسار الويبهوك. انظر :mod:`apps.money.inbound` للمنادي.

## مطفأٌ افتراضيّاً، ويرفض ولا يخمّن

بلا `MOYASAR_SECRET_KEY` يرفع هذا الملفّ :class:`MoyasarDisabled` بالعربيّة،
كما يفعل `apps.odoo.client` تماماً. والنداءُ الذي لا يصل ليس دليلاً على أن شيئاً
لم يحدث عندهم (المادة ٢-٤) — ولذلك :class:`MoyasarUnreachable` منفصلةٌ عن
:class:`MoyasarRejected`: الأولى تُعاد المحاولةُ عليها، والثانية جوابُهم
المدروس ولا تُعاد كما هي.
"""

from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.core import jsonio

log = logging.getLogger(__name__)

__all__ = [
    "MoyasarDisabled",
    "MoyasarRejected",
    "MoyasarUnreachable",
    "create_invoice",
    "fetch_payment",
    "is_configured",
]

#: مهلتان لا واحدة، كـ`apps.odoo.client`: اتصالٌ ٥ث وقراءةٌ ٢٠ث. والقراءةُ أطول
#: من أودو لأن هذا النداء يُنشئ فاتورةً عند طرفٍ ثالث: قطعُه في منتصفه يترك
#: فاتورةً منشأةً لا نعرف رقمها، وذلك أسوأ من انتظارِ خمسِ ثوانٍ إضافيّة.
TIMEOUT_SECONDS = (5, 20)


class MoyasarDisabled(RuntimeError):
    """التكاملُ مطفأٌ في هذه البيئة، عن قصد."""


class MoyasarUnreachable(RuntimeError):
    """النداءُ لم يكتمل — شبكةٌ أو مهلةٌ أو خطأُ خادمٍ عندهم.

    منفصلةٌ عن الرفض عمداً (المادة ٢-٤): عدمُ الوصول ليس دليلاً على أن شيئاً لم
    يحدث عندهم. من يراها يُعيد المحاولة ولا يُعوّض.
    """


class MoyasarRejected(RuntimeError):
    """Moyasar ردّت بـ4xx — جوابٌ مدروس، وإعادةُ الطلب كما هو تُعيد الرفض نفسه."""


def is_configured() -> bool:
    """هل في هذه البيئة مفتاحٌ سرّيٌّ يسمح بمناداة Moyasar فعلاً؟

    تُقرأ قبل كل مسارٍ يفترض التكامل، فالجوابُ «لا» ليس عطلاً بل الحالةَ
    الافتراضيّة في التطوير وفي كل بيئةٍ لم يشغّلها مشغّل.
    """
    return bool((settings.MOYASAR_SECRET_KEY or "").strip())


def _base() -> str:
    return str(settings.MOYASAR_API_BASE).rstrip("/")


def _call(method: str, path: str, *, body: dict | None, reference: str) -> dict:
    """نداءٌ واحد إلى Moyasar، بـBasic Auth كما في v1 حرفيّاً.

    المفتاحُ السرّيّ اسمُ المستخدم وكلمةُ المرور فارغة — هذا ما يفعله v1 في
    ثلاثة ملفّات (`CURLOPT_USERPWD => $sk . ':'`)، وهو ما تنتظره Moyasar.

    و`reference` في التوقيع لأنه ما يُبحَث عنه في السجلّ حين تعلق عمليّة: نصُّ
    الخطأ وحده لا يقول أيَّ نيّةِ دفعٍ كانت.
    """
    if not is_configured():
        raise MoyasarDisabled(
            f"مفتاح Moyasar السرّي غير مضبوط في هذه البيئة؛ لم يُرسل {reference}"
        )

    url = f"{_base()}/{path.lstrip('/')}"
    try:
        response = requests.request(
            method,
            url,
            json=body,
            # كلمةُ المرور فارغة — Basic Auth بمفتاحٍ سرّيّ فقط، كـ v1.
            auth=((settings.MOYASAR_SECRET_KEY or "").strip(), ""),
            headers={"Accept": "application/json"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise MoyasarUnreachable(f"تعذّر الوصول إلى Moyasar: {exc}") from exc

    if response.status_code >= 500:
        raise MoyasarUnreachable(f"Moyasar ردّت {response.status_code}")
    if response.status_code >= 400:
        raise MoyasarRejected(
            f"Moyasar رفضت {reference}: {response.status_code} {response.text[:200]}"
        )

    try:
        # **لا `response.json()`.** ردُّهم يحمل مبالغَ، ومُفكِّكُ `requests`
        # يجعل كلَّ رقمٍ كسريٍّ `float` قبل أن يراه كودُنا — المادة ٣-٢، وهو
        # نفسُ سببِ وجود `jsonio` عند حدّ أودو.
        return jsonio.loads(response.content)
    except ValueError as exc:
        raise MoyasarRejected(
            f"ردُّ Moyasar على {reference} ليس JSON: {response.text[:200]}"
        ) from exc


def create_invoice(
    *,
    amount_minor: str,
    currency: str,
    description: str,
    reference: str,
    callback_url: str = "",
    expires_at=None,
) -> dict:
    """أنشئ فاتورةَ Moyasar مستضافة، وأعِد جسمَ ردّها كما هو.

    `amount_minor` **نصُّ عددٍ صحيحٍ** يأتي من :func:`apps.money.units.to_gateway`
    — بالهللة للريال. ويُحوَّل هنا بـ`int` لا بـ`float`: Moyasar تنتظر عدداً في
    الـJSON، و`float` على مسار المال ممنوع (المادة ٣-٢)، والنصُّ القادمُ من
    `to_gateway` عددٌ صحيحٌ بالتعريف فلا يخسر `int` منه شيئاً.

    و`metadata.reference` هو **المُعرِّف الوحيد الذي يعبر**. لا يعرف Moyasar
    مُعرِّفَ المستخدم عندنا ولا يحتاجه: v1 حاول استرجاعَ صاحب الدفعة من رابط
    العودة ومن الجلسة ومن `metadata.user_id`، فخرج بثلاث طرقٍ متضاربة و~٢١٠٠
    دفعةٍ بلا `user_id` أصلاً.

    و`expired_at` هو مقابلُ `payments_intents.expires_at = NOW()+2h` في v1: نيّةٌ
    مهجورةٌ يجب أن تموت عند الطرفين معاً، لا عندنا وحدنا — وإلا بقي رابطُ الدفع
    حيّاً بعد أن أعلنّا النيّةَ منتهية.
    """
    body: dict = {
        "amount": int(amount_minor),
        "currency": currency,
        "description": description,
        "metadata": {"reference": reference},
    }
    if callback_url:
        body["callback_url"] = callback_url
    if expires_at is not None:
        body["expired_at"] = expires_at.isoformat()

    invoice = _call("POST", "/invoices", body=body, reference=reference)
    log.info(
        "moyasar: invoice %s created for %s", invoice.get("id", "?"), reference
    )
    return invoice


def fetch_payment(payment_id: str) -> dict:
    """اقرأ دفعةً من Moyasar — **مصدرُ الحقيقة**، لا حمولةُ الويبهوك.

    v1 يفعل هذا في كل مسارٍ بلا استثناء، ويكتب سببَه في `wallet_topup_card_done`:
    المبلغُ المعتمَد هو ما أكّدته Moyasar «to avoid tampering». والحمولةُ الموقّعة
    تُثبت أن المرسِل يعرف السرّ، ولا تُثبت أن ما فيها هو ما جرى فعلاً.
    """
    if not payment_id:
        raise MoyasarRejected("لا رقم دفعةٍ في الرسالة — لا شيء يُستعلم عنه")
    return _call("GET", f"/payments/{payment_id}", body=None, reference=payment_id)
