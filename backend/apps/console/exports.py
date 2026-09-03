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
from django.utils import timezone

from apps.core.sheets import Sheet

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: The query parameter that turns a list screen into a download.
PARAM = "export"


def wants_export(request) -> bool:
    """Whether this request is asking for the file rather than the page."""
    return request.GET.get(PARAM) == "xlsx"


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
    response["Content-Disposition"] = f'attachment; filename="{name}-{stamp}.xlsx"'
    return response


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


def _text(value: Any) -> str:
    if value is None:
        return ""
    if value is True or value is False:
        return "نعم" if value else "لا"
    return str(value)


__all__ = [
    "PARAM",
    "export",
    "sheet_response",
    "wants_export",
    "workbook_response",
]
