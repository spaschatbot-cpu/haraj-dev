#!/usr/bin/env python
"""Fail if anything but `apps/money/services.py` writes the ledger.

Article 1-2 is the sharpest rule in the constitution — «`apps.money.services.post`
هو الشيء الوحيد في المشروع كله الذي ينشئ قيداً» — and until this file existed it
was the only rule with no automated guard. Auction state has one
(`auction_state_single_writer.py`), the vehicle price has one, the vehicle card
has one, spreadsheets have one, and floats have one. The ledger, which all of
them exist to protect, had none: the tree was clean today, and nothing made it
stay clean tomorrow.

That gap is not hypothetical. A settlement service in phase 006 or an admin
action in phase 009 that writes an `Entry` directly would pass review the way
six paths for ending an auction passed review in v1 — each written by someone
who fully intended to use the shared one.

What counts as a write
----------------------
* constructing an entry or a transaction: `Entry(...)`, `Transaction(...)`
* `Entry.objects.create/bulk_create/update/delete`, and the same on
  `Transaction`
* assigning to a balance: `account.balance = ...`
* `.update(balance=...)` on a queryset

What does not
-------------
Reading. `Entry.objects.filter(...)`, `Transaction.objects.count()` and every
other query are how the rest of the system *looks* at the ledger, which is the
whole point of keeping one.

Scope: `backend/apps`, `backend/config`, `backend/tests`. Tests are included
deliberately — a test that writes an `Entry` by hand is a test that proves
something about a ledger the service would never have produced.

Two narrowings, both deliberate, both stated rather than discovered:

* `apps/money/tests/test_verification.py` may write entries. Proving that
  `verify_ledger` reports drift requires forging drift, and drift is the one
  thing the writer can never produce. It is named here, so a second exception
  is a decision somebody makes in this file rather than a side effect of naming
  a file cleverly.
* Any file inside a `tests/` directory may write `.balance`. Article 4-2 says a
  constraint that is not tested under production settings does not exist, and
  the only way to test `customer_buckets_never_go_negative` or
  `check_cached_balances` is to set a balance the service would never set. The
  ledger-row rule above still applies to those files in full.

Run:  python ops/checks/money_single_writer.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

#: The one writer.
ALLOWED = {
    BACKEND / "apps" / "money" / "services.py",
    # Forges drift on purpose, to prove the verifier reports it. A verifier
    # tested only through the writer that can never produce drift tests nothing.
    BACKEND / "apps" / "money" / "tests" / "test_verification.py",
}

SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules"}

#: The tables that are the ledger.
LEDGER_MODELS = frozenset({"Entry", "Transaction"})

#: Manager methods that write.
WRITING_METHODS = frozenset(
    {"create", "bulk_create", "get_or_create", "update_or_create", "update", "delete"}
)


def _root_name(node: ast.AST) -> str:
    """The leftmost name of an expression: `Entry.objects.filter(x)` → `Entry`."""
    while isinstance(node, ast.Attribute | ast.Call | ast.Subscript):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else ""


class LedgerWriteHunter(ast.NodeVisitor):
    def __init__(self, *, balances_too: bool = True) -> None:
        #: False inside a `tests/` directory: forging a stored balance is how a
        #: CHECK and the verifier are proven, and the rows themselves stay
        #: forbidden either way.
        self.balances_too = balances_too
        self.hits: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        # Entry(...) / Transaction(...) — constructing a row of the ledger.
        if isinstance(func, ast.Name) and func.id in LEDGER_MODELS:
            self.hits.append((node.lineno, f"ينشئ {func.id}(...) مباشرةً"))

        if isinstance(func, ast.Attribute):
            # Entry.objects.create(...), Transaction.objects.update(...)
            if func.attr in WRITING_METHODS and _root_name(func.value) in LEDGER_MODELS:
                self.hits.append(
                    (node.lineno, f"‏{_root_name(func.value)}.…{func.attr}(…) يكتب")
                )
            # .update(balance=…) on any queryset
            if (
                self.balances_too
                and func.attr == "update"
                and any(keyword.arg == "balance" for keyword in node.keywords)
            ):
                self.hits.append((node.lineno, "‏.update(balance=…) على استعلام"))

        self.generic_visit(node)

    def _balance_target(self, target: ast.AST) -> bool:
        return (
            self.balances_too
            and isinstance(target, ast.Attribute)
            and target.attr == "balance"
        )

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if self._balance_target(target):
                self.hits.append((node.lineno, "إسناد مباشر إلى .balance"))
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if self._balance_target(node.target):
            self.hits.append((node.lineno, "تعديل مباشر على .balance"))
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
            hunter = LedgerWriteHunter(balances_too="tests" not in path.parts)
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("المادة ١-٢: الدفتر يُكتب في apps/money/services.py وحدها:\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. استعمل apps.money.services.post.")
        return 1

    print("لا كتابة في الدفتر خارج apps/money/services.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
