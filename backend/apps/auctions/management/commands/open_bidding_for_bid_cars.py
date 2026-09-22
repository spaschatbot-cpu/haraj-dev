"""انقل المركبةَ التي عليها مزايداتٌ من «معروضة» إلى «تحت المزايدة».

**العطل، مقيساً.** على سيرفر التجربة **٢٠٦** مركبةً للشريك حالتُها `listed`
وعلى الواحدة منها أربعون مزايدة، ومزادُها منتهٍ. و«قبول أعلى عرض» في شاشة
اتخاذ القرار يردّ: «لا يمكن نقل المركبة من «معروضة» إلى «مرسّاة»» — فالشاشةُ
تقبل الرفضَ ولا تقبل القبول، وهو نصفُ عملها.

**ولا يُفتح بابٌ في آلة الحالات.** `listed → awarded` نقلةٌ ممنوعةٌ عن قصد:
`bidding → awarded` وحدَها تحمل شرطَ «لها فائزٌ مسمّى»، وفتحُ الأولى يعني
ترسيةً بلا مزايدة. والخللُ في **البيان** لا في القاعدة: مركبةٌ عليها أربعون
عرضاً ليست «معروضة»، والاستيرادُ من v1 كتب المزايدات ولم ينقل الحالة — وv1
بلا آلةِ حالاتٍ أصلاً فلا شيءَ عنده يُنقل.

والنقلةُ هي نقلةُ الآلة نفسُها (`open_bidding` ← `move_vehicle`)، لا
`update()` على العمود: ما لا يمرّ بالكاتب الوحيد لا يُفحص ولا يُسجَّل.

ويُعاد تشغيلُه بلا ضرر: لا يمسّ إلا `listed` وعليها مزايدة.

    python manage.py open_bidding_for_bid_cars --dry-run
    python manage.py open_bidding_for_bid_cars
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.auctions.models import Vehicle
from apps.auctions.services import open_bidding
from apps.auctions.states import VehicleState


class Command(BaseCommand):
    help = "انقل المركبات المعروضة التي عليها مزايدات إلى «تحت المزايدة»."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب.")
        parser.add_argument(
            "--marketing",
            action="store_true",
            help="سيارات التسويق وحدها.",
        )

    def handle(self, *args, **options):
        rows = (
            Vehicle.objects.filter(state=VehicleState.LISTED)
            .annotate(bids_count=Count("bids"))
            .filter(bids_count__gt=0)
        )
        if options["marketing"]:
            rows = rows.filter(is_marketing=True)

        rows = list(rows.select_related("auction").order_by("auction__number", "lot_number"))
        self.stdout.write(f"معروضةٌ وعليها مزايدات: {len(rows)}")
        if not rows:
            self.stdout.write(self.style.SUCCESS("لا شيءَ يُنقل."))
            return
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("تجربةٌ بلا كتابة."))
            return

        # واحدةً بعد واحدة لا دفعةً: رفضُ السابعة لا يُلغي ستّاً صحيحة،
        # ويُقال أيُّها رُدَّت ولماذا — كما في الحكم الجماعيّ.
        moved, failed, first_why = 0, 0, ""
        for vehicle in rows:
            try:
                open_bidding(vehicle)
                moved += 1
            except Exception as refusal:
                failed += 1
                first_why = first_why or f"{vehicle.pk}: {refusal}"

        self.stdout.write(self.style.SUCCESS(f"نُقلت {moved} مركبة."))
        if failed:
            self.stdout.write(self.style.ERROR(f"وردّت {failed} — أوّلُها {first_why}"))
