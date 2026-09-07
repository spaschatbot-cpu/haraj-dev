"""قراءةُ نسخة v1 من ملفّ `mysqldump` مباشرةً — بلا خادمٍ ولا كلمة مرور. T854.

لماذا من الملفّ لا من خادم
==========================
الطريقُ المعتاد أن تُستورد النسخةُ في MariaDB ثم تُقرأ بـSQL. وهو يحتاج
كلمةَ مرورٍ لا أملكها، وخادماً يعمل، وثلاثةَ جيجابايت على القرص مرّتين —
مرّةً في الملفّ ومرّةً في الجداول.

والملفُّ نفسُه **هو** البيانات: `mysqldump` يكتب `INSERT INTO ... VALUES
(...),(...)` وترتيبُ القيم هو ترتيبُ الأعمدة في `CREATE TABLE` فوقه. فقراءتُه
تدفّقاً تُعطي الصفوفَ نفسَها، وتنتهي بلا أثرٍ يُنظَّف.

وثمنُه المعروف: لا فهارس ولا `WHERE`. من أراد صفّاً بعينه يقرأ الملفَّ كلَّه.
وهذا مقبولٌ لأن الاستيراد يمرّ على كل صفٍّ مرّةً واحدة أصلاً.

ما يفكّه هذا المحلّل، وما لا يفكّه
==================================
يفكّ ما يكتبه `mysqldump` فعلاً: نصوصاً بين علامتين مفردتين، وهروبَ
`\\'` و`\\"` و`\\\\` و`\\n` و`\\r` و`\\t` و`\\0`، و`NULL` عارية، وأرقاماً،
وثوابتَ ثنائية `_binary '...'`.

ولا يفكّ SQL عامّاً: لا دوالَّ ولا تعابيرَ ولا استعلاماتٍ متداخلة. ونسخةُ
`mysqldump` لا تحوي منها شيئاً — وإن حوت، رمى المحلِّل بدل أن يخمّن.

**والترميز `utf8mb4` مُصرَّحٌ عند الفتح.** بايتات العربية في الملفّ هي بايتاتُ
`utf8mb4`، وقراءتُها بترميز النظام (cp1256 على ويندوز) لا تفشل — تنجح وتُعطي
`Ø¹Ø¨Ø¯`. وذلك عطلٌ لا يظهر إلا بعد أشهر حين يفتح موظّفٌ شاشةً.
"""

from __future__ import annotations

import gzip
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

__all__ = ["columns_of", "count_rows", "read_table", "table_names"]

#: `CREATE TABLE \`name\` (` — بداية تعريفِ جدول.
_CREATE = re.compile(r"^CREATE TABLE `([^`]+)` \($")

#: سطرُ عمودٍ داخل التعريف: `` `name` type ... `` — والقيودُ تبدأ بكلماتٍ
#: محجوزة، فتُستثنى بالاسم لا بالترتيب.
_COLUMN = re.compile(r"^\s+`([^`]+)`\s")
_NOT_A_COLUMN = re.compile(r"^\s+(PRIMARY|UNIQUE|KEY|CONSTRAINT|FULLTEXT|SPATIAL|CHECK)")

#: `INSERT INTO \`name\` VALUES (…),(…);`
_INSERT = re.compile(r"^INSERT INTO `([^`]+)` VALUES ")

#: هروبُ `mysqldump` — وهو محدودٌ ومعروف.
_UNESCAPE = {
    "0": "\0",
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "Z": "\x1a",
    "\\": "\\",
    "'": "'",
    '"': '"',
}


def _open(path: Path):
    """يفتح النسخةَ بترميزها المُصرَّح، مضغوطةً كانت أو لا."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="strict", newline="")
    return path.open("r", encoding="utf-8", errors="strict", newline="")


def table_names(path: Path) -> list[str]:
    """كلُّ جدولٍ في النسخة، بترتيب ظهوره."""
    names: list[str] = []
    with _open(path) as handle:
        for line in handle:
            found = _CREATE.match(line)
            if found:
                names.append(found.group(1))
    return names


def columns_of(path: Path, table: str) -> list[str]:
    """أعمدةُ الجدول **بترتيبها**، وهو ترتيبُ القيم في `INSERT`.

    الترتيبُ هو كلُّ شيء هنا: `mysqldump` لا يكتب أسماءَ الأعمدة مع القيم،
    فصفٌّ يُقرأ بترتيبٍ خاطئ يضع رقمَ الهوية في خانة الجوّال — وينجح.
    """
    inside = False
    columns: list[str] = []
    with _open(path) as handle:
        for line in handle:
            if not inside:
                found = _CREATE.match(line)
                if found and found.group(1) == table:
                    inside = True
                continue
            if line.startswith(")"):
                break
            if _NOT_A_COLUMN.match(line):
                continue
            found = _COLUMN.match(line)
            if found:
                columns.append(found.group(1))
    if not columns:
        raise LookupError(f"لا جدول اسمه {table!r} في النسخة")
    return columns


def _split_values(payload: str) -> Iterator[list[Any]]:
    """يفكّ `(…),(…),(…);` إلى صفوف — حرفاً حرفاً، لأن الفاصلة تقع داخل النصّ.

    و`split(",")` هنا خطأٌ صامت: عنوانٌ فيه فاصلة يقسم الصفَّ إلى صفّين
    ويُزيح كلَّ ما بعده عموداً.
    """
    index, size = 0, len(payload)
    while index < size:
        while index < size and payload[index] in " \t\r\n,":
            index += 1
        if index >= size or payload[index] == ";":
            return
        if payload[index] != "(":
            around = payload[index - 20 : index + 20]
            raise ValueError(f"صفٌّ لا يبدأ بقوس عند {index}: {around!r}")
        index += 1

        row: list[Any] = []
        field: list[str] = []
        quoted = False

        while index < size:
            char = payload[index]

            if quoted:
                if char == "\\":
                    index += 1
                    field.append(_UNESCAPE.get(payload[index], payload[index]))
                elif char == "'":
                    # `''` داخل نصٍّ اقتباسٌ مضاعف لا نهاية.
                    if index + 1 < size and payload[index + 1] == "'":
                        field.append("'")
                        index += 1
                    else:
                        quoted = False
                else:
                    field.append(char)
                index += 1
                continue

            if char == "'":
                quoted = True
                index += 1
                continue
            if char in ",)":
                row.append(_scalar("".join(field)))
                field = []
                index += 1
                if char == ")":
                    break
                continue
            field.append(char)
            index += 1

        yield row


def _scalar(raw: str) -> Any:
    """قيمةٌ خامّ من الملفّ إلى قيمةٍ في بايثون.

    النصوصُ تصل هنا مفكوكةً من علاماتها، فما بقي عارياً هو `NULL` أو رقم.
    ولا يُحوَّل الرقمُ إلى `float` هنا: مبالغُ المال تُقرأ نصّاً وتُبنى
    `Decimal` عند الاستعمال (المادة ٣-٢).
    """
    text = raw.strip()
    if text == "NULL":
        return None
    if text.startswith("_binary"):
        return text[len("_binary") :].strip()
    return text


def read_table(path: Path, table: str, *, limit: int | None = None) -> Iterator[dict]:
    """صفوفُ الجدول قواميسَ — تدفّقاً، فلا يُحمَّل الملفُّ في الذاكرة.

    ``limit`` للاستطلاع: قراءةُ عشرة صفوفٍ من جدولٍ بثلاثة عشر ألفاً لا
    تحتاج المرور على الملفّ كلّه.
    """
    names = columns_of(path, table)
    width = len(names)
    seen = 0

    with _open(path) as handle:
        for line in handle:
            found = _INSERT.match(line)
            if not found or found.group(1) != table:
                continue
            for values in _split_values(line[found.end() :]):
                if len(values) != width:
                    raise ValueError(
                        f"{table}: صفٌّ بـ{len(values)} قيمة والأعمدة {width} — "
                        "تغيّر التعريف أو انكسر التحليل"
                    )
                yield dict(zip(names, values, strict=True))
                seen += 1
                if limit is not None and seen >= limit:
                    return


def count_rows(path: Path, table: str) -> int:
    """عدُّ صفوف الجدول بلا بنائها قواميسَ."""
    return sum(1 for _ in read_table(path, table))
