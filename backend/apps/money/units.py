"""وحدةُ المبلغ عند البوّابة — هللةٌ أم ريال، ومن يقرّر.

## العطل

`inbound.py` كان يقرأ مبلغ البوّابة هكذا:

```python
amount = Decimal(str(payload.get("amount", "0")))
```

**بلا قسمة.** وMoyasar — البوّابةُ الافتراضيّة في `PAYMENT_GATEWAY`، وهي التي
يستعملها v1 — ترسل المبلغ **بالهللة**: عشرةُ آلاف ريالٍ تصل `1000000`. وv1 يعالجها
صراحةً (`$amount_sar = $payment['amount'] / 100.0`).

فكلُّ دفعةٍ كانت ستُقرأ **مئةَ ضعفٍ** من قيمتها، فلا تطابق نيّةَ الدفع، فتذهب
النيّةُ إلى `DISPUTED` والمبلغُ كاملاً إلى الحساب المعلَّق — **ولا تُقيَّد وديعةٌ
واحدةٌ أبداً**. عميلٌ يدفع، ويرى محفظته صفراً، ويتّصل. وذلك في كل دفعةٍ من أوّل
يوم.

والعطلُ مرآتُه في الصادر أيضاً: `gateway.checkout_target` كان يضع المبلغ
**بالريال** في رابط النموذج المستضاف، وMoyasar تقرؤه هللةً — فيُطالَب العميل بمئة
ريالٍ بدل عشرة آلاف.

## لماذا جدولُ أُسُسٍ لا قسمةٌ على ١٠٠

لأن المقسومَ عليه **يتبع العملة**: الريال والدولار خانتان، والدينار الكويتيّ
والبحرينيّ ثلاث، والينُّ صفر. وقسمةٌ ثابتةٌ على ١٠٠ تصنع العطلَ نفسه لعملةٍ أخرى
يومَ تُضاف — أي أنها تؤجّله لا تُصلحه.

**وعملةٌ لا نعرف أُسَّها تُرفَض ولا تُقسَم على ١٠٠ تخميناً.** هذا هو الدرسُ
حرفيّاً: التخمينُ هو ما صنع العطل.

## ولماذا الوحدةُ إعدادُ بيئة

لأن `PAYMENT_GATEWAY` مُعدٌّ أصلاً لأن يتغيّر، والبوّاباتُ تنقسم: Moyasar وStripe
وCheckout ترسل الأصغر، وبعضُ البوّابات المحليّة ترسل الأكبر. وتثبيتُ «هللة» في
الشيفرة يجعل تبديلَ البوّابة تغييرَ كودٍ لا تغييرَ إعداد — وهو ما ترفضه
:mod:`apps.money.gateway` صراحةً في صدرها.

والافتراضُ `minor` لأن البوّابة الافتراضيّة Moyasar. **وخطأُ الإعداد لا يضيع
مالاً**: القراءةُ بوحدةٍ خاطئة تُنتج مبلغاً لا يطابق النيّة، فتقع في المعلَّق
بقرار `apply_gateway_payment` — محفوظاً كاملاً وبانتظار إنسان، لا مقيَّداً خطأً.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.conf import settings

__all__ = [
    "AmountUnreadable",
    "MINOR_UNIT_EXPONENT",
    "exponent",
    "from_gateway",
    "to_gateway",
]


class AmountUnreadable(ValueError):
    """المبلغُ أو عملتُه لا يُقرآن بيقين. لا يُخمَّن، ولا يُقرَّب."""


#: كم خانةً عشريّةً في الوحدة الصغرى لكل عملة (ISO 4217).
#:
#: مقصورةٌ على ما يمكن أن تراه هذه المنصّة فعلاً. والقصرُ مقصود: عملةٌ ليست هنا
#: تُرفَع بها :class:`AmountUnreadable` بدل أن تُقسَم على ١٠٠ افتراضاً — والدينارُ
#: الكويتيّ المقسومُ على ١٠٠ يُقرأ **عشرةَ أضعافه**.
MINOR_UNIT_EXPONENT: dict[str, int] = {
    "SAR": 2,
    "AED": 2,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "EGP": 2,
    "QAR": 2,
    # ثلاثُ خاناتٍ — الخليجُ فيه أربعُ عملاتٍ كذلك، وهي أكثرُ ما يُنسى.
    "KWD": 3,
    "BHD": 3,
    "OMR": 3,
    "JOD": 3,
    # بلا خاناتٍ إطلاقاً.
    "JPY": 0,
}


def exponent(currency: str) -> int:
    """أُسُّ الوحدة الصغرى لهذه العملة، أو رفضٌ يسمّيها."""
    code = (currency or "").strip().upper()
    if code not in MINOR_UNIT_EXPONENT:
        raise AmountUnreadable(
            f"عملةٌ لا نعرف وحدتها الصغرى: {currency!r} — "
            "تُضاف إلى MINOR_UNIT_EXPONENT بأُسّها، ولا تُقسَم على ١٠٠ تخميناً"
        )
    return MINOR_UNIT_EXPONENT[code]


def _unit() -> str:
    """`minor` أو `major` — بأيّ وحدةٍ تتكلّم هذه البوّابة."""
    value = str(getattr(settings, "PAYMENT_AMOUNT_UNIT", "minor")).strip().lower()
    if value not in ("minor", "major"):
        raise AmountUnreadable(
            f"PAYMENT_AMOUNT_UNIT قيمتها {value!r} — المسموح «minor» أو «major»"
        )
    return value


def from_gateway(raw, currency: str) -> Decimal:
    """مبلغُ البوّابة محوَّلاً إلى الريال (الوحدة الكبرى)، أو رفضٌ بسبب.

    **ولا تقريبَ في أيّ اتّجاه.** بوّابةٌ تتكلّم بالهللة ترسل عدداً صحيحاً من
    الهللات بالتعريف؛ فـ`1000000.5` ليست «١٠٬٠٠٠٫٠٠٥ ريال» — هي رسالةٌ لا نفهمها،
    وتقريبُها يخترع رقماً يدخل الدفتر. وكذلك `10.555` ريالاً: ثلاثُ خاناتٍ في
    عملةٍ لها خانتان.

    والرفضُ هنا لا يُسقط مالاً: المنادي (:mod:`apps.money.inbound`) يكتب الرسالة
    `failed` بالسبب، فتبقى في طابور الإعادة ويقرؤها إنسان — المادة ٢-٢.
    """
    if raw is None:
        raise AmountUnreadable("الرسالة بلا مبلغ")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        raise AmountUnreadable(f"مبلغ غير صالح: {raw!r}") from None
    if not value.is_finite():
        raise AmountUnreadable(f"مبلغ غير منتهٍ: {raw!r}")

    exp = exponent(currency)
    scale = Decimal(10) ** exp

    if _unit() == "minor":
        if value != value.to_integral_value():
            raise AmountUnreadable(
                f"مبلغٌ بالوحدة الصغرى وفيه كسر: {raw!r} — "
                "الهللةُ لا تتجزّأ، والتقريبُ هنا يخترع رقماً"
            )
        return (value / scale).quantize(Decimal(1).scaleb(-exp))

    if value != value.quantize(Decimal(1).scaleb(-exp)):
        raise AmountUnreadable(
            f"مبلغٌ بخاناتٍ أكثر مما تحتمله {currency}: {raw!r}"
        )
    return value.quantize(Decimal(1).scaleb(-exp))


def to_gateway(amount: Decimal, currency: str) -> str:
    """مبلغُنا بالوحدة التي تفهمها البوّابة، نصّاً.

    نصٌّ لا عدد، ولا `float` في أيّ خطوة — المادة ٣-٢. وبالهللة يكون عدداً صحيحاً
    بلا فاصلة، وهو ما ينتظره نموذج Moyasar المستضاف.
    """
    exp = exponent(currency)
    value = Decimal(amount)
    if _unit() == "major":
        return str(value.quantize(Decimal(1).scaleb(-exp)))

    minor = value.scaleb(exp)
    if minor != minor.to_integral_value():
        raise AmountUnreadable(
            f"{amount} {currency} لا يُعبَّر عنه بعددٍ صحيحٍ من الوحدة الصغرى"
        )
    return str(int(minor))
