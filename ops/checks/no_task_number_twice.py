#!/usr/bin/env python
"""Fail if one task number names two tasks.

`T822` was written twice in a single day — the analytics dashboard and the
capability-grant screen — because two people appended to opposite ends of the
same `tasks.md` and neither read what the other had added. No code broke. What
broke is a **reference**: somebody asking "what is T822?" finds two answers,
and a commit message, a spec row and an audit note that each mean a different
one.

The rule is per file, not global: phases number independently, and `T101` in
one phase has nothing to say about `T101` in another. What is forbidden is one
number appearing twice as a **heading** inside one phase's `tasks.md`.

Headings only, deliberately. A task's body cites other tasks constantly — "see
T803", "blocked on T901" — and a check that counted mentions would fire on
every cross-reference, which is exactly the noise that gets a check switched
off.

Run:  python ops/checks/no_task_number_twice.py
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"

#: عنوانُ تاسك: `###` ثم علامة حالة اختيارية ثم المعرّف.
HEADING = re.compile(r"^#{2,4}\s+(?:[^\w\s]\S*\s+)*((?:T|HR-)[0-9]+[أ-ي]?)\b")


def duplicates_in(path: Path) -> dict[str, list[int]]:
    seen: dict[str, list[int]] = defaultdict(list)
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = HEADING.match(line)
        if match:
            seen[match.group(1)].append(number)
    return {key: lines for key, lines in seen.items() if len(lines) > 1}


def main() -> int:
    files = sorted(SPECS.glob("*/tasks.md"))
    if not files:
        print("لم يُعثر على ملفّ تاسكات واحد — الفحص لا يجد ما يحرسه.", file=sys.stderr)
        return 1

    broken = False
    for path in files:
        found = duplicates_in(path)
        if found:
            broken = True
            rel = path.relative_to(ROOT).as_posix()
            for key, lines in sorted(found.items()):
                where = "، ".join(str(line) for line in lines)
                print(f"{rel}: «{key}» عنوانٌ لتاسكين — الأسطر {where}", file=sys.stderr)

    total = sum(
        1
        for path in files
        for line in path.read_text(encoding="utf-8").splitlines()
        if HEADING.match(line)
    )
    if total < 50:
        print(f"وُجد {total} عنوان تاسك فقط — الفحص لا يجد ما يحرسه.", file=sys.stderr)
        return 1

    if broken:
        print(
            "\nرقمٌ واحد لتاسكين مرجعٌ مكسور: من يسأل «ما هذا التاسك؟» يجد\n"
            "جوابين، ورسالةُ commit وصفٌّ في spec وقيدُ تدقيق يعني كلٌّ منها\n"
            "غير ما يعنيه الآخر. أعِد ترقيم الثاني بترتيب الملفّ.",
            file=sys.stderr,
        )
        return 1

    print(f"لا رقمَ تاسكٍ مكرَّر — {total} عنواناً في {len(files)} ملفّاً.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
