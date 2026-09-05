#!/usr/bin/env python
"""Fail if anything but `apps/auctions/services.py` writes an auction state.

The rule (spec 005 §1): one place moves an auction or a vehicle between
states. The check exists because the rule is unenforceable by reading — v1 had
six paths that could end an auction, each written by someone who had every
intention of using the shared one, and the drift between them is what let a
car be awarded twice.

Scope: any module inside `apps/auctions`, plus any module anywhere in the
backend that imports from `apps.auctions`. A module that never touches these
models cannot break this rule, and scanning it would only produce false
positives on other apps' own `state` columns (`Hold.state`, `Invoice.state`).

What counts as a write:

* `something.state = ...`
* `.update(state=...)` on a queryset

Inside `apps/auctions` every such write counts. Outside it — a money test that
imports an auction fixture and then sets `invoice.state` — only writes whose
subject reads as an auction or a vehicle do, because that file's other models
have states of their own and their rules are not this check's business. The
cost of that narrowing is a write through a variable named something else
entirely; the alternative is a check that cries wolf in another team's app,
and a check people learn to ignore protects nothing.

What does not: `objects.create(state=...)` and `Vehicle(state=...)`. Choosing
the state a row is born in is not a transition, and forbidding it would make
fixtures impossible without teaching them a service call for every row.

Run:  python ops/checks/auction_state_single_writer.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ بعد
# ثالث مرة — وهذا أسوأ من حارسٍ لا يعمل، لأنه يُطفأ عن قناعة.
#
# و`hasattr` ليست حذراً زائداً: `tests/test_no_float_check.py` يستورد هذا
# الملف، وpytest يكون قد استبدل `sys.stdout` بكائن التقاطٍ بلا `reconfigure`.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

#: The one writer.
ALLOWED = {BACKEND / "apps" / "auctions" / "services.py"}

SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules"}


def _touches_auctions(path: Path, tree: ast.AST) -> bool:
    if "auctions" in path.parts:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "apps.auctions"
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name.startswith("apps.auctions") for alias in node.names
        ):
            return True
    return False


#: Words that make a subject one of ours.
SUBJECTS = ("auction", "vehicle", "lot", "car")


def _subject_of(node: ast.AST) -> str:
    """The leftmost name in an expression: `Vehicle.objects.filter(...)` → Vehicle."""
    while isinstance(node, ast.Attribute | ast.Call | ast.Subscript):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id.lower() if isinstance(node, ast.Name) else ""


def _is_ours(node: ast.AST) -> bool:
    subject = _subject_of(node)
    return any(word in subject for word in SUBJECTS)


class StateWriteHunter(ast.NodeVisitor):
    def __init__(self, *, everything: bool) -> None:
        #: Inside `apps/auctions` no name is innocent; outside, the subject has
        #: to look like an auction or a vehicle.
        self.everything = everything
        self.hits: list[tuple[int, str]] = []

    def _relevant(self, node: ast.AST) -> bool:
        return self.everything or _is_ours(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "state"
                and self._relevant(target.value)
            ):
                self.hits.append((node.lineno, "إسناد مباشر إلى .state"))
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        target = node.target
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "state"
            and self._relevant(target.value)
        ):
            self.hits.append((node.lineno, "تعديل مباشر على .state"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "update":
            if any(keyword.arg == "state" for keyword in node.keywords) and (
                self._relevant(func.value)
            ):
                self.hits.append((node.lineno, "‏.update(state=…) على استعلام"))
        self.generic_visit(node)


def violations(roots: list[Path], allowed: set[Path] | None = None) -> list[str]:
    allowed = ALLOWED if allowed is None else allowed
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts) or path in allowed:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if not _touches_auctions(path, tree):
                continue
            hunter = StateWriteHunter(everything="auctions" in path.parts)
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("حالة المزاد والمركبة تتغيّر في apps/auctions/services.py وحدها:\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. استعمل دوال الخدمة.")
        return 1

    print("لا تغيير لحالة مزاد أو مركبة خارج الخدمة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
