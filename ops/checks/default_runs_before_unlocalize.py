"""لا قالبَ يكتب ``|unlocalize|default:"…"`` — فالافتراضي لا يقع، وتُطبع «None».

العطل
=====
مرشّحا Django يعملان بالترتيب المكتوب، و``unlocalize`` مُعرَّف كـ``str(value)``.
فحين تكون القيمة ``None``:

    {{ vehicle.reserve_price|unlocalize|default:"—" }}

يحوّلها ``unlocalize`` أوّلاً إلى **السلسلة** ``"None"`` — وهي سلسلةٌ غير فارغة،
أي «صحيحة» عند ``default`` — فلا يقع الافتراضي، وتُطبع على الشاشة كلمة ``None``.
والترتيب المعكوس صحيح:

    {{ vehicle.reserve_price|default:"—"|unlocalize }}

لماذا فحصٌ لا مراجعة
====================
لأنه وقع بالفعل في **خمس شاشات** قبل أن يُكتشف — سعر الوقوف في قائمة المركبات،
وفي تفاصيلها، وفي تفاصيل المزاد، وفي شاشتَي الشريك، والممشى وسعر الرسو. ومركبةٌ
بلا سعر وقوفٍ حالةٌ عادية تماماً، فكان كلُّ من فتح واحدةً منها يقرأ ``None`` في
خانة مبلغ.

ولا يظهر في اختبار: الصفحة تُرسم بنجاح، والحالة `200`، ولا استثناء. ولا يظهر
في مراجعةٍ بالعين إلا لمن يعرف أن ``unlocalize`` يبتلع ``None`` — وهي معلومةٌ
لا يُفترض أن تُحمَل في رأس كل من يكتب قالباً.

المدى
=====
الترتيب المعكوس (``default`` ثم ``unlocalize``) صحيحٌ دائماً، فالفحص يرفض
الاتجاه الواحد ولا يشترط وجود المرشّحين معاً. و``default_if_none`` مثله تماماً
للسبب نفسه.

    python ops/checks/default_runs_before_unlocalize.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح — وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ عن قناعة.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates"

#: ``|unlocalize`` يليه ``|default`` أو ``|default_if_none``، بمسافاتٍ أو بدونها.
#: المسافات مسموحةٌ حول الأنبوب في قوالب Django، فالنمط يقبلها كي لا يمرّ
#: العطلُ نفسه مكتوباً بمسافة.
WRONG = re.compile(r"\|\s*unlocalize\s*\|\s*default(_if_none)?\s*:")


def offenders(root: Path = TEMPLATES) -> list[tuple[Path, int, str]]:
    """(الملف, رقم السطر, السطر) لكل موضعٍ بالترتيب المعكوس."""
    found = []
    for path in sorted(root.rglob("*.html")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if WRONG.search(line):
                found.append((path, number, line.strip()))
    return found


def main() -> int:
    if not TEMPLATES.is_dir():
        raise SystemExit(
            f"لا مجلد قوالب في {TEMPLATES} — إن انتقل فحدّث هذا الفحص. "
            "حارسٌ لا يجد ما يحرسه يجب أن يصرخ لا أن يمرّ."
        )

    #: الحارس الذي لا يجد ما يحرسه يصرخ — وهذا المجلد فيه ~٣٠ قالباً، وأكثر من
    #: نصفها يستعمل `unlocalize`. صفرُ قوالبٍ يعني أن المسار خطأ لا أن الشجرة
    #: نظيفة.
    total = len(list(TEMPLATES.rglob("*.html")))
    if total == 0:
        raise SystemExit(f"لا قالب واحد تحت {TEMPLATES} — المسار خطأ.")

    rows = offenders()
    if rows:
        print("مرشّحاتٌ بترتيبٍ يجعل الافتراضي لا يقع:\n")
        for path, number, line in rows:
            print(f"  {path.relative_to(ROOT)}:{number}")
            print(f"    {line}")
        print()
        print('`unlocalize` يحوّل None إلى السلسلة "None" فلا يقع `default` بعدها.')
        print("الصواب: `|default:\"—\"|unlocalize` — الافتراضي أولاً.")
        return 1

    print(f"ترتيب المرشّحات سليم — {total} قالباً فُحص.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
