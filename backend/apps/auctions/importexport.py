"""Vehicles out to a file, and the same file back in unchanged.

The columns are defined once, in :data:`COLUMNS`, and both directions read
that definition — an export that writes a column the import cannot read is the
bug this file exists to make impossible (E5).

Three rules that shaped it:

**State never arrives from a spreadsheet.** «حالة المركبة» and «حالة العرض»
are written for the reader and ignored on import. Accepting them would make
this file a second writer of state next to `services.py`, and a mis-typed cell
would award a car.

**An optional column is written only when some row carries it.** A file whose
`الممشى` column is empty for every row comes back without the column, and the
import therefore has nothing to say about odometers — instead of quietly
setting them all to blank.

**Nothing is saved when nothing changed.** A row whose parsed values equal the
stored ones is counted as unchanged and not written, so a re-upload leaves
`updated_at` alone. "Zero rows changed" is then a fact about the database, not
about our intentions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from apps.core.sheets import Sheet, SheetError

from .models import (
    Auction,
    FuelType,
    PlateType,
    Transmission,
    Vehicle,
    VehicleCondition,
    VehicleState,
)
from .visibility import ListingState, listing_state


class VehicleImportError(Exception):
    """The file itself could not be used — not a single row's problem."""


def _choice_writer(choices):
    def write(value: str) -> str:
        try:
            return choices(value).label
        except ValueError:
            return value or ""

    return write


def _choice_reader(choices, arabic_name: str):
    """Accept the Arabic label an operator sees, or the stored code.

    Files come back edited by hand. Insisting on the code would make the
    export unusable as a template, which is how people end up maintaining a
    second spreadsheet beside the system.
    """
    by_label = {str(choice.label).strip(): choice.value for choice in choices}
    by_value = {choice.value: choice.value for choice in choices}

    def read(raw: str):
        text = raw.strip()
        if text in by_label:
            return by_label[text]
        if text in by_value:
            return by_value[text]
        allowed = "، ".join(str(choice.label) for choice in choices)
        raise ValueError(
            f"قيمة «{arabic_name}» غير معروفة: «{text}» — المسموح: {allowed}"
        )

    return read


def _read_int(name: str, *, minimum: int | None = None):
    def read(raw: str):
        text = raw.strip()
        if text == "":
            return None
        try:
            value = int(Decimal(text))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"«{name}» ليس رقماً صحيحاً: «{text}»") from exc
        if minimum is not None and value < minimum:
            raise ValueError(f"«{name}» لا يمكن أن يقل عن {minimum}")
        return value

    return read


def _read_amount(name: str):
    def read(raw: str):
        text = raw.strip().replace(",", "")
        if text == "":
            return None
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"«{name}» ليس مبلغاً صحيحاً: «{text}»") from exc
        if value < 0:
            raise ValueError(f"«{name}» لا يمكن أن يكون سالباً")
        # Quantised to the column's own precision so a re-upload of an
        # exported "50000.00" compares equal to what is stored.
        return value.quantize(Decimal("0.01"))

    return read


def _read_text(name: str, *, max_length: int):
    def read(raw: str):
        text = raw.strip()
        if len(text) > max_length:
            raise ValueError(f"«{name}» أطول من {max_length} حرفاً")
        return text

    return read


def _amount_out(value) -> str:
    return "" if value is None else f"{value:.2f}"


@dataclass(frozen=True)
class Column:
    """One column, in both directions.

    `read is None` marks a column the file shows but the import ignores —
    derived facts and states, which have exactly one writer elsewhere.
    """

    header: str
    write: Callable[[Vehicle], str]
    read: Callable[[str], object] | None = None
    attribute: str | None = None
    required: bool = False
    optional: bool = False


COLUMNS: tuple[Column, ...] = (
    Column(
        "رقم المزاد",
        write=lambda v: str(v.auction.number),
        read=_read_int("رقم المزاد", minimum=1),
        required=True,
    ),
    Column(
        "رقم اللوت",
        write=lambda v: str(v.lot_number),
        read=_read_int("رقم اللوت", minimum=1),
        required=True,
    ),
    Column(
        "الماركة",
        write=lambda v: v.make,
        read=_read_text("الماركة", max_length=80),
        attribute="make",
        required=True,
    ),
    Column(
        "الطراز",
        write=lambda v: v.model,
        read=_read_text("الطراز", max_length=120),
        attribute="model",
        required=True,
    ),
    Column(
        "سنة الصنع",
        write=lambda v: str(v.year),
        read=_read_int("سنة الصنع", minimum=1900),
        attribute="year",
        required=True,
    ),
    Column(
        "رقم الهيكل",
        write=lambda v: v.vin,
        read=_read_text("رقم الهيكل", max_length=32),
        attribute="vin",
        optional=True,
    ),
    Column(
        "رقم اللوحة",
        write=lambda v: v.plate_number,
        read=_read_text("رقم اللوحة", max_length=16),
        attribute="plate_number",
        optional=True,
    ),
    Column(
        "نوع اللوحة",
        write=lambda v: _choice_writer(PlateType)(v.plate_type),
        read=_choice_reader(PlateType, "نوع اللوحة"),
        attribute="plate_type",
    ),
    Column(
        "الممشى",
        write=lambda v: "" if v.odometer_km is None else str(v.odometer_km),
        read=_read_int("الممشى", minimum=0),
        attribute="odometer_km",
        optional=True,
    ),
    Column(
        "ناقل الحركة",
        write=lambda v: _choice_writer(Transmission)(v.transmission),
        read=_choice_reader(Transmission, "ناقل الحركة"),
        attribute="transmission",
    ),
    Column(
        "الوقود",
        write=lambda v: _choice_writer(FuelType)(v.fuel_type),
        read=_choice_reader(FuelType, "الوقود"),
        attribute="fuel_type",
    ),
    Column(
        "الحالة الفنية",
        write=lambda v: _choice_writer(VehicleCondition)(v.condition),
        read=_choice_reader(VehicleCondition, "الحالة الفنية"),
        attribute="condition",
    ),
    Column(
        "سعر الوقوف",
        write=lambda v: _amount_out(v.reserve_price),
        read=_read_amount("سعر الوقوف"),
        attribute="reserve_price",
        optional=True,
    ),
    # ---- read-only in the file: shown, never taken back in ----
    Column("حالة المركبة", write=lambda v: VehicleState(v.state).label),
    Column("حالة العرض", write=lambda v: ListingState(listing_state(v)).label),
    Column(
        "الشريك المالك",
        write=lambda v: v.owner_company.name if v.owner_company_id else "",
    ),
)

COLUMNS_BY_HEADER = {column.header: column for column in COLUMNS}

#: The two columns that identify a row. Everything else is a value.
AUCTION_HEADER = "رقم المزاد"
LOT_HEADER = "رقم اللوت"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_sheet(vehicles) -> Sheet:
    """Build the table. An optional column appears only if a row fills it."""
    vehicles = list(vehicles)

    cells: dict[str, list[str]] = {
        column.header: [column.write(vehicle) for vehicle in vehicles]
        for column in COLUMNS
    }

    headers = [
        column.header
        for column in COLUMNS
        if not column.optional or any(value != "" for value in cells[column.header])
    ]

    rows = [
        [cells[header][index] for header in headers] for index in range(len(vehicles))
    ]
    return Sheet(headers=headers, rows=rows)


def export_vehicles(vehicles) -> bytes:
    """The exported workbook, ready to hand to an operator."""
    return export_sheet(vehicles).to_xlsx()


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowRejection:
    row: int
    reason: str
    lot: str = ""

    def __str__(self) -> str:
        where = f" (لوت {self.lot})" if self.lot else ""
        return f"صف {self.row}{where}: {self.reason}"


@dataclass
class ImportReport:
    """What the upload did — every rejected row named, not the first five.

    v1 stopped after five and told the operator "and 95 more errors", so the
    file went round the office one fix at a time. A hundred bad rows produce a
    hundred reasons here, and the report is a sheet they can work from.
    """

    created: list[int] = field(default_factory=list)
    updated: list[int] = field(default_factory=list)
    unchanged: list[int] = field(default_factory=list)
    rejections: list[RowRejection] = field(default_factory=list)
    ignored_headers: list[str] = field(default_factory=list)

    @property
    def changed(self) -> int:
        return len(self.created) + len(self.updated)

    @property
    def read_rows(self) -> int:
        return (
            len(self.created)
            + len(self.updated)
            + len(self.unchanged)
            + len(self.rejections)
        )

    def to_sheet(self) -> Sheet:
        return Sheet(
            headers=["الصف", "اللوت", "السبب"],
            rows=[[str(r.row), r.lot, r.reason] for r in self.rejections],
        )

    def summary(self) -> str:
        return (
            f"قُرئ {self.read_rows} صفاً: "
            f"{len(self.created)} جديدة، {len(self.updated)} محدَّثة، "
            f"{len(self.unchanged)} بلا تغيير، {len(self.rejections)} مرفوضة"
        )


def import_vehicles(data: bytes) -> ImportReport:
    """Read a file and apply it, row by row, rejecting what it must.

    One row's problem never stops the rest: an operator uploading a hundred
    cars gets ninety-eight in and two named reasons, rather than a transaction
    that rolls the lot back over a typo in row 57.
    """
    try:
        sheet = Sheet.read(data)
    except SheetError as exc:
        raise VehicleImportError(str(exc)) from exc

    for header in (AUCTION_HEADER, LOT_HEADER):
        if header not in sheet.headers:
            raise VehicleImportError(f"الملف ينقصه عمود «{header}»")

    known = [h for h in sheet.headers if h in COLUMNS_BY_HEADER]
    report = ImportReport(
        ignored_headers=[h for h in sheet.headers if h not in COLUMNS_BY_HEADER]
    )

    auctions: dict[int, Auction] = {}

    for index, record in enumerate(sheet.records(), start=2):
        _apply_row(record, known, index, auctions, report)

    return report


def _apply_row(
    record: dict[str, str],
    known: list[str],
    row_number: int,
    auctions: dict[int, Auction],
    report: ImportReport,
) -> None:
    lot_text = record.get(LOT_HEADER, "").strip()

    def reject(reason: str) -> None:
        report.rejections.append(RowRejection(row_number, reason, lot_text))

    values: dict[str, object] = {}
    for header in known:
        column = COLUMNS_BY_HEADER[header]
        raw = record.get(header, "")
        if column.read is None:
            continue
        if column.required and raw.strip() == "":
            reject(f"«{column.header}» مطلوب وفارغ")
            return
        try:
            values[column.header] = column.read(raw)
        except ValueError as exc:
            reject(str(exc))
            return

    auction_number = values.get(AUCTION_HEADER)
    lot_number = values.get(LOT_HEADER)
    if auction_number is None or lot_number is None:
        reject("رقم المزاد ورقم اللوت مطلوبان")
        return

    auction = auctions.get(auction_number)
    if auction is None:
        auction = Auction.objects.filter(number=auction_number).first()
        if auction is None:
            reject(f"لا يوجد مزاد رقمه {auction_number}")
            return
        auctions[auction_number] = auction

    attributes = {
        COLUMNS_BY_HEADER[header].attribute: value
        for header, value in values.items()
        if COLUMNS_BY_HEADER[header].attribute is not None
    }

    vehicle = Vehicle.objects.filter(auction=auction, lot_number=lot_number).first()
    if vehicle is None:
        _create(auction, lot_number, attributes, reject, report)
        return

    _update(vehicle, attributes, reject, report)


def _create(auction, lot_number, attributes, reject, report) -> None:
    missing = [
        column.header
        for column in COLUMNS
        if column.required
        and column.attribute is not None
        and attributes.get(column.attribute) in (None, "")
    ]
    if missing:
        reject("مركبة جديدة تحتاج: " + "، ".join(missing))
        return

    # صفٌّ يعيد شاصياً موجوداً في هذا المزاد يُرفض **بسببه**، ولا يُترك للقيد.
    #
    # `one_vin_per_auction` (HR-11) يمنع السيارة الواحدة أن تدخل المزاد
    # الواحد مرتين، وهو الصواب. لكنه قيدُ قاعدة: بلوغه من هنا يرفع
    # `IntegrityError` من داخل الحلقة، فيسقط الرفع كلّه على صفٍّ واحد —
    # وذلك عكس ما يَعِد به هذا المستورِد صراحةً: «مشكلة صفٍّ لا توقف بقيّته».
    #
    # فيُسأل قبل الكتابة. والسؤال عن الشاصي **غير الفارغ** وحده، لأن القيد
    # جزئيٌّ مثله: أسطولٌ لم تصل أوراقه يدخل بمركباتٍ كثيرة بلا شاصي، وليست
    # نسخاً من بعضها.
    vin = str(attributes.get("vin") or "").strip()
    if vin and Vehicle.objects.filter(auction=auction, vin=vin).exists():
        reject(f"الشاصي {vin} مُدخَل في هذا المزاد بالفعل")
        return

    # A new row starts as a draft. State is never read from the file, so an
    # import can add a car but can never put one on the block (T402).
    vehicle = Vehicle.objects.create(auction=auction, lot_number=lot_number, **attributes)
    report.created.append(vehicle.pk)


def _update(
    vehicle: Vehicle,
    attributes: dict,
    reject: Callable[[str], None],
    report: ImportReport,
) -> None:
    changed = [
        name
        for name, value in attributes.items()
        if getattr(vehicle, name) != value
        and not _both_blank(getattr(vehicle, name), value)
    ]
    if not changed:
        report.unchanged.append(vehicle.pk)
        return

    # الطريق الثاني إلى `one_vin_per_auction`، وسدَّ HR-11ب الأولَ وحده.
    #
    # لا يحتاج الموظّف صفّاً جديداً ليكرّر شاصياً: تكفي خانةٌ يعدّلها في صفٍّ
    # قائم لتطابق جاره — ونفس `IntegrityError` يسقط الملفّ كلّه على صفٍّ واحد.
    #
    # والسؤال داخل `if "vin" in changed` لا خارجه، وذلك ما يجعله صحيحاً بلا
    # `exclude(pk=...)`: صفٌّ يُعيد شاصيه كما هو لا يدخل هنا أصلاً، فلا يُقارَن
    # بنفسه ولا يُرفض. جُرّبت إضافة `exclude` ثم نزعُها فلم يُسقط النزعُ
    # اختباراً — وسطرٌ لا تُميّزه مخالفةٌ عن سطرٍ لا يعمل لا يبقى.
    #
    # ولولا الشرط لرُفضت كلّ إعادة رفعٍ للملفّ كما هو، وحارسٌ يرفض العمل
    # السليم يُطفَأ في أسبوع — ولذلك له اختباره أدناه.
    if "vin" in changed:
        vin = str(attributes.get("vin") or "").strip()
        clash = (
            vin
            and Vehicle.objects.filter(auction_id=vehicle.auction_id, vin=vin).exists()
        )
        if clash:
            reject(f"الشاصي {vin} مُدخَل في هذا المزاد بالفعل")
            return

    for name in changed:
        setattr(vehicle, name, attributes[name])
    vehicle.save(update_fields=[*changed, "updated_at"])
    report.updated.append(vehicle.pk)


def _both_blank(current, incoming) -> bool:
    """`None` and `""` mean the same absence in a spreadsheet cell.

    Without this, exporting a car with no VIN and re-uploading it would count
    as a change from "" to "" — and E5 would fail for a reason that has
    nothing to do with the data.
    """
    return current in (None, "") and incoming in (None, "")
