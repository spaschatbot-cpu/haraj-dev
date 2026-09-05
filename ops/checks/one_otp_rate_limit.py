#!/usr/bin/env python
"""Fail if any path that can send or spend a one-time code is unmetered.

The rule (spec 007, T602): **one shared limit covers every path that sends a
code** — registration, sign-in, changing a phone number, recovering an account.

Why a text check and not a code review. The limit on the path that exists today
is easy; T602 is about the fourth path, added next quarter by someone who copied
the third one. In v1 the SMS bill had a month nobody could explain, and the cause
was a single account-recovery endpoint that had been written after the limit and
never learned about it. One unmetered send path is a free SMS gateway for
whoever finds it, and finding it costs an attacker one afternoon.

Two rules, both about the same thing — no second door:

1. **A code is sent only from a metered view.** A call to
   `send_verification_code` anywhere but `apps/accounts/services.py` (where it
   is defined) must sit inside a view class that declares
   ``throttle_classes = OTP_SEND_THROTTLES``. The same holds for the paths that
   *spend* codes — `check_verification_code` and `sign_in_with_code` — which
   must carry ``OTP_VERIFY_THROTTLES``.
2. **The limits are always a named set, never a hand-written list.** A view
   that writes out ``throttle_classes = [OtpSendPerPhoneThrottle]`` is a view
   that will not notice when a third limit joins the set. Any ``*_THROTTLES``
   symbol satisfies this — bidding has its own (T611) and is not this check's
   business — but a list literal does not, so adding a limit reaches every path
   that carries the set at once.

Test directories are skipped: a test that *proves* the limit works has to build
throttled and unthrottled views of its own, and a check that fires on the proof
is a check people switch off.

Run:  python ops/checks/one_otp_rate_limit.py
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

#: Where the sending and checking functions are defined, and the only module
#: allowed to call them without a view's limits around it.
SERVICE_LAYER = BACKEND / "apps" / "accounts" / "services.py"

SKIP_PARTS = {"__pycache__", "migrations", "tests", ".venv", "node_modules"}

#: call name -> the throttle set a view making that call must declare.
GUARDED_CALLS = {
    "send_verification_code": "OTP_SEND_THROTTLES",
    "check_verification_code": "OTP_VERIFY_THROTTLES",
    "sign_in_with_code": "OTP_VERIFY_THROTTLES",
}

ACCEPTED_SETS = frozenset(GUARDED_CALLS.values())


def _is_a_named_set(name: str) -> bool:
    """`OTP_SEND_THROTTLES`, `BID_THROTTLES` — a module-level set, not a literal.

    Rule 2 is about the *shape* of the declaration, not about which domain owns
    it. An earlier version of this check accepted only the two OTP sets, and it
    fired on `apps.bidding`'s own limits the day T611 landed — a check that
    complains about correct code is one people learn to switch off.
    """
    return name.isupper() and name.endswith("_THROTTLES")


def _called_name(node: ast.Call) -> str:
    """``send_verification_code(...)`` and ``services.send_verification_code(...)``."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _declared_throttles(cls: ast.ClassDef) -> list[str]:
    """What ``throttle_classes`` on this class is set to, as written.

    A name (`OTP_SEND_THROTTLES`) is what rule 2 wants. Anything else — a list
    literal, a concatenation, an empty list — is reported as written so the
    failure names what it actually found.
    """
    for node in cls.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and target.id == "throttle_classes":
                value = node.value
                if isinstance(value, ast.Name):
                    return [value.id]
                if isinstance(value, ast.List):
                    return [
                        item.id if isinstance(item, ast.Name) else ast.dump(item)
                        for item in value.elts
                    ] or ["[]"]
                return [ast.dump(value) if value is not None else "None"]
    return []


def _visit(node: ast.AST, cls: ast.ClassDef | None, found: list[str], path: Path) -> None:
    """Walk the tree remembering which class body we are inside."""
    for child in ast.iter_child_nodes(node):
        inside = child if isinstance(child, ast.ClassDef) else cls

        if isinstance(child, ast.Call):
            name = _called_name(child)
            required = GUARDED_CALLS.get(name)
            if required is not None:
                declared = _declared_throttles(inside) if inside is not None else []
                if inside is None:
                    found.append(
                        f"{path}:{child.lineno}: استدعاء «{name}» خارج أي كلاس "
                        f"— لا مكان تُعلَّق عليه الحدود"
                    )
                elif required not in declared:
                    written = "، ".join(declared) if declared else "لا شيء"
                    found.append(
                        f"{path}:{child.lineno}: «{inside.name}» يستدعي «{name}» "
                        f"و throttle_classes = {written}؛ المطلوب {required}"
                    )

        if isinstance(child, ast.ClassDef):
            declared = _declared_throttles(child)
            stray = [name for name in declared if not _is_a_named_set(name)]
            if stray:
                found.append(
                    f"{path}:{child.lineno}: «{child.name}» يكتب الحدود بيده "
                    f"({'، '.join(stray)}) بدل المجموعة المسمّاة"
                )

        _visit(child, inside, found, path)


def violations(roots: list[Path], service_layer: Path | None = None) -> list[str]:
    service_layer = SERVICE_LAYER if service_layer is None else service_layer
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts) or path == service_layer:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            _visit(tree, None, found, path)

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config"])
    if found:
        print("كل مسار يرسل أو يصرف رمزاً يحمل حدّ المعدّل المسمّى:\n")
        for item in found:
            print(f"  {item}")
        print(
            f"\n{len(found)} مخالفة. مسار إرسال بلا حدّ = بوابة رسائل مجانية "
            "لمن يجده."
        )
        return 1

    print("لا مسار OTP بلا حدّ معدّل.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
