#!/usr/bin/env python
"""Fail if anything but `check_eligibility` decides who may bid.

The rule (spec 006 §"قواعد الأهلية"): there is one function that says whether a
person may bid, every path calls it, and no path asks a question of its own.

Why a text check and not a code review: in v1 the home page alone had **six**
paths that could send a bid. Each was written by someone who meant to use the
shared rule, and every new rule had to be remembered six times — the one that
was forgotten became the hole a debtor bid through. A rule of that shape cannot
be held by reading; the failure is a *new place* appearing, and a new place is
exactly what a syntax-tree check can see.

Two rules, and both are about the same thing — one door:

1. **The facts are read in one file.** `phone_verified_at`, `deposit_required`,
   `outstanding`, `owner_company`, an exception granted by the owner: whoever
   reads one of these is deciding something about eligibility. Only
   `apps/bidding/eligibility.py` may.
2. **Bids are written in one file.** A `Bid` row created anywhere but
   `apps/bidding/services.py` is a bidding path that has not passed the gate,
   whatever else it does.

Scope: modules inside `apps/bidding`, plus any module anywhere in the backend
that imports from `apps.bidding`. A file that never touches bidding cannot open
a second bidding path, and scanning it would fire on other apps' own use of the
same column names — `Invoice.outstanding` belongs to the money engine and its
rules are not this check's business.

Test directories are skipped, deliberately. A test that asserts
`user.phone_verified_at is None` is not a second decision point, and a check
that fires on assertions is a check people learn to switch off — which protects
nothing at all.

Run:  python ops/checks/one_eligibility_gate.py
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

#: The one place a fact about eligibility may be read.
GATE = BACKEND / "apps" / "bidding" / "eligibility.py"

#: The one place a bid may be written.
BID_WRITER = BACKEND / "apps" / "bidding" / "services.py"

SKIP_PARTS = {"__pycache__", "migrations", "tests", ".venv", "node_modules"}

#: Attribute names that, when read, mean somebody is judging a bidder. The `_id`
#: twins are listed because Django gives every foreign key two names and a check
#: that knows only one of them is a check with a door left open.
FACTS = frozenset(
    {
        "phone_verified_at",
        "national_id",
        "is_open_for_bidding",
        "deposit_required",
        "outstanding",
        "owner_company",
        "owner_company_id",
        "exception_note",
        "exception_granted_by",
        "exception_granted_by_id",
    }
)


def _touches_bidding(path: Path, tree: ast.AST) -> bool:
    if "bidding" in path.parts:
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
            "apps.bidding"
        ):
            return True
        if isinstance(node, ast.Import) and any(
            alias.name.startswith("apps.bidding") for alias in node.names
        ):
            return True
    return False


class GateHunter(ast.NodeVisitor):
    """Collects reads of an eligibility fact, and rows of `Bid` being made."""

    def __init__(self, *, watch_facts: bool, watch_bids: bool) -> None:
        self.watch_facts = watch_facts
        self.watch_bids = watch_bids
        self.hits: list[tuple[int, str]] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Loads only. Writing `hold.exception_note = ...` is granting the
        # exception; *reading* it is deciding on one, and only the gate may.
        if (
            self.watch_facts
            and isinstance(node.ctx, ast.Load)
            and node.attr in FACTS
        ):
            self.hits.append(
                (node.lineno, f"قراءة شرط أهلية «{node.attr}» خارج check_eligibility")
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if self.watch_bids and _creates_a_bid(node.func):
            self.hits.append((node.lineno, "إنشاء مزايدة خارج place_bid"))
        self.generic_visit(node)


def _creates_a_bid(func: ast.AST) -> bool:
    """`Bid(...)`, `Bid.objects.create(...)`, `Bid.objects.bulk_create(...)`."""
    if isinstance(func, ast.Name):
        return func.id == "Bid"
    if isinstance(func, ast.Attribute) and func.attr in ("create", "bulk_create"):
        subject = func.value
        while isinstance(subject, ast.Attribute):
            subject = subject.value
        return isinstance(subject, ast.Name) and subject.id == "Bid"
    return False


def violations(
    roots: list[Path],
    gate: Path | None = None,
    bid_writer: Path | None = None,
) -> list[str]:
    gate = GATE if gate is None else gate
    bid_writer = BID_WRITER if bid_writer is None else bid_writer
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts):
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            if not _touches_bidding(path, tree):
                continue
            hunter = GateHunter(
                watch_facts=path != gate, watch_bids=path != bid_writer
            )
            hunter.visit(tree)
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config"])
    if found:
        print("الأهلية تُقرَّر في apps/bidding/eligibility.py وحدها:\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. استدعِ check_eligibility بدل فحص الشرط بنفسك.")
        return 1

    print("لا شرط أهلية يُفحص خارج البوابة الواحدة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
