"""تسليمُ الإشعارات إلى أجهزة التطبيق عبر FCM. T943.

## القرارُ: FCM وحدَها، لا مزوّدان

v1 يحمل مسلكين في `NotificationController::sendPushIfConfigured`: **OneSignal**
أوّلاً (بـ`player_id` على `userss`)، فإن لم تُضبط مفاتيحُه فـ**FCM** بالتوكنات.
ومزوّدان في مسارٍ واحدٍ يعني أن جوابَ «لماذا لم تصله الرسالة؟» يحتاج أن تعرف
أوّلاً **أيّهما** حاول — وهو سؤالٌ لا تجيبه شاشةٌ ولا صفّ.

وقرارُ المالك (١٨ سبتمبر ٢٠٢٦): «كان عندي طريقتين… أنا عايز الطريقة بتاعة
FCM، إننا نبعت الإشعارات كنوتيفيكيشن على التطبيق عن طريق FCM». فواحدةٌ فقط،
و`player_id` لا يُنقل ولا يُقرأ.

## واجهةُ FCM المستعمَلة — HTTP v1 لا القديمة

`https://fcm.googleapis.com/v1/projects/{project}/messages:send`، والمصادقةُ
**حسابُ خدمة** يُوقَّع منه JWT ثمّ يُبدَّل برمز وصول. والواجهةُ القديمة
(`fcm.googleapis.com/fcm/send` بمفتاح خادمٍ في ترويسة) **أوقفتها جوجل في
يونيو ٢٠٢٤** — فنقلُها «كما هي» نقلُ بابٍ مغلق. وv1 يستعمل v1 كذلك
(`src/Services/FcmSender.php`).

## والمفتاحُ في بيئة الخادم لا في القاعدة

المفتاحُ الخاصّ لحساب الخدمة يُقرأ من `FCM_SERVICE_ACCOUNT_JSON` أو من ملفٍّ
يشير إليه `FCM_SERVICE_ACCOUNT_PATH` — كما يُقرأ `OURSMS_TOKEN` ومفاتيحُ أودو.
**ولا يُخزَّن في جدول**: نسخةُ قاعدةٍ تُؤخذ للتطوير أو للتحليل تحمل معها كلَّ
صفّ، ومفتاحٌ في صفٍّ يخرج مع أوّل نسخة. و`.env` على الخادم لا يخرج مع النسخ.

وشاشةُ اللوحة **تُدير كلَّ ما عدا المفتاح**: تقول أمضبوطٌ هو أم لا، وأيُّ
مشروع، وكم جهازاً مسجَّلاً وبأيّ نظام، وتُسلّم الطابور، وتُجرّب الإرسال إلى
جهازٍ واحد. وهذا هو ما يُدار.

## والجهازُ الذي يرفضه FCM يُحذف

`UNREGISTERED` و`INVALID_ARGUMENT` جوابان يعنيان أن التوكن مات — التطبيقُ
أُزيل، أو أُعيد ضبطُ الجهاز. وإبقاؤه يعني محاولةً فاشلةً في كلّ بثٍّ إلى
الأبد، ورقمَ «فشل» يكبر بلا سببٍ قائم. فيُحذف صفُّه.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
from django.conf import settings
from django.core.cache import cache

log = logging.getLogger(__name__)

#: نقطةُ الإرسال. `{project}` يُملأ من الإعدادات.
SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"

#: نقطةُ تبديل الـJWT برمز وصول.
TOKEN_URL = "https://oauth2.googleapis.com/token"

#: الصلاحيةُ المطلوبة — إرسالُ رسائلِ Firebase لا أكثر.
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"

#: مهلةُ كلّ نداءٍ شبكيّ. الطابورُ يُسلَّم في مهمّةٍ مؤجَّلة، لكنّ جهازاً
#: واحداً لا يحقّ له أن يوقف الدفعةَ دقيقةً.
TIMEOUT = 10

#: رمزُ الوصول صالحٌ ساعةً؛ يُخزَّن أقلَّ من ذلك بهامشٍ يكفي دفعةً كاملة.
TOKEN_TTL = 50 * 60
TOKEN_KEY = "notifications.fcm.access_token"

#: أجوبةُ FCM التي تعني «هذا التوكن مات». انظر رأس الملفّ.
DEAD = {"UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"}


class PushNotConfigured(RuntimeError):
    """لا مشروعَ ولا حسابَ خدمة — والإرسالُ يُرفض بجملةٍ لا بانهيار."""


@dataclass
class Outcome:
    """نتيجةُ دفعةٍ واحدة — بالأرقام، وبما يُكتب في صفّ الإشعار."""

    sent: int = 0
    failed: int = 0
    #: توكن ⟶ سببُ الفشل، لِما فشل وحدَه.
    errors: dict[str, str] = field(default_factory=dict)
    #: توكناتٌ أقرّ FCM بموتها — تُحذف صفوفُها.
    dead: list[str] = field(default_factory=list)
    #: توكن ⟶ اسمُ الرسالة عند FCM (`projects/…/messages/…`).
    names: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# الإعداد
# ---------------------------------------------------------------------------


def service_account() -> dict | None:
    """حسابُ الخدمة من البيئة — نصّاً مباشراً أو ملفّاً. أو `None`."""
    raw = (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
    if not raw:
        path = (getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", "") or "").strip()
        if path and Path(path).is_file():
            raw = Path(path).read_text(encoding="utf-8")
    if not raw:
        return None
    try:
        account = json.loads(raw)
    except json.JSONDecodeError:
        # لا يُرفع: شاشةُ الإعدادات تقول «غيرُ مضبوط» بدل أن تسقط الصفحةُ كلُّها
        # لأن أحداً لصق JSON ناقصاً.
        log.warning("FCM service account is not valid JSON")
        return None
    return account if account.get("client_email") and account.get("private_key") else None


def project_id() -> str:
    """معرّفُ مشروع Firebase — من الإعداد، وإلّا من حساب الخدمة نفسِه."""
    explicit = (getattr(settings, "FCM_PROJECT_ID", "") or "").strip()
    if explicit:
        return explicit
    account = service_account()
    return str(account.get("project_id", "")) if account else ""


def is_configured() -> bool:
    """أيمكن الإرسالُ الآن؟ — مشروعٌ وحسابُ خدمةٍ مقروءان."""
    return bool(project_id() and service_account())


def status() -> dict:
    """ما تعرضه شاشةُ الإعدادات — بلا سرٍّ واحد.

    و`client_email` يُعرَض لأنه **ليس سرّاً**: هو عنوانُ الحساب الذي يُمنح
    الصلاحية في وحدة تحكّم Firebase، ومن يضبط الربط يحتاج أن يراه ليطابقه.
    والمفتاحُ الخاصّ لا يُعرَض ولا يُعاد ولا يُسجَّل.
    """
    account = service_account()
    return {
        "configured": is_configured(),
        "project": project_id(),
        "client_email": (account or {}).get("client_email", ""),
        "source": (
            "متغيّر البيئة"
            if (getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or "").strip()
            else (getattr(settings, "FCM_SERVICE_ACCOUNT_PATH", "") or "")
        ),
    }


# ---------------------------------------------------------------------------
# رمزُ الوصول
# ---------------------------------------------------------------------------


def _signed_assertion(account: dict) -> str:
    """JWT موقَّعٌ بـRS256 من مفتاح حساب الخدمة.

    و`cryptography` هي التي توقّع — أُضيفت للمشروع لهذا وحدَه. والبديلُ الوحيد
    كان الواجهةَ القديمة بمفتاح خادمٍ في ترويسة، **وهي مغلقةٌ منذ يونيو ٢٠٢٤**.
    """
    import base64

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    def b64(raw: bytes) -> bytes:
        return base64.urlsafe_b64encode(raw).rstrip(b"=")

    now = int(time.time())
    header = b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    claims = b64(
        json.dumps(
            {
                "iss": account["client_email"],
                "scope": SCOPE,
                "aud": TOKEN_URL,
                "iat": now,
                "exp": now + 3600,
            }
        ).encode()
    )
    body = header + b"." + claims
    key = serialization.load_pem_private_key(
        account["private_key"].encode(), password=None
    )
    signature = key.sign(body, padding.PKCS1v15(), hashes.SHA256())
    return (body + b"." + b64(signature)).decode()


def access_token(*, refresh: bool = False) -> str:
    """رمزُ وصولٍ صالح — مخزَّنٌ حتى لا يُوقَّع JWT لكلّ جهاز.

    بلا التخزين يصير بثٌّ إلى ألف جهازٍ **ألفَ توقيعٍ وألفَ رحلةٍ** إلى جوجل
    قبل أن تبدأ الرحلاتُ الحقيقيّة.
    """
    if not refresh:
        cached = cache.get(TOKEN_KEY)
        if cached:
            return cached

    account = service_account()
    if account is None:
        raise PushNotConfigured("لا حسابَ خدمةٍ مضبوطاً لـFCM.")

    answer = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": _signed_assertion(account),
        },
        timeout=TIMEOUT,
    )
    if answer.status_code != 200:
        raise PushNotConfigured(
            f"رفضت جوجل حسابَ الخدمة ({answer.status_code}): {answer.text[:200]}"
        )

    token = answer.json().get("access_token", "")
    if not token:
        raise PushNotConfigured("جوابُ جوجل بلا رمز وصول.")
    cache.set(TOKEN_KEY, token, TOKEN_TTL)
    return token


# ---------------------------------------------------------------------------
# الإرسال
# ---------------------------------------------------------------------------


def _message(*, token: str, title: str, body: str, data: dict | None) -> dict:
    """حمولةُ FCM لجهازٍ واحد.

    و`data` قيمُه **نصوصٌ كلُّها** — FCM يرفض `{"broadcast": 7}` بـ400
    ويقبل `{"broadcast": "7"}`. والتحويلُ هنا مرّةً، لا في كلّ مُنادٍ.
    """
    payload: dict = {
        "token": token,
        "notification": {"title": title, "body": body},
    }
    if data:
        payload["data"] = {str(k): str(v) for k, v in data.items() if v is not None}
    return {"message": payload}


def send_to_tokens(
    *, title: str, body: str, tokens: list[str], data: dict | None = None
) -> Outcome:
    """أرسِل إلى كلّ توكن. **جهازٌ يفشل لا يُسقط الدفعة.**

    FCM HTTP v1 لا يقبل عدّة توكناتٍ في نداءٍ واحد (خلافاً للواجهة القديمة)،
    فالنداءُ لكلّ جهاز. والفشلُ يُجمَع ولا يُرفع: بثٌّ إلى ألفٍ يسقط كلُّه لأن
    جهازاً واحداً مات هو بالضبط ما لا يجوز.
    """
    out = Outcome()
    if not tokens:
        return out

    bearer = access_token()
    url = SEND_URL.format(project=project_id())
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json; charset=utf-8",
        }
    )

    for token in tokens:
        try:
            answer = session.post(
                url,
                data=json.dumps(
                    _message(token=token, title=title, body=body, data=data),
                    ensure_ascii=False,
                ).encode("utf-8"),
                timeout=TIMEOUT,
            )
        except requests.RequestException as exc:
            out.failed += 1
            out.errors[token] = f"شبكة: {exc}"[:500]
            continue

        if answer.status_code == 200:
            out.sent += 1
            out.names[token] = answer.json().get("name", "")
            continue

        out.failed += 1
        reason = _reason(answer)
        out.errors[token] = reason[:500]
        if reason.split(":", 1)[0] in DEAD:
            out.dead.append(token)

    return out


def _reason(answer) -> str:
    """سببُ الرفض كما يقوله FCM — رمزُه ونصُّه، لا رقمُ الحالة وحدَه.

    ورقمُ الحالة لا يكفي: `400` تعني «توكن فاسد» و«حمولةٌ خاطئة» معاً، والأول
    يُحذف صفُّه والثاني عطلٌ في كودنا.
    """
    try:
        error = answer.json().get("error", {})
    except ValueError:
        return f"HTTP {answer.status_code}: {answer.text[:200]}"

    status_code = str(error.get("status", ""))
    detail = str(error.get("message", ""))
    for item in error.get("details", []):
        if item.get("@type", "").endswith("FcmError"):
            status_code = str(item.get("errorCode", status_code))
    return f"{status_code}: {detail}" if status_code else detail or "رفضٌ بلا سبب"


__all__ = [
    "Outcome",
    "PushNotConfigured",
    "access_token",
    "is_configured",
    "project_id",
    "send_to_tokens",
    "service_account",
    "status",
]
