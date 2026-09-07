"""الحُرّاس التي تمنع الإعدادات من العمل بأسرار افتراضية أو بتكامل مفتوح.

هذه الحُرّاس تُطلق أثناء **استيراد** ملف الإعدادات، لا عند استدعاء دالة، فلا
يمكن اختبارها بالطريقة المعتادة: الإعدادات محمَّلة بالفعل في هذه العملية.
لذلك كل اختبار هنا يستورد الإعدادات في مفسّر بايثون جديد ببيئة نتحكّم فيها،
ثم يقرأ ما فعله ذلك المفسّر. هذا أبطأ من الاستيراد المباشر، لكنه الشيء الوحيد
الذي يقيس الحارس فعلاً بدل أن يقيس نسخة معاد تحميلها بحالة ملوّثة.

المرجع: المادة ٢-٦ (التكامل مطفأ افتراضياً) والمادة ٥-٣ (الأسرار خارج
المستودع)، ومعيار القبول A3 في spec الفيز 001.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PACKAGE_DIR = BACKEND_DIR / "config" / "settings"

#: المتغيّرات التي تملكها هذه الاختبارات: تُحذف من بيئة المفسّر الفرعي حتى لا
#: تتسرّب قيمة من صدفة المطوّر فتجعل الحارس يمرّ لسبب خاطئ.
MANAGED = frozenset(
    {
        "SECRET_KEY",
        "DEBUG",
        "ODOO_ENABLED",
        "DJANGO_SETTINGS_MODULE",
        # `prod` refuses to boot without it, and that refusal is a third
        # guard's subject. Owned here so neither test below can fail — or
        # pass — for a reason it is not about.
        "ALLOWED_HOSTS",
        # The dev-cache default is measured with no server address anywhere:
        # neither the developer's shell nor their `.env` may supply one.
        "CACHE_URL",
    }
)

DEFAULT_SECRET_KEY = "dev-only-insecure-key"


def production_settings_module() -> str:
    """اسم وحدة إعدادات الإنتاج، أياً كانت بنية الإعدادات الحالية.

    بعد T002 تصير `config.settings.prod`؛ قبله الإعدادات ملف واحد. الاختبار
    يقيس الحارس لا مكانه، فيتبع البنية الموجودة بدل أن ينكسر عند نقلها.
    """
    return "config.settings.prod" if SETTINGS_PACKAGE_DIR.is_dir() else "config.settings"


#: Neutralises `environ.Env.read_env` in the child before the settings are
#: imported. `read_env` is handed an absolute `BASE_DIR / ".env"`, so no cwd or
#: environment variable can steer it away from the developer's own file — and
#: with that file present, both guards below used to *skip*. A skipped guard
#: reads as a single `s` in pytest's output, so the two checks the acceptance
#: criterion calls «الاختباران يمرّان» were passing nowhere: not locally, where
#: they skipped, and not in CI, which has never run them. Stubbing the reader is
#: what makes them measure the thing they name — the value with no `.env` and no
#: variable set — on every machine.
NO_DOTENV = "import environ;environ.Env.read_env = staticmethod(lambda *a, **k: None);"


def import_settings_in_a_fresh_process(script: str, **environment: str):
    env = {key: value for key, value in os.environ.items() if key not in MANAGED}
    env.update(environment)
    return subprocess.run(
        [sys.executable, "-c", NO_DOTENV + script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_settings_refuse_the_default_secret_key():
    """A3: بلا DEBUG وبمفتاح افتراضي، العملية تموت — لا تعمل بمفتاح معروف."""
    module = production_settings_module()
    result = import_settings_in_a_fresh_process(
        f"import importlib; importlib.import_module({module!r})",
        DEBUG="False",
        ALLOWED_HOSTS="example.test",
    )

    assert result.returncode != 0, "الإعدادات قبلت المفتاح الافتراضي خارج DEBUG"
    assert "RuntimeError" in result.stderr
    assert "SECRET_KEY" in result.stderr


def test_the_default_secret_key_is_still_the_one_the_guard_watches():
    """لو تغيّر النص الافتراضي في الإعدادات وحده، الحارس أعلاه يصير بلا معنى."""
    assert any(
        DEFAULT_SECRET_KEY in path.read_text(encoding="utf-8")
        for path in (BACKEND_DIR / "config").rglob("*.py")
    ), f"لم يعد {DEFAULT_SECRET_KEY!r} موجوداً في الإعدادات — حدّث هذا الاختبار مع الحارس"


def test_odoo_is_off_unless_someone_turns_it_on_deliberately():
    """المادة ٢-٦: لا شيء يصل لنظام محاسبة حقيقي بلا قرار صريح لتلك البيئة."""
    assert settings.ODOO_ENABLED is False, "التكامل مفتوح تحت إعدادات الاختبار"

    module = production_settings_module()
    result = import_settings_in_a_fresh_process(
        "import importlib;"
        f"m = importlib.import_module({module!r});"
        "print('ODOO_ENABLED=', repr(m.ODOO_ENABLED))",
        # A real key, because `prod` refuses the default one and that refusal is
        # the *other* guard's subject. This one is only about the integration
        # switch, and it must not pass or fail for the key's reasons.
        SECRET_KEY="a-key-that-is-not-the-insecure-default",
        DEBUG="False",
        ALLOWED_HOSTS="example.test",
    )

    assert result.returncode == 0, result.stderr
    assert "ODOO_ENABLED= False" in result.stdout


def test_the_test_settings_inherit_production_not_development():
    """فحص نصّي — اختبار يعمل تحت إعدادات ألطف من الإنتاج لا يثبت شيئاً.

    (v1: `sql_mode` متساهل محلياً وصارم على الخادم، فمرّ منطق فلوس ثم سقط.)
    """
    if not SETTINGS_PACKAGE_DIR.is_dir():
        pytest.skip(
            "الإعدادات ما زالت ملفاً واحداً — T002 لم يُنفَّذ بعد. "
            "هذا الفحص يسري تلقائياً فور ظهور config/settings/."
        )

    source = (SETTINGS_PACKAGE_DIR / "test.py").read_text(encoding="utf-8")
    import_lines = [
        line
        for line in source.splitlines()
        if line.startswith("from ") or line.startswith("import ")
    ]

    assert any("prod" in line for line in import_lines), "test.py لا يرث prod"
    assert not any("dev" in line for line in import_lines), "test.py يستورد من dev"


def test_dev_cache_defaults_to_local_memory_without_redis():
    """بلا Redis على جهاز المطوّر، أول POST على الدخول كان 500.

    القاعدة كانت تشير الكاش إلى Redis دائماً، ولا شيء في dev يشغّله — فكل لمسة
    كاش (ومحدِّد الدخول أولها) تموت على الاتصال. الافتراضي هنا ذاكرة محلية ما
    لم يقل CACHE_URL غير ذلك، وبوابة `--deploy` (accounts.E003) ترفضها في أي
    بيئة منشورة.
    """
    script = (
        "import importlib;"
        "m = importlib.import_module('config.settings.dev');"
        "print('CACHE_BACKEND=', m.CACHES['default']['BACKEND'])"
    )
    result = import_settings_in_a_fresh_process(script)

    assert result.returncode == 0, result.stderr
    assert "CACHE_BACKEND= django.core.cache.backends.locmem.LocMemCache" in result.stdout


def test_dev_cache_still_honours_an_explicit_redis_address():
    """الافتراضي أعلاه لا يقفل الباب: عنوان مكتوب يبقى عنواناً."""
    script = (
        "import importlib;"
        "m = importlib.import_module('config.settings.dev');"
        "print('CACHE_BACKEND=', m.CACHES['default']['BACKEND'])"
    )
    result = import_settings_in_a_fresh_process(
        script, CACHE_URL="redis://127.0.0.1:6379/2"
    )

    assert result.returncode == 0, result.stderr
    assert "CACHE_BACKEND= django.core.cache.backends.redis.RedisCache" in result.stdout
