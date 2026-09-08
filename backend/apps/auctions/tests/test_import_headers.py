"""T867 — مستورِدُ المركبات يقبل ملفَّ المالك كما هو.

الحراس الخمسة المطلوبة بموجب المادة 4 من CLAUDE.md:
1. ملف فيه سطر عنوان أو شعار فوق الرأس -> يُكتشف الرأس ويُستورد صحيحاً.
2. رأس بعناوين مشوّهة («الماركه»، «Make»، «رقم اللوحه»، إلخ) -> تُطابق كلها عبر المرادفات.
3. أرقام عربية-هندية (٠-٩) وفارسية (۰-۹) في الخلايا -> تُقرأ أعداداً ومبالغ صحيحة.
4. ملف بلا رأس إطلاقاً -> يُقرأ بالوضع الموضعيّ (v1 mapVehicleCsvRow).
5. صف خاطئ وسط ملف صحيح -> الباقي يُستورد، والرفض يُذكر برقم سطره الدقيق.
"""

from __future__ import annotations

from decimal import Decimal
import io

import pytest
from django.utils import timezone
from openpyxl import Workbook

from apps.auctions.importexport import (
    HEADER_SYNONYMS,
    RowRejection,
    VehicleImportError,
    import_vehicles,
    normalize_header_cell,
)
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.core.sheets import Sheet

pytestmark = pytest.mark.django_db


@pytest.fixture
def target_auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=880,
        title="مزاد الرياض التجريبي",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=2),
        state=AuctionState.LIVE,
        deposit_required=Decimal("5000.00"),
    )


def _make_xlsx(rows: list[list[str]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. سطر عنوان فوق الرأس
# ---------------------------------------------------------------------------


def test_title_row_above_header_is_ignored_and_file_imported(target_auction):
    """سطر عنوان أو شعار فوق الجدول لا يُسقط الملف — يُكتشف الرأس في أول 5 صفوف وما قبله يُهمل."""
    raw_rows = [
        ["كشف سيارات المزاد رقم 880 — تقرير قسم العمليات الميدانية"],  # سطر 1: عنوان يُهمل
        ["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع", "سعر الوقوف"],  # سطر 2: الرأس الحقيقي
        ["880", "1", "تويوتا", "كامري", "2022", "55000.00"],  # سطر 3: مركبة 1
        ["880", "2", "هيونداي", "سوناتا", "2021", "48000.00"],  # سطر 4: مركبة 2
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 2
    assert report.rejections == []
    assert Vehicle.objects.filter(auction=target_auction).count() == 2
    v1 = Vehicle.objects.get(auction=target_auction, lot_number=1)
    assert v1.make == "تويوتا"
    assert v1.model == "كامري"
    assert v1.year == 2022
    assert v1.reserve_price == Decimal("55000.00")


# ---------------------------------------------------------------------------
# 2. عناوين مشوهة ومرادفات v1
# ---------------------------------------------------------------------------


def test_distorted_headers_and_synonyms_are_all_matched(target_auction):
    """عناوين مشوهة بالتاء المربوطة أو الإنجليزية أو مرادفات v1 تُطابق الأعمدة المعيارية."""
    # «المزاد» -> رقم المزاد
    # «اللوت» -> رقم اللوت
    # «الماركه» -> الماركة
    # «الموديل» -> الطراز
    # «سنه_الصنع» -> سنة الصنع
    # «رقم اللوحه» -> رقم اللوحة
    # «starting_price» -> سعر الوقوف
    # «الحالة» -> الحالة الفنية
    raw_rows = [
        [
            "المزاد",
            "اللوت",
            "الماركه",
            "الموديل",
            "سنه_الصنع",
            "رقم اللوحه",
            "starting_price",
            "الحالة",
        ],
        [
            "880",
            "10",
            "نيسان",
            "باترول",
            "2023",
            "1234 أ ب ج",
            "120000",
            "running",
        ],
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 1, [str(r) for r in report.rejections]
    v = Vehicle.objects.get(auction=target_auction, lot_number=10)
    assert v.make == "نيسان"
    assert v.model == "باترول"
    assert v.year == 2023
    assert v.plate_number == "1234 أ ب ج"
    assert v.reserve_price == Decimal("120000.00")
    assert v.condition == "running"


def test_english_column_synonyms_are_matched(target_auction):
    """عناوين إنجليزية مستخرجة من v1 (Make, model, year, plate, chassis, reserve_price)."""
    raw_rows = [
        ["auction_number", "lot_number", "Make", "model", "year", "plate", "chassis", "reserve_price"],
        ["880", "11", "فورد", "توروس", "2020", "5678 د ه و", "1FA6P8CF9H5123456", "65000.00"],
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 1, [str(r) for r in report.rejections]
    v = Vehicle.objects.get(auction=target_auction, lot_number=11)
    assert v.make == "فورد"
    assert v.model == "توروس"
    assert v.year == 2020
    assert v.plate_number == "5678 د ه و"
    assert v.vin == "1FA6P8CF9H5123456"
    assert v.reserve_price == Decimal("65000.00")


# ---------------------------------------------------------------------------
# 3. أرقام عربية-هندية وفارسية في الخلايا
# ---------------------------------------------------------------------------


def test_arabic_indic_and_persian_digits_in_data_cells(target_auction):
    """الأرقام العربية-الهندية ٠-٩ والفارسية ۰-۹ في خلايا البيانات تُقرأ كأعداد ومبالغ صحيحة."""
    raw_rows = [
        ["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع", "الممشى", "سعر الوقوف"],
        [
            "٨٨٠",        # رقم المزاد بالأرقام المشرقية
            "١٥",         # رقم اللوت بالأرقام المشرقية
            "شفروليه",
            "تاهو",
            "٢٠٢٢",       # سنة الصنع
            "١٤٥٠٠٠",     # الممشى
            "٧٥٠٠٠٫٥٠",    # السعر مع الفاصلة العشرية العربية
        ],
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 1, [str(r) for r in report.rejections]
    v = Vehicle.objects.get(auction=target_auction, lot_number=15)
    assert v.year == 2022
    assert v.odometer_km == 145000
    assert v.reserve_price == Decimal("75000.50")


# ---------------------------------------------------------------------------
# 4. الوضع الموضعي (ملف بلا رأس)
# ---------------------------------------------------------------------------


def test_headerless_file_is_imported_via_positional_mode(target_auction):
    """ملف بلا رأس إطلاقاً يُقرأ بالفهارس الموضعية v1 (mapVehicleCsvRow 3581-3600).

    والخلية الأولى فارغة ⇒ يُهمل الصف بلا خطأ.
    """
    raw_rows = [
        # صف 1: خلية أولى فارغة -> يُهمل الصف دون أي خطأ أو رفض
        ["", "30000", "running", "نيسان", "صني", "2018", "", "", "", "", "", "", ""],
        # صف 2: صف بيانات صالح بترتيب v1 مع رقم اللوت في 13 ورقم المزاد في 14
        [
            "كامري قراندي",          # 0: vehicle_name
            "52000",                 # 1: starting_price
            "running",               # 2: vehicle_condition
            "تويوتا",                # 3: vehicle_brand
            "كامري",                 # 4: model
            "2021",                  # 5: year_of_manufacture
            "80000",                 # 6: mileage
            "أبيض",                  # 7: color
            "9999 ط ي ر",            # 8: Plate_number
            "JT2CAMRY2021VIN",       # 9: chassis_number
            "",                      # 10: insurance
            "",                      # 11: overview
            "",                      # 12: condition_notes
            "30",                    # 13: lot_number
            "880",                   # 14: auction_number
        ],
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 1
    assert report.rejections == []
    v = Vehicle.objects.get(auction=target_auction, lot_number=30)
    assert v.make == "تويوتا"
    assert v.model == "كامري"
    assert v.year == 2021
    assert v.reserve_price == Decimal("52000.00")
    assert v.plate_number == "9999 ط ي ر"
    assert v.vin == "JT2CAMRY2021VIN"


# ---------------------------------------------------------------------------
# 5. صف خاطئ وسط ملف صحيح
# ---------------------------------------------------------------------------


def test_bad_row_in_middle_of_file_is_rejected_with_exact_line_number(target_auction):
    """صف خاطئ وسط ملف صالح لا يوقف الباقي، ورقم السطر المرفوض دقيق كما في الإكسل."""
    raw_rows = [
        ["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع"],  # سطر 1: رأس
        ["880", "101", "تويوتا", "يارس", "2020"],                     # سطر 2: صالح
        ["880", "102", "نيسان", "صني", "سنة_غير_صالحة"],              # سطر 3: خطأ في سنة الصنع
        ["880", "103", "مازدا", "6", "2022"],                          # سطر 4: صالح
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 2  # 101 و 103 أُنشئا
    assert len(report.rejections) == 1
    rejection = report.rejections[0]
    assert rejection.row == 3  # رقم السطر الدقيق في الملف
    assert rejection.lot == "102"
    assert "سنة الصنع" in rejection.reason
    assert Vehicle.objects.filter(auction=target_auction, lot_number=101).exists()
    assert Vehicle.objects.filter(auction=target_auction, lot_number=103).exists()
    assert not Vehicle.objects.filter(auction=target_auction, lot_number=102).exists()


def test_bad_row_with_title_banner_reports_file_line_number(target_auction):
    """حين يوجد سطر عنوان في البداية، رقم السطر في تقرير الرفض يطابق رقم الصف في الإكسل."""
    raw_rows = [
        ["كشف سيارات المزاد"],                                          # سطر 1: عنوان
        ["رقم المزاد", "رقم اللوت", "الماركة", "الطراز", "سنة الصنع"],  # سطر 2: رأس
        ["880", "201", "تويوتا", "كورولا", "2021"],                   # سطر 3: صالح
        ["880", "202", "كيا", "سيراتو", "سنة_خطأ"],                   # سطر 4: خطأ
        ["880", "203", "هيونداي", "النترا", "2022"],                  # سطر 5: صالح
    ]
    payload = _make_xlsx(raw_rows)

    report = import_vehicles(payload)

    assert len(report.created) == 2
    assert len(report.rejections) == 1
    assert report.rejections[0].row == 4  # السطر الرابع في الإكسل
    assert report.rejections[0].lot == "202"
