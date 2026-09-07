"""T410 — one reader, one writer, and the format read from the content.

The cases here are the ones that broke files in v1: a workbook renamed to
`.csv`, a CSV exported from Excel with a BOM, a lot number that came back as
`7.0` because a spreadsheet stores every number as a double, and a VIN that
Excel decided was scientific notation.

No database: this module touches no model.
"""

from __future__ import annotations

import pytest

from apps.core.sheets import Sheet, SheetError


def test_a_workbook_survives_a_round_trip():
    original = Sheet(headers=["أ", "ب"], rows=[["1", "قيمة"], ["2", ""]])

    back = Sheet.read(original.to_xlsx())

    assert back.headers == original.headers
    assert back.rows == original.rows


def test_a_csv_survives_a_round_trip():
    original = Sheet(headers=["أ", "ب"], rows=[["1", "قيمة، بفاصلة"]])

    back = Sheet.read(original.to_csv())

    assert back.rows == original.rows


def test_the_format_is_decided_by_content_not_by_name():
    """A workbook someone renamed to `.csv` still reads as a workbook — the
    bytes are what we have, and the name is what people get wrong."""
    workbook_bytes = Sheet(headers=["أ"], rows=[["1"]]).to_xlsx()

    assert Sheet.read(workbook_bytes).rows == [["1"]]


def test_a_csv_with_a_bom_reads_cleanly():
    """Excel writes the BOM and would not open the file without it."""
    data = Sheet(headers=["الماركة"], rows=[["تويوتا"]]).to_csv()

    assert data.startswith(b"\xef\xbb\xbf")
    assert Sheet.read(data).headers == ["الماركة"]


def test_a_number_typed_into_excel_comes_back_as_it_was_written():
    """openpyxl hands back `7.0` for a cell containing 7; writing that into a
    lot number column would change a row that nobody edited."""
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.append(["رقم اللوت"])
    workbook.active.append([7])

    import io

    buffer = io.BytesIO()
    workbook.save(buffer)

    assert Sheet.read(buffer.getvalue()).rows == [["7"]]


def test_short_rows_are_padded_rather_than_refused():
    """Editors drop trailing empty cells; refusing the file would reject
    something a person can produce by pressing Enter."""
    data = "أ,ب,ج\r\n1,2\r\n".encode("utf-8-sig")

    assert Sheet.read(data).rows == [["1", "2", ""]]


def test_blank_rows_are_dropped():
    data = "أ,ب\r\n1,2\r\n,\r\n".encode("utf-8-sig")

    assert Sheet.read(data).rows == [["1", "2"]]


def test_records_pair_each_cell_with_its_header():
    sheet = Sheet(headers=["أ", "ب"], rows=[["1", "2"]])

    assert sheet.records() == [{"أ": "1", "ب": "2"}]


def test_an_empty_file_is_refused_in_arabic():
    with pytest.raises(SheetError, match="فارغ"):
        Sheet.read(b"")


def test_a_file_with_only_a_header_reads_as_zero_rows():
    assert Sheet.read("أ,ب\r\n".encode("utf-8-sig")).rows == []


def test_binary_that_is_not_a_workbook_is_refused_with_a_reason():
    with pytest.raises(SheetError):
        Sheet.read(b"\xff\xfe\x00\x01\x02rubbish")
