#!/usr/bin/env python
"""Fail if anything but `money.services.tax_of` decides what tax an amount carries.

HR-05, and `PHASE_03` §2 calls it the finest trap in the v1 files. It is not a
rounding bug — it is a silent 15% overcharge:

    an invoice we raise carries amounts **before** tax;
    an invoice Odoo sends back carries amounts **including** it.

One equation applied to both charges the customer 15% on a figure that already
had it. And that is exactly what a second place computing a total looks like:
correct in isolation, wrong on half the rows, and visible to nobody until a
customer adds up their own invoice.

So the rate has one reader. A screen that wants a total asks `tax_of`, which
looks at `Invoice.source` before it multiplies anything.

What this refuses, anywhere but the one function:

* reading `settings.VAT_RATE` or calling `vat_rate()`;
* the literal `1.15` / `0.15` / `Decimal("1.15")` on any line;
* `* 1.15` and `/ 1.15` in any spelling.

Run it as `python ops/checks/one_tax_rule.py`; it exits non-zero and names the
file and line, like every other check in this directory.
"""

from __future__ import annotations

import re
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

#: The one place allowed to know the rate.
OWNER = BACKEND / "apps" / "money" / "services.py"

#: Where the setting itself is declared, and where it is documented.
ALLOWED = {
    OWNER,
    BACKEND / "config" / "settings" / "base.py",
}

SKIP_DIRS = {"migrations", "__pycache__", ".venv", "node_modules", "tests"}

PATTERNS = [
    (re.compile(r"\bVAT_RATE\b"), "قراءة نسبة الضريبة"),
    (re.compile(r"\bvat_rate\s*\("), "نداء nisbat الضريبة"),
    (re.compile(r"(?<![\w.])1\.15(?![\d])"), "معامل 1.15"),
    (re.compile(r"(?<![\w.])0\.15(?![\d])"), "نسبة 0.15"),
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
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, what in PATTERNS:
                if pattern.search(line):
                    rel = path.relative_to(ROOT)
                    found.append(f"{rel}:{number}: {what} — {stripped[:80]}")
    return found


def main() -> int:
    found = offences()
    if found:
        print("حساب ضريبة خارج money.services.tax_of:", file=sys.stderr)
        for line in found:
            print("  " + line, file=sys.stderr)
        print(
            "\nالفاتورة المحلية مبالغها قبل الضريبة والواردة من أودو شاملةٌ لها. "
            "معادلةٌ واحدة عليهما تفرض 15% فوق مبلغٍ يحملها — اسأل tax_of.",
            file=sys.stderr,
        )
        return 1
    print("قاعدة الضريبة في مكان واحد.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
