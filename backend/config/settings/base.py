"""Settings shared by every environment.

This module is never used directly. Each environment imports it and then
narrows it: `dev`, `prod`, and `test` (which inherits `prod`, not `dev` —
see `specs/001-foundation/plan.md`).
"""

from pathlib import Path

import environ

# base.py sits two packages deep (config/settings/), so BASE_DIR is the
# third parent, not the second.
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    ODOO_ENABLED=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

INSECURE_SECRET_KEY = "dev-only-insecure-key"

SECRET_KEY = env("SECRET_KEY", default=INSECURE_SECRET_KEY)
DEBUG = env("DEBUG")
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
        default="postgres://haraj:haraj@127.0.0.1:5432/haraj2",
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
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
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

# --------------------------------------------------------------------------
# Odoo — off by default. Nothing reaches the accounting system until an
# operator turns it on for this environment, deliberately.
# --------------------------------------------------------------------------

ODOO_ENABLED = env("ODOO_ENABLED")
ODOO_BASE_URL = env("ODOO_BASE_URL", default="")
ODOO_DB = env("ODOO_DB", default="")
ODOO_USERNAME = env("ODOO_USERNAME", default="")
ODOO_API_KEY = env("ODOO_API_KEY", default="")
ODOO_WEBHOOK_SECRET = env("ODOO_WEBHOOK_SECRET", default="")

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
