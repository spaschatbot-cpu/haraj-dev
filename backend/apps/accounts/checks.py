"""Deployment checks this app owns.

A system check, not a `raise` at import time. The one-time-code settings are
wrong only in a *deployed* environment, and `settings/test.py` inherits from
`prod.py` on purpose — an import-time guard there would refuse to let the test
settings load at all, which is how a rule about production ends up breaking CI.

`manage.py check --deploy` is already a blocking CI step against `prod`, so
these findings reach the same gate as Django's own.
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

CONSOLE_BACKEND = "apps.accounts.sms.console_backend"

#: البوّاباتُ الحقيقيّة التي يعرف هذا المستودعُ ما تحتاجه، ولكلٍّ متغيّراتُها.
#: مكتوبةٌ لا مشتقّة: إضافةُ مزوّدٍ تعديلٌ مقصودٌ في مكانين، لا مزوّدٌ يدخل
#: بلا أن يقول أحدٌ ما الذي يجعله شغّالاً.
REAL_SMS_GATEWAYS = {
    "apps.accounts.sms.oursms_backend": ("OURSMS_API_URL", "OURSMS_TOKEN"),
}


@register(Tags.security, deploy=True)
def one_time_codes_are_safe_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """The code must go to the customer's phone and nowhere else."""
    findings: list = []

    if settings.SMS_BACKEND == CONSOLE_BACKEND:
        findings.append(
            Error(
                "SMS_BACKEND is the console backend, which writes one-time codes "
                "into the application log.",
                hint="Point SMS_BACKEND at a real provider before deploying.",
                id="accounts.E001",
            )
        )

    # Six digits with an unbounded number of guesses is not a secret, it is a
    # countdown. The cap is what makes the length sufficient.
    if settings.OTP_MAX_ATTEMPTS > 10:
        findings.append(
            Warning(
                f"OTP_MAX_ATTEMPTS is {settings.OTP_MAX_ATTEMPTS}; a "
                f"{settings.OTP_CODE_DIGITS}-digit code stops being a secret "
                "once guessing is cheap.",
                hint="Five is the default, and is already generous.",
                id="accounts.W001",
            )
        )

    # An access token that outlives the working day cannot be revoked by
    # expiry, which is the only thing that limits a token stolen off a device
    # that never comes back to us.
    if settings.ACCESS_TOKEN_TTL_SECONDS > 60 * 60 * 24:
        findings.append(
            Warning(
                "ACCESS_TOKEN_TTL_SECONDS is longer than a day.",
                hint="Short access, long refresh — the refresh token is the "
                "one designed to be rotated and revoked.",
                id="accounts.W002",
            )
        )

    return findings


@register(Tags.security, deploy=True)
def the_sms_gateway_is_configured_when_it_is_real(app_configs, **kwargs) -> list:
    """`SMS_BACKEND` يشير إلى بوّابةٍ حقيقيّة — فليكن معها ما تُرسل به.

    الفحصُ فوق يمسك **الطرفَ الأوّل**: مزوّدٌ صوريٌّ في بيئةٍ منشورة. وهذا
    يمسك الطرفَ الثاني، وهو أهدأ وأخطر: مزوّدٌ حقيقيٌّ **بلا مفاتيح**. مقيسٌ في
    `docs/environment-contract.md` §٤ — `SMS_BACKEND=…oursms_backend` بلا
    `OURSMS_TOKEN` يعطي `check --deploy` رمزَ خروجٍ **صفراً**، ثم لا يمرّ تحقّقٌ
    واحدٌ في تلك البيئة إطلاقاً: كلُّ محاولةِ دخولٍ ترفع `SmsSendFailed`، ويُكتب
    السطرُ في `SmsFailure`، ولا أحدَ ينظر في جدولٍ لا يعرف أنه امتلأ.

    وهو عطلُ v1 نفسُه بوجهٍ آخر: هناك ابتلعت `sendSmsSafely` ردَّ المزوّد فلم
    يعرف أحدٌ أن الرصيد نفد؛ وهنا قد لا يكون ثمّة رصيدٌ ولا توكنٌ أصلاً.

    و`E005` — المسارُ الذي لا يُستورَد — أشدُّها صمتاً: خطأٌ إملائيٌّ في اسم
    الوحدة لا يظهر عند الإقلاع أبداً، لأن `import_string` تُنادى **لحظةَ
    الإرسال**. أوّلُ من يكتشفه عميلٌ يرى 500 في شاشة الدخول.
    """
    backend = str(getattr(settings, "SMS_BACKEND", "") or "").strip()
    if not backend or backend == CONSOLE_BACKEND:
        # لا مزوّد، أو مزوّدُ السجلّ — والفحصُ أعلاه يقول فيهما ما يلزم.
        return []

    findings: list = []

    from django.utils.module_loading import import_string

    try:
        import_string(backend)
    except ImportError:
        findings.append(
            Error(
                f"SMS_BACKEND هو {backend!r} ولا يمكن استيراده.",
                hint="لا يُنادى إلا لحظةَ إرسال أوّل رمز، فالخطأُ لا يظهر عند "
                "الإقلاع: كلُّ محاولةِ دخولٍ تصير 500. تحقّق من المسار "
                "الكامل للدالّة.",
                id="accounts.E005",
            )
        )
        # لا معنى لسؤال «أين مفاتيحه؟» عن وحدةٍ لا وجود لها.
        return findings

    for name in REAL_SMS_GATEWAYS.get(backend, ()):
        if not str(getattr(settings, name, "") or "").strip():
            findings.append(
                Error(
                    f"SMS_BACKEND هو بوّابةٌ حقيقيّة ({backend}) و{name} فارغ.",
                    hint="لا رسالةَ تخرج: أوّلُ إرسالٍ يرفع `SmsSendFailed` "
                    "ويُسجَّل في `SmsFailure`، فلا يتحقّق أحدٌ من رقمه ولا "
                    "يدخل أحدٌ إلى النظام — والشاشةُ لا تقول أكثر من «تعذّر "
                    "إرسال رمز التحقق».",
                    id="accounts.E004",
                )
            )

    return findings


#: Every scope `apps.accounts.throttling` can read. Listed here rather than
#: derived from the classes so that deleting a limit is a deliberate edit in two
#: files, not a limit that quietly stops being required.
REQUIRED_THROTTLE_SCOPES = ("otp_send_phone", "otp_send_caller", "otp_verify_caller")

LOCAL_MEMORY_CACHE = "django.core.cache.backends.locmem.LocMemCache"
DUMMY_CACHE = "django.core.cache.backends.dummy.DummyCache"


@register(Tags.security, deploy=True)
def otp_rate_limits_are_real_in_a_deployed_environment(app_configs, **kwargs) -> list:
    """A limit that is off, or that each worker counts on its own, is not a limit.

    Both findings here are `Error`, not `Warning`: an unmetered send path is a
    third party's SMS bill charged to us, and the whole reason T602 exists.
    """
    findings: list = []

    rates = getattr(settings, "OTP_THROTTLE_RATES", {})
    missing = [scope for scope in REQUIRED_THROTTLE_SCOPES if not rates.get(scope)]
    if missing:
        findings.append(
            Error(
                "OTP rate limits are not configured for: " + ", ".join(missing) + ".",
                hint="Set them in OTP_THROTTLE_RATES. An unmetered send path is "
                "a free SMS gateway for whoever finds it.",
                id="accounts.E002",
            )
        )

    # A per-process cache under N workers turns "5/hour" into "5N/hour", and
    # nothing in the settings says so. This is the difference between a limit
    # and the appearance of one.
    backend = settings.CACHES.get("default", {}).get("BACKEND", "")
    if backend in (LOCAL_MEMORY_CACHE, DUMMY_CACHE):
        findings.append(
            Error(
                f"The default cache is {backend}, which every worker process "
                "holds separately — so the OTP rate limits count per worker.",
                hint="Point CACHE_URL at Redis; the limits are only shared if "
                "the counter is.",
                id="accounts.E003",
            )
        )

    return findings
