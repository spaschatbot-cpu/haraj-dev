"""بانِي رسم الهوية — T307. يُبنى أوّلاً، ولا يُنسب ريالٌ قبله.

    python manage.py build_identity_map --dump D:/tmp/…_data_….sql.gz --dry-run
    python manage.py build_identity_map --dump D:/tmp/…_data_….sql.gz

## لماذا هذا أوّلُ البناة

«هذا هو ترتيبُ الفشل في v1 بالضبط — الفلوسُ نُسبت قبل حسم الهوية» (نصُّ
`tasks.md`). وصدرُ :class:`~apps.odoo.models.CustomerLink` يروي الحادثة: «حين
تبيّن أن ثلاثة عملاء لهم حسابان أو ثلاثة، قوبل مالٌ مفتاحُه أودو بودائعَ
مفتاحُها المستخدم، وخُصم ٢٠٬٠٠٠ مرّتين».

**والثلاثةُ عُدّوا.** في نسخة ٢٠٢٦-٠٩-٠٥: ١٤٬٧٠٨ صفَّ ربطٍ، ١٤٬٧٠٤ عميلَ أودو
متميّزاً، و**ثلاثةٌ** منهم لهم أكثر من حساب (اثنان بحسابين وواحدٌ بثلاثة)،
و**حسابٌ واحد** له عميلا أودو. فالرواية عدٌّ، والمراجعةُ أربعةُ صفوف.

## القاعدة الحاكمة هنا: المتنازَعُ عليه لا يُحسَم آلياً

`is_primary` يُرفع **فقط** حين يكون لعميل أودو حسابٌ واحدٌ لا غير. وما عداه
يُكتب ربطاً **بلا أساسيّ** — فيقرأ
:func:`apps.odoo.processing._resolve_customer` «روابطُ بلا حساب أساسيّ — يحتاج
قراراً بشرياً»، وتذهب دفعتُه إلى المعلَّق حتى يحسمها إنسان من ملفّ العميل
(`T221`).

وهذا ليس تردّداً: اختيارُ «الأحدث» أو «الأوّل» بين حسابين هو **بالضبط** التخمينُ
الذي خصم ٢٠٬٠٠٠ مرّتين. والصمتُ هنا مكلفٌ ومرئيّ (مالٌ في المعلَّق وأربعةُ صفوف
في تقرير)، والتخمينُ رخيصٌ وغيرُ مرئيّ.

## ولا يقرأ `userss.id_customer`

`tasks.md` يقول «ابنِ `CustomerLink` من `id_customer`»، و**المصدرُ المعتمَد
`customer_links`** كما تقول خريطة الحقول §أ — وهو الجدولُ الذي بناه v1 من ذلك
العمود نفسِه بعد أن اكتشف أن العمود لا يكفي (`source='column'` في ١٤٬٧٠٧ صفّاً
منه، و`manual` في واحد). فالقراءةُ من الجدول تأخذ العمودَ **ومعه** ما صحّحه
الإنسان، والقراءةُ من العمود تُسقط التصحيح.

و`confidence` و`source` يُحفظان في `note` **ولا يُبنى عليهما منطق** (المادة
٢-٣): كلمةُ النظام القديم تُحفظ ولا تُصدَّق.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.migration.dumpfile import read_table
from apps.migration.models import LegacyRef
from apps.odoo.models import CustomerLink

#: كم صفّاً من المتنازَع عليه يُطبع كاملاً قبل الاكتفاء بالعدد.
REVIEW_LIMIT = 50


class Command(BaseCommand):
    help = "ابنِ رسم الهوية (CustomerLink) من نسخة v1 — T307."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default=settings.V1_DUMP_PATH,
            help="مسارُ نسخة mysqldump (.sql أو .sql.gz).",
        )
        parser.add_argument("--dry-run", action="store_true", help="اقرأ وشخّص ولا تكتب")

    def handle(self, *args, **options):
        path = Path(options["dump"] or "")
        if not path.is_file():
            raise CommandError(f"النسخة غير موجودة: {path or '(بلا مسار)'}")
        self.dry = options["dry_run"]

        self.stdout.write(f"النسخة: {path}")
        if self.dry:
            self.stdout.write(self.style.WARNING("وضع القراءة فقط — لا يُكتب شيء"))

        # ١) الجسرُ الذي كتبه `import_v1`. بلا صفٍّ فيه لا معنى لأيّ ترجمة —
        #    ورسالةٌ تقول ذلك خيرٌ من بناء صفرِ ربطٍ والإبلاغ عنه نجاحاً.
        bridge = LegacyRef.resolve("accounts.user")
        if not bridge:
            raise CommandError(
                "لا جسرَ مفاتيحَ للمستخدمين. شغّل `import_v1` أوّلاً — "
                "وبلا الجسر لا تُترجَم `customer_links.user_id` إلى حساب."
            )
        self.stdout.write(f"جسرُ المستخدمين: {len(bridge):,} حساباً")

        # ٢) اقرأ الرسم كما هو، وارسم الرسمَ البيانيّ في الذاكرة قبل الكتابة:
        #    «من له أكثر من حساب» سؤالٌ عن **المجموعة كلّها**، ولا يُجاب صفّاً
        #    صفّاً أثناء الكتابة.
        rows: list[dict] = []
        unknown_user = missing_field = 0
        by_odoo: dict[str, set] = defaultdict(set)
        by_user: dict[int, set] = defaultdict(set)

        for row in read_table(path, "customer_links"):
            odoo_id = row.get("odoo_customer_id")
            legacy_user = row.get("user_id")
            if odoo_id in (None, "", 0) or legacy_user in (None, ""):
                missing_field += 1
                continue
            odoo_id = str(odoo_id)
            ours = bridge.get(str(legacy_user))
            if ours is None:
                # حسابٌ لم يُرحَّل (جوّالٌ مرفوض، أو صفٌّ مكرَّر خسر التفرّد).
                # يُعدّ ولا يُخمَّن — المادة ٢-٣.
                unknown_user += 1
                continue
            rows.append(
                {
                    "legacy_id": str(row.get("id") or ""),
                    "odoo_customer_id": odoo_id,
                    "user_id": ours,
                    "source": str(row.get("source") or ""),
                    "confidence": str(row.get("confidence") or ""),
                }
            )
            by_odoo[odoo_id].add(ours)
            by_user[ours].add(odoo_id)

        contested_odoo = {o: u for o, u in by_odoo.items() if len(u) > 1}
        contested_user = {u: o for u, o in by_user.items() if len(o) > 1}

        self.stdout.write(
            f"صفوفُ الربط المقروءة: {len(rows):,} · "
            f"بحقلٍ ناقص: {missing_field:,} · بحسابٍ غير مُرحَّل: {unknown_user:,}"
        )

        # ٣) اكتب. الأساسيُّ للمتّفق عليه وحده.
        made = primary = 0
        if not self.dry:
            with transaction.atomic():
                batch = [
                    CustomerLink(
                        user_id=r["user_id"],
                        odoo_customer_id=r["odoo_customer_id"],
                        # **المتنازَعُ عليه بلا أساسيّ** — والقرارُ لإنسان.
                        is_primary=len(by_odoo[r["odoo_customer_id"]]) == 1,
                        note=self._note(r),
                    )
                    for r in rows
                ]
                primary = sum(1 for link in batch if link.is_primary)
                # `ignore_conflicts`: القيدُ `one_link_per_pair` يجعل إعادةَ
                # التشغيل بلا أثر (القاعدة ٢)، لا خطأً على أوّل صفٍّ سبق بناؤه.
                CustomerLink.objects.bulk_create(
                    batch, batch_size=1000, ignore_conflicts=True
                )
                made = len(batch)
                # **المفاتيحُ تُقرأ بعد الكتابة لا تُؤخذ من الدفعة.**
                # `bulk_create(ignore_conflicts=True)` لا يملأ `pk` على
                # PostgreSQL — الدفعةُ تعود كما أُرسلت، و`link.pk` فيها `None`.
                # فأوّلُ تشغيلٍ كتب ١٤٬٧٠٦ رابطاً وصفرَ جسر، وكان الترحيلُ
                # ليمضي بجسرٍ فارغٍ لا يشكو.
                #
                # والمفتاحُ الطبيعيُّ هنا هو قيدُ `one_link_per_pair` نفسُه:
                # (الحساب، عميلُ أودو). فالقراءةُ به تُصيب الصفَّ الذي كُتب،
                # والصفَّ الذي كان موجوداً من تشغيلٍ سابق — وكلاهما مقصود.
                written = {
                    (user_id, odoo_id): pk
                    for pk, user_id, odoo_id in CustomerLink.objects.filter(
                        odoo_customer_id__in={r["odoo_customer_id"] for r in rows}
                    ).values_list("pk", "user_id", "odoo_customer_id")
                }
                LegacyRef.remember(
                    "odoo.customerlink",
                    {
                        r["legacy_id"]: written.get(
                            (r["user_id"], r["odoo_customer_id"])
                        )
                        for r in rows
                        if r["legacy_id"]
                    },
                )
            self.stdout.write(
                f"رُبط: {made:,} صفّاً · منها {primary:,} أساسيّ "
                f"({made - primary:,} بلا أساسيّ، بانتظار قرار)"
            )
        else:
            primary = sum(1 for r in rows if len(by_odoo[r["odoo_customer_id"]]) == 1)
            self.stdout.write(
                f"سيُربط: {len(rows):,} صفّاً · منها {primary:,} أساسيّ "
                f"({len(rows) - primary:,} بلا أساسيّ)"
            )

        self._review(contested_odoo, contested_user, rows)

    # -- التقرير -----------------------------------------------------------

    def _note(self, row: dict) -> str:
        """كلمةُ v1 عن نفسه، محفوظةً ولا يُبنى عليها منطق (المادة ٢-٣)."""
        parts = [f"من customer_links #{row['legacy_id']}"]
        if row["source"]:
            parts.append(f"source={row['source']}")
        if row["confidence"]:
            parts.append(f"confidence={row['confidence']}")
        return " · ".join(parts)[:1000]

    def _review(self, contested_odoo: dict, contested_user: dict, rows: list) -> None:
        """قائمةُ المراجعة — وهي **معيارُ قبول T307** لا زينةً في المخرَج.

        «قائمةُ الحسابات المتعددة مطبوعة ومراجَعة؛ الأساسيّ محدَّد لكل واحد».
        فالمطبوعُ هنا هو ما يوقّع عليه المالك، والتحديدُ يقع في ملفّ العميل.
        """
        self.stdout.write("")
        if not contested_odoo and not contested_user:
            self.stdout.write(self.style.SUCCESS("لا هويّةَ متنازَعاً عليها."))
            return

        by_user_of_odoo = defaultdict(list)
        for r in rows:
            by_user_of_odoo[r["odoo_customer_id"]].append(r["user_id"])

        self.stdout.write(
            self.style.WARNING(
                f"للمراجعة قبل بناء الدفتر: {len(contested_odoo)} عميلَ أودو "
                f"بأكثر من حساب · {len(contested_user)} حساباً بأكثر من عميل أودو"
            )
        )
        spread = Counter(len(u) for u in contested_odoo.values())
        self.stdout.write(f"  توزيعُ العدد: {dict(sorted(spread.items()))}")

        for odoo_id, users in list(contested_odoo.items())[:REVIEW_LIMIT]:
            ours = ", ".join(str(u) for u in sorted(users))
            self.stdout.write(f"  أودو {odoo_id} ⟶ حساباتنا [{ours}] — بلا أساسيّ")
        for user_id, odoos in list(contested_user.items())[:REVIEW_LIMIT]:
            theirs = ", ".join(sorted(odoos))
            self.stdout.write(f"  حسابُنا {user_id} ⟶ أودو [{theirs}]")

        self.stdout.write("")
        self.stdout.write(
            "كلُّ ما فوق **بلا حسابٍ أساسيّ**، فدفعاتُه تذهب إلى المعلَّق ولا "
            "تُنسب بتخمين. يُحسم كلٌّ منها من ملفّ العميل ← «الربط بأودو»."
        )
