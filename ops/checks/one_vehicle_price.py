#!/usr/bin/env python
"""Fail if a second "what does this car cost" number appears.

`reserve_price` is the only field that means the price a vehicle stands on
(spec 005 §4). In v1 four screens each computed their own — a starting price
here, an estimated value there — and customers were quoted different numbers
for the same car in the same hour. The fix was never "make them agree"; it was
"there is one field, and a screen that computes another is broken".

A text check is the right shape for this: the failure is a *new name* being
introduced, and a name is exactly what a grep-like check can see. It reads the
code as a syntax tree rather than as lines so that a comment mentioning
`start_price` in a story about v1 does not fail the build.

Allowed price names, and why each is not a second price:

* `reserve_price` — the one.
* `awarded_price` — what it actually sold for, a settlement result.
* `price` — the argument that carries the awarded price into the service.

Run:  python ops/checks/one_vehicle_price.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

ALLOWED_NAMES = {"reserve_price", "awarded_price", "price"}

#: Anything else whose name talks about a price.
PRICE_NAME = re.compile(r"price", re.IGNORECASE)

SKIP_PARTS = {"__pycache__", ".venv", "node_modules"}


def _touches_auctions(path: Path, tree: ast.AST) -> bool:
    if "auctions" in path.parts:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "apps.auctions"
        ):
            return True
    return False


class PriceNameHunter(ast.NodeVisitor):
    """Collects every identifier that talks about a price."""

    def __init__(self) -> None:
        self.hits: list[tuple[int, str]] = []

    def _check(self, name: str | None, lineno: int) -> None:
        if not name or name in ALLOWED_NAMES:
            return
        # A test named `test_an_award_needs_a_price` is describing the rule,
        # not adding a second price.
        if name.startswith("test_"):
            return
        if PRICE_NAME.search(name):
            self.hits.append((lineno, f"اسم يحمل سعراً ثانياً: {name}"))

    def visit_Name(self, node: ast.Name) -> None:
        self._check(node.id, node.lineno)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self._check(node.attr, node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check(node.name, node.lineno)
        for argument in [*node.args.args, *node.args.kwonlyargs]:
            self._check(argument.arg, node.lineno)
        self.generic_visit(node)

    def visit_keyword(self, node: ast.keyword) -> None:
        self._check(node.arg, node.value.lineno)
        self.generic_visit(node)


def violations(roots: list[Path]) -> list[str]:
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if not _touches_auctions(path, tree):
                continue
            hunter = PriceNameHunter()
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("سعر وقوف المركبة حقل واحد اسمه reserve_price (المعيار E4):\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. اقرأ reserve_price بدل حساب رقم ثانٍ.")
        return 1

    print("سعر المركبة يأتي من حقل واحد.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
