#!/usr/bin/env python
"""Fail if the v1 test fixture disagrees with the v1 schema it is seeded from.

`specs/004-data-migration/v1-seed.sql` exists so a developer can build an
extractor, a field map and the migration builders without the production dump
on their disk. That only works while the fixture is loadable, and there is no
MySQL on the machine this was written on — so what cannot be proven by running
it is proven by reading it:

* every INSERT names a table the schema declares, and only columns it declares;
* the value count matches the column count on every row;
* no string is longer than its column;
* every enum value is one the column allows;
* **no INSERT touches a table that has no CREATE TABLE**, which is how a
  fixture quietly seeds a table that was renamed.

And the rule the whole fixture exists for, checked here because a comment
cannot enforce it:

* **the schema file carries no data** — zero INSERT statements. It is a dump of
  structure, and a dump of structure that grew rows is the production database
  entering the repository by the back door (Article 5-3).

What this does **not** prove is that MySQL accepts the file. That needs a
server, and it is written as an open item in `tasks.md` rather than implied by
a green check here.

Run:  python ops/checks/v1_fixture_matches_its_schema.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "specs" / "004-data-migration" / "v1-schema.sql"
SEED = ROOT / "specs" / "004-data-migration" / "v1-seed.sql"

CREATE = re.compile(r"^CREATE TABLE `([^`]+)` \($")
COLUMN = re.compile(r"^\s+`([^`]+)` (\w+)(\(([^)]*)\))?")
INSERT = re.compile(r"^INSERT INTO `([^`]+)` \(([^)]*)\) VALUES$")

STRUCTURAL = ("PRIMARY", "KEY", "UNIQUE", "CONSTRAINT", "FULLTEXT", "SPATIAL", "INDEX")


def read_schema() -> dict[str, dict[str, dict]]:
    tables: dict[str, dict[str, dict]] = {}
    current = None
    for line in SCHEMA.read_text(encoding="utf-8").split("\n"):
        created = CREATE.match(line)
        if created:
            current = created.group(1)
            tables[current] = {}
            continue
        if current is None:
            continue
        if line.startswith(")"):
            current = None
            continue
        if line.strip().upper().startswith(STRUCTURAL):
            continue
        column = COLUMN.match(line)
        if column:
            name, kind, _, size = column.groups()
            tables[current][name] = {
                "type": kind.lower(),
                "limit": int(size) if size and size.isdigit() else None,
                "enum": re.findall(r"'([^']*)'", size or "") if kind.lower() == "enum" else [],
            }
    return tables


def split_values(row: str) -> list[str]:
    """The top-level values of one `(...)` tuple, respecting quotes."""
    values: list[str] = []
    current: list[str] = []
    in_string = False
    escaped = False
    for ch in row:
        if in_string:
            current.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_string = False
            continue
        if ch == "'":
            in_string = True
            current.append(ch)
        elif ch == ",":
            values.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    values.append("".join(current).strip())
    return values


def violations() -> list[str]:
    found: list[str] = []
    schema_text = SCHEMA.read_text(encoding="utf-8")
    if "INSERT INTO" in schema_text:
        found.append(
            f"{SCHEMA.name}: فيه `INSERT` — وهو ملفّ بنية. صفوفٌ فيه تعني أن"
            " قاعدة الإنتاج تدخل المستودع من الباب الخلفي (المادة ٥-٣)"
        )

    tables = read_schema()
    if len(tables) < 100:
        found.append(
            f"{SCHEMA.name}: قُرئ منه {len(tables)} جدولاً فقط — فحصٌ لا يجد ما"
            " يحرسه يصرخ ولا يمرّ"
        )

    lines = SEED.read_text(encoding="utf-8").split("\n")
    seeded: set[str] = set()
    index = 0
    while index < len(lines):
        inserted = INSERT.match(lines[index])
        if not inserted:
            index += 1
            continue
        table, raw = inserted.group(1), inserted.group(2)
        columns = re.findall(r"`([^`]+)`", raw)
        seeded.add(table)
        if table not in tables:
            found.append(f"`{table}`: يُبذَر ولا `CREATE TABLE` له")
            index += 1
            continue
        unknown = [c for c in columns if c not in tables[table]]
        if unknown:
            found.append(f"`{table}`: أعمدة لا وجود لها — {'، '.join(unknown)}")

        index += 1
        row_number = 0
        while index < len(lines) and lines[index].startswith("("):
            row_number += 1
            row = lines[index].rstrip(",;")
            values = split_values(row[1:-1])
            if len(values) != len(columns):
                found.append(
                    f"`{table}` الصف {row_number}: {len(values)} قيمة مقابل"
                    f" {len(columns)} عموداً"
                )
            else:
                for column, value in zip(columns, values, strict=True):
                    spec = tables[table].get(column)
                    if spec is None or not value.startswith("'"):
                        continue
                    literal = value[1:-1].replace("\\'", "'").replace("\\\\", "\\")
                    if spec["limit"] and len(literal) > spec["limit"]:
                        found.append(
                            f"`{table}`.`{column}`: {len(literal)} حرفاً في عمود"
                            f" {spec['limit']}"
                        )
                    if spec["enum"] and literal not in spec["enum"]:
                        found.append(
                            f"`{table}`.`{column}`: {literal!r} ليست من"
                            f" {spec['enum']}"
                        )
            index += 1

    missing = sorted(set(tables) - seeded)
    if missing:
        found.append(
            f"{len(missing)} جدولاً بلا بذرة — ومطلبُ التجهيزة صفوفٌ في **كل**"
            f" جدول: {'، '.join(missing[:8])}{' …' if len(missing) > 8 else ''}"
        )
    return found


if __name__ == "__main__":
    problems = violations()
    if problems:
        print("تجهيزة اختبار v1 لا تطابق بنيتها:\n", file=sys.stderr)
        for problem in problems[:40]:
            print(f"  {problem}", file=sys.stderr)
        if len(problems) > 40:
            print(f"  … و{len(problems) - 40} غيرها", file=sys.stderr)
        print(
            f"\n{len(problems)} مخالفة. التجهيزة تُولَّد من البنية، فإن اختلفت"
            " عنها فإما البنية تغيّرت ولم يُعَد التوليد، أو أُضيف صفٌّ بيد.",
            file=sys.stderr,
        )
        sys.exit(1)
    print("تجهيزة اختبار v1 مطابقة لبنيتها، وملفّ البنية بلا صفوف.")
