"""T806 — the export uploads again and changes nothing.

That round trip is the acceptance criterion and the reason one writer produces
both files (`apps.core.sheets`, T410). In v1 the export was built by one piece
of code and the import expected another's shape, so a file downloaded from the
console could not be uploaded back to it — and the way people compensated was to
retype rows.

The rest of this file is about the two things a screen adds to logic that phase
005 already tested: **every** rejection reaches the operator as a sheet they can
work from, and a preview shows what would happen without doing it.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.console.importexport import MAX_UPLOAD_BYTES
from apps.core.models import AuditLog
from apps.core.permissions import Role
from apps.core.sheets import Sheet

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str = "966500000021") -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def importer(client):
    user = staff(Role.OPERATIONS)
    client.force_login(user)
    return user


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=880,
        title="مزاد الاستيراد",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


def a_car(auction: Auction, lot: int, **extra) -> Vehicle:
    fields = {
        "auction": auction,
        "lot_number": lot,
        "make": "تويوتا",
        "model": "كامري",
        "year": 2020,
        "state": VehicleState.LISTED,
        "reserve_price": Decimal("55000.00"),
        "odometer_km": 90000,
    }
    fields.update(extra)
    return Vehicle.objects.create(**fields)


def as_upload(payload: bytes, name: str = "vehicles.xlsx"):
    handle = BytesIO(payload)
    handle.name = name
    return handle


def snapshot() -> list[tuple]:
    """Every field the sheet round-trips, for every car, in a stable order."""
    return list(
        Vehicle.objects.order_by("auction_id", "lot_number").values_list(
            "auction_id",
            "lot_number",
            "make",
            "model",
            "year",
            "reserve_price",
            "odometer_km",
            "transmission",
            "fuel_type",
            "condition",
            "plate_type",
            "vin",
            "plate_number",
        )
    )


# ---------------------------------------------------------------------------
# The round trip — T806's acceptance criterion
# ---------------------------------------------------------------------------


def test_a_download_uploads_again_and_changes_no_row(client, importer, auction):
    """One writer produces both files, so this holds by construction.

    It is asserted anyway: "by construction" is a claim about today's code, and
    the whole reason the check exists is that v1's two halves drifted.
    """
    for lot in range(1, 6):
        a_car(auction, lot, make=f"ماركة{lot}")

    before = snapshot()

    downloaded = client.get(reverse("console:vehicles-export")).content
    response = client.post(
        reverse("console:vehicles-import"), {"sheet": as_upload(downloaded)}
    )

    assert response.status_code == 200
    report = response.context["report"]
    assert report.rejections == [], f"رُفضت صفوف من ملفنا: {report.rejections}"
    assert report.changed == 0, "الرفع غيّر صفوفاً وهو نفس الملف"
    assert snapshot() == before


def test_the_export_honours_the_filter(client, importer, auction):
    """An operator who searched for one auction and pressed export wants those.

    v1 exported everything every time, so the file was useless and people copied
    rows out of the screen by hand.
    """
    other = Auction.objects.create(
        number=881,
        title="مزاد آخر",
        starts_at=timezone.now(),
        ends_at=timezone.now() + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )
    a_car(auction, 1, make="هوندا")
    a_car(other, 1, make="نيسان")

    payload = client.get(
        reverse("console:vehicles-export"), {"auction": auction.number}
    ).content
    rows = Sheet.read(payload).records()

    makes = {row.get("الماركة") for row in rows}
    assert makes == {"هوندا"}


def test_the_export_is_a_real_xlsx(client, importer, auction):
    """I5: it opens in Excel without a warning, which means a real zip archive."""
    a_car(auction, 1)

    response = client.get(reverse("console:vehicles-export"))

    assert response["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
    assert response.content[:2] == b"PK"
    assert "attachment" in response["Content-Disposition"]


# ---------------------------------------------------------------------------
# The upload
# ---------------------------------------------------------------------------


def sheet_with(rows: list[dict]) -> bytes:
    headers = list(rows[0])
    return Sheet(
        headers=headers, rows=[[str(row[h]) for h in headers] for row in rows]
    ).to_xlsx()


def test_an_upload_creates_the_rows_it_describes(client, importer, auction):
    payload = client.get(reverse("console:vehicles-export")).content
    sheet = Sheet.read(payload)

    a_car(auction, 1)
    fresh = client.get(reverse("console:vehicles-export")).content
    Vehicle.objects.all().delete()

    response = client.post(
        reverse("console:vehicles-import"), {"sheet": as_upload(fresh)}
    )

    assert response.context["report"].changed == 1
    assert Vehicle.objects.count() == 1
    del sheet


def test_a_preview_reports_what_would_happen_and_writes_nothing(
    client, importer, auction
):
    """An operator uploading four hundred rows wants to see it first.

    Nothing in v1 had a preview, and the way people compensated was to upload
    ten rows at a time.
    """
    a_car(auction, 1)
    payload = client.get(reverse("console:vehicles-export")).content
    Vehicle.objects.all().delete()

    response = client.post(
        reverse("console:vehicles-import"), {"sheet": as_upload(payload), "dry_run": "1"}
    )

    assert response.context["report"].changed == 1
    assert Vehicle.objects.count() == 0, "المعاينة كتبت في القاعدة"
    assert not AuditLog.objects.filter(action="console.import_vehicles").exists()


def test_every_rejected_row_is_named_not_the_first_five(client, importer, auction):
    """v1 stopped after five and said "and 95 more errors"."""
    rows = [
        {
            "رقم المزاد": str(auction.number),
            "رقم اللوت": str(lot),
            "الماركة": "تويوتا",
            "الموديل": "كامري",
            "السنة": "ليست سنة",
        }
        for lot in range(1, 13)
    ]

    response = client.post(
        reverse("console:vehicles-import"), {"sheet": as_upload(sheet_with(rows))}
    )
    report = response.context["report"]

    assert len(report.rejections) == 12
    body = response.content.decode()
    for rejection in report.rejections:
        assert str(rejection.row) in body


def test_the_rejections_download_as_a_sheet(client, importer, auction):
    """An operator fixes them in the file they already have."""
    rows = [
        {
            "رقم المزاد": str(auction.number),
            "رقم اللوت": "1",
            "الماركة": "تويوتا",
            "الموديل": "كامري",
            "السنة": "ليست سنة",
        }
    ]

    response = client.post(
        reverse("console:vehicles-import-errors"),
        {"sheet": as_upload(sheet_with(rows))},
    )

    assert response.content[:2] == b"PK"
    assert "rejections.xlsx" in response["Content-Disposition"]


def test_a_file_that_is_not_a_sheet_is_a_message_not_a_500(client, importer):
    """A PDF renamed, a corrupt upload. The operator can fix a file."""
    response = client.post(
        reverse("console:vehicles-import"),
        {"sheet": as_upload(b"this is not a spreadsheet at all", "notes.xlsx")},
        follow=True,
    )

    assert response.status_code == 200
    assert "تعذّرت قراءة الملف" in response.content.decode()


def test_an_upload_with_no_file_says_so(client, importer):
    response = client.post(reverse("console:vehicles-import"), {}, follow=True)

    assert "اختر ملفاً أولاً" in response.content.decode()


def test_an_oversized_upload_is_refused_before_it_is_read(client, importer):
    """A spreadsheet of the whole fleet, or an image somebody renamed."""
    response = client.post(
        reverse("console:vehicles-import"),
        {"sheet": as_upload(b"x" * (MAX_UPLOAD_BYTES + 1))},
        follow=True,
    )

    assert "أكبر من الحدّ" in response.content.decode()


def test_a_real_import_is_recorded_with_its_reason(client, importer, auction):
    a_car(auction, 1)
    payload = client.get(reverse("console:vehicles-export")).content
    Vehicle.objects.all().delete()

    client.post(
        reverse("console:vehicles-import"),
        {"sheet": as_upload(payload), "reason": "دفعة الشريك الأسبوعية"},
    )

    # One entry per car, not one per upload: an audit row that names no row
    # cannot answer "who last touched *this* car", which is the question a
    # partner asks about their own lot.
    entry = AuditLog.objects.get(action="console.import_vehicles")
    assert entry.actor_id == importer.pk
    assert entry.note == "دفعة الشريك الأسبوعية"
    assert entry.entity_id == str(Vehicle.objects.get().pk)
    assert entry.after["batch"]["created"] == 1


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_reading_the_screens_does_not_admit_you_to_the_import(client, auction):
    """`auctions.import` is its own capability: a bulk write is its own trust."""
    reader = staff(Role.SUPPORT, phone="966500000022")
    client.force_login(reader)

    assert client.get(reverse("console:vehicles-export")).status_code == 403
    assert client.get(reverse("console:vehicles-import")).status_code == 403


def test_the_import_page_is_in_the_sidebar_for_those_who_have_it(client, importer):
    body = client.get(reverse("console:home")).content.decode()

    assert "استيراد المركبات" in body
