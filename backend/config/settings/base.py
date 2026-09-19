"""Settings shared by every environment.

This module is never used directly. Each environment imports it and then
narrows it: `dev`, `prod`, and `test` (which inherits `prod`, not `dev` —
see `specs/001-foundation/plan.md`).
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# base.py sits two packages deep (config/settings/), so BASE_DIR is the
# third parent, not the second.
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    ODOO_ENABLED=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


#: ما تقبله `django-environ` صحيحاً، حرفياً (`environ.Env.BOOLEAN_TRUE_STRINGS`).
TRUE_WORDS = ("true", "on", "ok", "y", "yes", "1")
#: وما نقبله خطأً. وكلُّ ما عداهما **يُرفض**، ولا يُقرأ إطفاءً.
FALSE_WORDS = ("false", "off", "no", "n", "0")


def flag(name: str, *, default: bool) -> bool:
    """قيمةٌ منطقيّةٌ من البيئة — **أو رفضٌ يسمّي المتغيّر**، لا إطفاءٌ صامت.

    `env.bool` تقرأ كلَّ ما ليس في :data:`TRUE_WORDS` **خطأً**: فمن كتب
    ``ODOO_ENABLED=yes`` بمسافةٍ زائدة، أو ``True.`` بنقطة، أو ``ture``، يظنّ
    أودو شغّالاً وهو مطفأ — ولا سطرَ واحدٌ يقول ذلك. مقيسٌ في
    `docs/environment-contract.md` §٥-٣: ``ODOO_ENABLED=maybe`` تُقرأ ``False``
    بلا خطأ، والفحصُ يمرّ بـ`rc=0`، ولا يُكتشف العطلُ إلا من محاسبٍ يسأل عن
    فواتيرَ لم تصل.

    والقاعدةُ هي نفسُها التي في :mod:`apps.money.units` («عملةٌ لا نعرف وحدتها
    تُرفَض ولا تُقسَم على ١٠٠ تخميناً»): **ما لا يُفهم يُرفض، ولا يُفسَّر بأهون
    المعنيين**. وثمنُ ذلك أن خطأً إملائيّاً يمنع الإقلاع — وهو الثمنُ المقصود:
    السقوطُ في الثانية الأولى أرخصُ من تكاملٍ مطفأٍ يُكتشف بعد أسبوع.

    والمُعرَّفُ فارغاً (``ODOO_ENABLED=``) يبقى على الافتراض: سطرٌ بلا قيمة هو
    «لم أقل شيئاً»، لا قيمةٌ لا تُفهم.
    """
    # `cast=str` صراحةً: المتغيّرُ قد يكون في مخطّط `Env` أعلاه بـ`(bool, …)`،
    # وعندها تُحوّله `env()` بنفسها **قبل أن نراه** — فتبتلع القيمةَ المجهولة
    # وتردّها `False`، وهو العطلُ نفسُه الذي كُتبت هذه الدالّة له.
    raw = env(name, cast=str, default=None)
    if raw is None or isinstance(raw, bool):
        return default if raw is None else raw
    text = str(raw).strip().lower()
    if not text:
        return default
    if text in TRUE_WORDS:
        return True
    if text in FALSE_WORDS:
        return False
    raise ImproperlyConfigured(
        f"{name}={raw!r} قيمةٌ لا تُفهم. المقبول: "
        f"{', '.join(TRUE_WORDS)} أو {', '.join(FALSE_WORDS)}. "
        "ولا تُقرأ قيمةٌ مجهولةٌ إطفاءً — تكاملٌ يظنّه مشغّلُه شغّالاً وهو مطفأ "
        "لا يُكتشف إلا بعد أسبوع."
    )


INSECURE_SECRET_KEY = "dev-only-insecure-key"

#: قاعدةُ التطوير، مسمّاةً كي يميّزها حارسُ `prod.py` عن قاعدةٍ حقيقيّة.
#: بلا هذا الاسم يكون الافتراضُ قيمةً مجهولةَ المصدر في `env.db`، ولا شيء
#: يستطيع أن يقول «هذه قاعدةُ جهازِ مطوّرٍ، لا قاعدةُ إنتاج».
DEV_DATABASE_URL = "postgres://haraj:haraj@127.0.0.1:5432/haraj2"

SECRET_KEY = env("SECRET_KEY", default=INSECURE_SECRET_KEY)
DEBUG = flag("DEBUG", default=False)
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# The environment names itself on /health, in the UI, and in every outbound
# message, so a test message can never look like it came from production
# (Article 5-6). "base" is a sentinel that no running environment keeps: each
# of dev/test/prod overrides it, and seeing it in a response means a settings
# module was pointed at directly, which is itself the bug.
ENVIRONMENT_NAME = "base"

# Stamped in at build time. Left empty locally, where /health falls back to
# reading the checked-out git ref.
GIT_COMMIT = env("GIT_COMMIT", default="")

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.money",
    "apps.odoo",
    "apps.migration",
    "apps.auctions",
    "apps.bidding",
    "apps.notifications",
    # ما يقرؤه **العميل** ويحرّره الموظّف: شريطُ الأخبار وباقاتُ الاشتراك.
    # ليست في `core` لأن `core` أدواتٌ مشتركة (سجلُّ التدقيق، الوقت، القفل) لا
    # نطاقٌ له شاشات؛ وليست في `notifications` لأن الإشعار رسالةٌ **لشخصٍ**
    # بقناةٍ وحالةِ تسليم، وشريطُ الأخبار جملةٌ تُعرَض للجميع بلا مُرسَلٍ إليه.
    "apps.storefront",
    # محادثاتُ الدعم — **طرفان يتبادلان**، لا رسالةٌ من النظام إلى شخص.
    # ولذلك ليست في `notifications`: تلك لها قناةٌ وحالةُ تسليمٍ وتنتهي عند
    # وصولها، وهذه لها عمرٌ وقسمٌ ومُسنَدٌ إليه وإغلاق.
    "apps.support",
    "apps.console",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # The sidebar, built from the same rows that guard the pages
                # (T802). A context processor rather than a per-view context
                # entry: a view that forgets it renders a console with no
                # navigation, and that is how a page becomes unreachable.
                "apps.console.context.navigation",
                # بصمةُ ورقة الأنماط من وقت تعديلها — بديلُ رقمٍ كان
                # يُكتب بيدٍ في القالب ولا يتذكّره أحد، فيبقى المتصفّح
                # على نسخةٍ قديمةٍ أسبوعاً كاملاً (`Cache-Control` سبعةُ أيام).
                "apps.console.context.assets",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database — PostgreSQL only.
#
# The money engine relies on SELECT ... FOR UPDATE and on deferrable
# constraints; SQLite provides neither, so it is not an accepted fallback
# even for tests.
# --------------------------------------------------------------------------

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        # والافتراضُ هنا قاعدةُ جهازِ المطوّر. وهو مريحٌ محلّيّاً وخطرٌ منشوراً:
        # إنتاجٌ بلا `DATABASE_URL` يُقلع صامتاً مشيراً إليها، وعلى آلةٍ فيها
        # PostgreSQL محلّيّ **قد يتّصل فعلاً** فيكتب في دفترٍ ليس دفترَه.
        # لذلك يرفضه `prod.py` بالاسم — انظر الحارس هناك.
        default=DEV_DATABASE_URL,
    )
}
# Connection reuse is an environment decision: prod holds connections open,
# dev and test do not.
DATABASES["default"].setdefault("CONN_MAX_AGE", 0)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# --------------------------------------------------------------------------
# Time — the hardest-won lesson from v1.
#
# Everything is stored in UTC. Auction times are entered and displayed in Saudi
# time. The conversion happens once, at the presentation edge, never in a query.
# --------------------------------------------------------------------------

LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "العربية"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "UTC"
DISPLAY_TIME_ZONE = "Asia/Riyadh"
USE_I18N = True
USE_TZ = True

# Where the admin console is mounted. A setting rather than a literal because
# the console has lived under three different prefixes across v1's four panels,
# and every hard-coded link broke on each move. Nothing writes a console path
# by hand — `ops/checks/console_urls_are_named.py` fails the build on one.
APP_BASE = env("APP_BASE", default="console").strip("/")

# من يُصادَق وبماذا — خلفيّةٌ واحدة، و`ModelBackend` **ليس** معها. T918
#
# قرارُ المالك بالحرف: «عايز تسجيل دخول الادمن يكون بيوزر و باس، مش بالرقم».
# و`ModelBackend` يُصادِق بـ`USERNAME_FIELD` وهو `phone` — فلو بقي في القائمة
# لبقي دخولُ الموظّف **برقم جوّاله وكلمته** شغّالاً إلى جانب الاسم، أي أن
# القرار يُنفَّذ في الشاشة ويُنقَض في الخلفيّة، وهو أسوأُ من ألّا يُنفَّذ:
# الشاشةُ تقول «اسم المستخدم» والباب القديم مفتوح خلفها.
#
# وما يعتمد عليه — فُحص لا افتُرض: لا نداءَ لـ`authenticate()` في `apps/`
# إطلاقاً (الوحيدةُ في `apps.accounts.authentication` صنفُ DRF لا خلفيّة)،
# ودخولُ العميل جوّالٌ و‎OTP‎ ولا يمرّ بخلفيّاتِ جانغو أصلاً، وآلةُ الصلاحيات
# موروثةٌ كاملةً لأن الخلفيّة تمتدّ `ModelBackend` ولا تُعيد كتابتَه.
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.StaffUsernameBackend"]

# Staff sign-in lands in the staff console, not Django's raw admin index. An
# explicit `?next=` still wins — this is only the default for a bare visit to
# the login page, which otherwise drops a freshly signed-in operator on a
# developer screen with no way forward.
LOGIN_REDIRECT_URL = f"/{APP_BASE}/"

# By name, not by path. Unset, Django sends every guarded page to its own
# default `/accounts/login/`, which this project has never routed — so a
# signed-out operator opening the console was handed a 404 instead of the
# sign-in page. Naming the route also keeps it correct if the login moves,
# the same reason the console is linked by `{% url %}` and never by prefix.
LOGIN_URL = "admin-login"

# Absolute, with the leading slash, deliberately. A relative "static/" makes
# `{% static %}` emit a path resolved against the *page* — so the stylesheet of
# `/admin/login/` was requested from `/admin/static/…` and no styled page ever
# loaded, including Django's own admin skin. Nobody noticed because the project
# had no static files of its own until the console gained one (T819).
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "media"))

# الأصل الذي تُطلب منه الصور — ولا بدّ أن يكون مطلقاً.
#
# ‏`FieldFile.url` يعطي مساراً نسبياً (`/media/…`)، وهو صحيحٌ ما دام الخادم
# الذي يرسم الصفحة هو الذي يخدم الملفّ. ولم يعد كذلك: الويب تطبيق Next على
# أصلٍ آخر (وعلى Vercel في الإنتاج)، والتطبيق يقرأ من الخلفية. فمسارٌ نسبيّ
# في بطاقة المركبة يُطلب من أصل **العميل** لا من أصلنا، فترجع 404 على كل صورة
# — وقد وقع ذلك حرفياً: البطاقات كاملةً والصور مكسورة.
#
# وفارغاً يبقى السلوك القديم (مسارٌ نسبيّ)، وهو الصواب حين يخدم الخادمُ نفسه
# الصفحةَ والملفّ — كلوحة التحكّم. ويُملأ في كل بيئة لها عميلٌ منفصل، وفي
# الإنتاج بعنوان S3/CloudFront لا بعنوان الخادم. و`check_media_base_url`
# يرفض إنتاجاً بلا قيمة.
MEDIA_BASE_URL = env("MEDIA_BASE_URL", default="").rstrip("/")

# --------------------------------------------------------------------------
# Uploads — T912.
#
# The rules live in `apps.core.uploads`; these are the numbers it reads. They
# are settings because they are the knobs an operator turns when a partner's
# camera starts producing bigger files, and because a test needs to lower them
# without editing a rule.
#
# In v1 a webshell lived for months inside the photographs directory, and the
# ceilings below are only the cheap half of what stops that. The half that
# matters is that nothing under MEDIA_ROOT is ever executed or interpreted:
# Django does not serve it (there is no `static()` line in `config/urls.py`),
# and the deployment serves it as inert bytes — `docs/runbooks/uploads.md`
# carries the web-server stanza and `apps.core.checks` refuses a deployed
# environment that hands the directory to Django or to the static files app.
# --------------------------------------------------------------------------

#: Ten megabytes. A phone photograph of a car is one to four; twice the largest
#: real one leaves room for a partner's DSLR without leaving room for a payload.
UPLOAD_MAX_BYTES = env.int("UPLOAD_MAX_BYTES", default=10 * 1024 * 1024)

#: Read from the header **before** anything decodes the file. A 6 KB PNG can
#: declare 40,000 × 40,000 and ask for gigabytes the moment it is opened, and no
#: byte limit sees that coming.
UPLOAD_MAX_IMAGE_PIXELS = env.int("UPLOAD_MAX_IMAGE_PIXELS", default=50_000_000)
UPLOAD_MAX_IMAGE_EDGE = env.int("UPLOAD_MAX_IMAGE_EDGE", default=12_000)

# Django buffers an upload in memory up to this size and spills the rest to a
# temporary file. Kept below the upload ceiling so a large file costs disk
# rather than resident memory in every worker at once.
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "FILE_UPLOAD_MAX_MEMORY_SIZE", default=2 * 1024 * 1024
)

# The whole non-file request body. Django's own default; written down because
# it is a rate limit wearing another name and reviewers should see the number.
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DATA_UPLOAD_MAX_MEMORY_SIZE", default=2 * 1024 * 1024
)

# Explicit rather than inherited: a stored upload is data, and a file arriving
# with the executable bit set is one misconfigured web server away from being a
# program. This is the mode every written file gets.
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# --------------------------------------------------------------------------
# The edge — who is calling, and how often they may. T914.
# --------------------------------------------------------------------------

#: How many proxies sit in front of this process.
#:
#: 0 means the application is reached directly and `REMOTE_ADDR` is the truth;
#: `X-Forwarded-For` is then a header a caller wrote and is ignored entirely. An
#: environment behind one nginx sets 1, and only the last entry of the header is
#: read. Both `apps.core.net.client_ip` and DRF's `NUM_PROXIES` below are this
#: number, because two answers to "who is calling" is two different rate limits.
#:
#: Why it matters more than it looks: with DRF's default (unset), the *whole*
#: forwarded header becomes the caller's identity, so writing a different value
#: on each request buys a fresh budget each time — one header and a loop, and
#: the metered OTP path is unmetered again.
TRUSTED_PROXY_HOPS = env.int("TRUSTED_PROXY_HOPS", default=0)

#: Limits on the paths DRF's throttles cannot reach, read by
#: `apps.core.ratelimit`. A scope missing from this dict means that limit is
#: off; `settings/test.py` empties it so the suite is not order-dependent, and
#: `apps.core.checks` refuses a deployed environment where any of them is
#: missing.
#:
#: The numbers:
#:
#: * **odoo_webhook** — Odoo bursts when an operator posts a batch, so the
#:   ceiling is generous. It bounds a runaway retry loop; it does not shape
#:   normal traffic, because a limiter that drops real messages would break the
#:   one rule that boundary exists to keep.
#: * **payment_callback** — the same shape and one sender, and until T914 it had
#:   no limit at all: every request from anyone who could reach it wrote a row.
#: * **staff_login_ip / staff_login_account** — the passwords behind these open
#:   `money.act` and `money.exception`. Ten an hour from one address is a person
#:   who forgot which password they used; five against one account is the same
#:   person and not a list being worked through. Both, for the reason
#:   `apps.accounts.throttling` gives at length: the per-account limit alone is
#:   defeated by spraying one password across many accounts, and the per-address
#:   limit alone is defeated by a botnet aimed at one account.
EDGE_THROTTLE_RATES: dict[str, str] = {
    "odoo_webhook": env("ODOO_WEBHOOK_RATE", default="600/minute"),
    "payment_callback": env("PAYMENT_CALLBACK_RATE", default="600/minute"),
    "staff_login_ip": env("STAFF_LOGIN_RATE_PER_IP", default="10/hour"),
    "staff_login_account": env("STAFF_LOGIN_RATE_PER_ACCOUNT", default="5/hour"),
}

# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Bearer first: the customer apps carry a token and nothing else, and
        # trying it first keeps the common path one lookup long. Session stays
        # for the staff pages and the browsable schema.
        "apps.accounts.authentication.BearerTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    # الوسمُ اسمُ المورد لا `v1` — والسبب ومداه في `config/schema_hooks.py`.
    "DEFAULT_SCHEMA_CLASS": "config.schema_hooks.ResourceTaggedAutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    # One envelope for every error the API can return, so the Flutter app has a
    # single branch to write and every message reaches the user in Arabic.
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
    # How many proxies in front of us DRF should believe (T914).
    #
    # This one number is the difference between a rate limit and the appearance
    # of one, and DRF's default is the dangerous value: unset, `get_ident`
    # returns the *whole* `X-Forwarded-For` header as the caller's identity, so
    # a caller writing a different value on each request gets a fresh budget
    # every time. One header and a loop reopens the free-SMS gateway T602
    # closed. Read from the same setting `apps.core.net` reads, so the two
    # cannot drift, and `apps.core.checks` fails a deployed environment where
    # they have.
    "NUM_PROXIES": TRUSTED_PROXY_HOPS,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Haraj One API",
    "VERSION": "2.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    #: غلافُ الخطأ الموحَّد يُوصَف في المخطط. كان قائماً في الكود وغائباً عن
    #: العقد، فكان كلُّ عميلٍ يُولَّد منه يجهل شكلَ الرفض. السبب في
    #: `config/schema_hooks.py`.
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "config.schema_hooks.describe_the_error_envelope",
        "config.schema_hooks.state_enum_defaults_in_prose",
    ],
}

# --------------------------------------------------------------------------
# Background work
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Cache
#
# A rate limit lives in the cache, so the cache decides whether the limit is a
# limit. Under gunicorn each worker holds its own local memory: four workers
# make "five an hour" mean twenty an hour, and nobody reading the setting would
# know. Redis is therefore the deployed default and `apps.accounts.checks`
# refuses a deployed environment still on local memory.
#
# Database 2 — 0 and 1 belong to Celery above, and a `FLUSHDB` aimed at a queue
# should not silently reset everyone's rate limits.
# --------------------------------------------------------------------------

CACHES = {
    "default": env.cache("CACHE_URL", default="redis://127.0.0.1:6379/2"),
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://127.0.0.1:6379/1")
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TIMEZONE = "UTC"

# --------------------------------------------------------------------------
# **لا جدولةَ دوريّة في هذا المشروع** — قرارُ المالك، ٢٠٢٦-٠٩-١٠.
#
# الكرونُ يحمل قراراً ثم يسقط صامتاً: مهمّةٌ تتوقّف فلا يفتح المزادُ في موعده
# المعلن، ولا يظهر العطلُ إلا شكوى عميل. وقد وقع هنا حرفياً — مزادٌ حان وقتُه
# ولم يُفعَّل، وآخرُ انتهى وحالتُه `live`.
#
# فالبديلُ شقّان:
#
# **ما يُقرأ يُشتقّ.** «هل المزاد مفتوح؟» جوابُه `engine.phase` من الساعة
# والحالة معاً، فالمزادُ مفتوحٌ لأن نافذته مفتوحة لا لأن عموداً قُلب. ولا شيء
# يحتاج أن يعمل ليصير الجوابُ صحيحاً.
#
# **وما يُنفَّذ يُحجَز للحظته.** تحريكُ المال بعد الانتهاء — فكُّ تأمين الخاسر
# وفوترةُ الفائز — يجب أن يقع ولو لم يفتح أحدٌ صفحة. فيُحجَز عند جدولة المزاد
# بموعدٍ هو `ends_at` نفسه (`apply_async(eta=…)`): مهمّةٌ واحدة لكل مزادٍ تعمل
# في ثانيتها، لا استطلاعٌ كلَّ دقيقة يسأل «هل خلص شيء؟».
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Domain constants
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# Signing in — one-time code, then two tokens.
#
# The numbers are settings, not literals in the code, because they are the knobs
# support asks to turn ("customers say the code expires too fast") and because
# a test needs to shorten them without editing a rule.
# --------------------------------------------------------------------------

OTP_CODE_DIGITS = env.int("OTP_CODE_DIGITS", default=6)

# Five minutes. Long enough for a delayed SMS on a bad connection, short enough
# that a code left visible on a lock screen is worthless by the time anyone
# reads it.
OTP_TTL_SECONDS = env.int("OTP_TTL_SECONDS", default=300)

# Five guesses against a six-digit code. Brute force needs 100,000 on average;
# this budget is spent long before that, and spending it voids the code rather
# than merely pausing it.
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)

# The courtesy limit on one number: no second message while the first is this
# young. It expires with the code, so it is not the limit that protects the
# bill — OTP_THROTTLE_RATES below is.
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=60)

# How often a code may be *sent*, and how often codes may be *tried*. Read by
# `apps.accounts.throttling`, deliberately not by DRF's DEFAULT_THROTTLE_RATES:
# `settings/test.py` empties DRF's throttle configuration so the suite is not
# order-dependent, and these limits must survive that decision with an off
# switch of their own rather than an ImproperlyConfigured.
#
# A scope missing from this dict means that limit is off. `apps.accounts.checks`
# refuses a deployed environment where any of them is.
#
# The numbers: five messages an hour to one number is more than a customer who
# is fighting a bad signal ever needs, and far less than harassment. Twenty an
# hour from one address covers a household or an office behind one NAT and stops
# a script walking the numbering plan. Thirty verify attempts an hour is six
# codes' worth of the five-guess budget — a person mistyping, not a list being
# worked through.
OTP_THROTTLE_RATES: dict[str, str] = {
    "otp_send_phone": env("OTP_SEND_RATE_PER_PHONE", default="5/hour"),
    "otp_send_caller": env("OTP_SEND_RATE_PER_CALLER", default="20/hour"),
    "otp_verify_caller": env("OTP_VERIFY_RATE_PER_CALLER", default="30/hour"),
}

# Fifteen minutes on the access token, thirty days on the refresh. Short access
# is what makes a stolen token expire on its own; long refresh is what keeps a
# customer from signing in every morning.
ACCESS_TOKEN_TTL_SECONDS = env.int("ACCESS_TOKEN_TTL_SECONDS", default=900)
REFRESH_TOKEN_TTL_SECONDS = env.int(
    "REFRESH_TOKEN_TTL_SECONDS", default=60 * 60 * 24 * 30
)

# The seam, not the provider. `apps.accounts.checks` refuses the console backend
# under `check --deploy`, so a real environment cannot quietly log codes instead
# of sending them.
SMS_BACKEND = env("SMS_BACKEND", default="apps.accounts.sms.console_backend")

#: بوّابةُ الرسائل — OURSMS، وهي نفسُها التي يرسل منها v1.
#:
#: فارغةٌ افتراضياً، و`SMS_BACKEND` يبقى على `console_backend` حتى يُوجَّه
#: صراحةً إلى `apps.accounts.sms.oursms_backend`. فبيئةٌ تُرفع بلا مفاتيح تطبع
#: ولا ترسل، ولا تكلّف هللة — بدل أن ترسل إلى أرقامٍ حقيقيةٍ بلا قصد.
OURSMS_API_URL = env("OURSMS_API_URL", default="")
OURSMS_TOKEN = env("OURSMS_TOKEN", default="")
OURSMS_SENDER = env("OURSMS_SENDER", default="HirajOne")

#: كلفةُ الرسالة النصّيّة الواحدة بالريال — **بلا قيمةٍ افتراضيّة، عمداً**.
#:
#: شاشةُ «إرسال إشعار» تعرض تقديرَ الكلفة قبل الزرّ (عددُ المستلمين × هذه)،
#: والرقمُ المخترَع في شاشةِ إنفاقٍ أسوأُ من فراغ: من يقرأ «٤٤٬٠٣٦ × ٠٫١٠ =
#: ٤٬٤٠٣ ريالاً» يتصرّف على أساسه، ولو كان العقدُ بضعفِ ذلك لكان قد قرّر على
#: رقمٍ اخترعناه له. فالفارغُ يُعرض فارغاً: «الكلفة غير معروفة — يحتاج قيمةً
#: من المالك»، والبثُّ لا يُمنع بسببه.
#:
#: وسلسلةٌ لا `float`: المادة ٣-٢ تمنع `float` على مسار مال، وقارئُها الوحيد
#: يحوّلها `Decimal`. وv1 لا يملك هذا الإعداد ولا ما يشبهه — لا سعرَ رسالةٍ
#: ولا ميزانيةَ ولا حدّاً أقصى في الشجرة كلِّها.
SMS_COST_PER_MESSAGE = env.str("SMS_COST_PER_MESSAGE", default="")

# ---------------------------------------------------------------------------
# إشعاراتُ التطبيق — FCM. T943
# ---------------------------------------------------------------------------
#
# **مزوّدٌ واحدٌ بقرار المالك** (١٨ سبتمبر ٢٠٢٦): «أنا عايز الطريقة بتاعة FCM».
# وv1 يحمل مسلكين — OneSignal ثمّ FCM — ومزوّدان في مسارٍ واحد يجعلان جوابَ
# «لماذا لم تصله؟» يحتاج أن تعرف أوّلاً أيّهما حاول.
#
# **والمفتاحُ هنا لا في القاعدة**: نسخةُ قاعدةٍ تُؤخذ للتطوير تحمل كلَّ صفّ،
# ومفتاحٌ في صفٍّ يخرج مع أوّل نسخة. و`.env` على الخادم لا يخرج معها.
# وشاشةُ اللوحة تُدير كلَّ ما عداه (انظر `apps/notifications/push.py`).

#: معرّفُ مشروع Firebase. فارغاً يُقرأ من `project_id` في حساب الخدمة.
FCM_PROJECT_ID = env("FCM_PROJECT_ID", default="")

#: حسابُ الخدمة **نصَّ JSON كاملاً** — أو اتركه واستعمل المسار أدناه.
FCM_SERVICE_ACCOUNT_JSON = env("FCM_SERVICE_ACCOUNT_JSON", default="")

#: أو مسارُ ملفِّ حساب الخدمة على الخادم. أوضحُ للملفّات الطويلة، ويُقرأ عند
#: كلّ نداءٍ فلا يحتاج إعادةَ تشغيلٍ بعد استبداله.
FCM_SERVICE_ACCOUNT_PATH = env("FCM_SERVICE_ACCOUNT_PATH", default="")

# ---------------------------------------------------------------------------
# حسابُ الحوالات البنكيّة — ما يُعرَض للعميل ليحوّل إليه. T954.
# ---------------------------------------------------------------------------
# قناتان لشحن التأمين: ميسر، **والحوالة البنكيّة**. وكان زرُّ الحوالة في
# التطبيق يردّ «قريباً» بلا رقم حساب، فالعميلُ الذي يريد التحويل لا يجد إلى
# أين. والفاتورةُ تُسدَّد بالحوالة **وحدَها** (قرار المالك ١٩ سبتمبر ٢٠٢٦:
# «ممنوع السداد من رصيد التأمين للفواتير»).
#
# **في البيئة لا في الشيفرة**: v1 يخزّنها في `account_page_settings` ويحرّرها
# من اللوحة، والمقصدُ واحد — تغييرُ الحساب لا يحتاج إصدارَ تطبيقٍ جديد ولا
# نشرَ كود. وليست سرّاً (حسابٌ يُستقبَل عليه)، لكنّها بيانُ شركةٍ يتغيّر،
# ومكتوبةٌ في المستودع تعني نشرةً لكلّ تعديل.
#
# وفارغةً افتراضاً: النقطةُ ترفض بجملةٍ تقول «غير مضبوط» بدل أن تعرض حساباً
# نصفَ صحيح — ورقمُ آيبانٍ خطأ يُرسل مالَ عميلٍ إلى حسابٍ آخر.
BANK_TRANSFER_BENEFICIARY = env("BANK_TRANSFER_BENEFICIARY", default="")
BANK_TRANSFER_BANK = env("BANK_TRANSFER_BANK", default="")
BANK_TRANSFER_IBAN = env("BANK_TRANSFER_IBAN", default="")
BANK_TRANSFER_ACCOUNT = env("BANK_TRANSFER_ACCOUNT", default="")

CURRENCY = "SAR"
INSURANCE_DEPOSIT_AMOUNT = env.int("INSURANCE_DEPOSIT_AMOUNT", default=10_000)

# A setting and not a literal, because the rate is a fact about the tax year and
# not about this code. Read as a string and turned into a Decimal at the one
# place that uses it — `float` is forbidden on any money path (Article 3-2).
VAT_RATE = env.str("VAT_RATE", default="0.15")

# The smallest bid the platform accepts, in riyals. Not a price the car stands
# on — that is `Vehicle.reserve_price` and nothing else — and deliberately not
# derived from it: a bid under the reserve is a supported outcome that sends
# the car to its owner for a decision. This refuses the one-riyal bid, which
# pins a full deposit and says nothing about the car.
MINIMUM_BID = env.int("MINIMUM_BID", default=1_000)

# How often one signed-in bidder may act (T611). Not about cost — a bid sends
# no message — but about a script racing the close (fifty transactions the rest
# of the auction queues behind) and about reading somebody's deposit balance off
# the refusals, which name their numbers because a customer is entitled to know.
#
# Sixty an hour is a bidder revising often on a busy day; it is not a loop.
# Read by `apps.bidding.throttling`, and off when unset, for the same reason
# OTP_THROTTLE_RATES above is: `settings/test.py` empties DRF's throttle
# configuration so the suite is not order-dependent.
BID_THROTTLE_RATES: dict[str, str] = {
    "bid_caller": env("BID_RATE_PER_CALLER", default="60/hour"),
}

# --------------------------------------------------------------------------
# Card payments — off by default, like every other integration.
#
# The callback endpoint is unauthenticated by nature, so the shared secret is
# what stands between a stranger and a credited wallet. With no secret set the
# endpoint refuses every message rather than falling back to trusting them.
# --------------------------------------------------------------------------

PAYMENT_GATEWAY = env("PAYMENT_GATEWAY", default="moyasar")
#: Where a customer is sent to pay, as a template the environment supplies.
#:
#: Empty by default, and `apps.money.gateway` refuses in Arabic when it is —
#: an unconfigured integration must refuse rather than guess, because the guess
#: here is a customer sent to a broken page with money in their hand.
#:
#: A template rather than code so that changing gateway is an environment
#: decision. It may name `{reference}`, `{amount}` and `{currency}`; the
#: reference is the only identifier that crosses, and the gateway never learns a
#: user id (that is the whole reason `PaymentIntent` is written first).
PAYMENT_CHECKOUT_TEMPLATE = env("PAYMENT_CHECKOUT_TEMPLATE", default="")
PAYMENT_WEBHOOK_SECRET = env("PAYMENT_WEBHOOK_SECRET", default="")
#: The gateway's own words for "the money arrived". Kept as data, because a new
#: word from them must never be read as success by accident.
PAYMENT_SUCCESS_STATUSES = env.list("PAYMENT_SUCCESS_STATUSES", default=["paid"])
#: بأيّ وحدةٍ تتكلّم هذه البوّابة: `minor` (هللة/سنت) أو `major` (ريال).
#:
#: الافتراضُ `minor` لأن البوّابة الافتراضيّة Moyasar ترسل الهللة — وv1 يقسم على
#: ١٠٠ صراحةً. وكان هذا الطرفُ **غائباً تماماً**، فكانت كلُّ دفعةٍ ستُقرأ مئةَ
#: ضعفها وتذهب إلى المعلَّق. راجع :mod:`apps.money.units`.
PAYMENT_AMOUNT_UNIT = env("PAYMENT_AMOUNT_UNIT", default="minor")
#: كم دقيقةً تبقى نيّةُ الدفع قابلةً للدفع قبل أن تنتهي.
#:
#: ١٢٠ لأن v1 يكتب `payments_intents.expires_at = NOW() + INTERVAL 2 HOUR`.
#: وكان `PaymentIntentState.EXPIRED` و`CANCELLED` **معرَّفتين ولا يسندهما أي
#: مسار** — فنيّةٌ هجرها صاحبُها تبقى `pending` للأبد، وزرُّ الدفع حيٌّ عليها،
#: ورابطُ البوّابة يقبل الدفع بعد شهر.
PAYMENT_INTENT_TTL_MINUTES = env.int("PAYMENT_INTENT_TTL_MINUTES", default=120)
#: هل يُستعلَم عن الدفعة من البوّابة قبل تقييدها؟ **نعم افتراضاً.**
#:
#: v1 يفعلها في كل مسارٍ بلا استثناء («Fetch من Moyasar (مصدر الحقيقة)»)، ولا
#: يثق بحمولة الويبهوك أبداً. `False` إعلانُ مشغّلٍ صريحٌ بأن بوّابة هذه البيئة
#: بلا واجهةِ استعلام — وعندها تصير الحمولةُ الموقّعة هي المصدر، ويُكتب ذلك في
#: ملاحظة الرسالة لا يُسكت عنه.
PAYMENT_CONFIRM_WITH_GATEWAY = flag("PAYMENT_CONFIRM_WITH_GATEWAY", default=True)

#: مفاتيح Moyasar — فارغةٌ افتراضاً، والتكاملُ يرفض بالعربيّة حين تكون كذلك.
#:
#: السرّيُّ وحده كافٍ لأن **الخادم هو من يُنشئ الفاتورة**: لا يحتاج أيُّ عميلٍ
#: مفتاحاً منشوراً، ولا يصل المبلغ إلى متصفّحٍ أصلاً. v1 يضع
#: `publishable_api_key` في صفحة HTML ويمرّر `amount` من `$_GET` — وهو الباب
#: الذي أُغلق في v2 ولا يُفتح من الخلف.
MOYASAR_API_BASE = env("MOYASAR_API_BASE", default="https://api.moyasar.com/v1")
MOYASAR_SECRET_KEY = env("MOYASAR_SECRET_KEY", default="")
#: أين يعود العميلُ بعد الدفع. قالبٌ يسمّي `{reference}`، وفارغٌ يعني «لا
#: ترسل `callback_url` إلى Moyasar». الوجهةُ صفحةُ عميلٍ لا نقطةُ API: العودةُ
#: تحت إبهام الدافع ولا يتحرّك بها مال (`TopupDetailView` تشرح لماذا).
PAYMENT_RETURN_URL_TEMPLATE = env("PAYMENT_RETURN_URL_TEMPLATE", default="")

# --------------------------------------------------------------------------
# Odoo — off by default. Nothing reaches the accounting system until an
# operator turns it on for this environment, deliberately.
# --------------------------------------------------------------------------

# `flag` لا `env("ODOO_ENABLED")`: القيمةُ المجهولة تُرفض بصوتٍ ولا تُفسَّر
# إطفاءً — وهي المخالفةُ المقيسة في §٥-٣ من عقد البيئة.
ODOO_ENABLED = flag("ODOO_ENABLED", default=False)
ODOO_BASE_URL = env("ODOO_BASE_URL", default="")
ODOO_DB = env("ODOO_DB", default="")
ODOO_USERNAME = env("ODOO_USERNAME", default="")
ODOO_API_KEY = env("ODOO_API_KEY", default="")
ODOO_WEBHOOK_SECRET = env("ODOO_WEBHOOK_SECRET", default="")
#: أطفئ التحقّق من TLS في التطوير فقط (شهادةُ أجهزة التطوير قديمة غالباً، كـ v1).
#: يبقى `False` في الإنتاج — التحقّقُ قائم.
ODOO_INSECURE_TLS = flag("ODOO_INSECURE_TLS", default=False)
#: `payment_code` الذي يفرضه عقدُ أودو على كل دفعةٍ واستردادٍ واشتراك — وهو
#: **دفترُ اليومية عندهم**، أي أن قيمةً خاطئةً تُرحّل المالَ إلى الحساب الخطأ
#: بلا أن يُرفض النداء. لذلك إعدادُ بيئةٍ لا ثابتٌ في الشيفرة: قيمةُ الاختبار
#: غيرُ قيمة الإنتاج، وv1 يستعمل `005/01` للفواتير و`0002/02` للاشتراكات.
#:
#: **وكان افتراضيُّه `005/01` — دفترَ الإنتاج الحقيقيّ.** فبيئةُ تجريبٍ تنسى
#: كتابتَه **تُقيّد مالَ اختبارها في دفترٍ حقيقيّ**، ولا يُرفض النداء، ولا
#: يُكتشف إلّا من محاسبٍ يسأل بعد شهر. صار فارغاً بقرار المالك ٢٠٢٦-٠٩-١٤:
#: `odoo.E006` يرفض الإقلاع حين يكون أودو مُفعَّلاً بلا دفتر. وهي قاعدةُ
#: `apps/money/units.py` نفسُها — **ما لا نعرفه يُرفض ولا يُخمَّن** — لأن
#: التخمين هنا مالٌ يُقيَّد في حساب غيره.
ODOO_PAYMENT_CODE = env("ODOO_PAYMENT_CODE", default="")

# ---------------------------------------------------------------------------
# v1 — read only, and empty by default (phase 004)
# ---------------------------------------------------------------------------

# Empty means no connection is attempted at all. A migration layer that quietly
# connects to nothing and returns no rows reports "0 customers migrated" as a
# success, which is the one failure mode a migration must not have.
#
# The account this names must be **read only** at the grant (T301, criterion
# D6). `apps.migration.extract` refuses to send anything but a read, but that
# is the readable sentence in front of the guard, not the guard.
V1_DSN = env("V1_DSN", default="")

#: مسارُ نسخة `mysqldump` من v1، حين يُرحَّل من ملفٍّ لا من خادم
#: (:mod:`apps.migration.dumpfile`). فارغٌ افتراضاً للسبب نفسِه أعلاه.
#:
#: **إعدادٌ لا ثابتٌ في الأمر**: كان مسارُ جهازٍ بعينه (`D:/tmp/...`) مكتوباً
#: `default` داخل `import_v1`، فيفشل عند غيره صامتاً بـ«النسخة غير موجودة»،
#: ويحتاج أمران متتاليان كتابةَ المسار مرّتين ويختلفان يومَ تتغيّر النسخة.
V1_DUMP_PATH = env("V1_DUMP_PATH", default="")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "apps.money": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "apps.odoo": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
