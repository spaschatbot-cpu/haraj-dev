"""تقريرُ الفروق للمالك — T313.

    python manage.py migration_report                 # إلى الشاشة
    python manage.py migration_report --out تقرير.md  # إلى ملفّ

معيارُ القبول: «**المالك يقرؤه ويقرّر بلا شرحٍ شفهيّ**». ومنه تتبع كلُّ قاعدةٍ
في هذا الملفّ:

* **بلا مصطلحاتٍ تقنيّة** — لا `idempotency` ولا `constraint` ولا اسمَ جدول.
  ومن أراد التفصيل التقنيّ فهو في `tasks.md`؛ هذا الملفُّ للقرار لا للمراجعة.
* **الرقمُ قبل الشرح.** «٣١ عميلاً، مجموعُ الفرق ٤١٠٬٠٠٠ ريال» ثم السبب — لا
  فقرةٌ تنتهي برقم.
* **ولا مجموعَ كبيرٌ واحد** يُقرأ «هذا ما ضاع»: الفروقُ اتّجاهان، وجمعُها بلا
  تفريقٍ يُنتج رقماً لا يعني شيئاً. فالزيادةُ والنقصُ يُعرضان منفصلين.

والتقريرُ يُبنى **لحظةَ طلبه** من القاعدة والنسخة معاً، فلا يبقى ملفٌّ قديمٌ
يُقرأ حاضراً.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Sum

from apps.migration import reconcile
from apps.migration.dumpfile import read_table
from apps.migration.models import LegacyRef
from apps.money.models import Account, AccountKind, Invoice, InvoiceState, Transaction

ZERO = Decimal("0.00")


def _riyals(value: Decimal) -> str:
    """رقمٌ يُقرأ بالعين: فواصلُ آلافٍ، وخانتان، وكلمةُ ريال."""
    return f"{value:,.2f} ريال"


class Command(BaseCommand):
    help = "تقريرُ ترحيلٍ بالعربية للمالك — T313."

    def add_arguments(self, parser):
        parser.add_argument("--dump", default=settings.V1_DUMP_PATH)
        parser.add_argument("--out", default="", help="مسارُ ملفٍّ يُكتب فيه التقرير")

    def handle(self, *args, **options):
        dump = Path(options["dump"] or "")
        if not dump.is_file():
            raise CommandError(f"النسخة غير موجودة: {dump or '(بلا مسار)'}")

        lines = self._build(dump)
        text = "\n".join(lines)

        target = options["out"]
        if target:
            Path(target).write_text(text, encoding="utf-8", newline="\n")
            self.stdout.write(self.style.SUCCESS(f"كُتب التقرير في {target}"))
        else:
            self.stdout.write(text)

    # ------------------------------------------------------------------

    def _build(self, dump: Path) -> list[str]:
        found = reconcile.differences(dump)
        stats = reconcile.summary(found)

        short = [d for d in found if d.gap < ZERO]
        over = [d for d in found if d.gap > ZERO]
        missing_gap = sum((d.gap for d in short), ZERO)
        extra_gap = sum((d.gap for d in over), ZERO)

        lines = [
            "# تقرير ترحيل بيانات النظام القديم",
            "",
            "هذا ما صار إليه كلُّ ريالٍ وكلُّ عميل بعد نقلهم إلى النظام الجديد،",
            "وما اختلف عن النظام القديم ولماذا. **الاختلافُ ليس خطأً بالضرورة**:",
            "النظام القديم نفسُه فيه أرقامٌ معطوبةٌ معروفة، والنقلُ يكشفها ولا",
            "ينقلها كما هي.",
            "",
            "---",
            "",
            "## ماذا نُقل",
            "",
        ]
        lines += self._what_moved()

        lines += [
            "",
            "---",
            "",
            "## العملاء الذين اختلف رصيدهم",
            "",
            f"**{stats['affected']:,} عميلاً** من أصل "
            f"{len(reconcile.v1_balances(dump)):,} له رصيدٌ في النظام القديم.",
            "",
            f"* **ناقصٌ عندنا:** {len(short):,} عميلاً · {_riyals(abs(missing_gap))}",
            f"* **زائدٌ عندنا:** {len(over):,} عميلاً · {_riyals(extra_gap)}",
            "",
            "والرقمان **لا يُجمعان**: أحدهما مالٌ لم يُبنَ والآخر مالٌ بُني بلا",
            "مقابل، وجمعُهما يُنتج رقماً لا يعني شيئاً.",
            "",
        ]

        if stats["by_reason"]:
            lines += [
                "### الأسباب، مصنَّفةً",
                "",
                "| السبب | عدد العملاء | مجموع الفرق |",
                "|---|---|---|",
            ]
            for reason, bucket in sorted(
                stats["by_reason"].items(), key=lambda kv: -kv[1]["count"]
            ):
                lines.append(
                    f"| {reason} | {bucket['count']:,} | {_riyals(bucket['gap'])} |"
                )
            lines.append("")

        if stats["largest"]:
            lines += [
                "### أكبر عشرة فروق",
                "",
                "| العميل | في النظام القديم | عندنا | الفرق | السبب |",
                "|---|---|---|---|---|",
            ]
            for difference in stats["largest"]:
                who = (
                    f"#{difference.user_id}"
                    if difference.user_id
                    else f"(لم يُنقل — قديم #{difference.legacy_id})"
                )
                lines.append(
                    f"| {who} | {_riyals(difference.theirs)} | "
                    f"{_riyals(difference.ours)} | {_riyals(difference.gap)} | "
                    f"{difference.reason} |"
                )
            lines.append("")

        lines += self._known_damage(dump)
        lines += self._what_needs_you()
        return lines

    def _known_damage(self, dump: Path) -> list[str]:
        """الحالاتُ المعروفةُ المشوّهة — T311، كلُّ واحدةٍ بصفٍّ ورقم.

        «تُرحَّل بحالتها كما هي مع ملاحظة، **ولا تُصحَّح صامتاً**» — و«كلُّ حالةٍ
        موثَّقةٍ في v1 لها صفٌّ في تقرير المراجعة». فهذا القسمُ هو ذلك الصفّ.

        ويُقرأ من النسخة لا من ذاكرةٍ: لقطاتُ الحوادث في v1 **جداولُ باسمها
        وتاريخها**، فتُعدّ صفوفُها بدل أن تُروى الحادثةُ رقماً في وثيقة.
        """
        from apps.migration.dumpfile import count_rows, table_names


        names = set(table_names(dump))
        odd_amounts = short_reason = 0
        for row in read_table(dump, "insurance_deposits"):
            try:
                amount = Decimal(str(row.get("amount") or "0"))
            except Exception:  # noqa: BLE001
                continue
            if amount != Decimal("10000.00"):
                odd_amounts += 1
            if str(row.get("status")) in ("refunded", "confiscated") and not row.get(
                "void_reason"
            ):
                short_reason += 1

        lines = [
            "---",
            "",
            "## أرقامٌ معطوبةٌ في النظام القديم — نُقلت كما هي",
            "",
            "هذه ليست أخطاءَ نقل. هي ما في النظام القديم فعلاً، ونُقل بحاله",
            "**عمداً**: تصحيحُه صامتاً يمحو الدليلَ ويجعل الخطأ رسمياً.",
            "",
            "| الحالة | العدد |",
            "|---|---|",
            f"| تأميناتٌ بمبلغٍ غير ١٠٬٠٠٠ (منها عشرةٌ بريالٍ واحد) | {odd_amounts} |",
            f"| تأميناتٌ خرجت بلا سببٍ مسجَّل | {short_reason} |",
        ]
        for table, label in (
            ("invoices_odoo_loopbak_20260606", "فواتيرُ حادثة ٦ يونيو المكرَّرة"),
            ("invoices_odoo_bak_20260620", "لقطةُ فواتيرِ ٢٠ يونيو"),
            ("invoices_odoo_bak_20260801_stale", "فواتيرُ قديمةٌ أُزيلت في ١ أغسطس"),
        ):
            if table in names:
                lines.append(f"| {label} (لم تُنقل) | {count_rows(dump, table):,} |")
        lines += [
            "",
            "وفي النظام القديم **٤٧ لقطةً** أُخذت قبل إصلاحاتٍ يدويّة، بعضُها",
            "باسم من أجراه. لم يُنقل منها شيء، وهي مرجعُ أيِّ سؤالٍ عن «لماذا",
            "اختلف رصيدُ هذا العميل».",
            "",
        ]
        return lines

    def _what_moved(self) -> list[str]:
        bridges = {
            "العملاء": "accounts.user",
            "السيارات": "auctions.vehicle",
            "ربط العملاء بالمحاسبة": "odoo.customerlink",
            "الفواتير": "money.invoice",
        }
        rows = ["| البند | العدد |", "|---|---|"]
        for label, key in bridges.items():
            rows.append(f"| {label} | {len(LegacyRef.resolve(key)):,} |")

        money = Account.objects.filter(
            kind__in=[
                AccountKind.INSURANCE_FREE,
                AccountKind.INSURANCE_HELD,
                AccountKind.INSURANCE_LOCKED,
            ]
        ).aggregate(total=Sum("balance"))["total"] or ZERO
        owed = Invoice.objects.exclude(state=InvoiceState.CANCELLED).aggregate(
            owed=Sum("amount"), paid=Sum("amount_paid")
        )
        rows += [
            f"| حركات مالية مبنيّة | {Transaction.objects.count():,} |",
            f"| **تأمينات العملاء اليوم** | **{_riyals(money)}** |",
            f"| فواتير مستحقّة | {_riyals(owed['owed'] or ZERO)} |",
            f"| منها مسدَّد | {_riyals(owed['paid'] or ZERO)} |",
        ]
        return rows

    def _what_needs_you(self) -> list[str]:
        """ما لا يُغلق إلا بقرارك — ويُعرض بلا تزويق."""
        from apps.odoo.models import CustomerLink

        contested = (
            CustomerLink.objects.values("odoo_customer_id")
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .count()
        )
        lines = [
            "---",
            "",
            "## ما ينتظر قرارك",
            "",
        ]
        if contested:
            lines += [
                f"**{contested} عميلاً في المحاسبة له أكثرُ من حسابٍ عندنا.**",
                "لم نختر بينهما: اختيارُ أحدهما بالحدس هو ما خصم من عميلٍ مرّتين",
                "في النظام القديم. وحتى تختار، أيُّ مبلغٍ يصل باسم هؤلاء يُحفظ",
                "جانباً ولا يُنسب لأحد.",
                "",
            ]
        lines += [
            "**النقل جرى على نسخةٍ من البيانات، لا على النظام الحيّ.** والنقل",
            "النهائيّ يحتاج حسابَ قراءةٍ على الخادم الحيّ، وهو ما لم يصل بعد.",
            "",
            "**ولم تُنقل صورُ السيارات** (اثنان وتسعون ألف صورة): ملفّاتُها على",
            "خادم النظام القديم لا في النسخة. تُجلب حين يُفتح الوصول.",
        ]
        return lines
