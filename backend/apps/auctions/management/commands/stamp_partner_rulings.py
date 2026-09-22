"""اختم حكمَ الشريك على ما حُسم أمرُه قبل الاستيراد.

**العطل، مقيساً.** على سيرفر التجربة **١٤٢** مركبةً مسدَّدةً و**٢٨** مفوترةً
عليها `partner_decided_at = NULL`. فشاشةُ «اتخاذ القرار» تقرؤها «بانتظار
قرارك» — وهي مباعةٌ ومقبوضٌ ثمنُها. وv1 على البيانات نفسِها يقرؤها «قبلتها»
لأن العمودَ عنده مكتوب، والاستيرادُ لم ينقله.

**والحكمُ يُقرأ من الواقعة لا يُخمَّن.** مركبةٌ رستْ ثم فُوترت ثم سُدِّدت =
الشريكُ قَبِل — وإلّا ما وقعت الترسية أصلاً؛ ومركبةٌ حالتُها «مرفوضة» =
رفض. وما سوى هاتين (معروضة، تحت المزايدة، بانتظار قرار المالك، مسحوبة)
**لا يُختَم**: لم يُحسم أمرُها، والختمُ عليها كذبٌ يقفل بابَ القرار.

**ويمرّ بالخدمة** (`record_partner_ruling`): تقفل الصفَّ، وترفض ختماً ثانياً،
وترفض الحكمَ قبل انتهاء المزاد. ولا يُكتب العمودُ بـ`update()` — وإلّا خُتم
حكمٌ على مزادٍ لم ينتهِ، وهو الشرطُ الوحيد الذي يحمله v1 نفسُه.

و`partner_decided_by` يبقى **فارغاً**: لا أحدَ حكم في هذا النظام، والختمُ
نقلٌ لواقعةٍ سابقة. واسمُ مستخدمٍ هنا يخترع صاحبَ قرارٍ لم يقرّر.

ويُعاد تشغيلُه بلا ضرر: لا يمسّ مركبةً مختومةً، ولا يغيّر حالةَ مركبة.

    python manage.py stamp_partner_rulings --dry-run
    python manage.py stamp_partner_rulings
"""

from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from apps.auctions.models import PartnerDecision, Vehicle
from apps.auctions.services import record_partner_ruling
from apps.auctions.states import VehicleState

#: حُسم أمرُها بيعاً — والترسيةُ لا تقع على سيارة شريكٍ إلّا بقبوله.
SOLD = (
    VehicleState.AWARDED,
    VehicleState.INVOICED,
    VehicleState.PAID,
    VehicleState.RELEASED,
)


class Command(BaseCommand):
    help = "اختم حكم الشريك على المركبات التي حُسم أمرها قبل الاستيراد."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب.")

    def handle(self, *args, **options):
        rows = list(
            Vehicle.objects.filter(
                is_marketing=True,
                partner_decided_at__isnull=True,
                state__in=(*SOLD, VehicleState.REJECTED),
            )
            .select_related("auction", "awarded_to")
            .order_by("auction__number", "lot_number")
        )

        counts = Counter(v.state for v in rows)
        for state, n in sorted(counts.items()):
            self.stdout.write(f"  {state}: {n}")
        self.stdout.write(f"بلا ختمٍ وقد حُسم أمرُها: {len(rows)}")
        if not rows:
            self.stdout.write(self.style.SUCCESS("لا شيءَ يُختَم."))
            return
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("تجربةٌ بلا كتابة."))
            return

        # واحدةً بعد واحدة: رفضُ السابعة لا يُلغي ستّاً، ويُقال أيُّها رُدَّت
        # ولماذا — كما في الحكم الجماعيّ في الشاشة.
        stamped, failed, first_why = 0, 0, ""
        for vehicle in rows:
            decision = (
                PartnerDecision.REJECTED
                if vehicle.state == VehicleState.REJECTED
                else PartnerDecision.ACCEPTED
            )
            # والمزايدةُ التي رستْ — لا أعلى عرضٍ يُعاد حسابُه: مركبةٌ رستْ
            # على الثاني تعرض رقمَ الأوّل، والرقمُ يدخل حديثَ الفاتورة.
            bid = None
            if decision == PartnerDecision.ACCEPTED and vehicle.awarded_to_id:
                bid = (
                    vehicle.bids.filter(
                        bidder_id=vehicle.awarded_to_id, amount=vehicle.awarded_price
                    )
                    .order_by("-placed_at")
                    .first()
                )
            try:
                record_partner_ruling(
                    vehicle, decision=decision, actor=None, bid=bid
                )
                stamped += 1
            except Exception as refusal:
                failed += 1
                first_why = first_why or f"{vehicle.pk}: {refusal}"

        self.stdout.write(self.style.SUCCESS(f"خُتمت {stamped} مركبة."))
        if failed:
            self.stdout.write(self.style.ERROR(f"وردّت {failed} — أوّلُها {first_why}"))
        self.stdout.write(
            "بلا ختمٍ بعده: "
            + str(
                Vehicle.objects.filter(
                    is_marketing=True,
                    partner_decided_at__isnull=True,
                    state__in=(*SOLD, VehicleState.REJECTED),
                ).count()
            )
        )
