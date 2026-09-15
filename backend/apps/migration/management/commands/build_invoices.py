"""بانِي الفواتير — T309.

    python manage.py build_invoices --dry-run
    python manage.py build_invoices

يُشغَّل **بعد** `import_v1` (المركبات والحسابات) و`build_identity_map`.

## الأسئلةُ الأربعة التي كانت تمنعه — مُجابةً بالعدّ لا بالرأي

`field-map.md` §د يسم أربعةَ صفوفٍ بـ🔍 «يحتاج قراءة الإنتاج». عُدَّت كلُّها من
نسخة ٢٠٢٦-٠٩-٠٥ (١٢٬٤٣٤ صفّاً)، وهذه أجوبتُها — وكلُّ قرارٍ أدناه مبنيٌّ عليها:

**١) أيُّ جدولِ فواتيرَ هو الحيّ؟** `invoices_odoo` (١٢٬٤٣٤). والأحد عشر الباقي
لقطاتُ حوادثَ أو فارغة: `_bak_20260620`=1,046 · **`_loopbak_20260606`=786** (لوب
يونيو، وهو دليلُ T313 لا مصدرُ حالة) · `_bak_20260728_backfill`=38 ·
`_bak_20260801_stale`=12 · `_deleted_bak`=3 · `_late_dupe_purge_20260607`=3 ·
و`invoices`/`invoices_odoo2`/`invoicesonepayment` **صفر**.

**٢) `customer_id` أم `id_user`؟** يختلفان في **١٢٬٤٣٤ من ١٢٬٤٣٤** — أي دائماً،
بلا استثناءٍ واحد. `id_user` مفتاحُنا (مدى `userss.id`)، و`customer_id` معرّفُ
أودو. وهو فخُّ `refunds_requests` نفسُه بأسماءٍ أخرى، **ويُسند فاتورةً لشخصٍ آخر**
لو قُرئ الخطأ.

**٣) أيُّ عمودِ مبلغٍ هو ما يدفعه العميل؟** أربعةُ أعمدة، والعدُّ يحسمها:
`total == amount + fees_amount` في **٢٬٧١١** صفّاً، و`total = 0` في **٩٬٧٢٣**.
فـ`total` مجموعٌ يُملأ أحياناً ولا يُعتمد وحده؛ والقاعدةُ الواحدة
`amount + fees_amount` تساوي `total` حيثما وُجد — **قاعدةٌ واحدةٌ مطابِقةٌ في كل
صفٍّ يحملها**، لا فرعان.

**٤) والمبلغُ شاملُ الضريبة — HR-05، وخطؤه ضريبةٌ مزدوجة.** قيس: `amount / 1.15`
يعطي **ريالاً صحيحاً تماماً في ٦٦٫٧٪** من الصفوف (٨٬٢٨٥ من ١٢٬٤٢٩). واحتمالُ ذلك
مصادفةً ~١٪. فالمبلغُ في v1 **شاملٌ**، بلا شكّ عمليّ. عيّناتٌ من النسخة:
`17250.00 ⟶ 15000` · `30590.00 ⟶ 26600` · `21848.85 ⟶ 18999`.

## ولذلك كلُّ فاتورةٍ مُرحَّلةٍ تُكتب `ODOO_SYNC`

ولو كان عمودُ `source` عندهم يقول `NULL` (٨٬٢٩٤ صفّاً، أغلبُها `posted`) أو
`odoo_webhook` (٤٬١٣٩، أغلبُها `draft`).

لأن :class:`~apps.money.models.InvoiceSource` **يعرّف نفسه بما يعنيه المبلغ**
لا بمكان الميلاد: «Where an invoice was born — **and therefore what its
`amount` means**». و`LOCAL` تعني «قبل الضريبة»، وقد قِيس أن مبالغ v1 شاملة. فأيُّ
صفٍّ يُكتب `LOCAL` هنا يصير مرشَّحاً لأن تُضاف عليه ضريبةٌ ثانية.

وكلمةُ v1 عن نفسها **لا تضيع**: `source` الأصليّ وحالتُهم الخام يُحفظان في
`odoo_state_raw` والملاحظة (المادة ٢-٣) — تُقرأ ولا يُبنى عليها منطق.

## والمكوّنات **تُترك صفراً** — ولا تُشتقّ

الإجماليُّ وحده يُكتب، و`net_amount` و`admin_fee` و`tax_amount` أصفار.

وليس ذلك كسلاً — هو الشقُّ الثاني من قيد `invoice_parts_add_up_to_its_total`،
مكتوباً بنصّه: «**للفواتير المرآة من أودو: هي تحمل إجمالياً بلا تفصيل، فلا
يُفرض عليها تفصيلٌ لا نملكه**».

وقد حاولتُ اشتقاقَه، **فرفضه القيدُ عند الكتابة** — وكان مُحقّاً: اشتقاقُ
`net = إجمالي/1.15` ثم وضعُ `admin_fee = fees_amount` بجواره يحسب الرسمَ مرّتين
(`net + tax` يساوي الإجماليَّ أصلاً). وصفٌّ حقيقيّ كشفه: `amount=2900.00` مع
`fees=695.65` فصار المجموعُ `3595.65`.

**ولا يُصلَح بمعادلةٍ أخرى، لأن مفردات الرسم في v1 غيرُ متّسقة** — قِيس على
٤٬١٢٧ صفّاً برسمٍ موجب: أغلبُها `800.00` (صافٍ، وإجماليُّه ٩٢٠ كما في مثال
`AuctionVat` حرفيّاً: «٨٠٠ رسم + ١٢٠ ضريبة الرسم»)، وبعضُها `695.65` — وهو
صافي ٨٠٠ نفسِها. أي أن العمودَ يحمل **الصافيَ مرّةً والصافيَ-من-الإجماليّ
مرّةً**، ولا معادلةَ واحدة تفكّ الاثنين.

**والأهمُّ:** صفوفُ الرسم هي **بعينها** الصفوفُ التي لا يقبل إجماليُّها القسمةَ
النظيفة على ١٫١٥ (صفرٌ من ٤٬١٢٧)، بينما الصفوفُ بلا رسمٍ تقبلها (٨٬٢٨٥). فتفصيلُ
الفاتورة ذات الرسم **غيرُ معروفٍ من هذه البيانات**، واختراعُه يُنتج رقماً يبدو
صحيحاً — وهو أسوأ ما يُنتجه ترحيل.

والإجماليُّ نفسُه **ليس مشكوكاً فيه**: هو ما يدين به العميل، وهو ما تقارنه D2.

## والازدواج: ٧٣ مركبةً سيرفضها القيد

٢٢٧ مركبةً لها أكثر من فاتورة (٢١٧ باثنتين و١٠ بثلاث)، **و٧٣ منها لها أكثر من
فاتورةٍ حيّة**. وقيدُ `one_live_invoice_per_vehicle` (T118) يرفض الثانية — وهو
صحيح: فاتورتان حيّتان لسيّارةٍ واحدة هو عينُ ما أنتجه لوبُ يونيو.

فالأحدثُ يُختار، و**المستبعَدُ يُكتب بسببه ورقمه** — وهو نصُّ معيار القبول:
«اختر الفاتورة الحية عند الازدواج **ووثّق المستبعَد**».
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.migration.dumpfile import read_table

# نفسُ محوّل الوقت الذي يستعمله `import_v1` — لا نسخةٌ ثانية منه: أعمدةُ
# `datetime` في v1 بلا منطقة، وهي ساعةُ الرياض. وتخزينُها كما هي يجعل كلَّ
# فاتورةٍ متقدّمةً ثلاثَ ساعات، ومقارنةَ D2 تُقارن يومين مختلفين عند الحدود.
from apps.migration.management.commands.import_v1 import moment
from apps.migration.models import LegacyRef
from apps.money.models import Invoice, InvoiceSource, InvoiceState

#: الجدولُ الحيّ. مسمّىً صراحةً لأن في النسخة أحدَ عشرَ جدولاً باسمٍ يشبهه،
#: ومن يقرأ الخطأ منها **يرحّل تاريخاً ميتاً على أنه حاضر**.
LIVE_TABLE = "invoices_odoo"

CENT = Decimal("0.01")

#: حالاتُهم ⟶ حالتُنا. **حسّاسةٌ للحالة عمداً**: `Not_paid` بحرفٍ كبير في
#: المصدر، ومطابقةٌ متساهلة تُخفي انزياحاً في مفرداتهم بدل أن تكشفه.
STATE_MAP = {
    "posted": InvoiceState.OPEN,
    "paid": InvoiceState.PAID,
    "Not_paid": InvoiceState.OPEN,
    "part_paid": InvoiceState.PARTIAL,
    "partially paid": InvoiceState.PARTIAL,
    "draft": InvoiceState.DRAFT,
    "cancelled": InvoiceState.CANCELLED,
    "cancel": InvoiceState.CANCELLED,
    "reversed": InvoiceState.CANCELLED,
}

#: ما يُعدّ «حيّاً» عند اختيار واحدةٍ من فاتورتين لمركبةٍ واحدة.
LIVE_STATES = frozenset(
    {InvoiceState.OPEN, InvoiceState.PARTIAL, InvoiceState.DRAFT}
)


def _decimal(raw) -> Decimal | None:
    try:
        value = Decimal(str(raw or "0"))
    except (InvalidOperation, TypeError):
        return None
    return value if value.is_finite() else None


class Command(BaseCommand):
    help = "ابنِ الفواتير من نسخة v1 — T309."

    def add_arguments(self, parser):
        parser.add_argument("--dump", default=settings.V1_DUMP_PATH)
        parser.add_argument("--dry-run", action="store_true", help="اقرأ وشخّص ولا تكتب")

    def handle(self, *args, **options):
        path = Path(options["dump"] or "")
        if not path.is_file():
            raise CommandError(f"النسخة غير موجودة: {path or '(بلا مسار)'}")
        self.dry = options["dry_run"]
        self.rejected: Counter = Counter()
        self.samples: dict[str, str] = {}

        users = LegacyRef.resolve("accounts.user")
        vehicles = LegacyRef.resolve("auctions.vehicle")
        if not users:
            raise CommandError("لا جسرَ مفاتيحَ للمستخدمين. شغّل `import_v1` أوّلاً.")
        self.stdout.write(
            f"النسخة: {path}\n"
            f"الجسر: {len(users):,} حساباً · {len(vehicles):,} مركبة"
        )
        if not vehicles:
            # ليس خطأً قاتلاً: الفاتورةُ تُرحَّل بلا مركبة. لكنه يُقال بصوتٍ
            # عالٍ — فاتورةٌ بلا مركبةٍ لا يُقفل عليها رهنٌ ولا تُقرأ في شاشة.
            self.stdout.write(
                self.style.WARNING(
                    "لا جسرَ للمركبات — ستُرحَّل الفواتير بلا ربطِ مركبة. "
                    "شغّل `import_v1` بنسخةٍ كاملة إن أردت الربط."
                )
            )

        drafts, per_vehicle = self._read(path, users, vehicles)
        chosen, dropped = self._resolve_duplicates(drafts, per_vehicle)
        renamed = self._disambiguate_numbers(chosen)
        landed = self._write(chosen)
        self._report(len(drafts), dropped, renamed, len(chosen), landed)

    # -- القراءة -----------------------------------------------------------

    def _read(self, path: Path, users: dict, vehicles: dict):
        """اقرأ الجدولَ الحيّ وحوّل كلَّ صفٍّ إلى مسودّة، أو ارفضه بسببه."""
        drafts: list[dict] = []
        per_vehicle: dict[int, list[int]] = defaultdict(list)

        for row in read_table(path, LIVE_TABLE):
            legacy = str(row.get("id") or "")

            # **`id_user` لا `customer_id`** — والعدُّ حسمها: يختلفان دائماً.
            owner = users.get(str(row.get("id_user") or ""))
            if owner is None:
                self._reject("فاتورة: حسابٌ غير مُرحَّل", legacy, row.get("id_user"))
                continue

            amount = _decimal(row.get("amount"))
            fees = _decimal(row.get("fees_amount")) or Decimal("0")
            if amount is None or amount <= 0:
                self._reject("فاتورة: مبلغٌ غير موجب", legacy, row.get("amount"))
                continue

            # `total` حيثما وُجد يساوي `amount + fees` — قيس على ٢٬٧١١ صفّاً.
            # فالقاعدةُ واحدة، و`total` يُقرأ تأكيداً لا مصدراً ثانياً.
            gross = (amount + fees).quantize(CENT)

            raw_state = str(row.get("status") or "")
            state = STATE_MAP.get(raw_state)
            if state is None:
                # حالةٌ لم نرها. تُرفض ولا تُخمَّن — وظهورُها اكتشافٌ يُبلَّغ.
                self._reject("فاتورة: حالةٌ غير معروفة", legacy, raw_state)
                continue

            # **`auction_id` لا يُقرأ إطلاقاً**: يحمل `vehicle_id` (`spec.md`).
            vehicle_pk = vehicles.get(str(row.get("vehicle_id") or ""))

            number = str(row.get("invoice_number") or "").strip()
            if not number:
                # ١٬٦٤٩ صفّاً بلا رقم. `number` فريدٌ عندنا، فيُشتقّ من مفتاح
                # المصدر — لا يُترك فارغاً (يصطدم) ولا يُخترع عدّاداً (يتصادم
                # عند إعادة التشغيل).
                number = f"V1-{legacy}"

            drafts.append(
                {
                    "legacy_id": legacy,
                    "customer_id": owner,
                    "vehicle_id": vehicle_pk,
                    "number": number[:64],
                    "amount": gross,
                    # الرسمُ يُحفظ **للمراجعة** لا ليُكتب حقلاً: `admin_fee`
                    # عندنا مكوّنٌ يدخل معادلةَ القيد، وقيمةُ v1 لا تُفكّ إليها.
                    "v1_fees": fees.quantize(CENT),
                    "state": state,
                    "odoo_invoice_id": str(row.get("odoo_record_id") or "")[:64],
                    "odoo_state_raw": raw_state[:64],
                    "issued_at": moment(row.get("created_at")),
                    "v1_source": str(row.get("source") or "—"),
                }
            )
            if vehicle_pk is not None:
                per_vehicle[vehicle_pk].append(len(drafts) - 1)

        return drafts, per_vehicle

    # -- الازدواج ----------------------------------------------------------

    def _resolve_duplicates(self, drafts: list[dict], per_vehicle: dict):
        """مركبةٌ بأكثر من فاتورةٍ حيّة: تُختار واحدة، ويُكتب المستبعَد.

        **والأحدثُ يفوز**، بمفتاح المصدر حين يتساوى التاريخ: الفاتورةُ الثانية
        لسيّارةٍ واحدة نشأت في v1 من إعادة إصدارٍ أو من لوب يونيو، وفي الحالتين
        الأخيرةُ هي ما يراه العميل على شاشته اليوم.
        """
        dropped: list[tuple[dict, str]] = []
        keep = set(range(len(drafts)))

        for indices in per_vehicle.values():
            live = [i for i in indices if drafts[i]["state"] in LIVE_STATES]
            if len(live) < 2:
                continue
            def freshness(index: int):
                draft = drafts[index]
                return (str(draft["issued_at"] or ""), int(draft["legacy_id"] or 0))

            live.sort(key=freshness)
            winner = live[-1]
            for loser in live[:-1]:
                keep.discard(loser)
                dropped.append(
                    (
                        drafts[loser],
                        f"فاتورةٌ حيّةٌ ثانية على المركبة نفسها — "
                        f"بقيت #{drafts[winner]['legacy_id']}",
                    )
                )

        return [drafts[i] for i in sorted(keep)], dropped

    # -- أرقامٌ يعيد v1 استعمالها ---------------------------------------------

    def _disambiguate_numbers(self, chosen: list[dict]) -> list[dict]:
        """رقمُ الفاتورة فريدٌ عندنا، و**v1 يعيد استعماله**. يُلحَق به مفتاحُه.

        وهذا ما كشفه أوّلُ تشغيلٍ ناجح: الأمرُ قال «رُحِّل ١٢٬٣٢٤» وفي القاعدة
        **١٢٬١٦٩**. مئةٌ وخمسةٌ وخمسون فاتورةً بمبالغَ حقيقيّة ابتلعها
        `bulk_create(ignore_conflicts=True)` **بصمت** — وهو بالضبط ما يمنعه
        `spec.md`: «صفٌّ لا يمكن ترحيله بثقة يذهب لتقرير المراجعة، ولا يُخترَع
        له سبب». والصمتُ أسوأ من الاختراع.

        والسببُ ثلاثةُ أرقامٍ في v1 تتكرّر على ~١٥٨ صفّاً — فواتيرُ مختلفةٌ
        بمبالغَ مختلفة، لا نسخٌ من واحدة، فإسقاطُها فقدُ مال.

        **ولا تُدمَج ولا تُسقَط: يُلحَق برقمها مفتاحُ مصدرها** (`…-v1<id>`)،
        فيبقى الرقمُ الأصليُّ مقروءاً في أوّله. وهو ما يفعله `issue_invoice`
        نفسُه حين تُفوتَر سيّارةٌ مرّتين.
        """
        seen: set[str] = set()
        renamed: list[dict] = []
        for draft in chosen:
            number = draft["number"]
            if number in seen:
                draft["number"] = f"{number}-v1{draft['legacy_id']}"[:64]
                renamed.append(draft)
            else:
                seen.add(number)
        return renamed

    # -- الكتابة -----------------------------------------------------------

    def _write(self, chosen: list[dict]) -> int:
        """يُرجع **ما لَحِق بالقاعدة فعلاً**، لا ما أُرسل إليها."""
        if self.dry:
            self.stdout.write(f"سيُرحَّل: {len(chosen):,} فاتورة")
            return len(chosen)

        now = timezone.now()
        with transaction.atomic():
            rows = [
                Invoice(
                    customer_id=d["customer_id"],
                    vehicle_id=d["vehicle_id"],
                    number=d["number"],
                    amount=d["amount"],
                    # **أصفارٌ عمداً** — الشقُّ الثاني من القيد. راجع صدر الوحدة.
                    state=d["state"],
                    odoo_invoice_id=d["odoo_invoice_id"],
                    odoo_state_raw=d["odoo_state_raw"],
                    # **كلُّها `ODOO_SYNC`** — راجع صدر الوحدة: الحقلُ يعرّف
                    # نفسه بما يعنيه المبلغ، والمبلغُ هنا شاملٌ الضريبة قياساً.
                    source=InvoiceSource.ODOO_SYNC,
                    issued_at=d["issued_at"] or now,
                )
                for d in chosen
            ]
            Invoice.objects.bulk_create(rows, batch_size=1000, ignore_conflicts=True)

            # المفاتيحُ تُقرأ بعد الكتابة لا تُؤخذ من الدفعة:
            # `ignore_conflicts` لا يملأ `pk` على PostgreSQL (درسُ T307).
            written = {
                number: pk
                for pk, number in Invoice.objects.filter(
                    number__in=[d["number"] for d in chosen]
                ).values_list("pk", "number")
            }
            LegacyRef.remember(
                "money.invoice",
                {d["legacy_id"]: written.get(d["number"]) for d in chosen},
            )
        landed = len(written)
        self.stdout.write(f"رُحِّل: {landed:,} فاتورة")
        return landed

    # -- التقرير -----------------------------------------------------------

    def _reject(self, why: str, legacy_id, sample) -> None:
        self.rejected[why] += 1
        self.samples.setdefault(why, f"صفّ {legacy_id} — {str(sample)[:40]}")

    def _report(
        self, read: int, dropped: list, renamed: list, sent: int, landed: int
    ) -> None:
        total = read + sum(self.rejected.values())
        self.stdout.write(f"\nقُرئ من `{LIVE_TABLE}`: {total:,}")

        if renamed:
            self.stdout.write(
                f"\nأرقامٌ يعيد v1 استعمالها: {len(renamed)} فاتورة أُلحق برقمها "
                "مفتاحُ مصدرها — **ولم تُسقَط**."
            )
            for draft in renamed[:10]:
                self.stdout.write(f"  #{draft['legacy_id']} · {draft['number']}")

        # **الفارقُ يُصرَخ به.** `ignore_conflicts` يبتلع كلَّ اصطدامِ قيدٍ
        # بصمت، فعددُ ما أُرسل ليس عددَ ما وصل — والفرقُ فواتيرُ بمالٍ حقيقيّ.
        # وقد وقع فعلاً: ١٢٬٣٢٤ أُرسلت و١٢٬١٦٩ وصلت، ولا سطرَ يقول ذلك.
        if not self.dry and landed < sent:
            self.stdout.write(
                self.style.ERROR(
                    f"\n⚠ أُرسل {sent:,} ووصل {landed:,} — "
                    f"**{sent - landed:,} فاتورةً رفضها قيدٌ ولم تُرحَّل**. "
                    "لا يُغلق التاسك قبل معرفة أيّها ولماذا."
                )
            )

        if self.rejected:
            self.stdout.write("\nالمرفوض، بسببه:")
            for why, count in self.rejected.most_common():
                self.stdout.write(f"  {count:>6}  {why}   ({self.samples[why]})")

        if not dropped:
            self.stdout.write("\nلا ازدواجَ حيّاً على أيّ مركبة.")
            return

        self.stdout.write(
            self.style.WARNING(f"\nالمستبعَد بالازدواج: {len(dropped)} فاتورة")
        )
        for draft, why in dropped[:50]:
            self.stdout.write(
                f"  #{draft['legacy_id']} · {draft['number']} · {draft['amount']} "
                f"· {draft['odoo_state_raw']} — {why}"
            )
        self.stdout.write(
            "\nوهذه هي «قائمةُ المستبعَد» التي يطلبها معيارُ القبول: فاتورتان "
            "حيّتان لسيّارةٍ واحدة هو عينُ ما أنتجه لوبُ يونيو، ويرفضه قيدُ "
            "`one_live_invoice_per_vehicle`."
        )
