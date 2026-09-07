"""يحمّل نسخةَ v1 الحقيقية في قاعدة التطوير — بلا خادم MySQL. T854.

    python manage.py import_v1 --dump D:/tmp/haraj_db_dump/…_data_….sql.gz
    python manage.py import_v1 --dry-run          # يعدّ ويشخّص ولا يكتب

ما يفعله، وما لا يفعله
======================
يقرأ الملفَّ تدفّقاً عبر :mod:`apps.migration.dumpfile`، ويحوّل أربعة جداول
إلى نماذجنا. **ولا يلمس نسخة v1 ولا يكتب فيها بحال** — الملفُّ يُفتح للقراءة.

* ``auctions`` (٥٦) ⟶ :class:`Auction`
* ``userss`` (٤٤٬٠٣٩) ⟶ العملاء
* ``auction_vehicles`` (١٣٬٠٧٩) ⟶ :class:`Vehicle`
* ``car_images`` (٩٢٬٠٢٤) ⟶ **يُعدّ ولا يُنسخ** — انظر أدناه

**ولا يستورد المال.** لا أرصدةً ولا فواتيرَ ولا مزايدات. وذلك قرارٌ لا نقص:
دفترُنا قيدٌ مزدوج، وv1 يخزّن الرصيد **رقماً محسوباً** في ثلاثة أعمدة على
`userss` — نقلُه رقماً يعني دفتراً لا يتّزن من أوّل يوم، وكلَّ تقريرٍ يُبنى
عليه كذبة. المالُ يُبنى بقيوده أو لا يُبنى، وذلك تاسكٌ آخر بقرار المالك.

**والصورُ تُعدّ ولا تُنسخ:** `car_images` تسعون ألف صفٍّ تشير إلى ملفّاتٍ على
خادم v1 لا في هذه النسخة. فتُسجَّل تغطيةُ الصور رقماً على المركبة، والملفّاتُ
تُجلب حين يُفتح الوصول (T301).

القاعدةُ التي تحكم كلَّ تحويلٍ هنا
==================================
**ما لا يُفهَم يُرفض ويُعدّ، ولا يُخمَّن** (المادة ٢-٣). صفٌّ بتاريخٍ فاسد أو
جوّالٍ لا يُقرأ يدخل تقريرَ الرفض بسببه ورقمِه، ولا يُكتب بقيمةٍ افتراضية —
لأن قيمةً مخترعة تنجح صامتةً وتُقرأ حقيقةً بعد شهور.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.migration.dumpfile import read_table

#: توقيتُ v1: الأعمدة `datetime` بلا منطقة، وهي ساعةُ الرياض كما كتبها
#: الموظّف. تُقرأ بها ثم تُخزَّن UTC — والتحويلُ مرّةً واحدة هنا، لا في
#: كلّ استعمالٍ لاحق (المادة ٣-١).
RIYADH = ZoneInfo("Asia/Riyadh")

#: تاريخُ v1 النائب عن «بلا موعد».
PLACEHOLDER = "1900-01-01 00:00:00"

#: حالةُ v1 ⟶ حالتُنا. `later` و`upcoming` **لافتةُ عرضٍ** لا حالة، فتُقرأ
#: كلُّها `SCHEDULED` وتُكتب اللافتةُ في `showcase`.
AUCTION_STATE = {
    "later": AuctionState.SCHEDULED,
    "upcoming": AuctionState.SCHEDULED,
    "soon": AuctionState.SCHEDULED,
    "coming": AuctionState.SCHEDULED,
    "relater": AuctionState.SCHEDULED,
    "active": AuctionState.LIVE,
    "ended": AuctionState.ENDED,
    "not_active": AuctionState.ENDED,
}

SHOWCASE = {"later": "later", "upcoming": "upcoming", "soon": "soon"}

#: حالةُ سيارةٍ في v1 ⟶ عندنا.
VEHICLE_STATE = {
    "active": VehicleState.LISTED,
    "soon": VehicleState.LISTED,
    "coming": VehicleState.LISTED,
    "later": VehicleState.DRAFT,
    "not active": VehicleState.DRAFT,
    "not_active": VehicleState.DRAFT,
    "sold": VehicleState.AWARDED,
    "ended": VehicleState.REJECTED,
}

#: جوّالٌ سعوديّ كما يقبله نموذجُنا: تسعة أرقامٍ بعد 966.
PHONE = re.compile(r"^(?:\+?966|0)?(5\d{8})$")


def money(raw) -> Decimal | None:
    """نصٌّ من الملفّ ⟶ `Decimal`. ولا `float` في الطريق (المادة ٣-٢)."""
    if raw in (None, "", "0.00"):
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return None


def moment(raw) -> datetime | None:
    """`datetime` بتوقيت الرياض ⟶ UTC، أو `None` لِما لا يُقرأ."""
    if not raw or raw in (PLACEHOLDER, "0000-00-00 00:00:00"):
        return None
    try:
        naive = datetime.strptime(str(raw)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return naive.replace(tzinfo=RIYADH)


def phone_of(raw) -> str | None:
    found = PHONE.match(str(raw or "").strip().replace(" ", "").replace("-", ""))
    return f"966{found.group(1)}" if found else None


def digits(raw) -> int | None:
    text = re.sub(r"[^\d]", "", str(raw or ""))
    return int(text) if text else None


class Command(BaseCommand):
    help = "يحمّل نسخة v1 من ملفّ mysqldump في قاعدة التطوير"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default="D:/tmp/haraj_db_dump/hara_clone_v1_data_20260905_1444.sql.gz",
        )
        parser.add_argument("--dry-run", action="store_true", help="اقرأ وشخّص ولا تكتب")
        parser.add_argument(
            "--limit", type=int, default=None, help="حدُّ صفوفٍ لكل جدول — للاستطلاع"
        )

    def handle(self, *args, **options):
        # المادة ٥-٦: بيئةٌ تسمّي نفسها قبل أن تُكتب. واستيرادُ أربعةٍ وأربعين
        # ألفَ عميلٍ حقيقيّ في قاعدةٍ ظنَّها المشغّل تطويراً وهي غيرُها هو
        # بالضبط ما لا يُصلَح بعد وقوعه.
        # `ENVIRONMENT_NAME` هو الاسم الذي تُسمّي به كلُّ بيئةٍ نفسَها
        # (المادة ٥-٦)، و`base` سَمةٌ لا تبقى في بيئةٍ تعمل.
        env = getattr(settings, "ENVIRONMENT_NAME", "")
        if env not in ("development", "test", "local"):
            raise CommandError(f"لا يُستورد إلا في بيئة تطوير — البيئة هنا {env!r}")

        path = Path(options["dump"])
        if not path.exists():
            raise CommandError(f"لا ملفّ عند {path}")

        self.dry = options["dry_run"]
        self.limit = options["limit"]
        self.rejected: Counter[str] = Counter()
        self.samples: dict[str, str] = {}

        self.stdout.write(f"النسخة: {path}")
        self.stdout.write("وضع القراءة فقط — لا يُكتب شيء\n" if self.dry else "")

        auctions = self._auctions(path)
        people = self._people(path)
        self._vehicles(path, auctions, people)
        self._report()

    # -- المزادات ---------------------------------------------------------

    def _auctions(self, path: Path) -> dict[str, Auction]:
        made: dict[str, Auction] = {}
        skipped = 0

        for row in read_table(path, "auctions", limit=self.limit):
            starts, ends = moment(row["start_time"]), moment(row["end_time"])
            if starts is None or ends is None or ends <= starts:
                # القيدُ `auction_ends_after_it_starts` يرفضه في القاعدة؛
                # ورفضُه هنا يجعل السببَ مقروءاً بدل `IntegrityError`.
                self._reject("مزاد: موعدٌ ناقص أو نهايةٌ قبل بداية", row["id"])
                skipped += 1
                continue

            stored = str(row.get("status") or "").lower().strip()
            fields = {
                "title": (
                    row.get("name_of_auction")
                    or row.get("car_name")
                    or f"مزاد {row['id']}"
                ),
                "starts_at": starts,
                "ends_at": ends,
                "state": AUCTION_STATE.get(stored, AuctionState.ENDED),
                "showcase": SHOWCASE.get(stored, "upcoming"),
                "deposit_required": (
                    money(row.get("insurance_amount")) or Decimal("10000.00")
                ),
                "admin_fee": money(row.get("fees")) or Decimal("0.00"),
                "sms_reminder_at": moment(row.get("sms_reminder_time")),
            }
            if self.dry:
                made[row["id"]] = Auction(number=int(row["id"]), **fields)
                continue
            auction, _ = Auction.objects.update_or_create(
                number=int(row["id"]), defaults=fields
            )
            made[row["id"]] = auction

        self.stdout.write(f"المزادات: {len(made)} محمَّلاً · {skipped} مرفوضاً")
        return made

    # -- العملاء ----------------------------------------------------------

    def _people(self, path: Path) -> dict[str, object]:
        from django.contrib.auth import get_user_model

        User = get_user_model()
        made: dict[str, object] = {}
        skipped = 0
        batch: list = []

        for row in read_table(path, "userss", limit=self.limit):
            phone = phone_of(row.get("phone"))
            if phone is None:
                self._reject("عميل: جوّال لا يُقرأ", row["id"], str(row.get("phone"))[:20])
                skipped += 1
                continue

            person = User(
                phone=phone,
                full_name=(row.get("name") or row.get("full_name") or "").strip()[:150],
                national_id=str(row.get("identity_number") or "")[:20],
                # **بلا كلمة مرور.** نسخةُ v1 تحمل `password` مجزوءاً بخوارزميّةٍ
                # أخرى، ونقلُه يعني حساباً يُفتح بكلمةٍ لا نعرف قوّتها ولا نملك
                # سجلَّ تغييرها. ومن أراد الدخول يعيد التوثيق برسالة.
                is_active=str(row.get("block_status") or "allowed") == "allowed",
            )
            person.set_unusable_password()
            batch.append(person)
            made[row["id"]] = person

        if not self.dry:
            # `ignore_conflicts`: الجوّالُ مفتاحٌ فريد، وv1 يحوي مكرَّرات —
            # وهي حقيقةٌ في بياناته لا عطلٌ عندنا. الأوّلُ يفوز ويُعدّ الباقي.
            User.objects.bulk_create(batch, batch_size=1000, ignore_conflicts=True)
            found = {p.phone: p for p in User.objects.filter(
                phone__in=[p.phone for p in batch]
            )}
            made = {
                key: found[person.phone]
                for key, person in made.items()
                if person.phone in found
            }

        self.stdout.write(f"العملاء: {len(made)} محمَّلاً · {skipped} مرفوضاً")
        return made

    # -- المركبات ---------------------------------------------------------

    def _vehicles(self, path: Path, auctions: dict, people: dict) -> None:
        batch: list[Vehicle] = []
        skipped = 0
        lots: set[tuple[int, int]] = set()

        for row in read_table(path, "auction_vehicles", limit=self.limit):
            auction = auctions.get(str(row.get("auction_id")))
            if auction is None:
                self._reject(
                    "مركبة: مزادٌ غير موجود", row["id"], str(row.get("auction_id"))
                )
                skipped += 1
                continue

            lot = digits(row.get("lot_number")) or int(row["id"])
            # المفتاحُ من **رقم مزاد v1** لا من مفتاحنا: في وضع القراءة
            # لا مفتاحَ لنا بعد، فيصير صفراً للجميع وتتصادم كلُّ اللوتات.
            key = (str(row.get("auction_id")), lot)
            if key in lots:
                # `one_lot_per_auction` قيدٌ في القاعدة، وv1 يحوي مكرَّرات.
                self._reject(
                    "مركبة: رقمُ لوتٍ مكرَّر في المزاد نفسه", row["id"], str(lot)
                )
                skipped += 1
                continue
            lots.add(key)

            name = (row.get("vehicle_name") or "").strip()
            make = (
                row.get("vehicle_brand")
                or row.get("make")
                or name.split(" ")[0]
                or "غير محدد"
            )
            year = digits(row.get("year_of_manufacture")) or digits(row.get("year"))

            batch.append(
                Vehicle(
                    auction=auction,
                    lot_number=lot,
                    make=str(make)[:80],
                    model=str(row.get("model") or name)[:120],
                    # سنةٌ خارج المعقول تُترك للقيمة الدنيا لا تُخترَع:
                    # v1 فيه `210` و`0` في هذا العمود.
                    year=year if year and 1950 <= year <= 2100 else 1950,
                    vin=str(row.get("chassis_number") or "")[:32],
                    plate_number=str(row.get("Plate_number") or "")[:16],
                    odometer_km=digits(row.get("mileage")),
                    claim_number=str(row.get("claim_number") or "")[:60],
                    insurance_company=str(row.get("insurance_company") or "")[:255],
                    runs_status=str(row.get("runs_status") or "")[:100],
                    key_status=str(row.get("key_status") or "")[:100],
                    is_marketing=str(row.get("is_marketing") or "0") == "1",
                    state=VEHICLE_STATE.get(
                        str(row.get("status") or "").lower().strip(), VehicleState.DRAFT
                    ),
                )
            )

        if not self.dry:
            Vehicle.objects.bulk_create(batch, batch_size=1000, ignore_conflicts=True)

        self.stdout.write(f"المركبات: {len(batch)} محمَّلاً · {skipped} مرفوضاً")

    # -- التقرير ----------------------------------------------------------

    def _reject(self, why: str, row_id, sample: str = "") -> None:
        self.rejected[why] += 1
        if why not in self.samples:
            self.samples[why] = f"صفّ {row_id}" + (f" — {sample}" if sample else "")

    def _report(self) -> None:
        if not self.rejected:
            self.stdout.write(self.style.SUCCESS("\nلا صفَّ مرفوضاً."))
            return
        self.stdout.write("\nالمرفوض، بسببه:")
        for why, count in self.rejected.most_common():
            self.stdout.write(f"  {count:>6}  {why}   (مثال: {self.samples[why]})")
