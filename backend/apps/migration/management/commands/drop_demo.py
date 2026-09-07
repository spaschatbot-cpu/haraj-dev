"""يمحو بيانات العرض والقياس بعد أن حلّت محلَّها نسخةُ v1 الحقيقية. T855.

    python manage.py drop_demo --dry-run     # يعدّ ولا يمحو
    python manage.py drop_demo               # يمحو

لماذا أمرٌ لا سطرٌ في الصدفة
============================
المحوُ لا يُعكَس، وهذا يجعل **قراءتَه قبل تشغيله** جزءاً منه: ما يُمحى مكتوبٌ
هنا صراحةً، وترتيبُ المحو مكتوبٌ لأنه ليس اختيارياً، وما **لا** يُمحى مكتوبٌ
لأنه أهمُّ من الأوّل.

ما يُمحى
========
* **مزادات العرض الثلاثة** (١٠٠١ · ١٠٠٢ · ١٠٠٣) وسياراتُها وصورُها. وأرقامُها
  ليست في نسخة v1 — أرقامُ v1 هي ١…٤٠ و١٠٠٠ و١٠٠٤…١٠١٨ — فهي من البذرة وحدها.
* **العملاء التجريبيّون الستّة** (`966551111100`…`105`).
* **الدفترُ كلُّه**: خمسُمئة ألفِ معاملةٍ ومليونُ قيد. وهي بيانات قياسِ أداءٍ
  ولّدها `bench_ledger` — ومراجعُها تقولها: `cash:demo-cash-0001`. ومعها
  حساباتُها وحجوزُها وفواتيرُها.

ما لا يُمحى
===========
* **بيانات v1 الحقيقية**: أربعةٌ وخمسون مزاداً، واثنا عشر ألفَ مركبةٍ وتسعُمئة
  وتسعٌ وستّون، وأربعةٌ وأربعون ألفَ عميلٍ وثلاثةٌ وثلاثون.
* **حساباتُ الموظّفين وحسابُ المالك.** الشرطُ هنا على الاسم لا على الدور —
  ومحوُ حسابِ المالك يُغلق اللوحة على صاحبها.

ولماذا يُمحى الدفترُ كلُّه لا جزؤه
==================================
لأن القيدَ المزدوج لا يقبل نصفاً: حذفُ قيودٍ وترْكُ أخرى يجعل الحساباتِ لا
تتّزن، و`verify_ledger` يصرخ عن فرقٍ لا سبب له. ولا معاملةَ حقيقيّةً واحدة
في هذه القاعدة — الاستيرادُ لم ينقل مالاً عمداً (T854)، لأن v1 يخزّن الرصيد
رقماً محسوباً لا قيوداً تُنقَل. فالدفترُ يبدأ فارغاً ويُبنى بقيوده.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction

from apps.auctions.models import Auction, Vehicle, VehicleImage
from apps.bidding.models import Bid, BidRefusal
from apps.core.models import AuditLog
from apps.money.models import (
    Account,
    Entry,
    Hold,
    Invoice,
    PaymentIntent,
    PaymentSheet,
    RefundRequest,
    Transaction,
)

#: مزاداتُ البذرة. أرقامٌ ليست في نسخة v1، فلا تلتبس بمزادٍ حقيقيّ.
DEMO_AUCTIONS = (1001, 1002, 1003)

#: العملاء التجريبيّون، بالاسم كما تكتبه البذرة.
DEMO_CUSTOMER = "عميل تجريبي"

#: شاصي البذرة. **والوسمُ هو المعيار لا المزاد**: الاستيرادُ كتب فوق مزادَي
#: ١٠٠٤ و١٠٠٥ وجعلهما حقيقيَّين، وسياراتُ البذرة بقيت معلّقةً بهما. فيُبحث
#: عن السيارة بشاصيها لا بمزادها.
DEMO_VIN = "DEMO"


class Command(BaseCommand):
    help = "يمحو بيانات العرض والقياس بعد استيراد v1"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="عُدَّ ولا تمحُ")

    def handle(self, *args, **options):
        env = getattr(settings, "ENVIRONMENT_NAME", "")
        if env not in ("development", "test", "local"):
            raise CommandError(f"لا يُمحى إلا في بيئة تطوير — البيئة هنا {env!r}")

        User = get_user_model()
        auctions = Auction.objects.filter(number__in=DEMO_AUCTIONS)
        cars = Vehicle.objects.filter(
            models.Q(auction__in=auctions) | models.Q(vin__startswith=DEMO_VIN)
        )
        people = User.objects.filter(full_name__startswith=DEMO_CUSTOMER)

        # ومزايداتُ العميل التجريبيّ أينما وقعت: بعضُها على سياراتٍ صارت
        # تحت مزادٍ حقيقيّ بعد الاستيراد.
        bids = Bid.objects.filter(
            models.Q(vehicle__in=cars) | models.Q(bidder__in=people)
        )

        plan = [
            (
                "رفضُ مزايدات",
                BidRefusal.objects.filter(
                    models.Q(vehicle__in=cars) | models.Q(bidder__in=people)
                ),
            ),
            ("مزايدات", bids),
            # سجلُّ التدقيق يحمي المستخدم بـPROTECT. وهذه أسطرُ بذرةٍ لا
            # أفعالَ موظّفٍ حقيقيّ — تُمحى معها، ولا يُمسّ سطرٌ لغيرهم.
            ("أسطرُ تدقيقٍ للتجريبيّين", AuditLog.objects.filter(actor__in=people)),
            ("طلباتُ استرداد", RefundRequest.objects.all()),
            ("نوايا دفع", PaymentIntent.objects.all()),
            ("أوراقُ دفع", PaymentSheet.objects.all()),
            ("فواتير", Invoice.objects.all()),
            ("حجوزات", Hold.objects.all()),
            ("صورُ مركبات", VehicleImage.objects.filter(vehicle__in=cars)),
            ("مركباتُ العرض", cars),
            ("مزاداتُ العرض", auctions),
            ("قيودُ الدفتر", Entry.objects.all()),
            ("معاملات", Transaction.objects.all()),
            ("حساباتُ الدفتر", Account.objects.all()),
            ("عملاءُ تجريبيّون", people),
        ]

        if options["dry_run"]:
            self.stdout.write("عدٌّ فقط — لا يُمحى شيء\n")
            for label, rows in plan:
                self.stdout.write(f"  {rows.count():>9}  {label}")
            return

        with transaction.atomic():
            # الفائزُ يُفكّ قبل حذف المركبة: `awarded_to` مفتاحٌ إلى مستخدم،
            # وحذفُ المركبة وهي تحمله يشدّ الصفَّ الآخر معه.
            cars.update(awarded_to=None)
            # وسياراتٌ حقيقية رست على عميلٍ تجريبيّ: يُفكّ الفائزُ ولا
            # تُحذف السيارة — هي من v1.
            Vehicle.objects.filter(awarded_to__in=people).update(awarded_to=None)
            for label, rows in plan:
                removed = rows.delete()[0]
                self.stdout.write(f"  {removed:>9}  {label}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nالباقي: {Auction.objects.count()} مزاداً · "
                f"{Vehicle.objects.count()} مركبة · {User.objects.count()} مستخدماً"
            )
        )
