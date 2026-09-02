#!/usr/bin/env python
"""Fail if a float can reach a money path.

Article 3-2: currency is `Decimal(14,2)` and nothing else. This is a text
check rather than a type check because the failure it prevents is not a type
error — `0.1 + 0.2` is a perfectly valid float expression that produces
0.30000000000000004, and a report built from it is wrong by an amount too
small to notice and too persistent to explain.

Scope is `apps/money` and `apps/odoo`: the ledger and the boundary where
someone else's JSON becomes our numbers. `json.loads` turns `10000.50` into a
float without being asked, so the boundary matters as much as the core.

Run:  python ops/checks/no_float_in_money.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WATCHED = [ROOT / "backend" / "apps" / "money", ROOT / "backend" / "apps" / "odoo"]

# Migrations are generated and quote their own Decimals correctly; the check
# still reads them, but a bare number in a schema default is not a money path.
SKIP_PARTS = {"__pycache__", "migrations"}


class FloatHunter(ast.NodeVisitor):
    """Finds float literals and calls to `float()`."""

    def __init__(self, path: Path):
        self.path = path
        self.hits: list[tuple[int, str]] = []

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, float):
            self.hits.append((node.lineno, f"float literal {node.value!r}"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "float":
            self.hits.append((node.lineno, "call to float()"))
        self.generic_visit(node)


def main() -> int:
    failures: list[str] = []

    for root in WATCHED:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts):
                continue
            hunter = FloatHunter(path)
            hunter.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
            for line, what in hunter.hits:
                failures.append(f"{path.relative_to(ROOT)}:{line}: {what}")

    if failures:
        print("لا يجوز استعمال float في أي مسار مالي (المادة ٣-٢):\n")
        for failure in failures:
            print(f"  {failure}")
        print(f"\n{len(failures)} مخالفة. استعمل Decimal.")
        return 1

    print("لا float في المسارات المالية.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
