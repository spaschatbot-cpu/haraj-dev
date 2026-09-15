"""شكلُ نداء أودو كما هو، لا كما تخيّلناه.

## العطل

كان الصادرُ يرسل جسماً **مسطَّحاً** (`{"invoice": …, "amount": "…", "reference": …}`)
إلى `{BASE}/payments`. وأودو الذي يستعمله v1 — الموثَّق في
`D:\\haraj 1\\applicationtest\\ODOO_APIS.md`، ٤٥٢ سطراً وثمانِ نقاط — لا يعرف هذا
المسار ولا هذا الجسم. عقدُه:

```
POST {BASE}/create/payments
{"jsonrpc": "2.0", "method": "create_payment", "id": 1, "params": {…}}
Authorization: Bearer <token>
```

فأوّلُ إرسالٍ حقيقيّ كان سيعود `404` — ثم يُعاد ثماني مرّاتٍ بتراجعٍ أُسّيّ،
ثم يُهجر. ولا فرقَ بين «لم يصل» و«وصل إلى عنوانٍ لا وجود له» في النتيجة:
المحاسبةُ لا تعلم بشيء.

## لماذا وحدةٌ للغلاف وحده

لأن **ثلاثة تصوّراتٍ للواجهة** كانت في الحزمة في وقتٍ واحد: المسطَّح في
`outbox`، و`call_kw` في `reconciliation`، والـjsonrpc الصحيح في
`management/commands/odoo_ping.py` وحده. ثلاثةٌ لا يعرف قارئُها أيُّها الحقيقيّ.
فالشكلُ هنا، في مكانٍ واحد، ومن يريد تغيير البوّابة يغيّر ملفّاً.

## وقراءةُ الردّ ليست أبسط

أودو يضع الحقلَ نفسه في أربعة مواضع بحسب النقطة: `result.X` · `result.data.X`
· `result.response.X` · وفي الجذر. v1 يقبل الأربعة صراحةً («The service also
accepts customer id from several possible paths»)، وقراءةُ موضعٍ واحدٍ منها
تعني أن نصفَ الردود تُقرأ «بلا رقم» وهي تحمله.
"""

from __future__ import annotations

__all__ = ["ACCEPTED_STATES", "ENDPOINTS", "accepted", "path_and_method", "read", "wrap"]

#: اسمُنا المنطقيّ ⇐ (مسارُ أودو، اسمُ الدالّة في الغلاف).
#:
#: المفاتيحُ هي ما يُخزَّن في `OutboxMessage.endpoint`، وأُبقيت على أسمائها
#: القديمة (`payments` · `refund.request` · `banktopup.submit`) عمداً: في
#: الصندوق صفوفٌ تحملها، وإعادةُ تسميتها كانت ستجعلها غيرَ قابلةٍ للإرسال بلا
#: هجرةِ بيانات. والاسمُ المنطقيّ لا يُرسَل إلى أحد — المرسَلُ هو القيمة.
ENDPOINTS: dict[str, tuple[str, str]] = {
    "customer": ("create/customer", "create_customer"),
    "invoice": ("create/invoice", "create_invoice"),
    "payments": ("create/payments", "create_payment"),
    "refund.request": ("create/refunds", "create_refund"),
    # اشتراك/شحن محفظة — نفسُ نقطة v1 للتحويل البنكيّ ولبطاقة ميسر.
    "banktopup.submit": ("create/payment/subscription", "create_payment"),
}

#: ما يعدّه v1 قبولاً. أربعُ كلماتٍ لأن أودو يجيب بأيٍّ منها على نفس النداء
#: باختلاف النقطة — و`OdooService::createRefund` يقبل الأربع صراحةً.
#:
#: وغيابُ الحالة **ليس رفضاً**: نقاطٌ تردّ بالمعرّف وحده. فالرفضُ يُقرأ من رمز
#: HTTP (يتكفّل به `client.call`) ومن حالةٍ **مذكورةٍ وغيرِ مقبولة**، لا من
#: صمت — وإلا هُجرت رسائلُ نجحت.
ACCEPTED_STATES = frozenset(
    {"success", "posted", "draft", "paid", "approved", "done", "confirmed", "ok"}
)


def path_and_method(endpoint: str) -> tuple[str, str]:
    """مسارُ أودو واسمُ دالّته لاسمٍ منطقيّ — أو خطأٌ يسمّي المجهول.

    `KeyError` وليس افتراضاً: نقطةٌ لا نعرف مسارها تُرسَل إلى `{BASE}/<اسمنا>`
    فتعود `404` بعد ثماني محاولات. الانفجارُ عند الإدراج أرخص بيومين.
    """
    try:
        return ENDPOINTS[endpoint]
    except KeyError:
        raise KeyError(
            f"نقطة أودو غير معروفة: {endpoint!r} — أضِفها إلى ENDPOINTS بمسارها"
        ) from None


def wrap(method: str, params: dict) -> dict:
    """غلافُ JSON-RPC كما ينتظره أودو. `id` ثابتٌ عندهم كما في كل ملفّات v1."""
    return {"jsonrpc": "2.0", "method": method, "id": 1, "params": params}


def read(reply, *names: str):
    """أوّلُ قيمةٍ غيرِ فارغةٍ لأيٍّ من هذه الأسماء، في أيٍّ من مواضع أودو الأربعة.

    الترتيبُ من الأعمق إلى الجذر لأن الجذرَ أكثرُ عرضةً لحملِ اسمٍ عامّ
    (`status`) يخصّ الغلاف لا المضمون.
    """
    if not isinstance(reply, dict):
        return None
    result = reply.get("result")
    scopes = []
    if isinstance(result, dict):
        for key in ("response", "data"):
            nested = result.get(key)
            if isinstance(nested, dict):
                scopes.append(nested)
        scopes.append(result)
    scopes.append(reply)

    for scope in scopes:
        for name in names:
            value = scope.get(name)
            if value not in (None, "", []):
                return value
    return None


def accepted(reply) -> bool:
    """هل قال أودو نعم؟ — وصمتُه عن الحالة نعمٌ أيضاً.

    الرفضُ الصريح وحده يُهجِر الرسالة. أما ردٌّ بلا كلمةِ حالة (وكثيرٌ من نقاطهم
    كذلك: تردّ بالمعرّف فقط) فيُقرأ قبولاً — لأن الرفضَ الحقيقيّ يصل رمزَ HTTP
    ويلتقطه `client.call` قبل أن نصل إلى هنا.
    """
    state = read(reply, "status", "state", "payment_state")
    if state is None:
        return True
    return str(state).strip().lower() in ACCEPTED_STATES
