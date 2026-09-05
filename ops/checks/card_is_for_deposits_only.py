#!/usr/bin/env python
"""Fail if anything routes a purchase at the card gateway.

`PHASE_02` §5-1: the card rail carries insurance deposits and nothing else.
Cars are settled by bank transfer or from the wallet.

Two costs, and the platform paid both in v1:

* customers put purchases of **over a hundred thousand riyals** on bank cards,
  and the interchange on those "كبّد الشركة عمولات بنكية ضخمة";
* a card charge can be reversed months later — against a car that left the yard
  the same week, with nothing left to take back.

The enums already say this: `PaymentMethod` has no card member, `PaymentPurpose`
has only the deposit, and `record_payment` refuses `source="card"`. This check
exists because the rule is not broken by editing those — it is broken by a new
integration that reaches the gateway a different way, and reads as ordinary code
while doing it.

What it refuses, outside the money app's own gateway and payment modules:

* `PaymentPurpose` given anything but `INSURANCE_DEPOSIT`;
* a payment intent created for an invoice or a vehicle;
* `source="card"` on the same line as an invoice.

Run it as `python ops/checks/card_is_for_deposits_only.py`; it exits non-zero
and names the file and line, like every other check here.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"

#: The modules that own the gateway, and so are allowed to name its pieces.
ALLOWED = {
    BACKEND / "apps" / "money" / "services.py",
    BACKEND / "apps" / "money" / "models.py",
    BACKEND / "apps" / "money" / "gateway.py",
}

SKIP_DIRS = {"migrations", "__pycache__", ".venv", "node_modules", "tests"}

PATTERNS = [
    (
        re.compile(r"PaymentPurpose\.(?!INSURANCE_DEPOSIT\b)[A-Z_]+"),
        "غرض دفعٍ بالبطاقة غير إيداع التأمين",
    ),
    (
        re.compile(r"start_topup\s*\([^)]*\b(invoice|vehicle)\s*="),
        "نيّة دفعٍ بالبطاقة على فاتورة أو مركبة",
    ),
    (
        re.compile(r"""source\s*=\s*["']card["'][^\n]*invoice|invoice[^\n]*source\s*=\s*["']card["']"""),
        "سداد فاتورة بمصدر بطاقة",
    ),
]


def offences() -> list[str]:
    found: list[str] = []
    for path in sorted(BACKEND.rglob("*.py")):
        if path in ALLOWED or set(path.parts) & SKIP_DIRS:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(lines, start=1):
            if line.strip().startswith("#"):
                continue
            for pattern, what in PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(ROOT)
                    found.append(f"{rel}:{number}: {what} — {line.strip()[:80]}")
    return found


def main() -> int:
    found = offences()
    if found:
        print("البطاقة تُستعمل لغير شحن التأمين:", file=sys.stderr)
        for line in found:
            print("  " + line, file=sys.stderr)
        print(
            "\nالبطاقة لشحن ودائع التأمين وحدها. السيارة تُسدَّد بتحويل بنكي أو "
            "من الرصيد — العمولة تكلفة حقيقية، والاسترجاع بعد شهور لا يُردّ عليه.",
            file=sys.stderr,
        )
        return 1
    print("البطاقة لشحن التأمين وحده.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
