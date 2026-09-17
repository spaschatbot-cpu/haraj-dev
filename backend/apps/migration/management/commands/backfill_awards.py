"""الترسيةُ التي لم يقرأها الجسر — من `winner_user_id` لا من `status`. T928.

    python manage.py backfill_awards --dry-run
    python manage.py backfill_awards

## العطل، بعدده

`import_v1` يقرأ حالةَ المركبة من عمودٍ واحد: ``auction_vehicles.status``،
ويترجمه بخريطة فيها ``"sold" ⟶ AWARDED`` و``"won" ⟶ AWARDED``. **وv1 لا
يكتب أيّاً منهما.** قِيست القيمُ في لقطة الإنتاج (٢٠٢٦-٠٩-٠٥، ١٣٬٠٧٩ صفّاً):

    not_active  11,915   ·   active  405   ·   coming  363
    ended          288   ·   later   107   ·   soon      1

فكلُّ مركبةٍ تخرج `draft` أو `listed`، **وصفرُ مركبةٍ تخرج مرسّاة** — وشاشةُ
«المزايدات المقبولة» تُفتح على جدولٍ فارغ بعد ترحيلٍ نجح.

**والترسيةُ مكتوبةٌ في الجدول نفسِه، في عمودٍ آخر**: ``winner_user_id``
مملوءٌ في **٦٬١١٧** صفّاً، ومعه ``winning_bid_id`` و``winner_paid_at``.
أي أن البيعَ في v1 يُسجَّل بالفائز لا بالحالة — والحالةُ تصف **العرض**
(«نشط» · «قريباً» · «انتهى») لا **النتيجة**.

## ولماذا أمرٌ مستقلٌّ لا إصلاحٌ في الجسر

نفسُ حجّة `backfill_v1_fields`: `import_v1` يكتب بـ``ignore_conflicts=True``،
فإعادةُ تشغيله على قاعدةٍ مبنيّةٍ لا تُحدِّث صفّاً. وإصلاحُ الخريطة هناك يخدم
اللقطةَ القادمة ولا يُصلح ما بُني — وقد بُني فوقه فواتيرُ ودفترٌ وقيودُ تدقيق.

**والخريطةُ هناك لم تُغيَّر**، وتعليقٌ كُتب فوقها يقول أين الترسيةُ فعلاً:
قيمُها الستُّ تصف **العرضَ** وهي صحيحةٌ في وصفه (``ended ⟶ REJECTED`` يطابق
٢٨٨ صفّاً في الإنتاج)، والنقصُ أنها لا تصف **النتيجة** — ولا يُصلَح ذلك
بترجمةٍ أخرى لعمودٍ لا يحملها، بل بقراءة العمود الذي يحملها.

## والحالةُ تُشتقّ من المال لا من الفائز وحدَه

مركبةٌ لها فائزٌ وفاتورةٌ مسدَّدة ليست «مرسّاة» — هي «مسدَّدة». فالترتيب:

* فاتورةٌ حيّةٌ مسدَّدة  ⟶ ``PAID``
* فاتورةٌ حيّةٌ غيرُ مسدَّدة ⟶ ``INVOICED``
* فائزٌ بلا فاتورة ⟶ ``AWARDED``

وبغير هذا يُقرأ الجدولُ «رست ولم تُفوتَر» على مركبةٍ قُبض ثمنُها، فيُصدَر لها
فاتورةٌ ثانية.

## ولا يلمس ما قرّره إنسان

الشرطُ ``awarded_to__isnull=True``: مركبةٌ رساها موظّفٌ من اللوحة بعد الترحيل
لا تُدهَس بقيمةٍ من لقطةٍ أقدمَ منها.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.migration.dumpfile import read_table
from apps.migration.models import LegacyRef
from apps.money.models import Invoice, InvoiceState

#: الحالاتُ التي لا تُدهَس: قرارٌ وقع عندنا بعد الترحيل.
DECIDED = {VehicleState.REJECTED, VehicleState.RELEASED}


def _amount(raw) -> Decimal | None:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return value if value > 0 else None


class Command(BaseCommand):
    help = "يملأ الترسيةَ من `winner_user_id` — ما سقط من الجسر."

    def add_arguments(self, parser):
        parser.add_argument("--dump", default=None, help="مسارُ نسخة mysqldump")
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب")
        parser.add_argument(
            "--write-json",
            default=None,
            help="اكتب معرّفاتِ الترسية إلى ملفٍّ صغير بدل الكتابة في القاعدة",
        )
        parser.add_argument(
            "--from-json",
            default=None,
            help="اقرأ المعرّفاتِ من ملفِّ `--write-json` بدل النسخة الكاملة",
        )

    def handle(self, *args, **options):
        # **ولماذا ملفُّ معرّفاتٍ أصلاً.** النسخةُ الكاملة ٣١٩ م.ب فيها أسماءُ
        # ٤٤ ألف عميلٍ وجوّالاتُهم وبصماتُ كلماتِ مرورهم، وتُحذف من الخادم بعد
        # الترحيل. وهذا الأمرُ يحتاج منها **أربعةَ أعمدةٍ لا غير**: معرّفَ
        # المركبة ومعرّفَ الفائز ومبلغَ المزايدة الفائزة ووقتَها — أرقامٌ بلا
        # اسمٍ ولا جوّال. فنقلُها وحدَها أخفُّ وأقلُّ تعرّضاً من إعادة الـ٣١٩.
        source = options["from_json"]
        if source:
            return self._from_json(Path(source), options)

        raw = options["dump"] or os.environ.get("V1_DUMP_PATH")
        if not raw:
            self.stderr.write("لا نسخة: مرّر `--dump` أو اضبط `V1_DUMP_PATH`.")
            return
        # `dumpfile` يفحص اللاحقة، فيلزمه `Path` لا نصّ.
        path = Path(raw)
        dry = options["dry_run"]
        self.stdout.write(f"النسخة: {path}")
        if dry:
            self.stdout.write("وضع القراءة فقط — لا يُكتب شيء")

        vehicles, people = self._bridges()
        self.stdout.write(f"الجسر: {len(vehicles):,} مركبة · {len(people):,} حساب")

        # مبالغُ المزايدات الفائزة، مقروءةً مرّةً واحدة.
        bids: dict[str, Decimal] = {}
        for row in read_table(path, "bids"):
            value = _amount(row.get("amount"))
            if value is not None:
                bids[str(row.get("id"))] = value

        seen = matched = 0
        no_vehicle = no_person = no_price = 0
        updates: list[Vehicle] = []
        for row in read_table(path, "auction_vehicles"):
            winner = row.get("winner_user_id")
            if winner in (None, "", "NULL"):
                continue
            seen += 1

            ours = vehicles.get(str(row.get("id")))
            if ours is None:
                no_vehicle += 1
                continue
            buyer = people.get(str(winner))
            if buyer is None:
                no_person += 1
                continue
            price = bids.get(str(row.get("winning_bid_id")))
            if price is None:
                no_price += 1
                continue

            matched += 1
            updates.append(
                Vehicle(
                    id=ours,
                    awarded_to_id=buyer,
                    awarded_price=price,
                    awarded_at=row.get("winner_paid_at") or timezone.now(),
                )
            )

        self.stdout.write(
            f"\nفي اللقطة: {seen:,} مركبةً لها فائز · طابق الجسرُ {matched:,}"
        )
        if no_vehicle or no_person or no_price:
            self.stdout.write("ما لم يُطابَق، بسببه:")
            if no_vehicle:
                self.stdout.write(f"  {no_vehicle:>6,}  مركبةٌ غيرُ مُرحَّلة")
            if no_person:
                self.stdout.write(f"  {no_person:>6,}  فائزٌ غيرُ مُرحَّل")
            if no_price:
                self.stdout.write(f"  {no_price:>6,}  مزايدةٌ فائزةٌ بلا مبلغٍ صالح")

        legacy_vehicle = {ours: v1 for v1, ours in vehicles.items()}
        legacy_buyer = {ours: v1 for v1, ours in people.items()}
        target = options["write_json"]
        if target:
            rows = [
                {
                    "v1_vehicle": legacy_vehicle[v.id],
                    "v1_buyer": legacy_buyer[v.awarded_to_id],
                    "price": str(v.awarded_price),
                    "at": v.awarded_at if isinstance(v.awarded_at, str) else "",
                }
                for v in updates
            ]
            Path(target).write_text(
                json.dumps(rows, ensure_ascii=False), encoding="utf8"
            )
            self.stdout.write(f"كُتب {len(rows):,} صفّاً إلى {target}")
            return

        self._apply(updates, dry=dry)

    @staticmethod
    def _bridges() -> tuple[dict[str, int], dict[str, int]]:
        """جسرا المعرّفات: مركبةُ v1 ⟶ مركبتُنا، وحسابُ v1 ⟶ حسابُنا."""
        return (
            dict(
                LegacyRef.objects.filter(model_label="auctions.vehicle").values_list(
                    "legacy_id", "object_id"
                )
            ),
            dict(
                LegacyRef.objects.filter(model_label="accounts.user").values_list(
                    "legacy_id", "object_id"
                )
            ),
        )

    def _from_json(self, source: Path, options):
        """يقرأ معرّفاتِ الترسية من ملفٍّ صغيرٍ ويكتبها — بمعرّفاتنا نحن.

        **والمعرّفاتُ في الملفّ معرّفاتُ v1 لا معرّفاتُنا**، وتُترجَم هنا
        بجسر القاعدة التي تعمل عليها. ولو حُفظت بمعرّفاتنا لكانت خطأً صامتاً:
        قاعدةُ الإنتاج كان فيها ١٬٧٦١ مركبةً قبل الترحيل، فعدّادُها بدأ من
        رقمٍ أعلى — أي أن «المركبة ٤٠٠» عندها غيرُها في قاعدة البروفة،
        والترسيةُ كانت ستُكتب على سيارةٍ أخرى.
        """
        rows = json.loads(source.read_text(encoding="utf8"))
        vehicles, people = self._bridges()
        self.stdout.write(f"من الملفّ: {len(rows):,} ترسية")

        updates, lost = [], 0
        for row in rows:
            ours = vehicles.get(str(row["v1_vehicle"]))
            buyer = people.get(str(row["v1_buyer"]))
            if ours is None or buyer is None:
                lost += 1
                continue
            updates.append(
                Vehicle(
                    id=ours,
                    awarded_to_id=buyer,
                    awarded_price=Decimal(row["price"]),
                    awarded_at=row["at"] or timezone.now(),
                )
            )
        self.stdout.write(f"طابق الجسرُ: {len(updates):,} · سقط: {lost:,}")
        self._apply(updates, dry=options["dry_run"])

    def _apply(self, updates: list[Vehicle], *, dry: bool = False):
        # ما سيُكتب فعلاً: الفارغُ وحدَه، وبلا ما قرّره إنسانٌ بعد الترحيل.
        ids = [v.id for v in updates]
        open_now = set(
            Vehicle.objects.filter(id__in=ids, awarded_to__isnull=True)
            .exclude(state__in=DECIDED)
            .values_list("id", flat=True)
        )
        skipped = len(ids) - len(open_now)
        self.stdout.write(f"سيُكتب: {len(open_now):,} · يُترك كما هو: {skipped:,}")

        if dry or not open_now:
            self.stdout.write("انتهى — لا كتابة.")
            return

        # الحالةُ من المال: المسدَّدُ «مسدَّدة»، والمفوترُ «مفوترة»، والباقي
        # «مرسّاة». والاستعلامان مرّةً واحدةً لا مرّةً لكلّ صفّ.
        paid = set(
            Invoice.objects.filter(
                vehicle_id__in=open_now, state=InvoiceState.PAID
            ).values_list("vehicle_id", flat=True)
        )
        invoiced = (
            set(
                Invoice.objects.filter(vehicle_id__in=open_now)
                .exclude(state=InvoiceState.CANCELLED)
                .values_list("vehicle_id", flat=True)
            )
            - paid
        )

        write = [v for v in updates if v.id in open_now]
        for vehicle in write:
            if vehicle.id in paid:
                vehicle.state = VehicleState.PAID
            elif vehicle.id in invoiced:
                vehicle.state = VehicleState.INVOICED
            else:
                vehicle.state = VehicleState.AWARDED

        with transaction.atomic():
            Vehicle.objects.bulk_update(
                write,
                ["awarded_to", "awarded_price", "awarded_at", "state"],
                batch_size=500,
            )

        self.stdout.write(
            f"\nكُتبت {len(write):,} ترسية: "
            f"{len(paid):,} مسدَّدة · {len(invoiced):,} مفوترة · "
            f"{len(write) - len(paid) - len(invoiced):,} مرسّاة"
        )
        self.stdout.write(f"العملاءُ الفائزون: {len({v.awarded_to_id for v in write}):,}")
