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
DOTENV = BACKEND_DIR / ".env"

#: المتغيّرات التي تملكها هذه الاختبارات: تُحذف من بيئة المفسّر الفرعي حتى لا
#: تتسرّب قيمة من صدفة المطوّر فتجعل الحارس يمرّ لسبب خاطئ.
MANAGED = frozenset({"SECRET_KEY", "DEBUG", "ODOO_ENABLED", "DJANGO_SETTINGS_MODULE"})

DEFAULT_SECRET_KEY = "dev-only-insecure-key"


def production_settings_module() -> str:
    """اسم وحدة إعدادات الإنتاج، أياً كانت بنية الإعدادات الحالية.

    بعد T002 تصير `config.settings.prod`؛ قبله الإعدادات ملف واحد. الاختبار
    يقيس الحارس لا مكانه، فيتبع البنية الموجودة بدل أن ينكسر عند نقلها.
    """
    return "config.settings.prod" if SETTINGS_PACKAGE_DIR.is_dir() else "config.settings"


def dotenv_defines(name: str) -> bool:
    """هل ملف `.env` المحلي يعرّف هذا المتغيّر؟

    `django-environ` يقرأ `.env` ويملأ منه ما ليس في البيئة، فوجود المفتاح هناك
    يبطل الاختبار. `.env` غير مرفوع (وCI بلا واحد)، فهذه حالة الجهاز المحلي وحده.
    """
    if not DOTENV.exists():
        return False
    prefix = f"{name}="
    return any(
        line.strip().startswith(prefix)
        for line in DOTENV.read_text(encoding="utf-8").splitlines()
    )


def import_settings_in_a_fresh_process(script: str, **environment: str):
    env = {key: value for key, value in os.environ.items() if key not in MANAGED}
    env.update(environment)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )


def test_production_settings_refuse_the_default_secret_key():
    """A3: بلا DEBUG وبمفتاح افتراضي، العملية تموت — لا تعمل بمفتاح معروف."""
    if dotenv_defines("SECRET_KEY"):
        pytest.skip(f"{DOTENV} يعرّف SECRET_KEY فيغطّي الافتراضي — احذفه لتشغيل هذا الفحص")

    module = production_settings_module()
    result = import_settings_in_a_fresh_process(
        f"import importlib; importlib.import_module({module!r})",
        DEBUG="False",
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

    if dotenv_defines("ODOO_ENABLED"):
        pytest.skip(f"{DOTENV} يعرّف ODOO_ENABLED فيغطّي الافتراضي")

    module = production_settings_module()
    result = import_settings_in_a_fresh_process(
        "import importlib;"
        f"m = importlib.import_module({module!r});"
        "print('ODOO_ENABLED=', repr(m.ODOO_ENABLED))",
        DEBUG="True",
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
