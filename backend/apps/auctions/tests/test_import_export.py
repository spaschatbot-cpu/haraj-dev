"""E5 and T412 — the file goes out and comes back without moving anything.

"Zero rows changed" is checked against the database, not against the report:
`updated_at` is compared before and after, because a re-save that writes
identical values still moves that column, and a person auditing "who touched
this car last" would see the import instead of the truth.

The rejection half is the other half of the same idea. An operator who
uploads a hundred bad rows gets a hundred reasons, not the first five and a
count — v1's five-then-"and 95 more" is why files went round the office one
fix at a time.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.auctions.importexport import (
    COLUMNS,
    VehicleImportError,
    export_sheet,
    export_vehicles,
    import_vehicles,
)
from apps.auctions.models import Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.core.sheets import Sheet

pytestmark = pytest.mark.django_db


@pytest.fixture
def fleet(make_auction, make_vehicle, partner):
    auction = make_auction(state=AuctionState.LIVE)
    return [
        make_vehicle(
            auction,
            state=VehicleState.LISTED,
            lot_number=1,
            make="تويوتا",
            model="كامري",
            year=2022,
            vin="JT1234567890",
            odometer_km=140_000,
            transmission="automatic",
            fuel_type="petrol",
            condition="running",
            reserve_price=Decimal("50000.00"),
        ),
        make_vehicle(
            auction,
            state=VehicleState.BIDDING,
            lot_number=2,
            make="نيسان",
            model="التيما",
            year=2019,
            reserve_price=None,
            owner_company=partner.company,
        ),
        make_vehicle(
            auction,
            state=VehicleState.WITHDRAWN,
            lot_number=3,
            make="هيونداي",
            model="سوناتا",
            year=2020,
            odometer_km=0,
        ),
    ]


def _snapshot():
    return {
        vehicle.pk: (
            vehicle.updated_at,
            vehicle.make,
            vehicle.model,
            vehicle.year,
            vehicle.vin,
            vehicle.odometer_km,
            vehicle.reserve_price,
            vehicle.state,
        )
        for vehicle in Vehicle.objects.all()
    }


# ---------------------------------------------------------------------------
# E5 — the round trip
# ---------------------------------------------------------------------------


def test_export_then_reupload_changes_no_row(fleet):
    before = _snapshot()

    report = import_vehicles(export_vehicles(Vehicle.objects.all()))

    assert report.changed == 0
    assert len(report.unchanged) == len(fleet)
    assert report.rejections == []
    assert _snapshot() == before


def test_the_round_trip_survives_a_csv_of_the_same_sheet(fleet):
    """Format is decided by content, so an operator who saves the workbook as
    CSV in Excel still gets a file the system accepts."""
    before = _snapshot()

    report = import_vehicles(export_sheet(Vehicle.objects.all()).to_csv())

    assert report.changed == 0
    assert _snapshot() == before


def test_an_optional_column_is_absent_when_no_row_carries_it(make_auction, make_vehicle):
    auction = make_auction(state=AuctionState.LIVE)
    make_vehicle(auction, state=VehicleState.LISTED, vin="", reserve_price=None)

    sheet = export_sheet(Vehicle.objects.all())

    assert "رقم الهيكل" not in sheet.headers
    assert "سعر الوقوف" not in sheet.headers
    assert "الماركة" in sheet.headers  # a required column is always written


def test_an_optional_column_appears_when_one_row_carries_it(fleet):
    sheet = export_sheet(Vehicle.objects.all())

    assert "رقم الهيكل" in sheet.headers
    assert "الممشى" in sheet.headers


def test_the_file_separates_the_vehicle_state_from_the_display_state(fleet):
    sheet = export_sheet(Vehicle.objects.all())
    rows = sheet.records()

    assert "حالة المركبة" in sheet.headers
    assert "حالة العرض" in sheet.headers
    withdrawn = next(r for r in rows if r["رقم اللوت"] == "3")
    assert withdrawn["حالة المركبة"] == "مسحوبة"
    assert withdrawn["حالة العرض"] == "غير معروضة"


def test_state_is_never_taken_back_in_from_a_file(fleet):
    """A spreadsheet cannot award a car. `services` is the only writer."""
    sheet = export_sheet(Vehicle.objects.all())
    index = sheet.headers.index("حالة المركبة")
    for row in sheet.rows:
        row[index] = "مرسّاة"

    report = import_vehicles(sheet.to_xlsx())

    assert report.changed == 0
    assert set(Vehicle.objects.values_list("state", flat=True)) == {
        VehicleState.LISTED,
        VehicleState.BIDDING,
        VehicleState.WITHDRAWN,
    }


# ---------------------------------------------------------------------------
# Real edits still land
# ---------------------------------------------------------------------------


def test_an_edited_cell_updates_exactly_that_row(fleet):
    sheet = export_sheet(Vehicle.objects.all())
    column = sheet.headers.index("سعر الوقوف")
    sheet.rows[0][column] = "77000.00"

    report = import_vehicles(sheet.to_xlsx())

    assert len(report.updated) == 1
    assert len(report.unchanged) == 2
    assert Vehicle.objects.get(pk=fleet[0].pk).reserve_price == Decimal("77000.00")


def test_a_new_lot_number_creates_a_draft(fleet, make_auction):
    sheet = export_sheet(Vehicle.objects.all())
    row = list(sheet.rows[0])
    row[sheet.headers.index("رقم اللوت")] = "99"
    sheet.rows.append(row)

    report = import_vehicles(sheet.to_xlsx())

    assert len(report.created) == 1
    created = Vehicle.objects.get(lot_number=99)
    assert created.state == VehicleState.DRAFT  # never listed by a file


def test_choices_are_read_back_from_their_arabic_labels(fleet):
    sheet = export_sheet(Vehicle.objects.all())
    sheet.rows[1][sheet.headers.index("ناقل الحركة")] = "عادي"

    import_vehicles(sheet.to_xlsx())

    assert Vehicle.objects.get(pk=fleet[1].pk).transmission == "manual"


# ---------------------------------------------------------------------------
# T412 — every rejected row is named
# ---------------------------------------------------------------------------


def _bad_sheet(auction_number: int, count: int) -> Sheet:
    headers = ["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع"]
    rows = [
        [str(auction_number), str(1000 + i), "تويوتا", "كامري", "سنة غلط"]
        for i in range(count)
    ]
    return Sheet(headers=headers, rows=rows)


def test_a_hundred_bad_rows_produce_a_hundred_reasons(make_auction):
    auction = make_auction(state=AuctionState.LIVE)

    report = import_vehicles(_bad_sheet(auction.number, 100).to_xlsx())

    assert len(report.rejections) == 100
    assert {r.row for r in report.rejections} == set(range(2, 102))
    assert all("سنة الصنع" in r.reason for r in report.rejections)
    assert Vehicle.objects.count() == 0


def test_the_rejection_report_is_itself_a_sheet(make_auction):
    auction = make_auction(state=AuctionState.LIVE)

    report = import_vehicles(_bad_sheet(auction.number, 3).to_xlsx())

    assert report.to_sheet().headers == ["الصف", "اللوت", "السبب"]
    assert len(report.to_sheet().rows) == 3
    assert "3 مرفوضة" in report.summary()


def test_one_bad_row_does_not_stop_the_good_ones(fleet, make_auction):
    sheet = export_sheet(Vehicle.objects.all())
    sheet.rows[1][sheet.headers.index("سنة الصنع")] = "لا شيء"

    report = import_vehicles(sheet.to_xlsx())

    assert len(report.rejections) == 1
    assert len(report.unchanged) == 2


def test_a_row_naming_an_unknown_auction_is_rejected_with_its_number(fleet):
    sheet = export_sheet(Vehicle.objects.all())
    sheet.rows[0][sheet.headers.index("رقم المزاد")] = "4242"

    report = import_vehicles(sheet.to_xlsx())

    assert len(report.rejections) == 1
    assert "4242" in report.rejections[0].reason


def test_a_new_row_missing_a_required_field_says_which(make_auction):
    auction = make_auction(state=AuctionState.LIVE)
    sheet = Sheet(
        headers=["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع"],
        rows=[[str(auction.number), "5", "تويوتا", "", "2022"]],
    )

    report = import_vehicles(sheet.to_xlsx())

    assert len(report.rejections) == 1
    assert "الطراز" in report.rejections[0].reason


def test_a_file_without_the_identity_columns_is_refused_as_a_whole(make_auction):
    """Not a row problem — there is no way to know what any row refers to."""
    sheet = Sheet(headers=["الماركة", "الطراز"], rows=[["تويوتا", "كامري"]])

    with pytest.raises(VehicleImportError, match="رقم المزاد"):
        import_vehicles(sheet.to_xlsx())


def test_an_unknown_column_is_reported_and_ignored(fleet):
    sheet = export_sheet(Vehicle.objects.all())
    sheet.headers.append("ملاحظات المشرف")
    for row in sheet.rows:
        row.append("لا شيء")

    report = import_vehicles(sheet.to_xlsx())

    assert report.ignored_headers == ["ملاحظات المشرف"]
    assert report.changed == 0


def test_every_writable_column_can_be_read_back(fleet):
    """The two directions are one definition; this asserts the pairing."""
    for column in COLUMNS:
        if column.attribute is not None:
            assert column.read is not None, column.header
