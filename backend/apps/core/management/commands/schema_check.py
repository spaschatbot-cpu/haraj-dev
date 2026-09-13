"""المخطط المرفوع = ما يولّده الكود اليوم — T621.

**لماذا أمرٌ واحد يكتب ويفحص، لا أمران:** الفحص الذي يقارن بشيءٍ وُلِّد بطريقةٍ
غير التي كُتب بها الملفُّ المرفوع يقارن شيئين مختلفين، ويفشل على فرقٍ في
الترتيب أو السطر الأخير لا على فرقٍ في العقد. فالمولِّد هنا واحد، و`--write`
تكتب مخرجَه بعينه، والفحصُ يقارن به بايتاً ببايت.

**ولماذا هذا أصلاً:** `backend/openapi/schema.yaml` هو العقد الذي يُولَّد منه
عميلان — Dart في `mobile/` وTypeScript في `web/lib/api/schema.ts`. نسخةٌ قديمةٌ
فيه أسوأ من غيابه: البناء أخضر، و`tsc` راضٍ، والانحرافُ يكتشفه عميلٌ يرفض
الخادمُ طلبَه على حقلٍ ما زال العميل يظنّه موجوداً.

ثلاثةُ أسئلةٍ يجيب عنها هذا الأمر، وكلٌّ منها كان يُكتشف متأخّراً:

١. **هل يُبنى المخطط بلا تحذير؟** `--fail-on-warn` لا `--validate` وحده:
   spectacular *يحذّر* ولا يُخطئ حين يعجز عن استنتاج مُسلسِل أو نوع، والتحذير
   يصير `dynamic` في الـDart و`string` في الـTS — عميلٌ يُصرَّف ويحمل النوع
   الخطأ.

٢. **هل المرفوع هو ما يولّده الكود؟** وإلّا فالعقدُ في المستودع يصف خلفيّةً
   لم تعد موجودة.

٣. **هل كلُّ مسارٍ مسجَّلٍ تحت `/api/v1/` موجودٌ في المخطط؟** spectacular
   **يتخطّى بصمت** أي عرضٍ لا يستطيع استبطانه، فتُشحن نقطةٌ تعمل بـcurl ولا
   يراها أيُّ عميلٍ مولَّد — ولا يظهر ذلك في أي فرق، لأن المسار لم يدخل الملفَّ
   قطّ.

التشغيل:

    python manage.py schema_check            # يفحص، ويسقط بـ1 عند الاختلاف
    python manage.py schema_check --write    # يعيد توليد الملف المرفوع
"""

from __future__ import annotations

import difflib
import re
import tempfile
from pathlib import Path

import yaml
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.urls import URLPattern, URLResolver, get_resolver

#: العقد المرفوع. `BASE_DIR` هو `backend/`.
SCHEMA_FILE = Path(settings.BASE_DIR) / "openapi" / "schema.yaml"

#: ما دونه ليس عقدَ هذه المنصّة. لوحةُ الموظّفين و`/admin/` و`/webhooks/` خارج
#: العقد عمداً: لا عميل مولَّد يستهلكها.
API_PREFIX = "api/v1/"

#: `<int:pk>` في Django و`{id}` في المخطط اسمان لشيءٍ واحد، وspectacular يعيد
#: تسمية المُعامل من المُسلسِل. فالمقارنةُ على **هيكل** المسار لا على اسم
#: مُعامله — وإلّا سقط الفحص على إعادة تسميةٍ لا تغيّر العقد.
_DJANGO_PARAM = re.compile(r"<[^>]+>|\(\?P<[^>]+>[^)]*\)")
_SCHEMA_PARAM = re.compile(r"\{[^}]+\}")


class Command(BaseCommand):
    help = "يتحقّق أن openapi/schema.yaml هو ما يولّده الكود، أو يعيد كتابته."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--write",
            action="store_true",
            help="اكتب المخطط المولَّد فوق الملف المرفوع بدل مقارنته به.",
        )

    def handle(self, *args, **options) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            fresh = Path(scratch) / "schema.yaml"
            self._generate(fresh)
            document = yaml.safe_load(fresh.read_text(encoding="utf-8"))
            missing = _routes_missing_from(document)

            if options["write"]:
                SCHEMA_FILE.write_bytes(fresh.read_bytes())
                self.stdout.write(
                    f"{SCHEMA_FILE} كُتب — {len(document.get('paths', {}))} مساراً."
                )
            else:
                self._compare(fresh)
                self.stdout.write(
                    f"المخطط مطابق — {len(document.get('paths', {}))} مساراً."
                )

        # بعد الكتابة أيضاً: مسارٌ تخطّاه المولِّد لا يظهر في أي فرق، لأنه لم
        # يدخل الملفّ قطّ. فالسؤال يُسأل في الحالتين، ويسقط في الحالتين.
        if missing:
            raise CommandError(
                "مسارات مسجَّلة تحت /api/v1/ ولا أثر لها في المخطط "
                f"({len(missing)}):\n  " + "\n  ".join(missing) + "\n\n"
                "spectacular يتخطّى بصمتٍ عرضاً لا يستطيع استبطانه — النقطة تعمل "
                "بـcurl ولا يراها أيُّ عميل مولَّد. عرّف لها مُسلسِلاً أو "
                "`@extend_schema`."
            )

    # -- الخطوات -----------------------------------------------------------

    def _generate(self, target: Path) -> None:
        """المولِّد نفسُه الذي كُتب به الملفُّ المرفوع، بالأعلام نفسها."""
        try:
            call_command(
                "spectacular",
                "--validate",
                "--fail-on-warn",
                "--file",
                str(target),
            )
        except Exception as error:  # noqa: BLE001 — نريد الرسالة لا الأثر
            # `SchemaGenerationError` ليست `CommandError`، فتخرج أثراً كاملاً
            # يدفن السطر الوحيد المهمّ: أيُّ مُسلسِلٍ لم يُستنتج.
            raise CommandError(f"المخطط لم يُبنَ: {error}") from error

    def _compare(self, fresh: Path) -> None:
        if not SCHEMA_FILE.exists():
            raise CommandError(
                f"{SCHEMA_FILE} غير موجود. شغّل: manage.py schema_check --write"
            )

        committed = SCHEMA_FILE.read_text(encoding="utf-8")
        generated = fresh.read_text(encoding="utf-8")
        if committed == generated:
            return

        diff = list(
            difflib.unified_diff(
                committed.splitlines(),
                generated.splitlines(),
                fromfile="openapi/schema.yaml (المرفوع)",
                tofile="ما يولّده الكود",
                lineterm="",
            )
        )
        # الفرق كاملاً قد يكون آلاف الأسطر عند إعادة تسمية مُسلسِل؛ والمطلوب هنا
        # أن يُرى **أنّه** اختلف وأينَ بدأ، لا أن يُقرأ العقد كلُّه في سجلّ.
        shown = diff[:120]
        if len(diff) > len(shown):
            shown.append(f"… و{len(diff) - len(shown)} سطراً أخرى.")

        raise CommandError(
            "openapi/schema.yaml لا يطابق ما يولّده الكود.\n\n"
            + "\n".join(shown)
            + "\n\nشغّل:  manage.py schema_check --write  ثم ارفع الفرق.\n"
            "المخطط عقدٌ يُولَّد منه عميلا Dart وTypeScript؛ نسخةٌ قديمة هنا تعني "
            "بناءً أخضر وخطأً يكتشفه عميلٌ في يده."
        )


# -- تغطية المسارات --------------------------------------------------------


def _routes_missing_from(document: dict) -> list[str]:
    """المسارات المسجَّلة تحت `/api/v1/` ولا هيكلَ لها في `paths`."""
    in_schema = {_skeleton(_SCHEMA_PARAM, path) for path in document.get("paths", {})}
    missing = []
    for route in _registered_routes():
        if not route.startswith(API_PREFIX):
            continue
        if _skeleton(_DJANGO_PARAM, "/" + route) not in in_schema:
            missing.append("/" + route)
    return sorted(set(missing))


def _registered_routes(
    resolver: URLResolver | None = None, prefix: str = ""
) -> list[str]:
    """كل نمطٍ نهائيّ في الـURLconf، مسطَّحاً بمسارِه الكامل."""
    resolver = resolver or get_resolver()
    routes: list[str] = []
    for entry in resolver.url_patterns:
        here = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            routes.extend(_registered_routes(entry, here))
        elif isinstance(entry, URLPattern):
            routes.append(here)
    return routes


def _skeleton(pattern: re.Pattern[str], path: str) -> str:
    """المسار بلا أسماء مُعاملاته: `/api/v1/vehicles/{}/photos/`."""
    return pattern.sub("{}", path)
