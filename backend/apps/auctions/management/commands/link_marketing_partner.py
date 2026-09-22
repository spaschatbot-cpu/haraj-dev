"""اربط مركباتِ التسويق بشركةِ الشريك — الجسرُ الذي لم ينقله الاستيراد.

**العطل، مقيساً.** شاشاتُ قسم «شريك التسويق» كلُّها تُرشَّح بـ`owner_company`
(انظر `console.partner_console._scoped`). وعلى سيرفر التجربة: ١٢٬٩٦٣ مركبةً
و٥٤ مزاداً، ومنها **٣٧٧ عليها `is_marketing = True`** — و**صفرُ** مركبةٍ لها
`owner_company`، وصفرُ صفوفٍ في `Company`. فالقسمُ كلُّه يفتح فارغاً على
بياناتٍ حقيقيّة، ويُقرأ «الشاشة لا تعمل».

**ولماذا لا يُقرأ العلمُ مباشرةً في الشاشات.** لأن v1 هو الذي يفعل ذلك
(`PartnerConsoleController::scopeSql()` = `av.is_marketing = 1`)، وشريكُه
**واحدٌ ضمنيّ** لا كيانَ له: لا جدولَ شركاء ولا ربطَ مركبةٍ بشركة. وهنا
الشريكُ `Company` لها اسمٌ وسجلٌّ وصفحاتُها تُرشَّح به — فتصير الشاشةُ تحتمل
شريكين، ويُعرف صاحبُ كلّ مركبة. والعلمُ يبقى كما استُورد، وهذا الأمرُ يبني
الجسرَ بينه وبين الكيان.

**وشركةٌ واحدة، لا شركةٌ لكلّ شركةِ تأمين.** العلمُ في v1 مربّعٌ يضعه المشرف
بيده على المركبة (`AuctionController:691`) أو عمودٌ اسمُه «التسويق» في ملفّ
الاستيراد (`:3450`) — **وليس مشتقّاً من `insurance_company`**. فاشتقاقُ
الشركاء من شركة التأمين يخترع شركاءَ لا وجودَ لهم في القديم.

ويُعاد تشغيلُه بلا ضرر: يربط ما لم يُربط، ولا يمسّ مركبةً لها مالكٌ بالفعل.

    python manage.py link_marketing_partner --dry-run
    python manage.py link_marketing_partner
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Company
from apps.auctions.models import Vehicle

#: اسمُ الشريك كما يكتبه v1 في بيانات المركبات.
PARTNER_NAME = "الشركة التعاونية للتأمين التعاوني"

#: جوّالُ حساب الشركة. لا يُستعمل للدخول — `Company` تحتاج مستخدماً
#: (`OneToOneField`)، والحسابُ هنا حاملُ الاسم لا بابُ دخول: بلا كلمة مرورٍ
#: صالحة (`set_unusable_password`) وبلا `is_staff`.
PARTNER_PHONE = "966500000377"


class Command(BaseCommand):
    help = "اربط مركبات التسويق (is_marketing) بشركة الشريك."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب.")
        parser.add_argument("--name", default=PARTNER_NAME, help="اسم الشركة.")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        name = options["name"]

        flagged = Vehicle.objects.filter(is_marketing=True)
        unlinked = flagged.filter(owner_company__isnull=True)
        self.stdout.write(f"عليها علمُ التسويق: {flagged.count()}")
        self.stdout.write(f"منها بلا شركة:      {unlinked.count()}")
        linked_now = Vehicle.objects.filter(owner_company__isnull=False).count()
        self.stdout.write(f"مركبات لها شركةٌ الآن: {linked_now}")

        if dry:
            self.stdout.write(self.style.WARNING("تجربةٌ بلا كتابة."))
            return

        if not unlinked.exists():
            self.stdout.write(self.style.SUCCESS("لا شيءَ يُربط."))
            return

        with transaction.atomic():
            company = Company.objects.filter(name=name).first()
            if company is None:
                User = get_user_model()
                user = User.objects.filter(phone=PARTNER_PHONE).first()
                if user is None:
                    user = User(phone=PARTNER_PHONE, full_name=name)
                    user.set_unusable_password()
                    user.save()
                company = Company.objects.create(user=user, name=name)
                self.stdout.write(f"أُنشئت الشركة: {company.pk} — {company.name}")
            else:
                self.stdout.write(f"الشركةُ موجودة: {company.pk} — {company.name}")

            linked = unlinked.update(owner_company=company)

        self.stdout.write(self.style.SUCCESS(f"رُبطت {linked} مركبة."))
        still_unlinked = Vehicle.objects.filter(
            is_marketing=True, owner_company__isnull=True
        ).count()
        self.stdout.write(f"بلا شركةٍ بعده: {still_unlinked}")
