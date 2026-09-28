"""طابِق أرصدةَ العملاء مع أودو، واكتب الفروق — المادة ٢-٥.

**العطل، مقيساً على سيرفر التجربة.** `apps/odoo/reconciliation.py` مكتوبٌ
كاملاً: يحسب رصيدَ أودو، ويقارنه برصيدنا، و«الفرقُ يفتح سجلّاً ولا يحرّك
ريالاً». و**لا شيءَ في المشروع كلِّه ينادِيه**: لا أمرٌ ولا مهمّةٌ ولا مؤقّت
(`grep` على `reconciliation.` يُرجع تعليقين). أي أن قاعدةَ «تُطابَق سجلاتُ
المنصّة **دورياً** مع النظام المحاسبيّ» بلا يدٍ تنفّذها.

وتوثيقُ الوحدة نفسِه يقول لماذا تهمّ: «رصيدُ عميلٍ في v1 يقول ١٠٬٠٠٠ فزايد
به، ودفترُ أودو له يُقفل على صفر — وكلُّ حارسٍ بُني يومها كان يفحص أرقامَنا
بأرقامنا».

**ولا يحرّك ريالاً.** يقرأ ويكتب صفَّ مقارنةٍ فقط: تسويةُ الفرق بالكتابة في
الدفتر تصحيحٌ لدفتر القيد بالنسخة — والقرارُ لإنسان.

**وواحداً بعد واحد لا دفعةً**: فشلُ عميلٍ (رابطٌ ميّت، حالةٌ لم تُرَ من قبل)
لا يُوقف البقيّة، ويُقال أيُّهم ولماذا — كما في الحكم الجماعيّ.

    python manage.py reconcile_balances --dry-run
    python manage.py reconcile_balances
    python manage.py reconcile_balances --limit 200
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.odoo import reconciliation
from apps.odoo.models import CustomerLink


class Command(BaseCommand):
    help = "طابق أرصدة العملاء مع أودو واكتب الفروق."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="اقرأ ولا تكتب.")
        parser.add_argument(
            "--limit", type=int, default=0, help="عدد العملاء (0 = الكلّ)."
        )

    def handle(self, *args, **options):
        # **والتكاملُ المطفأ يُقال مرّةً لا أربعةَ عشرَ ألفاً.** أوّلُ تشغيلٍ
        # للوحدة الليليّة طبع «تعذّر: 14706 — تكامل أودو مطفأ في هذه البيئة»:
        # سطرٌ صحيحٌ في معناه، كاذبٌ في هيئته — يقرأ من يراه أن أربعةَ عشرَ
        # ألفَ عميلٍ فشلوا، والواقعُ إعدادٌ واحدٌ مغلق. وسطرٌ كهذا كلَّ ليلةٍ
        # يُعلّم الناسَ تجاهلَ المخرَج، فيختفي فيه فشلٌ حقيقيٌّ يوم يقع.
        if not settings.ODOO_ENABLED:
            self.stdout.write(
                self.style.WARNING(
                    "تكاملُ أودو مطفأ في هذه البيئة (ODOO_ENABLED=False) — "
                    "لا مطابقة. اضبطه لتعمل."
                )
            )
            return

        links = CustomerLink.objects.select_related("user").order_by("pk")
        if options["limit"]:
            links = links[: options["limit"]]
        links = list(links)

        self.stdout.write(f"عملاءُ مربوطون بأودو: {len(links)}")
        if not links:
            # ليس نجاحاً صامتاً: صفرُ روابطَ يعني أن المطابقةَ لا تفحص شيئاً،
            # وقراءةُ «تمّت» على صفرِ عملاءَ هي بالضبط كيف يُظنّ أن الحارس
            # يعمل وهو لا يفحص أحداً.
            self.stdout.write(
                self.style.WARNING(
                    "لا رابطَ عميلٍ بأودو — المطابقةُ لم تفحص أحداً. "
                    "ابنِ الروابط أوّلاً."
                )
            )
            return
        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("تجربةٌ بلا كتابة."))
            return

        agreed, differed, failed, first_why = 0, 0, 0, ""
        for link in links:
            try:
                result = reconciliation.check_customer(link)
            except Exception as refusal:
                failed += 1
                first_why = first_why or f"{link.odoo_customer_id}: {refusal}"
                continue
            # الاتّفاقُ فرقٌ صفريّ: `BalanceCheck` تحمل `difference` ولا
            # تحمل رايةً — والرايةُ المشتقّةُ في مكانين تتفارق.
            if getattr(result, "difference", 0):
                differed += 1
            else:
                agreed += 1

        self.stdout.write(self.style.SUCCESS(f"متطابقون: {agreed}"))
        if differed:
            self.stdout.write(self.style.ERROR(f"فروقٌ مفتوحة: {differed}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"تعذّر: {failed} — أوّلُها {first_why}"))

        still_open = len(list(reconciliation.open_differences()))
        self.stdout.write(f"فروقٌ قائمةٌ بعد هذه الجولة: {still_open}")
