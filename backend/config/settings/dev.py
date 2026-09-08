"""Local development.

The only settings module that relaxes anything. Nothing here may be imported
by `test` — a test that runs under gentler settings than production proves
nothing (Article 4-2).
"""

from .base import *  # noqa: F403

ENVIRONMENT_NAME = "development"

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Every connection is fresh, so a schema change is picked up without a restart.
DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405

# Redis is optional on a developer's machine, but the base default points the
# cache at it — so with no server running, every cache touch is a 500, starting
# with staff sign-in's own throttle. Dev therefore counts in local memory
# unless CACHE_URL points elsewhere. runserver is a single process, so
# "5/hour" still means 5/hour here; and the `--deploy` gate (accounts.E003)
# refuses local memory the moment anything deployed uses it, so this default
# cannot leak into production the way a silent fallback would.
CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}  # noqa: F405

# الويب على 3000 والخلفية هنا، فالصور تُطلب مطلقةً وإلا طلبها المتصفّح من
# أصل الويب ورجعت 404. قيمةٌ افتراضية حتى يعمل العرض بلا إعداد.
MEDIA_BASE_URL = env("MEDIA_BASE_URL", default="http://127.0.0.1:8000")  # noqa: F405

# عنوانُ أودو. الافتراضيُّ رابطُ الإنتاج **للعرض فقط** (زرُّ الفاتورة الضريبيّة
# في «ما بعد البيع»)، والاستدعاءُ يظلّ محجوباً بـ`ODOO_ENABLED=False`.
#
# لكنه الآن يقرأ `.env` أولاً: لربط أودو التيست ضع في `backend/.env`
#     ODOO_BASE_URL=https://haraj1test.odoo.com
#     ODOO_ENABLED=True
#     ODOO_API_KEY=<توكن التيست — سرٌّ لا يُودَع في الكود>
#     ODOO_INSECURE_TLS=True        # على أجهزة التطوير إن رفضت الشهادة
# فيوجَّه النقلُ إلى التيست بلا تعديل كود. غيابُ المتغيّر يُبقي رابطَ العرض.
ODOO_BASE_URL = env("ODOO_BASE_URL", default="https://haraj1.odoo.com")  # noqa: F405
