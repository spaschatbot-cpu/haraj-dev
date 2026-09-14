"""كل قائمة تُصدَّر — one download, for every list in the console. T817 / I5.

A list screen answers a question on the screen; an export answers the same
question in a file somebody sends to an accountant, a partner, or the owner's
phone. In v1 four screens grew four exports, each with its own quoting and its
own encoding, and the file one produced could not be opened beside the file the
next one produced. `ops/checks/one_sheet_writer.py` now refuses a second writer,
so this module is the console's whole answer: build a :class:`Sheet`, hand it to
:func:`sheet_response`.

Two rules, both learned the hard way
------------------------------------
**The export honours the filter.** Whoever searched for one auction's cars and
pressed تصدير wants those cars. v1 exported the whole table every time, so the
file was useless and people copied rows out of the screen by hand — which is
worse than no export, because it looks like a feature.

**A real `.xlsx`, never a CSV wearing the extension.** `Sheet.to_xlsx` writes an
actual workbook with every cell formatted as text, so Excel opens it without a
warning dialog and hands back the strings it was given — a VIN stays a VIN
rather than becoming scientific notation.

Why `?export=xlsx` and not a separate url per list
--------------------------------------------------
The filter is already in the query string. A second endpoint would have to
re-read and re-apply every filter its list screen applies, which is the same
"two places that agree until one is edited" that `navigation.PAGES` exists to
prevent — and the first thing to drift would be exactly the honouring of the
filter that this file is here to guarantee.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.core.sheets import Sheet

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: The query parameter that turns a list screen into a download.
PARAM = "export"

#: سقفُ صفوفِ الملفّ الواحد — **رفضٌ صريح، لا قصٌّ صامت**. T901.
#:
#: القياسُ الذي جاء منه الرقم (كتالوج السيارات على `haraj2_t307`، ١٤ سبتمبر
#: ٢٠٢٦): بلا مرشّح ⇐ **١٢٬٩٩٠ صفّاً في ٧٤٣٤ms و١٣٢٢ كيلوبايت**؛ وبمرشّحٍ
#: نصّيّ ⇐ ٢٥١ms و٢٨ كيلوبايت. و:class:`~apps.core.sheets.Sheet` تبني الصفوفَ
#: **كلَّها في الذاكرة** قبل أن تكتب بايتاً واحداً، فضغطتان متزامنتان على
#: قاعدةٍ أكبر بابُ استنزاف.
#:
#: ولماذا خمسةُ آلافٍ لا اثنا عشر ألفاً ولا خمسمئة — **مقيسٌ على نفس المسار**
#: (`export_table` على الكتالوج، `t307`، ١٤ سبتمبر ٢٠٢٦):
#: ٥٬٠٠٠ صفٍّ ⇐ **٢٩٦٢ms و٥٦٢ كيلوبايت** · ١٢٬٩٩٣ صفّاً ⇐ **٧٩٤٠ms و١٤٦٣
#: كيلوبايت**. فثلاثُ ثوانٍ ملفٌّ ينتظره الموظّفُ ولا يظنّ الشاشةَ معلّقة،
#: وثمانٍ ليست كذلك.
#: وهو أوسعُ من أيّ مزادٍ حقيقيّ بكثير: أكبرُ ثلاثة مزاداتٍ في `t307` هي
#: ٣٨٦ و٣٥٧ و٣٤٤ مركبة. فالسقفُ لا يصيب عملاً يوميّاً — يصيب «صدّر كلَّ
#: شيء» وحدَها.
#:
#: **والمقصوصُ صامتاً أسوأ من المرفوض**: ملفٌّ فيه خمسةُ آلافٍ من اثني عشر
#: ألفاً يُفتح ويُقرأ كاملاً ويُطابَق به كشفٌ بنكيّ، ولا شيء فيه يقول إنّ ثلثيه
#: ناقص. فالسقفُ يردّ صفحةً تقول العددَ والسقفَ وتطلب ترشيحاً — والمرشّحاتُ
#: تعمل فعلاً (٢٥١ms بمرشّح)، فليس حرماناً.
MAX_ROWS = 5000


def wants_export(request) -> bool:
    """Whether this request is asking for the file rather than the page."""
    return request.GET.get(PARAM) == "xlsx"


def oversize(rows) -> int:
    """عددُ الصفوف إن تجاوز :data:`MAX_ROWS`، وإلّا صفر.

    العدُّ استعلامٌ واحدٌ رخيص (قِيس: ٠٫٠٠٤ ثانيةٍ على ١٢٬٩٨١ صفّاً — جانغو
    يُسقط الاستعلاماتِ الفرعيّةَ غيرَ المستعملة من `COUNT`)، وأرخصُ بكثيرٍ من
    بناء اثني عشرَ ألفَ صفٍّ في الذاكرة ثم رميها.
    """
    count = rows.count()
    return count if count > MAX_ROWS else 0


def refuse(request, count: int) -> HttpResponse:
    """صفحةٌ تقول: النتيجةُ أكبرُ من السقف، رشّح ثمّ صدّر.

    و`400` لا `200`: الطلبُ لم يُنفَّذ، وصفحةٌ بحالة نجاحٍ تحمل اعتذاراً هي ما
    يجعل نصّاً كهذا يُقرأ «تنبيهٌ» ويُتجاوَز.
    """
    # الرقمان مفصولان بفواصلِ آلافٍ **هنا لا في القالب**، كما تفعل بطاقاتُ
    # اللوحة (`f"{n:,}"`): «12993» تُقرأ بعدّ الأرقام، و«12,993» تُقرأ لمحةً.
    return render(
        request,
        "console/export_too_many.html",
        {"count": f"{count:,}", "cap": f"{MAX_ROWS:,}"},
        status=400,
    )


def workbook_response(payload: bytes, *, name: str) -> HttpResponse:
    """Wrap already-built workbook bytes as a download.

    Separate from :func:`sheet_response` for one caller: the vehicles export is
    phase 005's `export_vehicles`, because that file is the *import's input*
    (T806) and a second column list here would produce a file that cannot be
    uploaded back into the screen it came from.

    The timestamp is in the filename because these files live in inboxes and on
    desktops for months, and «الفواتير.xlsx» twice in one folder is two files
    nobody can tell apart — including the person who exported them.
    """
    stamp = timezone.localtime(timezone.now()).strftime("%Y%m%d-%H%M")
    response = HttpResponse(payload, content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = disposition(name, stamp)
    return response


def disposition(name: str, stamp: str) -> str:
    """`Content-Disposition` لملفٍّ اسمُه عربيّ — بترميز RFC 5987.

    الترويسة تحمل بايتات لاتينية فقط. واسمٌ عربيٌّ يُوضع فيها كما هو يخرج من
    جانغو مشفَّراً بـRFC 2047 (`=?utf-8?b?…?=`) — **وهو ترميزٌ لرؤوس البريد لا
    تفهمه المتصفّحات هنا**، فيصل الملفَّ إلى سطح المكتب باسمٍ هو تلك السلسلة
    حرفياً. وكل تصديرٍ عربيّ الاسم كان يخرج هكذا بلا أن يُلاحَظ، لأن الاختبار
    كان يمرّ على أسماءٍ إنجليزية وحدها.

    فالصيغة هنا هي التي نصّ عليها RFC 6266: `filename` لاتينيّ احتياطيّ لمن لا
    يفهم، و`filename*=UTF-8''…` هو الاسم الحقيقيّ. والمتصفّح يفضّل الثاني حين
    يجده — وكلُّ متصفّحٍ حيٍّ يفهمه.
    """
    from urllib.parse import quote

    # الاحتياطيّ لا يُترجَم ولا يُنقحَر: نقحرةُ العربية إلى لاتينية تخترع اسماً
    # لا يعرفه أحد. ويحمل الختم كاملاً، فملفّان في مجلّدٍ واحد يبقيان مميَّزين
    # حتى عند من لا يفهم `filename*` — وذلك هو سببُ الختم أصلاً.
    ascii_name = name if name.isascii() else "export"
    quoted = quote(f"{name}-{stamp}.xlsx", safe="")
    return (
        f"attachment; filename=\"{ascii_name}-{stamp}.xlsx\"; filename*=UTF-8''{quoted}"
    )


def sheet_response(sheet: Sheet, *, name: str) -> HttpResponse:
    """One workbook from a :class:`Sheet`, named with the moment it was taken."""
    return workbook_response(sheet.to_xlsx(), name=name)


def export(
    rows: Iterable[Any],
    *,
    name: str,
    headers: list[str],
    cell: Callable[[Any], list[Any]],
) -> HttpResponse:
    """Render ``rows`` through ``cell`` into a downloadable workbook.

    Every value is stringified here rather than in each caller. A `None` becomes
    an empty cell and a `Decimal` becomes its own digits — never a float, which
    would put an amount through a binary approximation on its way to a file
    somebody reconciles against the ledger (Article 3-2).
    """
    sheet = Sheet(
        headers=headers,
        rows=[[_text(value) for value in cell(row)] for row in rows],
    )
    return sheet_response(sheet, name=name)


def export_table(rows: Iterable[Any], *, name: str, columns) -> HttpResponse:
    """تصديرٌ بأعمدةٍ ثنائيّة `(عنوان, دالّة)` — العنوانُ وخليّتُه في سطرٍ واحد.

    و:func:`export` بقائمتين متوازيتين تبقى لمن لا يحجب عموداً. أمّا حيث
    تُحذف أعمدةٌ بحسب صلاحيةِ القارئ (`sensitive.columns_for`) فقائمتان
    تتفارقان عند أوّل حذف: تُحذف الخليّةُ ويبقى عنوانُها، فيخرج الملفُّ
    بعنوانٍ فوق قيمةِ غيره — خطأٌ لا يُرى إلّا بفتح الملفّ ومقارنتِه بالشاشة.
    """
    return export(
        rows,
        name=name,
        headers=[header for header, _ in columns],
        cell=lambda row: [getter(row) for _, getter in columns],
    )


def _text(value: Any) -> str:
    if value is None:
        return ""
    if value is True or value is False:
        return "نعم" if value else "لا"
    return str(value)


__all__ = [
    "MAX_ROWS",
    "PARAM",
    "export",
    "export_table",
    "oversize",
    "refuse",
    "sheet_response",
    "wants_export",
    "workbook_response",
]
