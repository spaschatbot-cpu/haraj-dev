#!/usr/bin/env python
"""Fail if anything but `apps/core/sheets.py` reads or writes a spreadsheet.

One reader, one writer (T410). In v1 each export opened `csv.writer` where it
stood, so quoting, encoding and the meaning of an empty cell differed between
screens, and a file produced by one could not be uploaded to another. The
duplication was never visible in review — every instance was three correct
lines.

Run:  python ops/checks/one_sheet_writer.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
SHEETS = BACKEND / "apps" / "core" / "sheets.py"

# `tests` is exempt: a test of the wrapper has to be able to forge a hostile
# workbook — a lot number stored as a double, a CSV without a BOM — and
# forging one is precisely what the wrapper exists to survive.
SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules", "tests"}

#: Modules only `sheets.py` may touch.
RESERVED_MODULES = {"csv", "openpyxl", "xlsxwriter", "xlrd", "xlwt", "pandas"}


class SheetToolHunter(ast.NodeVisitor):
    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in RESERVED_MODULES:
                self.hits.append((node.lineno, f"استيراد {alias.name}"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        root = (node.module or "").split(".")[0]
        if root in RESERVED_MODULES:
            self.hits.append((node.lineno, f"استيراد من {node.module}"))
        self.generic_visit(node)


def violations(roots: list[Path], allowed: set[Path] | None = None) -> list[str]:
    allowed = {SHEETS} if allowed is None else allowed
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts) or path in allowed:
                continue
            hunter = SheetToolHunter()
            hunter.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("الجداول تُقرأ وتُكتب من apps/core/sheets.py وحدها:\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. استعمل Sheet.")
        return 1

    print("قارئ وكاتب واحد للجداول.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
