"""كل زوج لون/خلفية في اللوحة يبلغ حدّ WCAG المطلوب له.

لماذا فحصٌ لا مراجعةٌ بالعين
============================
لأن العين لا تقيس. صُمّمت اللوحة (T819) بلوحة ألوان تبدو هادئة ومقروءة، وكان
فيها **زرّ تسجيل الدخول نفسه** راسباً: أبيض على ``#3d9bd6`` نسبته ٣٫٠٦ والحدّ
٤٫٥. ومعه ثلاثة أخرى، أخبثها أن الرابط كان **يفتحّ** عند مرور المؤشر — فإشارة
«هذا قابل للنقر» كانت تجعله أصعب قراءةً، وهو عكس ما أُريد بها بالضبط.

ولا شيء من ذلك يظهر في لقطة شاشة، ولا يقوله مراجعٌ ينظر إلى صفحةٍ على شاشةٍ
جيدة في غرفةٍ مضاءة. يظهر في رقم، فهذا الملف يحسب الرقم.

حدّان لا حدّ واحد
=================
* **٤٫٥** للنصّ العادي (WCAG 2.2 AA، معيار 1.4.3). كل ما في اللوحة نصٌّ عادي:
  أصغر مقاس فيها ``.72rem`` وأكبر عنوان ``1.45rem`` — ولا شيء يبلغ حدّ «النصّ
  الكبير» (18.66px غليظاً أو 24px عادياً)، فلا استثناء يُطلب هنا.
* **٣٫٠** لمكوّنات الواجهة وحدودها (معيار 1.4.11): إطار التركيز، وحدّ الحقل.

لماذا الأزواج مكتوبة بيدٍ هنا
=============================
لأن السؤال ليس «ما الألوان الموجودة» بل «ما الذي يُرسَم فوق ماذا» — وذلك لا
يُستخرج من ورقة أنماط بلا متصفّح يحسب التتالي. فكل زوجٍ هنا موضعٌ حقيقي في
``app.css``، ومعه اسمه بالعربية ليقول تقريرُ الفشل أين ينظر القارئ.

وحين يُضاف زوجٌ جديد إلى الورقة يجب أن يُضاف هنا. هذه هي كلفة الطريقة، وهي
أرخص من كلفة زرٍّ لا يُقرأ.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "backend" / "apps" / "console" / "static" / "console" / "app.css"

#: النصّ العادي، ومكوّنات الواجهة. لا ثالث لهما في هذه اللوحة.
TEXT = 4.5
UI = 3.0


def tokens() -> dict[str, str]:
    """قيم `--*` من كتلة `:root`، فلا يُكرَّر لونٌ في مكانين ثم يختلفان."""
    text = SHEET.read_text(encoding="utf-8")
    root = re.search(r":root\s*\{(.*?)\n\}", text, re.DOTALL)
    if root is None:
        raise SystemExit(
            "لا كتلة :root في app.css — إن أُعيدت بنيتها فحدّث هذا الفحص. "
            "حارسٌ لا يجد ما يحرسه يجب أن يصرخ لا أن يمرّ."
        )
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", root.group(1)))


def _relative_luminance(colour: str) -> float:
    raw = [int(colour.lstrip("#")[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in raw]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    a, b = _relative_luminance(foreground), _relative_luminance(background)
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def main() -> int:
    t = tokens()
    white = "#ffffff"

    # (الوصف, المقدمة, الخلفية, الحدّ)
    pairs = [
        ("النصّ الأساسي على الأرضية", t["ink"], t["ground"], TEXT),
        ("النصّ الأساسي على البطاقة", t["ink"], t["panel"], TEXT),
        ("النصّ الثانوي على البطاقة", t["muted"], t["panel"], TEXT),
        ("النصّ الثانوي على الأرضية", t["muted"], t["ground"], TEXT),
        ("رأس الجدول", t["muted"], "#f1f6f4", TEXT),
        ("شارة البيئة (غير الإنتاج)", t["muted"], "#eef2f1", TEXT),
        ("شارة التطوير", t["info"], t["info-soft"], TEXT),
        ("شارة الإنتاج", white, t["danger"], TEXT),
        ("وصف الشريط الجانبي", t["side-dim"], t["side"], TEXT),
        ("اسم اللوحة في الشريط", t["brand-dark"], t["side"], TEXT),
        ("زرّ الإرسال", white, t["brand-solid"], TEXT),
        ("زرّ الإرسال عند المرور", white, t["brand-dark"], TEXT),
        ("القسم الحالي في القائمة", white, t["brand-solid"], TEXT),
        ("رابط القائمة عند المرور", t["ink"], t["brand-soft"], TEXT),
        ("رابط في المحتوى", t["brand-dark"], t["panel"], TEXT),
        ("رابط في المحتوى عند المرور", t["ink"], t["panel"], TEXT),
        ("إطار التركيز على البطاقة", t["brand-solid"], t["panel"], UI),
        ("إطار التركيز على الأرضية", t["brand-solid"], t["ground"], UI),
        ("حدّ الحقل", t["field-border"], t["panel"], UI),
    ]

    failures = []
    for name, fg, bg, floor in pairs:
        got = contrast(fg, bg)
        if got < floor:
            failures.append((name, fg, bg, got, floor))

    if failures:
        print("ألوان لا تُقرأ في لوحة الإدارة:\n")
        for name, fg, bg, got, floor in failures:
            print(f"  {name}")
            print(f"    {fg} على {bg} — النسبة {got:.2f} والحدّ {floor}")
        print()
        print("الحدّ ٤٫٥ للنصّ و٣ لمكوّنات الواجهة (WCAG 2.2 AA).")
        print("لا تُخفَّض الأرقام هنا؛ يُغمَّق اللون في app.css.")
        return 1

    print(f"ألوان اللوحة مقروءة — {len(pairs)} زوجاً فُحصت.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
