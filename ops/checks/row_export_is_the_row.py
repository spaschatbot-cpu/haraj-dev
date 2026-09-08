"""زرُّ التصدير على صفٍّ يُصدِّر ذلك الصفَّ لا الصفحة. T858.

العطل الذي وُجد لأجله
=====================
`export_url` هو **الطلبُ الحاليّ** بمعامل `export=xlsx` مضافاً إليه — يبنيه
`apps/console/context.py` من `request.get_full_path()`. وهذا صحيحٌ تماماً في
زرّ الشريط أعلى الشاشة: «صدِّر ما أراه الآن بفلاتره».

وكان مكتوباً أيضاً في عمود التحكم على **كلّ صفّ** في شاشة المزادات. فزرُّ
التصدير في صفّ المزاد ٥٤ وزرُّ المزاد ٥٣ وزرُّ الشريط كانوا يُنزّلون الملفَّ
نفسه: أربعةً وخمسين مزاداً في ثمانية كيلوبايت — لا سيّاراتِ المزاد المنقور
(ستّةً وثلاثين كيلوبايت، وثلاثمئةٍ وسبعاً وخمسين سيّارة).

**وهو عطلٌ صامت**: الملفُّ ينزل، والمتصفّح يقول «تمّ»، ولا شيء يقول إنه الملفّ
الخطأ. من يفتحه بعد يومين يظنّ المزاد فارغاً.

القاعدة
=======
داخل `<tbody>` — أي على صفٍّ — لا يُكتب `export_url`. المقصدُ هناك دائماً
«صدِّر هذا الصفّ»، وعنوانُه يُبنى من مفتاح الصفّ:
`{% url 'console:auction-detail' auction.pk %}?export=xlsx`.

وخارج `<tbody>` — شريطُ الأدوات ورأسُ الجدول — `export_url` هو الصواب،
فلا يُمَسّ.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates" / "console"

_OPEN = re.compile(r"<tbody\b", re.I)
_CLOSE = re.compile(r"</tbody\s*>", re.I)
_USE = re.compile(r"\bexport_url\b")

#: تعليقُ جانغو يُشرح فيه العطلُ باسمه — والشرحُ ليس استعمالاً. ولولا هذا
#: لأرسب الفحصُ التعليقَ الذي يشرح سببَ وجوده، وهو ما حدث أوّلَ تشغيل.
_COMMENT_OPEN = re.compile(r"{%-?\s*comment\s*-?%}")
_COMMENT_CLOSE = re.compile(r"{%-?\s*endcomment\s*-?%}")


def offenders() -> list[str]:
    found: list[str] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        depth = 0
        noted = 0
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            was_noted = noted > 0
            noted += len(_COMMENT_OPEN.findall(line)) - len(_COMMENT_CLOSE.findall(line))
            if was_noted or noted > 0:
                continue
            # يُفتح ويُغلق على السطر نفسه أحياناً؛ يُحسب الفارق لا الوجود.
            before = depth
            depth += len(_OPEN.findall(line)) - len(_CLOSE.findall(line))
            inside = before > 0 or (depth > 0 and before == 0 and _OPEN.search(line))
            if inside and _USE.search(line):
                where = path.relative_to(ROOT).as_posix()
                found.append(f"{where}:{number}: {line.strip()[:100]}")
    return found


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"لا مجلّد قوالبَ في {TEMPLATES} — الفحص لا يجد ما يحرسه.")
        return 1

    guarded = sum(
        1
        for path in TEMPLATES.rglob("*.html")
        if _USE.search(path.read_text(encoding="utf-8"))
    )
    if guarded == 0:
        print("لا قالبَ يستعمل `export_url` — الفحص لا يجد ما يحرسه.")
        return 1

    bad = offenders()
    if bad:
        print("زرُّ تصديرٍ على صفٍّ يُصدِّر الصفحة كلّها لا ذلك الصفّ:\n")
        for line in bad:
            print(f"  {line}")
        print(
            "\nعلى الصفّ يُبنى العنوان من مفتاحه:\n"
            "  {% url 'console:auction-detail' auction.pk %}?export=xlsx"
        )
        return 1

    print(f"لا `export_url` داخل صفّ — {guarded} قالباً يستعمله في شريطه.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
