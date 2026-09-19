"""نقلُ صور سيّارات v1 إلى v2. T950.

## لماذا كان هذا آخرَ ما نُقل

كلُّ شيءٍ آخر نُقل من الدَّمب: العملاء، والمركبات، والفواتير، وطلباتُ
الاسترداد. والصورُ **ليست في الدَّمب** — فيه أسماءُ ملفّاتها فقط
(`car_images.image`)، والملفّاتُ نفسُها ثلاثةَ عشرَ جيجابايتاً على قرص خادم v1
تحت `admin/includes/add_imags/uploads/`.

فبقيت الرئيسيّةُ تقول «لا توجد صورة» في كلّ كرت، وقِيس في ١٩ سبتمبر ٢٠٢٦:
`thumbnail_url = null` في أربعٍ وثلاثين مركبةً من أربعٍ وثلاثين.

## والمانيفست من الدَّمب لا من قاعدة v1

`car_images` موجودٌ في `hara_clone_v1_data_*.sql.gz`، فيُستخرج منه جدولٌ
بسيط — معرّفُ السيّارة إلى أسماء ملفّاتها — **ولا يُفتَح اتّصالٌ بقاعدة
الإنتاج الحيّة**. قِيس: 92,024 صورةً لـ8,471 سيّارة، أي نحو إحدى عشرةَ لكلّ
سيّارة.

و**الملفّات** وحدَها تُقرأ من الخادم، بـ`tar` يبثّ على الأنبوب بلا كتابةِ
ملفٍّ مؤقّتٍ هناك — v1 نظامُ إنتاجٍ حيٌّ للقراءة فقط.

## ولا يُنقَل كلُّ شيء

ثلاثةَ عشرَ جيجابايتاً لا معنى لجلبها كلِّها إلى قرص تطويرٍ لنرى شبكةَ كروت.
فالأمرُ يأخذ `--vehicles` و`--per-vehicle`، ويأخذ الأحدثَ أوّلاً (المزادات
الأخيرة هي التي تُفتح)، ويتخطّى ما له صورةٌ أصلاً — فإعادةُ تشغيله لا
تُضاعف شيئاً.

والحزمةُ الواحدة `tar` لا ملفٌّ ملفٌّ: مئتا ملفٍّ بمئتي جلسةِ SSH دقائق،
وبجلسةٍ واحدة ثوانٍ.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.auctions.models import Vehicle, VehicleImage
from apps.auctions.services import add_image
from apps.migration.models import LegacyRef

#: مجلّدُ الصور على خادم v1. مطلقٌ لأن `tar -C` يحتاجه، ومكتوبٌ هنا لأنه
#: حقيقةٌ عن نظامٍ آخر لا إعدادٌ لنا — من غيّره هناك يُغيّره هنا بقصد.
V1_UPLOADS = "/home/hara/public_html/application/admin/includes/add_imags/uploads"

#: اسمُ المضيف في `~/.ssh/config`، لا عنوانٌ ولا مفتاح: المفاتيحُ لا تُكتب في
#: المستودع (المادة ٥-٣)، والاسمُ المستعار يحمل المفتاحَ والمستخدم.
V1_HOST = "haraj1"


class Command(BaseCommand):
    help = "ينقل صور السيّارات من قرص v1 إلى مركبات v2 المناظرة."

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            required=True,
            help="ملفُّ JSON: {«معرّف سيّارة v1»: [أسماء الملفّات]}.",
        )
        parser.add_argument(
            "--vehicles",
            type=int,
            default=40,
            help="كم مركبةً تُعالَج في هذه الدفعة (الأحدثُ أوّلاً).",
        )
        parser.add_argument(
            "--per-vehicle",
            type=int,
            default=6,
            help="كم صورةً لكلّ مركبة. الأولى تصير الغلاف.",
        )
        parser.add_argument(
            "--ids",
            default="",
            help="معرّفاتُ مركبات v2 بالفاصلة — تتجاوز `--vehicles`.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="يقول ماذا سيجلب ولا يجلب.",
        )

    def handle(self, *args, **options):
        manifest = self._manifest(options["manifest"])
        wanted = self._targets(manifest, options)

        if not wanted:
            self.stdout.write("لا مركبةَ تنطبق — إمّا لا صور لها أو لها صورٌ أصلاً.")
            return

        files = sum(len(names) for _, names in wanted)
        self.stdout.write(
            f"{len(wanted)} مركبةً · {files} ملفاً من {V1_HOST}:{V1_UPLOADS}"
        )
        if options["dry_run"]:
            for vehicle, names in wanted[:10]:
                self.stdout.write(f"  {vehicle.id} ← {len(names)}: {names[0]}")
            return

        staging = Path(tempfile.mkdtemp(prefix="v1-images-"))
        try:
            self._fetch(sorted({n for _, names in wanted for n in names}), staging)
            self._attach(wanted, staging, options["per_vehicle"])
        finally:
            # المرحلةُ مؤقّتة بحقّ: `add_image` نسخ البايتات إلى التخزين وولّد
            # الطبقات، فلا شيء هنا يُحتاج بعدها.
            shutil.rmtree(staging, ignore_errors=True)

    # -- المانيفست والأهداف ------------------------------------------------

    def _manifest(self, path: str) -> dict[int, list[str]]:
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as error:
            raise CommandError(f"تعذّرت قراءة المانيفست: {error}") from error
        return {int(k): v for k, v in raw.items()}

    def _targets(self, manifest, options) -> list[tuple[Vehicle, list[str]]]:
        """المركباتُ التي لها مقابلٌ في v1 **ولا صورةَ لها عندنا بعد**.

        الربطُ عبر `LegacyRef` لا عبر تطابق المعرّفات: صحَّ التطابقُ في
        الصفوف الأولى ولا يصحّ في كلّها، ومطابقةُ رقمٍ برقمٍ هي بالضبط كيف
        تُلصَق صورُ سيّارةٍ بسيّارةٍ أخرى.
        """
        refs = {
            int(legacy): object_id
            for legacy, object_id in LegacyRef.objects.filter(
                model_label="auctions.vehicle"
            ).values_list("legacy_id", "object_id")
            if legacy.isdigit()
        }

        explicit = {
            int(part) for part in options["ids"].split(",") if part.strip().isdigit()
        }

        # مركباتُنا التي لها صورٌ هناك، منسوبةً إلى معرّف v1.
        by_vehicle = {
            refs[legacy]: names
            for legacy, names in manifest.items()
            if legacy in refs and names
        }
        if explicit:
            by_vehicle = {k: v for k, v in by_vehicle.items() if k in explicit}

        # **ما له صورةٌ أصلاً يُتخطّى** — فالأمرُ يُعاد تشغيله بلا مضاعفة.
        already = set(
            VehicleImage.objects.filter(vehicle_id__in=by_vehicle)
            .values_list("vehicle_id", flat=True)
            .distinct()
        )
        candidates = [v for v in by_vehicle if v not in already]

        # الأحدثُ أوّلاً: المزاداتُ الأخيرة هي التي تُفتح، وصورةٌ لسيّارةٍ
        # بيعت قبل سنتين لا يراها أحد.
        order = {
            vehicle.id: vehicle
            for vehicle in Vehicle.objects.filter(id__in=candidates).order_by("-id")
        }
        limit = len(order) if explicit else options["vehicles"]
        picked = list(order.values())[:limit]

        return [(v, by_vehicle[v.id][: options["per_vehicle"]]) for v in picked]

    # -- الجلب والإلصاق ----------------------------------------------------

    def _fetch(self, names: list[str], into: Path) -> None:
        """يجلب الملفّات المسمّاة في **جلسةٍ واحدة**، بلا كتابةٍ على v1.

        `tar -czf -` يبثّ على المخرج القياسيّ، و`-T -` يقرأ قائمةَ الأسماء من
        المدخل القياسيّ — فلا سطرُ أوامرَ طويل ولا ملفُّ قائمةٍ يُكتب هناك.
        و`--ignore-failed-read` لأن صفّاً في `car_images` قد يشير إلى ملفٍّ
        حُذف من القرص: ملفٌّ مفقودٌ يُتخطّى ولا يُسقط الدفعة.
        """
        command = [
            "ssh",
            "-o",
            "BatchMode=yes",
            V1_HOST,
            f"tar -czf - --ignore-failed-read -C {V1_UPLOADS} -T -",
        ]
        self.stdout.write(f"… جلبُ {len(names)} ملفاً في جلسةٍ واحدة")
        process = subprocess.run(  # noqa: S603
            command,
            input=("\n".join(names) + "\n").encode(),
            capture_output=True,
            check=False,
        )
        if not process.stdout:
            raise CommandError(
                "لم يصل شيء من v1: " + process.stderr.decode(errors="replace")[-400:]
            )

        archive = into / "bundle.tar.gz"
        archive.write_bytes(process.stdout)
        with tarfile.open(archive) as bundle:
            bundle.extractall(into, filter="data")
        archive.unlink()
        landed = sum(1 for _ in into.glob("*"))
        self.stdout.write(f"  وصل {landed} ملفاً ({len(process.stdout) // 1024} ك.ب)")

    def _attach(self, wanted, staging: Path, per_vehicle: int) -> None:
        """يُنشئ الصفوفَ عبر `add_image` وحدَه.

        وهو البابُ الوحيد بقصد: يُعقّم البايتات، ويُسمّي الملفَّ بنفسه، ويولّد
        الطبقتين (400×300 و1280×960) في المعاملة نفسِها. ونسخُ الملفّ إلى
        التخزين مباشرةً كان سيترك صفوفاً بلا طبقاتٍ ترى الشاشةُ فيها الأصلَ
        كاملاً — وذاك هو حادثُ الثلاثةَ عشرَ جيجابايتاً في v1 بعينه.
        """
        attached = missing = 0
        for vehicle, names in wanted:
            for position, name in enumerate(names[:per_vehicle]):
                source = staging / name
                if not source.exists():
                    missing += 1
                    continue
                with source.open("rb") as handle:
                    add_image(
                        vehicle=vehicle,
                        file=File(handle, name=name),
                        position=position,
                        cover=position == 0,
                    )
                attached += 1
            self.stdout.write(
                f"  {vehicle.id} · {vehicle.make} {vehicle.model} {vehicle.year}"
            )

        covered = (
            Vehicle.objects.filter(id__in=[v.id for v, _ in wanted])
            .annotate(shots=Count("images"))
            .filter(shots__gt=0)
            .count()
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{attached} صورةً على {covered} مركبة"
                + (f" · {missing} ملفاً مفقوداً على قرص v1" if missing else "")
            )
        )
