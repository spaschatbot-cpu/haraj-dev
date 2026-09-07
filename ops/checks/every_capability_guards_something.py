#!/usr/bin/env python
"""Fail if a capability is granted to somebody but guards nothing.

The rule (T816 §ب، وجرد التكافؤ): every value of `Capability` must be reachable
— named by a row in `console.navigation.PAGES`, or asked for by `can()` /
`require()` somewhere that is not a test.

**Why this is a defect and not tidiness.** `ROLE_CAPABILITIES` is written out
in full, on purpose: its own comment says a capability the owner should not
have must be "a deliberate omission rather than an accident of wildcard". That
makes the list a thing a person *reads to learn what a role may do*. A row in
it that guards nothing is therefore not dead code — it is a **false sentence in
the security model**. Somebody auditing "who can manage invoices?" reads
`invoices.manage` under FINANCE and concludes there is a controlled path. There
is none: no page, no `require`, no screen. The list said yes and the system has
no door at all.

And the shape recurs. A capability is written the day a screen is *planned*,
the screen slips, and the grant stays — pointing at nothing, and looking from
the outside exactly like a grant that works.

The opposite failure is worth naming too: a **page** whose capability nobody
grants is unreachable by every role, which `navigation` already prevents by
raising at import on an unknown page name. This check is the other direction.

Run:  python ops/checks/every_capability_guards_something.py
"""

from __future__ import annotations

import ast
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
APPS = ROOT / "backend" / "apps"
PERMISSIONS = APPS / "core" / "permissions.py"


def _members(class_name: str) -> list[str]:
    tree = ast.parse(PERMISSIONS.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            names = []
            for item in node.body:
                if isinstance(item, ast.Assign) and isinstance(item.targets[0], ast.Name):
                    names.append(item.targets[0].id)
            return names
    raise SystemExit(f"لم يُعثر على تعداد {class_name} — الملفّ تغيّر")


def used_anywhere(name: str) -> list[str]:
    """أين تُذكر القدرة خارج تعريفها وخارج الاختبارات.

    الاختبارات مستثناة عمداً: اختبارٌ يذكر قدرةً لا يجعلها تحرس شيئاً — بل
    يجعلها تبدو مستعملةً وهي ليست كذلك، وذلك بالضبط ما يُخفي هذا العطل.
    """
    pattern = re.compile(rf"\bCapability\.{name}\b")
    hits = []
    for path in sorted(APPS.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if "/migrations/" in rel or "/tests/" in rel or path.name.startswith("test_"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = len(pattern.findall(text))
        if path == PERMISSIONS:
            count -= 1  # سطر التعريف نفسه
        if count > 0:
            hits.append(rel)
    return hits


def main() -> int:
    names = _members("Capability")
    if len(names) < 8:
        print(f"وُجدت {len(names)} قدرة فقط — الفحص لا يجد ما يحرسه.", file=sys.stderr)
        return 1

    orphans = [name for name in names if not used_anywhere(name)]
    if orphans:
        print("قدراتٌ ممنوحةٌ لا تحرس شيئاً:", file=sys.stderr)
        for name in orphans:
            print(f"  • Capability.{name}", file=sys.stderr)
        print(
            "\nالقدرة التي لا تسمّيها صفحةٌ في `navigation.PAGES` ولا يطلبها\n"
            "`require()` هي جملةٌ كاذبة في نموذج الصلاحيات: من يقرأ\n"
            "`ROLE_CAPABILITIES` يظنّ أن للدور طريقاً محكوماً، ولا باب أصلاً.\n"
            "احذفها حتى تُبنى شاشتها، أو اربطها بصفحتها الآن.",
            file=sys.stderr,
        )
        return 1

    print(f"كل القدرات الـ{len(names)} تحرس شيئاً.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
