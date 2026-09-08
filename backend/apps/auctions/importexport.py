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

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from django.db.models import Q

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


# ---------------------------------------------------------------------------
# Normalization & Digit Folding (T867)
# ---------------------------------------------------------------------------

ARABIC_INDIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
HAMZA_AND_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
TASHKEEL_AND_TATWEEL = re.compile(r"[\u064B-\u065F\u0670\u0640]")
NON_ALPHANUM = re.compile(r"[^\w]+", re.UNICODE)


def fold_digits(text: str) -> str:
    """طيّ الأرقام في خلايا البيانات إلى ASCII مع تحويل الفاصلة العشرية العربية."""
    return text.translate(ARABIC_INDIC_DIGITS).replace("٫", ".")


def normalize_header_cell(text: str) -> str:
    """تطبيع اسم العمود قبل المطابقة مع جدول المرادفات (v1: 3385-3482):
    1. طيّ الأرقام العربية-الهندية والفارسية إلى ASCII.
    2. حذف التشكيل والتطويل ـ.
    3. توحيد الهمزات: أ إ آ ← ا، ى ← ي، ة ← ه.
    4. lowercase للإنجليزية.
    5. طيّ المسافات والرموز غير الأبجدية-الرقمية إلى _ وحذف الزوائد.
    """
    if not text:
        return ""
    text = text.translate(ARABIC_INDIC_DIGITS)
    text = TASHKEEL_AND_TATWEEL.sub("", text)
    text = text.translate(HAMZA_AND_LETTERS)
    text = text.lower()
    text = NON_ALPHANUM.sub("_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    return text


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
    by_normalized = {
        normalize_header_cell(str(choice.label)): choice.value for choice in choices
    }
    by_normalized.update(
        {normalize_header_cell(choice.value): choice.value for choice in choices}
    )

    def read(raw: str):
        text = raw.strip()
        if text in by_label:
            return by_label[text]
        if text in by_value:
            return by_value[text]
        norm = normalize_header_cell(text)
        if norm in by_normalized:
            return by_normalized[norm]
        allowed = "، ".join(str(choice.label) for choice in choices)
        raise ValueError(
            f"قيمة «{arabic_name}» غير معروفة: «{text}» — المسموح: {allowed}"
        )

    return read


def _read_int(name: str, *, minimum: int | None = None):
    def read(raw: str):
        text = fold_digits(raw.strip()).replace(",", "").replace("،", "")
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
        text = fold_digits(raw.strip()).replace(",", "").replace("،", "")
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

#: مرادفاتُ العناوين، **صفٌّ لكل عمود** — مستخرجةٌ من `normalizeHeaderCell`
#: في v1 (`AuctionController.php:3385-3482`). T867.
#:
#: ولماذا زوجٌ من الصفوف لا قاموسٌ مسطَّح: القاموسُ المسطَّح كان يقرؤه
#: `ops/checks/one_vehicle_card.py` **كرتَ مركبةٍ ثانياً** — مفاتيحُه `make`
#: و`model` و`year` و`lot_number`، وذلك بالضبط شكلُ الكرت الذي يحرسه. والصفُّ
#: هنا يقول «هذا العمود، وهذه أسماؤه»، وهو ما يُقرأ ويُراجَع أصلاً: عمودٌ
#: يُضاف صفٌّ يُضاف، ومرادفٌ يُضاف كلمةٌ تُضاف في صفّه.
HEADER_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("رقم المزاد", ("رقم_المزاد", "المزاد", "auction", "auction_id", "auction_number")),
    ("رقم اللوت", ("رقم_اللوت", "اللوت", "رقم_الموقف", "lot", "lot_no", "lot_number")),
    (
        "الماركة",
        (
            "الماركه", "الماركة", "vehicle_brand", "brand", "make",
            "اسم_السياره", "اسم_السيارة", "اسم_المركبه", "اسم_المركبة",
            "vehicle_name", "car_name",
        ),
    ),
    ("الطراز", ("الطراز", "الموديل", "model")),
    (
        "سنة الصنع",
        ("سنه_الصنع", "سنة_الصنع", "السنه", "السنة", "year_of_manufacture", "year"),
    ),
    (
        "رقم الهيكل",
        ("رقم_الهيكل", "رقم_الشاسيه", "الشاصي", "chassis_number", "chassis", "vin"),
    ),
    ("رقم اللوحة", ("رقم_اللوحه", "رقم_اللوحة", "plate_number", "plate")),
    ("نوع اللوحة", ("نوع_اللوحه", "نوع_اللوحة", "plate_type")),
    (
        "الممشى",
        ("الممشي", "الممشى", "المسافه", "المسافة", "mileage", "odometer", "odometer_km"),
    ),
    (
        "ناقل الحركة",
        ("ناقل_الحركه", "ناقل_الحركة", "القير", "transmission", "gear"),
    ),
    # `the_weight` **ليس هنا عمداً.** عنوانُه في v1 «الوزن / نوع الوقود»
    # وواجهةُ العميل تعرضه وقوداً — ولا يقول الكودُ أيَّهما تحمل الصفوف فعلاً.
    # وربطُه بالوقود تخمينٌ يكتب في عمودٍ تعداديّ، فيصير خطأً لا يُميَّز عن
    # قيمةٍ صحيحة. السؤالُ عند المالك، وحتى يُجاب يبقى العمود مُهمَلاً باسمه.
    ("الوقود", ("الوقود", "نوع_الوقود", "fuel", "fuel_type")),
    (
        "الحالة الفنية",
        (
            "الحاله_الفنيه", "الحالة_الفنية", "الحاله", "الحالة",
            "vehicle_condition", "the_condition", "condition",
        ),
    ),
    (
        "سعر الوقوف",
        ("سعر_الوقوف", "السعر_الابتدائي", "starting_price", "start_price", "reserve_price"),
    ),
    (
        "حالة المركبة",
        ("حاله_المركبه", "حالة_المركبة", "vehicle_status", "status"),
    ),
    (
        "حالة العرض",
        (
            "حاله_العرض", "حالة_العرض", "حاله_النشر", "حالة_النشر",
            "activation_status", "حاله_التفعيل", "حالة_التفعيل",
        ),
    ),
    # **الشريكُ المالك ليس شركةَ التأمين.** الأولُ مفتاحٌ أجنبيٌّ إلى شركةٍ
    # شريكة، والثانيةُ حقلٌ نصّيٌّ قائمٌ بذاته في `models.py`. وربطُهما — كما
    # وقع في أوّل نسخةٍ من هذا الجدول — يجعل ملفّاً فيه «شركة التأمين» يبحث
    # عن شريكٍ بهذا الاسم فلا يجده.
    ("الشريك المالك", ("الشريك_المالك",)),
)

#: القاموسُ الذي تُطابَق به الخلايا. يُبنى من `HEADER_ALIASES` ولا يُكتب بيده:
#: مصدران للمرادفات مصدران يفترقان (المادة ٤-٥).
HEADER_SYNONYMS: dict[str, str] = {
    alias: canonical for canonical, aliases in HEADER_ALIASES for alias in aliases
}

#: أعمدةٌ يعرفها v1 **ولا عمودَ لها في المستورِد بعد**. تُذكَر بأسمائها
#: للموظّف بدل أن تُبتلع في «أعمدة غير معروفة»:
#:
#: خمسةٌ منها لها **حقلٌ جاهزٌ في `models.py`** (اللون، ورقم المطالبة،
#: والمفاتيح، وحالة المحرك، والتسويق) وينقصها صفٌّ في `COLUMNS` وحده — وذلك
#: تاسكٌ قائمٌ بذاته لأنه يغيّر ملفَّ التصدير أيضاً. والباقي بلا حقلٍ أصلاً.
#:
#: و`mvpi_status` هنا لا مع «حالة المحرك»: العميلُ في v1 يفضّل `runs_status`
#: ويقع على `mvpi_status` عند غيابه (`AuctionApiController.php:638`) — أهما
#: حقلٌ واحدٌ أم اثنان سؤالٌ عند المالك، ودمجُهما هنا يجيب عنه نيابةً عنه.
KNOWN_BUT_NOT_A_COLUMN: dict[str, str] = {
    alias: label
    for label, aliases in (
        ("اللون", ("the_color", "color", "اللون")),
        (
            "رقم المطالبة",
            ("claim_number", "claim", "claim_no", "رقم_المطالبه", "رقم_المطالبة",
             "المطالبه", "المطالبة"),
        ),
        ("شركة التأمين", ("insurance_company", "شركه_التامين", "شركة_التأمين")),
        ("المفاتيح", ("key_status", "المفتاح", "المفاتيح")),
        ("عدد الأبواب", ("the_doors", "عدد_الابواب", "عدد_الأبواب")),
        ("حالة المحرك", ("mvpi_status", "حاله_المحرك", "حالة_المحرك")),
        ("الوزن أو نوع الوقود", ("the_weight", "نوع_الوقود_الوزن", "الوزن")),
        ("التسويق", ("is_marketing", "marketing", "التسويق", "تسويق")),
        ("الوصف", ("overview", "الوصف")),
        ("تقرير الفحص", ("inspection_report_media", "رابط_تقرير_الفحص")),
        ("أيام الفحص", ("inspection_days", "ايام_الفحص")),
        ("موقع المعاينة", ("preview_site", "موقع_المعاينه", "موقع_المعاينة")),
        ("وقت المعاينة", ("وقت_المعاينه", "وقت_المعاينة")),
        ("فترات المعاينة", ("time_periods", "فترات_المعاينه", "فترات_المعاينة")),
        ("وقت الإدخال", ("input_time", "وقت_الادخال", "وقت_الإدخال")),
        ("ملاحظات الحالة", ("condition_notes",)),
        ("المعرّف", ("id", "المعرف")),
        ("مزايدة تلقائية", ("auto_bid", "مزايده_تلقائيه", "مزايدة_تلقائية")),
        ("قيمة المزايدة", ("bidamount", "قيمه_المزايده", "قيمة_المزايدة")),
    )
    for alias in aliases
}

#: مؤشرات v1 الأربعة لاكتشاف صف الرأس (looksLikeVehicleHeader 3362-3371):
#: vehicle_name أو vehicle_brand (الماركة) أو starting_price (سعر الوقوف) أو vehicle_condition (الحالة الفنية).
HEADER_INDICATORS: set[str] = {
    "الماركة",
    "سعر الوقوف",
    "الحالة الفنية",
    "vehicle_name",
    "vehicle_brand",
    "starting_price",
    "vehicle_condition",
}


def resolve_header_cell(cell: str) -> str:
    """الاسمُ المعياريُّ للخلية — أو اسمُها المفهوم إن كانت معروفةً بلا عمود.

    والفرقُ بين الاثنين هو ما يقرؤه الموظّف: «أُهمل `the_color`» يقرؤها خطأً
    في ملفّه، و«اللون — عمودٌ معروف لا يُستورَد بعد» يقرؤها نقصاً في المستورِد.
    """
    norm = normalize_header_cell(cell)
    if not norm:
        return ""
    mapped = HEADER_SYNONYMS.get(norm)
    if mapped is not None and mapped in COLUMNS_BY_HEADER:
        return mapped
    known = KNOWN_BUT_NOT_A_COLUMN.get(norm)
    if known is not None:
        return known
    return cell.strip()


def looks_like_vehicle_header(row: list[str]) -> bool:
    """v1: looksLikeVehicleHeader (3362-3371)."""
    for cell in row:
        norm = normalize_header_cell(cell)
        if not norm:
            continue
        mapped = HEADER_SYNONYMS.get(norm, norm)
        if mapped in HEADER_INDICATORS or norm in HEADER_INDICATORS:
            return True
    return False


def detect_header(
    raw_table: list[list[str]],
) -> tuple[int | None, list[str] | None]:
    """امسح أول 5 صفوف غير فارغة بحثاً عن الرأس.
    أول صف يطابق looks_like_vehicle_header هو الرأس وما قبله يُهمل.
    وإن لم يطابق أي منها فالملف بلا رأس (الوضع الموضعي).
    """
    scanned = 0
    for idx, row in enumerate(raw_table):
        if not any(cell.strip() for cell in row):
            continue
        scanned += 1
        if looks_like_vehicle_header(row):
            canonical_headers = [resolve_header_cell(cell) for cell in row]
            return idx, canonical_headers
        if scanned >= 5:
            break
    return None, None


# Header-mapped uploads only. The positional (header-less) reader
# further down is left untouched on purpose: adding a column
# there would shift every index and silently corrupt the sheets
# people already use.
# الترتيب الموضعي لملفات v1 القديمة (عقدٌ مع ملفات المالك):
# إدخال عمود في وسطه يزيح كل ما بعده (v1: 3556-3559).
POSITIONAL_MAP: tuple[str, ...] = (
    "vehicle_name",         # 0
    "starting_price",       # 1
    "vehicle_condition",    # 2
    "vehicle_brand",        # 3
    "model",                # 4
    "year_of_manufacture",  # 5
    "mileage",              # 6
    "the_color",            # 7
    "Plate_number",         # 8
    "chassis_number",       # 9
    "insurance_company",    # 10
    "overview",             # 11
    "condition_notes",      # 12
    "lot_number",           # 13 (v2 row identity)
    "auction_number",       # 14 (v2 row identity)
)


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
    #: مركباتٌ كانت في مزادٍ آخر (غير مباعة) فنُقلت إلى هذا المزاد بدل تكرارها —
    #: سلوكُ v1 «نقل غير المباع». كلٌّ حركةٌ على صفٍّ فعليّ، فتُعدّ في `changed`.
    transferred: list[int] = field(default_factory=list)
    rejections: list[RowRejection] = field(default_factory=list)
    ignored_headers: list[str] = field(default_factory=list)

    @property
    def changed(self) -> int:
        return len(self.created) + len(self.updated) + len(self.transferred)

    @property
    def read_rows(self) -> int:
        return (
            len(self.created)
            + len(self.updated)
            + len(self.unchanged)
            + len(self.transferred)
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
            f"{len(self.transferred)} منقولة، "
            f"{len(self.unchanged)} بلا تغيير، {len(self.rejections)} مرفوضة"
        )


def import_vehicles(
    data: bytes,
    *,
    default_auction: Auction | int | None = None,
) -> ImportReport:
    """Read a file and apply it, row by row, rejecting what it must.

    One row's problem never stops the rest: an operator uploading a hundred
    cars gets ninety-eight in and two named reasons, rather than a transaction
    that rolls the lot back over a typo in row 57.
    """
    try:
        raw_table = Sheet.read_table(data)
    except SheetError as exc:
        raise VehicleImportError(str(exc)) from exc

    non_empty = [r for r in raw_table if any(cell.strip() for cell in r)]
    if not non_empty:
        raise VehicleImportError("الملف لا يحتوي على أي صف")

    header_idx, canonical_headers = detect_header(raw_table)
    auctions: dict[int, Auction] = {}

    if header_idx is not None:
        # ── الوضع ذو الرأس (Header-mapped Mode) ──
        headers = canonical_headers or []

        if AUCTION_HEADER not in headers and default_auction is None:
            raise VehicleImportError(f"الملف ينقصه عمود «{AUCTION_HEADER}»")

        if LOT_HEADER not in headers:
            raise VehicleImportError(f"الملف ينقصه عمود «{LOT_HEADER}»")

        known = [h for h in headers if h in COLUMNS_BY_HEADER]
        # عمودٌ نعرفه ولا نستورده يُسمّى بما يعنيه، لا بما كُتب في الملفّ —
        # ورأسٌ لا نعرفه يبقى كما كتبه صاحبُه ليجده في ملفّه.
        recognised = set(KNOWN_BUT_NOT_A_COLUMN.values())
        report = ImportReport(
            ignored_headers=[
                f"{h} (معروف، لا يُستورَد بعد)" if h in recognised else h
                for h in headers
                if h not in COLUMNS_BY_HEADER and h
            ]
        )

        for row_idx in range(header_idx + 1, len(raw_table)):
            row = raw_table[row_idx]
            if not any(cell.strip() for cell in row):
                continue
            padded_row = (row + [""] * len(headers))[: len(headers)]
            record = dict(zip(headers, padded_row))
            _apply_row(
                record,
                known,
                row_idx + 1,
                auctions,
                report,
                default_auction=default_auction,
            )

        return report

    # ── الوضع الموضعي (Positional Mode) ──
    # ملف بلا رأس يُقرأ بالفهارس كما في mapVehicleCsvRow.
    # والخلية الأولى فارغة ⇒ الصف يُهمل بلا خطأ.
    max_width = max((len(r) for r in raw_table), default=0)
    if max_width < 6:
        raise VehicleImportError(f"الملف ينقصه عمود «{AUCTION_HEADER}»")

    report = ImportReport()
    for row_idx, row in enumerate(raw_table):
        line_number = row_idx + 1
        if not any(cell.strip() for cell in row):
            continue
        vehicle_name = row[0].strip() if len(row) > 0 else ""
        if vehicle_name == "":
            # الخليّةُ الأولى فارغةً ⇒ الصفُّ يُهمَل بلا خطأ.
            continue

        make_candidate = (
            row[3].strip() if len(row) > 3 and row[3].strip() else vehicle_name
        )
        lot_val = row[13].strip() if len(row) > 13 else ""
        auction_val = row[14].strip() if len(row) > 14 else ""

        record = {
            AUCTION_HEADER: auction_val,
            LOT_HEADER: lot_val,
            "الماركة": make_candidate,
            "الطراز": row[4].strip() if len(row) > 4 else "",
            "سنة الصنع": row[5].strip() if len(row) > 5 else "",
            "سعر الوقوف": row[1].strip() if len(row) > 1 else "",
            "الحالة الفنية": row[2].strip() if len(row) > 2 else "",
            "الممشى": row[6].strip() if len(row) > 6 else "",
            "رقم اللوحة": row[8].strip() if len(row) > 8 else "",
            "رقم الهيكل": row[9].strip() if len(row) > 9 else "",
        }
        known = [h for h in record if h in COLUMNS_BY_HEADER]
        _apply_row(
            record,
            known,
            line_number,
            auctions,
            report,
            default_auction=default_auction,
        )

    return report


def _apply_row(
    record: dict[str, str],
    known: list[str],
    row_number: int,
    auctions: dict[int, Auction],
    report: ImportReport,
    *,
    default_auction: Auction | int | None = None,
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
        if (
            column.header == AUCTION_HEADER
            and raw.strip() == ""
            and (default_auction is not None or Auction.objects.count() == 1)
        ):
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

    if auction_number is None and default_auction is not None:
        if isinstance(default_auction, Auction):
            auction_number = default_auction.number
            auctions[auction_number] = default_auction
        else:
            auction_number = int(default_auction)
    elif auction_number is None and Auction.objects.count() == 1:
        single_auction = Auction.objects.first()
        auction_number = single_auction.number
        auctions[auction_number] = single_auction

    if auction_number is None or lot_number is None:
        if lot_number is None and auction_number is not None:
            reject(f"«{LOT_HEADER}» مطلوب وفارغ")
        elif auction_number is None and lot_number is not None:
            reject(f"«{AUCTION_HEADER}» مطلوب وفارغ")
        else:
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
        # سلوك v1 قبل الإنشاء: مركبةٌ بنفس الشاصي/اللوحة في مزادٍ آخر تُعامَل
        # حسب حالها — مباعةٌ تُرفض، غير مباعةٍ تُنقَل — فلا تُكرَّر.
        if _reuse_from_other_auction(auction, lot_number, attributes, reject, report):
            return
        _create(auction, lot_number, attributes, reject, report)
        return

    _update(vehicle, attributes, reject, report)


def _reuse_from_other_auction(
    auction, lot_number, attributes: dict, reject, report: ImportReport
) -> bool:
    """سلوكُ v1 «إعادة استخدام المركبة عبر المزادات». يُعيد True إن عالج الصفّ.

    يُطابَق بالشاصي (`vin`) أو اللوحة (`plate_number`) عبر **مزادٍ آخر**، وأحدثُ
    تطابقٍ يفوز (كما في v1: `ORDER BY id DESC`):

    * **مباعة** — لها فاتورةٌ نشِطة (غير ملغاة) — تُرفَض: سيارةٌ بيعت لا تُعاد
      جدولتها. هذا هو الحارسُ الماليُّ الذي كان ينقص v2.
    * **معروضةٌ في مزادٍ جارٍ** تُرفَض كذلك — نزعُها من مزادٍ حيٍّ يُفسد مزايداتٍ
      وتأميناتٍ قائمة (تشدّدٌ مقصودٌ فوق v1، الذي كان ينقلها فيكسر المزاد الحيّ).
    * **غير مباعةٍ ومزادُها منتهٍ** تُنقَل إلى هذا المزاد: تُسحَب مزايداتُها
      القديمة (تُحفَظ تاريخاً لا تُحذَف)، ويُصفَّر الفوز، وتُطبَّق بيانات الملف.

    بلا شاصٍ ولا لوحة لا هويّة تُطابَق، فيُترك الصفُّ للإنشاء العاديّ (False).
    """
    vin = str(attributes.get("vin") or "").strip()
    plate = str(attributes.get("plate_number") or "").strip()
    if not vin and not plate:
        return False

    ident = Q()
    if vin:
        ident |= Q(vin=vin)
    if plate:
        ident |= Q(plate_number=plate)
    existing = (
        Vehicle.objects.filter(ident)
        .exclude(auction=auction)
        .select_related("auction")
        .order_by("-pk")
        .first()
    )
    if existing is None:
        return False

    from apps.money.models import InvoiceState

    if existing.invoices.exclude(state=InvoiceState.CANCELLED).exists():
        reject(
            f"مباعة في المزاد #{existing.auction.number} ولها فاتورة نشِطة — "
            "لا تُعاد جدولتها"
        )
        return True

    # القيدُ `one_vin_per_auction`: لو دخل هذا الشاصي هذا المزاد سابقاً (صفٌّ
    # أبكرُ في الملف نفسه) لا يُنقَل فوقه، بل يُرفض بسببه لا بـIntegrityError.
    if vin and Vehicle.objects.filter(auction=auction, vin=vin).exists():
        reject(f"الشاصي {vin} مُدخَل في هذا المزاد بالفعل")
        return True

    if _auction_is_live(existing.auction):
        reject(
            f"معروضة في المزاد #{existing.auction.number} وهو جارٍ — "
            "لا تُنقَل قبل انتهائه"
        )
        return True

    _transfer(existing, auction, lot_number, attributes, report)
    return True


def _auction_is_live(auction) -> bool:
    """هل المزادُ جارٍ الآن؟ نقلُ مركبةٍ منه يُفسد مزايداتٍ وتأميناتٍ قائمة."""
    from apps.auctions.states import AuctionState

    return auction.state == AuctionState.LIVE


def _transfer(existing, auction, lot_number, attributes: dict, report: ImportReport) -> None:
    """انقل مركبةً غير مباعةٍ إلى مزادٍ جديد — نظيرُ `transferVehicleToAuction` في v1.

    المزايداتُ القديمة تُسحَب (`is_withdrawn`) لا تُحذَف: التاريخُ يبقى، والفتحةُ
    تتحرّر لمزايدةٍ جديدة، ولا يصطدم شيءٌ بـPROTECT على `Bid.supersedes`. والحالةُ
    تعود «معادة للعرض» بلا فائزٍ ولا سعرِ رسوّ.
    """
    from django.utils import timezone

    from apps.auctions.states import VehicleState

    existing.bids.filter(is_superseded=False, is_withdrawn=False).update(
        is_withdrawn=True, withdrawn_at=timezone.now()
    )

    existing.auction = auction
    existing.lot_number = lot_number
    existing.state = VehicleState.RELISTED
    existing.awarded_to = None
    existing.awarded_price = None
    for name, value in attributes.items():
        setattr(existing, name, value)
    existing.save()
    report.transferred.append(existing.pk)


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
