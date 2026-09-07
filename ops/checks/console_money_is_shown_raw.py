#!/usr/bin/env python
"""Fail if a console template prints a money value without `unlocalize`.

The rule is written at the top of `auction_detail.html` and obeyed by every
template the phase-009 author wrote:

    `unlocalize` on every amount: money is shown exactly as the ledger stores
    it. A thousands separator or a localised decimal comma is a display
    transformation on a money value, and an operator comparing this screen to
    the ledger must not have to undo one in their head.

**It had no check, and that is why it was broken.** `LANGUAGE_CODE = "ar"`, so
Django renders `Decimal("10000.00")` as `10000,00` — a comma where the ledger
holds a period. Four screens written in one day showed money that way, and
nothing said so: the page renders, the tests pass, and the number is *almost*
right, which is the worst kind of wrong for a figure somebody reconciles.

Measured, not assumed: rendering `{{ v }}` against these settings gives
`'10000,00'` and `{{ v|unlocalize }}` gives `'10000.00'`.

**What counts as money is a name, not a type.** A template cannot be asked what
a variable holds, so this matches on the field names the money models actually
use. That makes the check narrow on purpose: it will not catch a money value
stored under a name nobody here uses, and it will not fire on `vehicle.year`.

Run:  python ops/checks/console_money_is_shown_raw.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح. وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates" / "console"

#: أسماء الحقول التي تحمل مالاً في نماذج `apps.money` و`apps.auctions`.
MONEY_NAMES = {
    "amount",
    "balance",
    "requested",
    "shortfall",
    "free",
    "held",
    "locked",
    "outstanding",
    "total",
    "reserve_price",
    "awarded_price",
    "deposit_required",
    "paid",
    "due",
}

#: `{{ … }}` كاملةً، بما فيها المرشِّحات.
EXPRESSION = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def offending(text: str) -> list[str]:
    found = []
    for match in EXPRESSION.finditer(text):
        body = match.group(1)
        path = body.split("|")[0].strip()
        leaf = path.split(".")[-1]
        if leaf in MONEY_NAMES and "unlocalize" not in body:
            found.append(body)
    return found


def main() -> int:
    files = sorted(TEMPLATES.glob("*.html"))
    if len(files) < 10:
        print(f"وُجد {len(files)} قالباً فقط — الفحص لا يجد ما يحرسه.", file=sys.stderr)
        return 1

    broken = False
    for path in files:
        text = path.read_text(encoding="utf-8")
        for body in offending(text):
            broken = True
            rel = path.relative_to(ROOT).as_posix()
            print(f"{rel}: {{{{ {body} }}}} بلا unlocalize", file=sys.stderr)

    if broken:
        print(
            "\n`LANGUAGE_CODE = \"ar\"`، فـ`10000.00` تُعرض `10000,00`: فاصلةٌ حيث\n"
            "يحمل الدفتر نقطة. ومن يطابق شاشةً بدفترٍ لا يُطلب منه أن يفكّ تحويل\n"
            "عرضٍ في رأسه. أضِف `|unlocalize`، و`{% load l10n %}` في رأس القالب.",
            file=sys.stderr,
        )
        return 1

    print(f"كل مبلغ في قوالب اللوحة يُعرض كما يخزّنه الدفتر — {len(files)} قالباً.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
