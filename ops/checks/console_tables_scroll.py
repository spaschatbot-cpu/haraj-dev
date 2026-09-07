#!/usr/bin/env python
"""لا جدولَ في اللوحة بلا غلافٍ يمرّره — T838.

العطل الذي وُلد هذا لأجله، مقيساً
=================================
قِيست شاشات اللوحة في متصفّح على سبعة عروض (2026-09-07). على **٩٠٠ بكسل** —
أي لوحٌ أفقيّ أو حاسوبٌ محمول صغير، وهو ما يفتح عليه الموظّف اللوحة فعلاً —
كانت الصفحة **كلّها** تُسحب جانباً:

    /console/bids/accepted/     +١٤٣ بكسل
    /console/vehicles/catalog/  +١٠٥
    /console/after-sales/        +٩٢

فيغيب الشريط الجانبي والرأس عن حافّة الشاشة. وعلى ١٠٢٤ ما زالت الأولى تفيض
بـ١٩ بكسل.

ولم يظهر على الجوال لأن الورقة كانت تحمل
`main table { display: block; overflow-x: auto }` **داخل `max-width: 56rem`
وحدها**: تحت ٨٩٦ يمرّر الجدول، وفوقها لا يمرّر شيء. والفجوة هي المقاس الأشيع.

فصار لكل جدولٍ غلافٌ `<div class="scroller">` يمرّر في **كل** مقاس، وحُذفت
حيلة `display: block` — فكسبنا معها أن الجدول يبقى جدولاً في شجرة الوصول
(`display: block` يُخرج الصفوف والخانات منها في محرّكاتٍ عدّة) وأن الرأس
اللاصق يبقى لاصقاً.

ما يفحصه هذا الملف
==================
كل `<table>` في `backend/templates/console/` يسبقه — في السطر نفسه أو قبله —
عنصرٌ صفّه `scroller`، ولا شيء بينهما إلا فراغ. القالبُ الذي يُكتب غداً ينسى
الغلاف، ولا يظهر النسيان إلا على شاشةٍ بعرضٍ بعينه عند موظّفٍ بعينه.

**ويصرخ إن لم يجد ما يحرسه**: صفرُ جداولٍ يعني أن المسار تغيّر أو أن القوالب
نُقلت، وحارسٌ يفحص العدم يمرّ دائماً.

Run:  python ops/checks/console_tables_scroll.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ويندوز: cp1252 لا يمثّل العربية، فجملة النجاح نفسها ترمي `UnicodeEncodeError`
# ويخرج الحارس بـ1 وهو ناجح — وحارسٌ يُبلَّغ عنه فاشلاً وهو ناجح يُطفَأ عن قناعة.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "backend" / "templates" / "console"

#: الغلاف كما يُكتب: `<div class="scroller">` ثم فراغٌ ثم `<table`.
WRAPPED = re.compile(r'class="[^"]*\bscroller\b[^"]*"\s*>\s*<table\b', re.S)
TABLE = re.compile(r"<table\b")


def offences() -> tuple[list[str], int]:
    found: list[str] = []
    tables = 0

    for path in sorted(TEMPLATES.glob("*.html")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue

        #: مواضع الجداول المغلَّفة، لتُستثنى من العدّ بالموضع لا بالعدد:
        #: قالبٌ فيه جدولان أحدهما مغلَّف يجب أن يُبلَّغ عن الآخر وحده.
        wrapped_at = {match.end() for match in WRAPPED.finditer(source)}

        for match in TABLE.finditer(source):
            tables += 1
            if match.end() in wrapped_at:
                continue
            line = source.count("\n", 0, match.start()) + 1
            found.append(
                f"{path.relative_to(ROOT)}:{line}: "
                "جدولٌ بلا غلاف — لُفّه بـ`<div class=\"scroller\">` "
                "وإلا سُحبت الصفحة أفقياً على شاشةٍ ضيّقة"
            )

    return found, tables


def main() -> int:
    found, tables = offences()

    if tables == 0:
        print(
            f"لا جدول واحد في {TEMPLATES.relative_to(ROOT)} — "
            "تغيّر المسار أو نُقلت القوالب، والفحص يحرس العدم.",
            file=sys.stderr,
        )
        return 1

    if found:
        print("جداولٌ لا تمرّر أفقياً داخل نفسها:", file=sys.stderr)
        for item in found:
            print("  " + item, file=sys.stderr)
        print(
            f"\n{len(found)} مخالفة من {tables} جدولاً. "
            "قِيس على ٩٠٠ بكسل: الصفحة تفيض ١٤٣ بكسل بلا الغلاف.",
            file=sys.stderr,
        )
        return 1

    print(f"كل جدولٍ في اللوحة يمرّر داخل نفسه — {tables} جدولاً.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
