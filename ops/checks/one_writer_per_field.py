"""على الشاشة الواحدة، لكلّ حقلٍ نافذةٌ واحدة تكتبه. T859.

العطل الذي وُجد لأجله
=====================
شاشةُ المزادات تحمل ستَّ نوافذَ منبثقة، وكانت ثلاثٌ منها تُرسل `starts_at`
و`ends_at`، واثنتان تُرسلان `deposit_required`.

وليست نسخاً متطابقة — وهنا الأذى: «إعادة الجدولة» تتحقّق من النافذة الزمنية
**وتمسح مزايدات المركبات التي لم تُبَع** إن طُلب؛ و«التعديل» كانت تكتب
التاريخين نفسيهما بلا شيء من ذلك. فموظّفان يغيّران الموعد نفسه من نافذتين
يحصلان على أثرين مختلفين، **ولا شيء على الشاشة يقول ذلك**.

قال المالك: «التاسكات بتاعتهم متلغبطة، بحاول أحذف بيدخّلني على تعديل». وهو
لغطٌ في الملكيّة لا في الأزرار.

القاعدة
=======
داخل قالبٍ واحد، لا يظهر اسمُ حقلٍ في نافذتين. والمشتركُ المسموح مسمّىً
صراحةً أدناه: رمزُ CSRF، ووِجهةُ العودة، وسببُ التغيير، وختمُ HR-13 —
أربعةٌ ليست حقولَ بيانات بل لوازمُ كلِّ نموذج.

ولو أراد أحدٌ حقلاً في نافذتين حقّاً، فالجواب أن **يُوحَّد الكاتب** لا أن
يُوسَّع هذا الاستثناء.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates" / "console"

#: لوازمُ كلِّ نموذجٍ لا بياناتُه. تتكرّر بالضرورة، ولا تُكتب في المزاد.
SHARED = frozenset({"csrfmiddlewaretoken", "back", "reason", "row_stamp"})

_DIALOG_OPEN = re.compile(r"<dialog\b[^>]*\bid=\"([^\"]+)\"", re.I)
_DIALOG_CLOSE = re.compile(r"</dialog\s*>", re.I)
_NAME = re.compile(r'\bname="([A-Za-z_][A-Za-z0-9_]*)"')
_COMMENT_OPEN = re.compile(r"{%-?\s*comment\s*-?%}")
_COMMENT_CLOSE = re.compile(r"{%-?\s*endcomment\s*-?%}")


def writers_in(path: Path) -> dict[str, list[str]]:
    """أيُّ نافذةٍ تكتب أيَّ حقل، في قالبٍ واحد."""
    owners: dict[str, list[str]] = defaultdict(list)
    current: str | None = None
    noted = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        was_noted = noted > 0
        noted += len(_COMMENT_OPEN.findall(line)) - len(_COMMENT_CLOSE.findall(line))
        if was_noted or noted > 0:
            continue

        found = _DIALOG_OPEN.search(line)
        if found:
            current = found.group(1)
        if current:
            for name in _NAME.findall(line):
                if name not in SHARED and current not in owners[name]:
                    owners[name].append(current)
        if _DIALOG_CLOSE.search(line):
            current = None
    return owners


def main() -> int:
    if not TEMPLATES.is_dir():
        print(f"لا مجلّد قوالبَ في {TEMPLATES} — الفحص لا يجد ما يحرسه.")
        return 1

    seen_dialogs = 0
    bad: list[str] = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        count = len(_DIALOG_OPEN.findall(text))
        if count < 2:
            continue
        seen_dialogs += count
        where = path.relative_to(ROOT).as_posix()
        for name, dialogs in sorted(writers_in(path).items()):
            if len(dialogs) > 1:
                bad.append(f"{where}: `{name}` تكتبه {len(dialogs)} نوافذ — " + " · ".join(dialogs))

    if seen_dialogs == 0:
        print("لا قالبَ فيه نافذتان — الفحص لا يجد ما يحرسه.")
        return 1

    if bad:
        print("حقلٌ له أكثر من كاتبٍ على الشاشة الواحدة:\n")
        for line in bad:
            print(f"  {line}")
        print(
            "\nالجواب توحيدُ الكاتب: تُترك النافذة التي تملك الحقل بقواعده،\n"
            "وتُحذف نسخته من الأخرى — لا توسيعُ استثناء `SHARED` في هذا الفحص."
        )
        return 1

    print(f"لكلّ حقلٍ نافذةٌ واحدة — فُحصت {seen_dialogs} نافذة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
