"""الترحيلُ كلُّه بأمرٍ واحد، وبزمنٍ مقيسٍ لكلّ خطوة — T315.

    python manage.py migrate_v1 --dry-run
    python manage.py migrate_v1

## لماذا أمرٌ جامع

**الترتيبُ ليس اختيارياً**، وكلُّ خطوةٍ تسقط بلا سابقتها: البناةُ يترجمون مفاتيح
v1 عبر `LegacyRef` الذي يكتبه `import_v1`، والفواتيرُ تحتاج المركبات، والدفترُ
يحتاج الفواتيرَ ليرهن عليها. وترتيبٌ مكتوبٌ في رأس أحدٍ أو في وثيقةٍ يُنسى مرّةً
واحدةً ليلةَ التحويل — وليلةُ التحويل هي المرّةُ التي لا تُعاد.

## والزمنُ يُقاس هنا لا يُقدَّر

معيارُ `T315`: «**رقمٌ مقيسٌ مكتوب، لا تقدير**». فكلُّ خطوةٍ تُوقَّت ويُطبع زمنُها،
والمجموعُ في الأخير. ومن يقرّر نافذةَ التحويل يقرأ رقماً جرى فعلاً على نسخةٍ
كاملة، لا حدساً.

وإن تجاوز الزمنُ النافذةَ المقبولة، فالقرارُ (تشغيلٌ على دفعات) يُبنى على هذا
الرقم — ولا يُصمَّم قبل أن يُعرف.

## وهو **لا يمسّ v1 بحال**

كلُّ خطوةٍ تقرأ ملفَّ النسخة للقراءة فقط. ولا اتّصالَ بخادم v1 من هنا إطلاقاً.
"""

from __future__ import annotations

import time
from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand

#: الترتيبُ الواجب. الاسمُ ثم ما يُمرَّر إليه.
#:
#: `build_identity_map` **قبل** الفواتير والدفتر: «يُبنى أوّلاً، ولا يُنسب ريالٌ
#: قبله» — وهو ترتيبُ الفشل في v1 بالضبط، حيث نُسبت الفلوسُ قبل حسم الهويّة.
STEPS = (
    ("import_v1", "الحسابات والمزادات والمركبات والمزايدات"),
    ("build_identity_map", "رسمُ الهوية — قبل أيّ مال"),
    ("build_invoices", "الفواتير"),
    ("build_ledger", "الدفتر"),
)


def _clock(seconds: float) -> str:
    return str(timedelta(seconds=round(seconds)))


class Command(BaseCommand):
    help = "شغّل الترحيل كلَّه بالترتيب، وقِس زمنَ كلِّ خطوة — T315."

    def add_arguments(self, parser):
        parser.add_argument("--dump", default="")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--from",
            dest="start_at",
            default="",
            help="ابدأ من هذه الخطوة (لاستئنافِ تشغيلٍ انقطع).",
        )

    def handle(self, *args, **options):
        extra = {}
        if options["dump"]:
            extra["dump"] = options["dump"]
        if options["dry_run"]:
            extra["dry_run"] = True

        start_at = options["start_at"]
        started = False
        timings: list[tuple[str, float]] = []
        total = time.monotonic()

        for name, label in STEPS:
            if start_at and not started and name != start_at:
                self.stdout.write(f"— تُخطّى {name}")
                continue
            started = True

            self.stdout.write(
                self.style.MIGRATE_HEADING(f"\n══ {name} — {label}")
            )
            step = time.monotonic()
            # بلا `try`: خطوةٌ تسقط تُوقف ما بعدها عمداً. البناةُ التالون
            # يقرؤون ما كتبته السابقة، والمضيُّ بعد سقوطها يُنتج ترحيلاً ناقصاً
            # **لا يشكو** — وهو العطلُ الوحيد الذي لا يجوز للترحيل.
            call_command(name, **extra)
            elapsed = time.monotonic() - step
            timings.append((name, elapsed))
            self.stdout.write(f"   ⏱ {_clock(elapsed)}")

        self.stdout.write(self.style.MIGRATE_HEADING("\n══ الزمن المقيس"))
        for name, elapsed in timings:
            self.stdout.write(f"  {name:<22} {_clock(elapsed)}")
        self.stdout.write(
            self.style.SUCCESS(f"  {'المجموع':<22} {_clock(time.monotonic() - total)}")
        )
