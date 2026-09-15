"""Production.

This module is the reference environment: `test` inherits from it so that a
green test suite means something about production, not about a friendlier
local machine.
"""

from .base import *  # noqa: F403

ENVIRONMENT_NAME = env("ENVIRONMENT_NAME", default="production")  # noqa: F405

DEBUG = False

# An unset host list in production means every Host header is accepted, which
# is how host-header poisoning gets in. Fail at boot instead.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise RuntimeError("ALLOWED_HOSTS must be set in production")

# والفراغُ يُرفض كما تُرفض قيمةُ التطوير. كان الشرطُ يقارن بالسنتينل وحده،
# فسطرٌ اسمُه بلا قيمة (`SECRET_KEY=` في ملفّ بيئة) **يمرّ الحارس**: جانغو
# يرمي `ImproperlyConfigured` ويبتلعها `check` فتصير تحذير `W009`، ثم يسقط
# أوّلُ طلبٍ يمسّ الجلسة — أي أن الخادم يُقلع «سليماً» ويموت عند أوّل عميل.
# والغيابُ الكامل أأمنُ من السطر الفارغ، وهذا يسوّي بينهما.
if not SECRET_KEY or SECRET_KEY == INSECURE_SECRET_KEY:  # noqa: F405
    raise RuntimeError("SECRET_KEY must be set outside DEBUG")

# --------------------------------------------------------------------------
# Transport and cookies
# --------------------------------------------------------------------------

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

# الدفترُ هو الشيءُ الوحيد الذي لا يُعوَّض إن ضاع، و`DATABASE_URL` **له قيمةٌ
# افتراضيّةٌ وهي قاعدةُ التطوير** (`base.DEV_DATABASE_URL`). فغيابُه في الإنتاج
# لا يُسقط شيئاً: الخادمُ يُقلع مشيراً إلى `haraj2@127.0.0.1`، وعلى آلةٍ فيها
# PostgreSQL محلّيّ — وهو قرارُ النشر اليوم — **قد يتّصل فعلاً**، فيكتب إنتاجٌ
# كاملٌ في قاعدةٍ ليست قاعدته وهو يظنّ نفسه سليماً. مقيسٌ في عقد البيئة §٤:
# بلا `DATABASE_URL` يعطي `check` رمزَ خروجٍ صفراً و`NAME='haraj2'`.
#
# والقيمةُ الافتراضيّة تُرفض كما يُرفض الغياب، تماماً كحارس `SECRET_KEY` تحته:
# من نسخ `.env.example` كما هو لم يقل شيئاً عن قاعدته.
_settings_module = env("DJANGO_SETTINGS_MODULE", default="")  # noqa: F405
if not _settings_module.endswith(".test"):
    # و`settings/test.py` مستثنىً وحده لأنه يستبدل `DATABASES["default"]`
    # كاملاً بعد هذا السطر بأربعة أسطر (`TEST_DATABASE_URL`): حارسٌ يرفض قيمةً
    # لا تُستعمل هو قاعدةٌ عن الإنتاج تكسر ما ليس إنتاجاً.
    _database_url = env("DATABASE_URL", default="")  # noqa: F405
    if not _database_url or _database_url == DEV_DATABASE_URL:  # noqa: F405
        raise RuntimeError(
            "DATABASE_URL must be set outside DEBUG — refusing to boot on the "
            "development database"
        )

# Reusing connections matters here: the money engine opens a transaction per
# posting, and reconnecting on each one shows up immediately under load.
DATABASES["default"]["CONN_MAX_AGE"] = env.int(  # noqa: F405
    "CONN_MAX_AGE", default=60
)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True  # noqa: F405
DATABASES["default"].setdefault("OPTIONS", {})  # noqa: F405
DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 5)  # noqa: F405

# --------------------------------------------------------------------------
# Mail
# --------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = True

LOGGING["root"]["level"] = env("LOG_LEVEL", default="INFO")  # noqa: F405
