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

# معاينةُ تطبيق Flutter في متصفّح: صفحته على منفذٍ آخر، فهي أصلٌ آخر ويحجب
# المتصفّحُ كلَّ نداءٍ بلا ترويسة. الوسيطُ في `config/dev_cors.py` ولا يُستورَد
# من `prod` ولا `test` — والسببُ ومداه مشروحان هناك.
MIDDLEWARE = ["config.dev_cors.DevCorsMiddleware", *MIDDLEWARE]  # noqa: F405

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
#
# **والمنفذ لا بدّ أن يطابق الخادم الذي يعمل فعلاً**، وإلا أشار رابطُ كل صورة
# إلى منفذٍ لا أحد فيه: تعود 404، ويُزيلها `onerror` في القالب، فتظهر البطاقةُ
# كأن لا صورة لها. والعطل صامت — لا استثناء ولا سطر في السجلّ — وظُنّ مرّةً أن
# رفع صورة العرض لم يقع أصلاً وهي مرفوعةٌ سليمةٌ على القرص.
#
# **و8000 لا 8001** (١٣ سبتمبر ٢٠٢٦): المنفذُ الذي يعمل عليه الخادم هنا فعلاً،
# وهو الذي يبنى عليه تطبيقُ الجوّال (`HARAJ_API_BASE_URL` في أمر التشغيل).
# كُتب 8001 مرّةً على اسم إعدادٍ في `launch.json` لا على ما يعمل، فعادت كلُّ
# صورةٍ في الرئيسية «تعذّر تحميل الصورة». ومن يشغّل على منفذٍ آخر يضبط
# `MEDIA_BASE_URL` في بيئته.
MEDIA_BASE_URL = env("MEDIA_BASE_URL", default="http://localhost:8000")  # noqa: F405

# عنوانُ أودو. الافتراضيُّ رابطُ الإنتاج **للعرض فقط** (زرُّ الفاتورة الضريبيّة
# في «ما بعد البيع»)، والاستدعاءُ يظلّ محجوباً بـ`ODOO_ENABLED=False`.
#
# لكنه الآن يقرأ `.env` أولاً: لربط أودو التيست ضع في `backend/.env`
#     ODOO_BASE_URL=https://haraj1test.odoo.com
#     ODOO_ENABLED=True
#     ODOO_API_KEY=<توكن التيست — سرٌّ لا يُودَع في الكود>
#     ODOO_INSECURE_TLS=True        # على أجهزة التطوير إن رفضت الشهادة
# فيوجَّه النقلُ إلى التيست بلا تعديل كود. غيابُ المتغيّر يُبقي رابطَ العرض.
# `.env` قد يحمل `ODOO_BASE_URL=` فارغاً، و`env(..., default=…)` يُرجع الفارغَ
# لا الافتراض حين يكون المتغيّرُ **مُعرَّفاً فارغاً** — فيختفي زرُّ الفاتورة
# الضريبيّة في العرض. فالفارغُ يسقط إلى رابط العرض بـ`or`.
ODOO_BASE_URL = env("ODOO_BASE_URL", default="") or "https://haraj1.odoo.com"  # noqa: F405
