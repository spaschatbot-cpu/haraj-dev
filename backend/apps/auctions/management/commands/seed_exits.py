"""بياناتُ تجربةٍ للسان «متابعة نقل الملكية» — كلُّ حالةٍ تُرى مرّةً واحدة.

اللسانُ كان يُفحَص على صفٍّ واحدٍ أو صفر، فلا تُرى فيه حالةٌ إلا بالمصادفة:
خمسُ حالاتٍ في عمود «الغرض/الحالة» وأربعُ درجاتٍ في «المؤقّت» تعني **عشرين
احتمالاً** لا يُنتجها سيرُ العمل الطبيعيّ في جلسةٍ واحدة — تنبيهُ المالك وحده
يحتاج مركبةً خرجت قبل ثلاثين يوماً.

فهذه ثمانيةُ صفوفٍ مصنوعة: ستٌّ في المتابعة تغطّي الحالاتِ والعتباتِ كلَّها،
واثنتان في الأرشيف (بنقلٍ بعد الخروج، وبخروجٍ بعد النقل) ليُقاس اللسانُ الثالث.

  python manage.py seed_exits            # يُضيف ما ينقص
  python manage.py seed_exits --reset    # يحذف ما صنعه هذا الأمر ثم يُعيده

**ولا يعمل إلا على `DEBUG`.** الأمرُ يكتب مركباتٍ وأوامرَ خروجٍ ملفّقة، وقاعدةُ
الإنتاج فيها مركباتٌ حقيقيّةٌ بأرقام مطالباتٍ حقيقيّة — وأمرٌ كهذا يُشغَّل هناك
مرّةً بالخطأ يُدخل ثمانيةَ أوامرِ خروجٍ في طابور عملٍ يتابعه موظّفون.

ويُميَّز ما صنعه بـ`vin` يبدأ بـ`SEEDEXIT` — فـ`--reset` يحذف صفَّه هو ولا
يقترب من صفٍّ كتبه إنسان.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.exits import ExitReason, ExitStage, ExitType, VehicleExit
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import VehicleState

#: علامةُ ما صنعه هذا الأمر — بادئةُ `vin`.
MARK = "SEEDEXIT"

#: (لاحقة، ماركة، موديل، سنة، أيامٌ منذ الخروج، مرحلة، نوع، سبب، حظرٌ رُفع، ملاحظة)
ROWS = [
    (
        "01", "تويوتا", "هايلكس", 2021, 3,
        ExitStage.UNDER_TRANSFER, ExitType.WITHOUT_TRANSFER, ExitReason.NO_PROBLEM,
        False, "المشتري حجز موعد المرور يوم الخميس.",
    ),
    (
        "02", "نيسان", "باترول", 2019, 12,
        ExitStage.UNDER_TRANSFER, ExitType.REPAIR_INSPECTION, ExitReason.NO_PROBLEM,
        False, "في الورشة — بانتظار تقرير الفحص.",
    ),
    (
        "03", "هيونداي", "سوناتا", 2020, 18,
        ExitStage.UNDER_TRANSFER, ExitType.WITHOUT_TRANSFER,
        ExitReason.NO_PLATES_NO_INSPECTION, False,
        "لا فحص ولا لوحات — أُبلغ العميل مرّتين.",
    ),
    (
        "04", "شفروليه", "تاهو", 2022, 27,
        ExitStage.UNDER_TRANSFER, ExitType.WITHOUT_TRANSFER,
        ExitReason.NO_PLATES_BAN, False,
        "حظر على المركبة — الملف عند المحامي.",
    ),
    (
        "05", "فورد", "F-150", 2018, 34,
        ExitStage.UNDER_TRANSFER, ExitType.WITHOUT_TRANSFER,
        ExitReason.NO_PLATES_BAN, True,
        "رُفع الحظر، ويُتابَع النقل الآن بشكل عادي.",
    ),
    (
        "06", "مازدا", "CX-9", 2023, 31,
        ExitStage.UNDER_TRANSFER, ExitType.WITHOUT_TRANSFER, ExitReason.NO_PROBLEM,
        False, "لا ردّ من المشتري منذ أسبوعين.",
    ),
    (
        "07", "لكزس", "LX 570", 2021, 40,
        ExitStage.ARCHIVED, ExitType.WITHOUT_TRANSFER, ExitReason.NO_PROBLEM,
        False, "نُقلت الملكية بعد الخروج بأسبوع.",
    ),
    (
        "08", "جي إم سي", "يوكن", 2020, 9,
        ExitStage.ARCHIVED, ExitType.AFTER_TRANSFER, "",
        False, "خرجت بعد نقل الملكية — أُرشفت من البوابة.",
    ),
]


class Command(BaseCommand):
    help = "بيانات تجربة للسان متابعة نقل الملكية (DEBUG فقط)"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="احذف ما صنعه هذا الأمر سابقاً ثم أعِد بناءه",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError("لا يعمل إلا على DEBUG — هذه بياناتٌ ملفّقة.")

        auction = Auction.objects.order_by("-number").first()
        if auction is None:
            raise CommandError("لا مزادَ في القاعدة. شغّل seed_demo أولاً.")

        buyer = (
            User.objects.filter(is_staff=False, is_active=True)
            .order_by("id")
            .first()
        )
        if buyer is None:
            raise CommandError("لا عميلَ في القاعدة. شغّل seed_demo أولاً.")

        if options["reset"]:
            made = Vehicle.objects.filter(vin__startswith=MARK)
            # أوامرُ الخروج أولاً: `vehicle` عليها `PROTECT`، فحذفُ المركبة
            # قبلها يرفع `ProtectedError` في منتصف المعاملة.
            gone = VehicleExit.objects.filter(vehicle__in=made).delete()[0]
            gone += made.delete()[0]
            self.stdout.write(f"حُذف {gone} صفّاً من بيانات التجربة السابقة.")

        now = timezone.now()
        # اللوتُ فريدٌ داخل المزاد، فيُبدأ بعد آخر ما فيه لا من واحد.
        next_lot = (
            Vehicle.objects.filter(auction=auction)
            .order_by("-lot_number")
            .values_list("lot_number", flat=True)
            .first()
            or 0
        )

        made = 0
        for i, row in enumerate(ROWS):
            (
                suffix, make, model, year, days,
                stage, exit_type, reason, ban_lifted, note,
            ) = row
            vin = f"{MARK}{suffix}"
            if Vehicle.objects.filter(vin=vin).exists():
                continue

            exited_at = now - timedelta(days=days)
            vehicle = Vehicle.objects.create(
                auction=auction,
                lot_number=next_lot + i + 1,
                make=make,
                model=model,
                year=year,
                vin=vin,
                plate_number=f"ت ج ر {7100 + i}",
                claim_number=f"CLM-2026-{4300 + i}",
                state=VehicleState.RELEASED,
                awarded_to=buyer,
                awarded_price=45000 + i * 1500,
                awarded_at=exited_at - timedelta(days=5),
            )
            VehicleExit.objects.create(
                vehicle=vehicle,
                stage=stage,
                exit_type=exit_type,
                exit_reason=reason,
                recipient_name=f"مستلِم تجريبي {suffix}",
                recipient_id=f"10987654{suffix}",
                recipient_phone=f"96650000{7100 + i}",
                warehouse_exit_at=exited_at,
                # الأرشيفُ لا يكون بلا تاريخ نقل، و`after_transfer` تاريخُ نقله
                # تاريخُ خروجه نفسُه — كما تكتبه البوّابة في `confirm_gate`.
                transfer_at=(
                    exited_at
                    if exit_type == ExitType.AFTER_TRANSFER
                    else exited_at + timedelta(days=7)
                )
                if stage == ExitStage.ARCHIVED
                else None,
                ban_lifted_at=exited_at + timedelta(days=4) if ban_lifted else None,
                notes=note,
            )
            made += 1

        follow = VehicleExit.objects.filter(stage=ExitStage.UNDER_TRANSFER).count()
        archive = VehicleExit.objects.filter(stage=ExitStage.ARCHIVED).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"أُضيف {made} أمرَ خروج. الآن: {follow} في المتابعة، "
                f"{archive} في الأرشيف."
            )
        )
