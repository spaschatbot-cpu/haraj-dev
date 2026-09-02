#!/usr/bin/env python
"""Fail if anything asks about a role instead of asking about a capability.

The rule (spec 009 §"قواعد الصلاحيات", T801): one gate, `apps.core.permissions.can`,
and **no code anywhere asks "is this person an X?"**.

Why a text check and not a code review. v1's `hasRole()` returned true for every
role when the asker was the owner. That read as generous, and it was — until
somebody used the same function to ask *"is this user's role X?"* about a
specific person. For the owner it said yes to every role at once, the menu code
took the first match, and the console locked the owner out of his own platform.

The bug was not in `hasRole`. It was that a role question existed at all: a
question with that shape has a right answer for "may I?" and a wrong one for
"who is this?", and the two call sites look identical. So the shape is banned,
and the ban is checked rather than remembered.

Three rules:

1. **No comparison against a role value.** `user.console_role == "owner"`,
   `role in ("finance", "support")`, `Role.OWNER == whatever` — all of it.
2. **No role-shaped helper.** A function named `is_owner`, `has_role`,
   `is_finance` and so on, however it is implemented.
3. **`console_role` is read in one file.** `apps/core/permissions.py` turns it
   into a set of capabilities; everywhere else must ask `can()`.

`apps/core/permissions.py` is exempt from all three — it is the gate. Test
directories are skipped: a test that builds a user with a role and asserts the
gate's answer is the thing that proves the rule, and a check that fires on the
proof is a check people switch off.

Run:  python ops/checks/one_permission_gate.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

#: The one module allowed to know what a role is.
GATE = BACKEND / "apps" / "core" / "permissions.py"

SKIP_PARTS = {"__pycache__", "migrations", "tests", ".venv", "node_modules"}

#: The field that names a role. Reading it outside the gate is rule 3.
ROLE_FIELD = "console_role"

#: Role values as they appear in code. A comparison against one of these is a
#: role question whatever variable it is on.
ROLE_VALUES = frozenset({"owner", "operations", "finance", "support"})

#: Names that betray a role-shaped helper regardless of body.
BANNED_PREFIXES = ("is_owner", "is_staff_role", "has_role", "check_role")
BANNED_NAMES = frozenset(
    {"is_owner", "is_operations", "is_finance", "is_support", "has_role", "role_of"}
)


def _is_role_literal(node: ast.AST) -> bool:
    """A role value, alone or inside the collection of an ``in`` test.

    The collection case is not an afterthought: `role in ("finance", "support")`
    is the *most* natural way to write a role question, and a check that only
    saw `role == "finance"` would miss the shape people actually reach for.
    """
    if isinstance(node, ast.Constant):
        return node.value in ROLE_VALUES
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return any(_is_role_literal(element) for element in node.elts)
    return False


def _reads_role_field(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == ROLE_FIELD


class GateHunter(ast.NodeVisitor):
    def __init__(self, allow_role_field: bool) -> None:
        self.allow_role_field = allow_role_field
        self.hits: list[tuple[int, str]] = []

    def visit_Compare(self, node: ast.Compare) -> None:
        parts = [node.left, *node.comparators]
        if any(_is_role_literal(part) for part in parts) or any(
            _reads_role_field(part) for part in parts
        ):
            self.hits.append(
                (node.lineno, "مقارنة على الدور — اسأل can(user, capability)")
            )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            not self.allow_role_field
            and node.attr == ROLE_FIELD
            and isinstance(node.ctx, ast.Load)
        ):
            self.hits.append(
                (node.lineno, f"قراءة «{ROLE_FIELD}» خارج البوابة الواحدة")
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in BANNED_NAMES or node.name.startswith(BANNED_PREFIXES):
            self.hits.append(
                (node.lineno, f"دالة تسأل عن دور: «{node.name}»")
            )
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # type: ignore[arg-type]


def violations(roots: list[Path], gate: Path | None = None) -> list[str]:
    gate = GATE if gate is None else gate
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*.py"))
        for path in paths:
            if SKIP_PARTS & set(path.parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            hunter = GateHunter(allow_role_field=path == gate)
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config"])
    if found:
        print("الصلاحية تُسأل، لا الدور:\n")
        for item in found:
            print(f"  {item}")
        print(
            f"\n{len(found)} مخالفة. سؤال الدور هو ما أقفل لوحة v1 في وجه "
            "مالكها — استعمل can(user, capability)."
        )
        return 1

    print("لا سؤال عن دور خارج البوابة الواحدة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
