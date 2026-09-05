"""Generate a synthetic seed for the v1 schema. Three rows per table, no real data.

Reads `specs/004-data-migration/v1-schema.sql` — **the structure file, never the
production dump.** Nothing here is copied from real data: every name, phone,
identity number and amount is invented, and invented to *look* invented. A
fixture a reader might mistake for real data is a fixture somebody eventually
treats as real.

Deterministic on purpose. The same schema always produces the same file, so
`git diff` after a re-run shows what the *schema* changed and nothing else —
and a developer can regenerate rather than hand-edit, which is what keeps
`ops/checks/v1_fixture_matches_its_schema.py` green.

Values are shaped by the column's name as well as its type, so a join works and
a human reading a row can tell what they are looking at. Columns inside a
UNIQUE key are forced to vary across the three rows: three identical rows there
would be one row and two errors.

Run from the repository root:  python ops/fixtures/make_v1_seed.py
"""

from __future__ import annotations

import io
import re

SCHEMA = "specs/004-data-migration/v1-schema.sql"
OUT = "specs/004-data-migration/v1-seed.sql"
ROWS = 3

CREATE = re.compile(r"^CREATE TABLE `([^`]+)` \($")
COLUMN = re.compile(r"^\s+`([^`]+)` (\w+)(\([^)]*\))?(.*)$")
FK = re.compile(r"FOREIGN KEY \(`([^`]+)`\) REFERENCES `([^`]+)` \(`([^`]+)`\)")
UNIQUE = re.compile(r"^UNIQUE KEY `[^`]+` \(([^)]*)\)")

RESERVED = {
    "select", "insert", "update", "delete", "from", "where", "table", "key",
    "primary", "unique", "constraint", "fulltext", "spatial", "index",
}


def parse(text: str) -> dict:
    tables: dict[str, dict] = {}
    current = None
    for line in text.split("\n"):
        created = CREATE.match(line)
        if created:
            current = created.group(1)
            tables[current] = {"columns": [], "fks": {}, "pk": None, "unique": set()}
            continue
        if current is None:
            continue
        if line.startswith(")"):
            current = None
            continue
        stripped = line.strip()
        unique = UNIQUE.match(stripped)
        if unique:
            tables[current]["unique"].update(re.findall(r"`([^`]+)`", unique.group(1)))
            continue
        fk = FK.search(stripped)
        if fk:
            tables[current]["fks"][fk.group(1)] = fk.group(2)
            continue
        if stripped.split(" ")[0].strip("`").lower() in RESERVED:
            if stripped.upper().startswith("PRIMARY KEY"):
                inside = re.search(r"\(`([^`]+)`", stripped)
                if inside:
                    tables[current]["pk"] = inside.group(1)
            continue
        column = COLUMN.match(line)
        if column:
            name, kind, size, rest = column.groups()
            tables[current]["columns"].append(
                {
                    "name": name,
                    "type": kind.lower(),
                    "size": (size or "").strip("()"),
                    "nullable": "NOT NULL" not in rest,
                    "auto": "AUTO_INCREMENT" in rest,
                    "generated": " GENERATED " in rest.upper(),
                    "rest": rest,
                }
            )
    return tables


def enum_first(rest: str, size: str) -> str:
    values = re.findall(r"'([^']*)'", size)
    return values[0] if values else "test"


def quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def value_for(column: dict, table: str, n: int, fks: dict, unique=frozenset()) -> str:
    name = column["name"]
    lower = name.lower()
    kind = column["type"]

    if name in fks:
        return str(n)  # points at row n of the parent

    if kind in ("int", "bigint", "smallint", "mediumint", "tinyint"):
        if kind == "tinyint" and column["size"] == "1":
            return str(n % 2) if name in unique else "0"
        if lower in ("id",) or column["auto"]:
            return str(n)
        if lower.endswith("_id") or lower.endswith("id"):
            return str(n)
        return str(n)

    if kind in ("decimal", "float", "double", "numeric"):
        scale = 2
        if "," in column["size"]:
            scale = int(column["size"].split(",")[1])
        return f"{n * 1000}.{'0' * scale}"[: 60] if scale else str(n * 1000)

    if kind == "enum":
        values = re.findall(r"'([^']*)'", column["size"]) or ["test"]
        # Cycling matters only inside a UNIQUE key, where three identical rows
        # would be one row and two errors.
        return quote(values[(n - 1) % len(values)] if name in unique else values[0])

    if kind in ("date",):
        return quote(f"2026-01-0{n}")
    if kind in ("datetime", "timestamp"):
        return quote(f"2026-01-0{n} 09:00:00")
    if kind in ("time",):
        return quote("09:00:00")
    if kind in ("year",):
        return "2026"
    if kind in ("blob", "longblob", "mediumblob", "tinyblob", "binary", "varbinary"):
        return "NULL" if column["nullable"] else "''"
    if kind == "json":
        return quote("{}")

    # Text-ish. The name decides the shape, so a developer's join and a
    # developer's eye both work.
    limit = int(column["size"]) if column["size"].isdigit() else 255
    if "image" in lower or "photo" in lower or "url" in lower or "path" in lower:
        text = f"fixtures/{table}/{n}.jpg"
    elif "phone" in lower or "mobile" in lower or "jawal" in lower:
        text = f"96650000000{n}"
    elif "email" in lower:
        text = f"test{n}@example.invalid"
    elif "iban" in lower:
        text = f"SA000000000000000000{n:04d}"
    elif "identity_number" in lower or "national" in lower:
        text = f"100000000{n}"
    elif "vat" in lower:
        text = f"30000000000000{n}"
    elif "cr_number" in lower or "commercial" in lower:
        text = f"101000000{n}"
    elif "password" in lower or "token" in lower or "secret" in lower or "code" in lower:
        # Never a real-looking credential, and never one that could be tried.
        # A short column would truncate the warning into something that reads
        # like a real value, so a narrow one gets digits instead.
        text = f"NOT-A-REAL-SECRET-{n}" if limit >= 20 else str(n) * min(limit, 4)
    elif "arabic_name" in lower or "name" in lower or "title" in lower:
        text = f"تجريبي {n} — {table}"
    elif "note" in lower or "memo" in lower or "reason" in lower or "message" in lower:
        text = f"بيانات اختبار مُصطنَعة ({table})"
    elif "status" in lower or "state" in lower or "type" in lower:
        text = f"test-{n}" if name in unique else "test"
    else:
        text = f"{table}-{name}-{n}"
    return quote(text[:limit])


def order(tables: dict) -> list[str]:
    """Parents before children, so a plain `mysql <` load works."""
    done: list[str] = []
    seen: set[str] = set()

    def visit(name: str, stack: set[str]) -> None:
        if name in seen or name in stack or name not in tables:
            return
        stack.add(name)
        for parent in set(tables[name]["fks"].values()):
            visit(parent, stack)
        stack.discard(name)
        seen.add(name)
        done.append(name)

    for name in sorted(tables):
        visit(name, set())
    return done


def main() -> None:
    text = io.open(SCHEMA, encoding="utf-8").read()
    tables = parse(text)

    out = [
        "-- بيانات اختبار مُصطنَعة لبنية v1 — ثلاثة صفوف في كل جدول.",
        "--",
        "-- **لا صفَّ حقيقياً واحداً هنا.** كل اسمٍ ورقمِ جوالٍ ورقمِ هويّةٍ ومبلغ",
        "-- مُختلَق، ومُختلَقٌ ليبدو مُختلقاً: تجهيزةٌ يظنّها قارئٌ بياناتٍ حقيقية",
        "-- تجهيزةٌ يعاملها أحدهم يوماً على أنها كذلك. ونسخةُ الإنتاج نفسها لا",
        "-- تدخل المستودع (المادة 5-3، وانظر رأس `v1-schema.sql`).",
        "--",
        "-- مولَّدٌ حتمياً من `v1-schema.sql`: البنية نفسها تعطي الملفّ نفسه، فما",
        "-- يظهر في `git diff` هو ما تغيّر في البنية لا ترتيبٌ عشوائي.",
        "--",
        "-- المعرّفات 1 و2 و3 في كل جدول، وكل مفتاح أجنبي يشير إلى الصفّ المقابل",
        "-- في أبيه — فالربط يعمل، والجداول مرتَّبة آباءً قبل أبناء ليمرّ التحميل",
        "-- بأمر واحد:",
        "--",
        "--     mysql -u <user> hara_clone_v1_test < v1-schema.sql",
        "--     mysql -u <user> hara_clone_v1_test < v1-seed.sql",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS=0;",
        "",
    ]

    for name in order(tables):
        table = tables[name]
        columns = [c for c in table["columns"] if not c["generated"]]
        if not columns:
            out.append(f"-- `{name}`: لا عمود يُكتب فيه.\n")
            continue
        names = ", ".join(f"`{c['name']}`" for c in columns)
        rows = []
        for n in range(1, ROWS + 1):
            values = ", ".join(
                value_for(c, name, n, table["fks"], table["unique"]) for c in columns
            )
            rows.append(f"({values})")
        out.append(f"INSERT INTO `{name}` ({names}) VALUES")
        out.append(",\n".join(rows) + ";")
        out.append("")

    out.append("SET FOREIGN_KEY_CHECKS=1;")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    print(f"{OUT}: {len(tables)} جدولاً × {ROWS} صفوف")


if __name__ == "__main__":
    main()
