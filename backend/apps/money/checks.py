"""فحوصُ النشر التي يملكها هذا التطبيق: **مسارُ دفعٍ نصفُه مضبوط**.

فحصُ نظامٍ لا `raise` عند الاستيراد، للسبب الذي تقوله `apps.accounts.checks`:
`settings/test.py` يرث `prod.py` عمداً. و`check --deploy` حاجزٌ قائمٌ في خطوة
النشر.

## العطلُ الذي كُتبت له

زرُّ «ادفع» يُعرَض حين **تكون هناك بوّابة** (`gateway.is_configured`)، وتُقيَّد
الدفعةُ حين **يصل ردٌّ موقّع** (`PAYMENT_WEBHOOK_SECRET`)، وتُصدَّق حين
**يُستعلَم من البوّابة** (`MOYASAR_SECRET_KEY`). ثلاثةُ مفاتيحَ لطريقٍ واحد،
وكلُّ واحدٍ منها **مستقلٌّ وفارغٌ افتراضاً** — فبيئةٌ فيها اثنان من ثلاثة تبدو
سليمةً تماماً: الصفحةُ تُرسم، والزرُّ يظهر، والفحصُ يمرّ بـ`rc=0` (مقيسٌ في
`docs/environment-contract.md` §٤: الدفعُ كلُّه بلا مفاتيح، ولا اعتراض).

وما يحدث بعد ذلك واحدٌ من هذين، وكلاهما مالُ عميلٍ حقيقيّ:

* زرٌّ يعمل وردٌّ يُرفض → العميلُ يدفع، وتردّ نقطةُ الاستقبال **503**، ولا
  تُشحن المحفظة. المالُ خرج من حسابه ولم يدخل عندنا.
* ردٌّ يُقبل ولا بوّابة → لا أحدَ يُرسَل إلى مكان، والسرُّ المضبوطُ يوهم أن
  المسار مفتوح.

**والتكاملُ المُطفأ كلُّه ليس عطلاً**: بيئةٌ بلا دفعٍ إطلاقاً (لا مفتاح، ولا
قالب، ولا سرّ) لا يُنبَّه عليها بحرف — وهي الوضعُ الصحيح في التطوير.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


def _text(name: str) -> str:
    """قيمةُ الإعداد نصّاً بلا فراغ. مسافةٌ وحدها ليست مفتاحاً."""
    return str(getattr(settings, name, "") or "").strip()


@register(Tags.security, deploy=True)
def the_payment_path_is_whole_when_it_is_open(app_configs, **kwargs) -> list:
    """إمّا أن يكون الطريقُ كاملاً، وإمّا أن يكون مغلقاً — لا نصفَ طريق."""
    checkout = bool(_text("MOYASAR_SECRET_KEY") or _text("PAYMENT_CHECKOUT_TEMPLATE"))
    callback = bool(_text("PAYMENT_WEBHOOK_SECRET"))

    if not checkout and not callback:
        # لا دفعَ في هذه البيئة إطلاقاً، وهو قرارٌ صريحٌ لا نقص. ولا كلمة.
        return []

    findings: list = []

    if checkout and not callback:
        findings.append(
            Error(
                "مسارُ الدفع مفتوحٌ (زرُّ «ادفع» يُعرَض) و`PAYMENT_WEBHOOK_SECRET` "
                "فارغ.",
                hint="نقطةُ ردّ البوّابة تردّ 503 على كل رسالة («استقبال "
                "الدفعات غير مفعّل»): العميلُ يدفع فعلاً، والبوّابةُ تحاول "
                "إبلاغنا فتُرفض، ولا تُشحن محفظته. لا يُكتشف هذا إلا من عميلٍ "
                "يتّصل.",
                id="money.E001",
            )
        )

    if callback and not checkout:
        findings.append(
            Error(
                "`PAYMENT_WEBHOOK_SECRET` مضبوطٌ ولا بوّابةَ في هذه البيئة: "
                "`MOYASAR_SECRET_KEY` و`PAYMENT_CHECKOUT_TEMPLATE` كلاهما فارغ.",
                hint="نصفُ الطريق: نقبل ردّاً عن دفعةٍ لا نستطيع أن نُرسل أحداً "
                "ليدفعها. اضبط مفتاح Moyasar السرّي (المسارُ الأوّل: فاتورةٌ "
                "تُنشأ بنداء) أو `PAYMENT_CHECKOUT_TEMPLATE` لبوّابةٍ أخرى.",
                id="money.E002",
            )
        )

    confirming = bool(getattr(settings, "PAYMENT_CONFIRM_WITH_GATEWAY", True))
    is_moyasar = _text("PAYMENT_GATEWAY").lower() == "moyasar"

    if confirming and not is_moyasar:
        findings.append(
            Error(
                f"`PAYMENT_GATEWAY` هو {_text('PAYMENT_GATEWAY')!r} و"
                "`PAYMENT_CONFIRM_WITH_GATEWAY=True`، ولا استعلامَ تأكيديّاً "
                "مُنفَّذاً لغير Moyasar.",
                hint="كلُّ دفعةٍ ترتدّ `Unconfirmed` فلا تُقيَّد ولا تُرفض — "
                "تبقى في طابور الإعادة إلى الأبد. إن كانت بوّابةُ هذه البيئة "
                "بلا واجهةِ استعلامٍ فاكتب `PAYMENT_CONFIRM_WITH_GATEWAY=False` "
                "صراحةً، ليُكتب ذلك في ملاحظة كل رسالة.",
                id="money.E003",
            )
        )

    if confirming and is_moyasar and checkout and not _text("MOYASAR_SECRET_KEY"):
        findings.append(
            Error(
                "مسارُ الدفع مفتوحٌ بالقالب و`MOYASAR_SECRET_KEY` فارغ مع "
                "`PAYMENT_CONFIRM_WITH_GATEWAY=True`.",
                hint="الاستعلامُ التأكيديّ هو مصدرُ الحقيقة قبل التقييد (كـ v1 "
                "في كل مسار)، وبلا مفتاحٍ سرّيٍّ يرتدّ كلُّ ردٍّ `Unconfirmed` "
                "«لا يُقيَّد من الحمولة وحدها»: لا وديعةَ تُشحن، ولا رسالةَ خطأ "
                "يراها أحد.",
                id="money.E004",
            )
        )

    if not confirming and not settings.DEBUG:
        findings.append(
            Warning(
                "`PAYMENT_CONFIRM_WITH_GATEWAY=False` في بيئةٍ منشورة: يُقيَّد "
                "المالُ من الحمولة الموقّعة وحدها.",
                hint="تحذيرٌ لا خطأ — إعلانُ مشغّلٍ صريحٌ ومسموحٌ لبوّابةٍ بلا "
                "واجهةِ استعلام، ويُكتب في ملاحظة كل رسالة. لكنه يجعل من يملك "
                "السرَّ قادراً على شحن محفظةٍ بلا أن يدفع ريالاً.",
                id="money.W001",
            )
        )

    template = _text("PAYMENT_CHECKOUT_TEMPLATE")
    if template and "{reference}" not in template:
        findings.append(
            Error(
                "`PAYMENT_CHECKOUT_TEMPLATE` لا يذكر `{reference}`.",
                hint="المرجعُ هو المعرّفُ الوحيد الذي يعبر إلى البوّابة ويعود "
                "منها، وبدونه تصل الدفعةُ بلا صاحب — وهي بالضبط دفعاتُ v1 "
                "الـ~٢١٠٠ التي لا يُعرف لمن هي.",
                id="money.E005",
            )
        )

    return findings


@register(Tags.security, deploy=True)
def the_gateway_amount_unit_is_readable(app_configs, **kwargs) -> list:
    """بأيّ وحدةٍ تتكلّم هذه البوّابة — سؤالٌ لا يُخمَّن جوابُه.

    `apps.money.units` ترفض القيمةَ المجهولة، لكنها ترفضها **عند أوّل دفعة**:
    أي بعد أن يكون عميلٌ قد دفع. وهذا يقدّم الرفضَ إلى خطوة النشر.
    """
    from apps.money import units

    # نداءُ `_unit()` الخاصّ مقصود: القاعدةُ («minor أو major ولا ثالث») تعيش
    # في `units` وحدها، وإعادةُ كتابتها هنا تجعل قاعدةً واحدةً في مكانين
    # تفترقان يومَ تُضاف وحدةٌ ثالثة (المادة ٤-٥).
    try:
        units._unit()
    except units.AmountUnreadable as exc:
        return [
            Error(
                str(exc),
                hint="المسموحُ «minor» (هللة — وهو افتراضُ Moyasar) أو «major» "
                "(ريال). وقيمةٌ لا تُقرأ ترفع الاستثناءَ عند أوّل دفعةٍ تصل، "
                "أي بعد أن يكون المالُ قد خرج من حساب العميل.",
                id="money.E006",
            )
        ]
    return []
