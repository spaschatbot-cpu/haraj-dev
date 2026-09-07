#!/usr/bin/env python
"""Fail if a console template writes a class name no stylesheet defines.

`class="stats"` was written on three screens and **nothing styled it**. The
pages rendered — a class with no rule is not an error anywhere in the stack —
so every check stayed green while the cards stacked one per row down the whole
page instead of sitting in a grid. The real class was `board-stats`, four
characters away, already in `app.css`.

That is the shape of the defect this guards: not a crash, not a wrong number,
but a name that looks right and does nothing. Nobody notices until somebody
opens the page and it merely looks *odd* — and "odd" is what a reviewer
attributes to taste rather than to a bug.

Scope: `backend/templates/console/**.html` against
`backend/apps/console/static/console/app.css`. The login skin lives outside the
console and carries its own inline styles, so it is not scanned.

Run:  python ops/checks/every_class_is_styled.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates" / "console"
STYLESHEET = ROOT / "backend" / "apps" / "console" / "static" / "console" / "app.css"

#: `class="…"` بقيمةٍ ثابتة. وما فيه `{{` أو `{%` يُتخطّى: القيمةُ تُبنى وقت
#: العرض، فاسمُ الصنف ليس في النصّ أصلاً ولا يُفحص هنا.
CLASS_ATTRIBUTE = re.compile(r'class="([^"{}]*)"')

#: أسماءُ الأصناف كما تُعرَّف في CSS: `.name` في أي موضعٍ من المُحدِّد.
CSS_CLASS = re.compile(r"\.(-?[_a-zA-Z][\w-]*)")

#: أصنافٌ لا يصفها `app.css` بحقّ، ولكلٍّ سببُه.
ALLOWED = {
    # يقرؤها `theme.js` بـ`querySelector`، ولا شكلَ لها.
    "themer__reset",
    # صنفُ جانغو الافتراضيّ على أخطاء الاستمارة (`{{ form.as_p }}`).
    "errorlist",
    "helptext",
}


def declared() -> set[str]:
    return set(CSS_CLASS.findall(STYLESHEET.read_text(encoding="utf-8")))


def violations() -> list[str]:
    known = declared() | ALLOWED
    found: list[str] = []

    for path in sorted(TEMPLATES.rglob("*.html")):
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for attribute in CLASS_ATTRIBUTE.findall(line):
                for name in attribute.split():
                    if name and name not in known:
                        found.append(f"{path}:{number}: صنفٌ لا يصفه أحد: «{name}»")
    return found


def main() -> int:
    if not STYLESHEET.exists():
        print(f"لم تُوجد ورقة الأنماط: {STYLESHEET}", file=sys.stderr)
        return 1

    pages = list(TEMPLATES.rglob("*.html"))
    if not pages:
        print("لم يُعثر على قالبٍ واحد — الفحص لا يجد ما يحرسه.", file=sys.stderr)
        return 1

    broken = violations()
    if broken:
        print("صنفٌ مكتوبٌ في قالبٍ ولا قاعدةَ تصفه:\n", file=sys.stderr)
        for line in broken:
            print("  " + line, file=sys.stderr)
        print(
            f"\n{len(broken)} مخالفة. الصنفُ الذي لا يصفه أحد لا يكسر شيئاً — "
            "ولذلك يبقى: الصفحة تُرسم، وكلُّ فحصٍ أخضر، والشكلُ وحده خطأ.",
            file=sys.stderr,
        )
        return 1

    print(f"كل صنفٍ مكتوبٍ له قاعدة — {len(pages)} قالباً.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
