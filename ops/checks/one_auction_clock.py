#!/usr/bin/env python
"""ساعةُ المزاد تُقرأ في مكانٍ واحد — T839.

العطل الذي وُلد هذا لأجله، مقيساً
=================================
سؤالٌ واحد — «هل هذا المزاد مفتوحٌ للمزايدة الآن؟» — كان له **ثلاثة** أجوبةٍ
مكتوبةٍ بثلاث أيدٍ، ولا تتّفق:

1. ``Auction.is_open_for_bidding`` — ``state == LIVE and starts_at <= now < ends_at``
2. ``bidding/eligibility.py`` — فرعان يعيدان بناء الشرط نفسه
3. لوحةُ الإدارة (``dashboard`` و``analytics`` و``catalog`` و``partner_console``)
   — ``filter(state=LIVE)`` **بلا نظرٍ إلى الساعة أصلاً**

فالثالث يعدّ مزاداً انتهى وقتُه ولم يُغلَق بعدُ ضمن «الجارية». وقد رُئي في
قاعدة التطوير هذه: مزادٌ في الحالة ``live`` ونهايتُه قبل تسع ساعات — العدّاد
عند العميل يقول «مضى»، واللوحة تقول «جارٍ»، والبوّابة ترفض كل مزايدة. ثلاثُ
شاشاتٍ تقرأ صفّاً واحداً وتقول ثلاثة أشياء.

والسبب بنيويّ لا سهو: الحالةُ عمودٌ **يكتبه عاملُ خلفيّة**، والساعةُ لا تنتظر
العامل. فالفجوة بين اللحظتين موجودةٌ دائماً، وكلُّ من لم يسمّها أعاد اختراع
تفسيرٍ لها.

ما يفحصه هذا الملفّ
==================
لا موضعَ في الواجهة الخلفية يقارن ``starts_at`` أو ``ends_at`` بالزمن —
لا في بايثون (``auction.ends_at <= now``) ولا في الاستعلام
(``ends_at__lte=now``) — إلا :mod:`apps.auctions.engine`.

**ملفٌّ واحد مستثنى، لا قائمة.** قائمةُ الاستثناءات تكبر حتى تصير هي القاعدة؛
وحين احتاج ``states.py`` و``services.py`` الساعةَ لم يُضافا هنا، بل نادَيا
``engine.has_started`` و``engine.has_finished``.

ما لا يفحصه: الإسناد (``auction.ends_at = ...``) وحقولُ النماذج
(``ends_at = models.DateTimeField()``) والقيدُ في ``Meta``. تحديدُ الموعد ليس
قراءةً للساعة.

**ويصرخ إن لم يجد ما يحرسه**: صفرُ قراءاتٍ داخل المحرّك نفسه يعني أن الملفّ
نُقل أو أُفرغ، وحارسٌ يفحص العدم يمرّ دائماً.

Run:  python ops/checks/one_auction_clock.py
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
BACKEND = ROOT / "backend"

#: الموضع الوحيد الذي يقرأ الساعة.
ENGINE = BACKEND / "apps" / "auctions" / "engine.py"

SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules", "tests"}

#: قراءةٌ في بايثون: `x.starts_at <= now`، `now < auction.ends_at`، وأخواتها.
#:
#: **الترتيبُ وحده** (`<` و`<=` و`>` و`>=`). التساوي خارجٌ عمداً لا تساهلاً:
#: `ends_at == now` جملةٌ لا معنى لها على وقتٍ بدقّة الميكروثانية، فلا أحد
#: يكتبها لقراءة الساعة — ومن يكتب `!=` إنما يقارن موعداً بموعدٍ جديد، وهو ما
#: تفعله بذرةُ العرض حين تسأل «هل تغيّر الموعد؟». وإدخالُ التساوي هنا أرسبها
#: على سطرٍ لا يقرأ ساعةً أصلاً، وحارسٌ يرسب على البريء يُطفَأ.
COMPARISON = re.compile(
    r"(?:"
    r"\b(?:starts_at|ends_at)\b\s*[<>]=?"  # ends_at <= now
    r"|[<>]=?\s*[\w.]*\b(?:starts_at|ends_at)\b"  # now < a.ends_at
    r")"
)

#: قراءةٌ في الاستعلام: `ends_at__lte=now`. الاسمُ المجرّد `ends_at=` إسنادٌ
#: في `create()` أو `Auction(...)`، وليس قراءةً للساعة.
LOOKUP = re.compile(r"\b(?:starts_at|ends_at)__(?:lt|lte|gt|gte|range)\b")

#: حقلُ النموذج وقيدُ `Meta` — تعريفٌ لا قراءة.
DEFINITION = re.compile(r"models\.(?:DateTimeField|F)\(|F\(\"(?:starts_at|ends_at)\"\)")


def _strip_comments(source: str) -> str:
    """يُفرغ التعليقات والنصوص، فلا يرسب الملفُّ على شرحه لنفسه.

    كُتب هنا حارسٌ قبلَه رسب على تعليقه هو، فأثبت أن الشرح داخل الملفّ يُقرأ
    شيفرةً ما لم يُنزَع.
    """
    out: list[str] = []
    for line in source.splitlines():
        stripped = line.split("#", 1)[0]
        out.append(stripped)
    return "\n".join(out)


def offences() -> tuple[list[str], int]:
    found: list[str] = []
    inside_engine = 0

    for path in sorted(BACKEND.rglob("*.py")):
        if set(path.parts) & SKIP_PARTS:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "starts_at" not in source and "ends_at" not in source:
            continue

        for number, line in enumerate(_strip_comments(source).splitlines(), start=1):
            if DEFINITION.search(line):
                continue
            if not (COMPARISON.search(line) or LOOKUP.search(line)):
                continue
            if path == ENGINE:
                inside_engine += 1
                continue
            found.append(
                f"{path.relative_to(ROOT)}:{number}: "
                "قراءةٌ ثانية لساعة المزاد — نادِ "
                "`engine.phase` أو `has_started`/`has_finished` "
                f"بدلاً من: {line.strip()}"
            )

    return found, inside_engine


def main() -> int:
    found, inside_engine = offences()

    if inside_engine == 0:
        print(
            f"لا قراءةَ ساعةٍ واحدة في {ENGINE.relative_to(ROOT)} — "
            "نُقل المحرّك أو أُفرغ، والفحص يحرس العدم.",
            file=sys.stderr,
        )
        return 1

    if found:
        print("ساعةُ المزاد تُقرأ خارج المحرّك:", file=sys.stderr)
        for item in found:
            print("  " + item, file=sys.stderr)
        print(
            f"\n{len(found)} مخالفة. الجوابُ الواحد في "
            f"{ENGINE.relative_to(ROOT)}: `phase()` تعرف الفرق بين "
            "«جارٍ» و«انتهى وقته ولم يُغلَق»، والعمودُ وحده لا يعرفه.",
            file=sys.stderr,
        )
        return 1

    print(f"ساعةُ المزاد تُقرأ في المحرّك وحده — {inside_engine} قراءة.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
