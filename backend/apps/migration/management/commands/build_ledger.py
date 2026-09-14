"""بانِي الدفتر — T310، **الأهمّ**.

    python manage.py build_ledger --dry-run
    python manage.py build_ledger

يُشغَّل آخرَ البناة: بعد `import_v1` و`build_identity_map` و`build_invoices`.

## المبدأ الحاكم، ولا استثناء له

«**لا يُنسخ رصيد.** الدفتر يُبنى من الأحداث عبر `apps.money.services.post`
وحدها (المادة ١-٢)» — `field-map.md` §هـ. و«**ممنوعة الكتابة المباشرة في
الجداول**… الترحيلُ الذي يتخطّى طبقة الخدمة يتخطّى معها كلَّ قيدٍ بُني في الفيز
٠٠٢» — `tasks.md`.

فكلُّ حركةٍ هنا تمرّ بدالّةِ خدمةٍ مسمّاة (`deposit_insurance` ·
`hold_for_auction` · `lock_for_invoice` · `refund_insurance` · `confiscate` ·
`record_payment`)، ولا سطرَ `Entry(...)` ولا `Account.objects.update(...)` في
هذا الملفّ. ولذلك **كلُّ قيدٍ في الفيز ٠٠٢ يحرس البيانات المرحَّلة كما يحرس
الحيّة**: الدلوُ لا يسلب، والمعاملةُ تتوازن، والمسدَّدُ لا يتجاوز المستحقّ.

## من أين يُقرأ كلُّ شيء — وأين لا يُقرأ

**`insurance_deposits` هو الدفتر**، بنصّ `docs/v1-wallet-logic.md` §١: «صفٌّ =
وديعة». فحالتُه هي مصدرُ الحقيقة لما آلت إليه كلُّ وديعة، وأربعةُ طوابعِه تروي
المسار.

**و`refunds_requests` لا يحرّك ريالاً هنا.** وهذا قرارٌ جوهريّ لا إغفال:
الوديعةُ المستردَّة تحمل `status='refunded'` **وفي الوقت نفسه** يوجد صفُّ طلبٍ
بـ`deducted_at`. وبناءُ الاثنين يخصم المالَ مرّتين — ١١٬٥٥٠٬٠٠٠ من الودائع
و١١٬٠٤٠٬٠٠١ من الطلبات، وهما **المالُ نفسُه مرئيّاً من جهتين**. فالخروجُ يُبنى
من الوديعة (الدفتر)، والطلبُ حالةٌ لا حركة.

## أربعةُ قياساتٍ سبقت السطرَ الأوّل

**١) الوديعةُ ليست دائماً ١٠٬٠٠٠.** ٢٬١٢٩ من ٢٬١٤٣ كذلك، **وأربعَ عشرةَ ليست**:
عشرٌ بريالٍ واحد، واثنتان بـ٩٬٩٩٠، وواحدةٌ بـ٨، وواحدةٌ بـ١٬٠٠٠. ولذلك تُستعمل
`deposit_insurance` (بلا قيد المضاعفات) لا `whole_deposits_in` — **ودفترٌ لا
يستطيع التعبير عمّا حدث لا يمكن مطابقتُه به**.

**٢) الحالةُ والرابط:** `held`=٣١٧ وكلُّها تحمل `linked_auction_id` ✅ ·
`locked`=٨٠ (٧٠ برابط) · `confiscated`=٨٠ (٦ برابط) · `refunded`=١٬١٥٥ ·
`free`=٥١١.

**٣) الدفعاتُ غيرُ المرحَّلة لا تُطبَّق.** ٦٠٢ مليوناً في `payments_odoo` مقابل
٤٢٦ مليوناً مستحقّة — والفرزُ بـ`status='posted'` وحده يُسقط **٤٬٤٧٠ صفّاً**
وينزل عددُ الفواتير «المدفوعة أكثرَ من مستحقّها» من **٣٬٩٠٨ إلى ٣٤٧**. أي أن
٩١٪ من الفائض مسوّداتٌ وملغاةٌ ما كانت لتُطبَّق أصلاً.

**٤) والـ٣٤٧ الباقيةُ تشوّهٌ حقيقيّ في v1** — لا تقريب: الفاتورة `153825` دُفع
عليها ٤٢٬٠٥٥٬٠٥٠ ومستحقُّها ٤٢٬٠٥٥٫٥٠ (**ألفُ ضعفٍ بالضبط**)، و`194356` عشرةُ
أضعاف، و`256085` بزيادةِ ٣٠٠٬٠٠٠ صحيحة. فتُسدَّد الفاتورةُ إلى حدِّ المستحقّ
**والفائضُ يُكتب في التقرير باسمه ورقمه** (T311)، ولا يُخترَع له سبب، ولا
يُكتب `amount_paid > amount` — يرفضه `invoice_paid_not_above_amount` أصلاً.

## وخطوةُ «نقل الوديعة إلى دلوها» تُختم، وإلا سقط D5

معيارُ `D5`: «التشغيلُ مرّتين ينتج نفسَ الدفتر». وأوّلُ إعادةِ تشغيلٍ **كسرته**:
١٧٬٥٩١ حركةً صارت ١٧٬٦٠٦ — **خمسَ عشرةَ حركةَ رهنٍ جديدة**.

والسببُ ليس في المفاتيح: `deposit_insurance` و`record_payment` مفتاحُهما من
معرّف v1 فخَمَدا تماماً. السببُ أن `_settle` كان يقرّر من **حالة القاعدة
لحظتَها**: `_invoice_for` يبحث عن فاتورةٍ مفتوحةٍ أو مسدَّدةٍ جزئياً، وحالةُ
الفواتير تتغيّر خلال التشغيلة نفسِها (الدفعاتُ تُسدّدها). فوديعةٌ لم تجد فاتورةً
في التشغيلة الأولى وجدتها في الثانية.

**والقاعدة التي انكسرت:** المفتاحُ يُشتقّ من **هويّة الحدث في v1**، لا ممّا تبدو
عليه القاعدةُ الآن. فخطوةُ النقل تُختم في `LegacyRef` بمعرّف الوديعة، ويُتخطّى
المختومُ — نجح أو تعذّر. ومن أراد إعادةَ محاولةِ ما تعذّر يمرّر `--resettle`
صراحةً، فيكون ذلك **قراراً مكتوباً** لا فارقاً يظهر بين تشغيلتين.

## والترتيبُ الزمنيُّ لازم

الأحداثُ تُرتَّب بطوابعها قبل التنفيذ. ودلوُ العميل لا يسلب (قيدُ
`customer_buckets_never_go_negative`)، فاسترداد وديعةٍ قبل إيداعها يُرفض في
القاعدة — وهو رفضٌ صحيح، لكنه يظهر عطلاً في الترحيل لا في البيانات. فالإيداعُ
أوّلاً لكلِّ الودائع، ثم حركاتُها بترتيبها.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bidding import settlement
from apps.migration.dumpfile import read_table
from apps.migration.management.commands.import_v1 import moment
from apps.migration.models import LegacyRef
from apps.money import services
from apps.money.models import Invoice, InvoiceState, TransactionKind

CENT = Decimal("0.01")

#: الدفعاتُ التي حرّكت مالاً فعلاً عند أودو. وما عداها مسوّدةٌ أو ملغاة —
#: ٤٬٤٧٠ صفّاً، وتطبيقُها يُنتج ٣٬٩٠٨ فاتورةٍ مدفوعةٍ فوق مستحقّها بدل ٣٤٧.
POSTED = "posted"

#: ختمُ «هذه الوديعة مرّت بخطوة النقل». يُقرأ من `LegacyRef` كغيره من الجسور،
#: فيُرى في القاعدة ويُعدّ — لا علَمٌ في الذاكرة يموت مع الأمر.
SETTLED = "v1.deposit_settled"


def _decimal(raw) -> Decimal | None:
    try:
        value = Decimal(str(raw or "0"))
    except (InvalidOperation, TypeError):
        return None
    return value if value.is_finite() else None


class Command(BaseCommand):
    help = "ابنِ الدفتر من أحداث v1 عبر طبقة الخدمة وحدها — T310."

    def add_arguments(self, parser):
        parser.add_argument("--dump", default=settings.V1_DUMP_PATH)
        parser.add_argument("--dry-run", action="store_true", help="اقرأ وشخّص ولا تكتب")
        parser.add_argument(
            "--skip-payments",
            action="store_true",
            help="ابنِ التأمينات وحدها، بلا دفعات الفواتير",
        )
        parser.add_argument(
            "--resettle",
            action="store_true",
            help="أعِد محاولةَ نقلِ الودائع التي تعذّر نقلُها — قرارٌ صريح، لا افتراض.",
        )

    def handle(self, *args, **options):
        path = Path(options["dump"] or "")
        if not path.is_file():
            raise CommandError(f"النسخة غير موجودة: {path or '(بلا مسار)'}")
        self.dry = options["dry_run"]
        self.notes: Counter = Counter()
        self.samples: dict[str, str] = {}
        self.excess: list[tuple[str, Decimal, Decimal]] = []

        self.users = LegacyRef.resolve("accounts.user")
        # المزادُ لا يحتاج جسراً: `import_v1` يكتب `Auction.number = v1.id`،
        # فالمعرّفُ القديم **هو** رقمُ المزاد المعروض — هويّةٌ حقيقيّةٌ لا ترجمة.
        from apps.auctions.models import Auction

        self.auctions = {
            str(number): pk for pk, number in Auction.objects.values_list("pk", "number")
        }
        if not self.users:
            raise CommandError("لا جسرَ للمستخدمين. شغّل `import_v1` أوّلاً.")

        self.stdout.write(f"النسخة: {path}")
        if self.dry:
            self.stdout.write(self.style.WARNING("وضع القراءة فقط — لا يُكتب شيء"))

        self._resettle = options["resettle"]
        self._deposits(path)
        if not options["skip_payments"]:
            self._payments(path)
        self._report()

    # -- التأمينات ---------------------------------------------------------

    def _deposits(self, path: Path) -> None:
        """كلُّ وديعةٍ تُودَع أوّلاً، ثم تُنقَل إلى دلوها الأخير بحالتها.

        **بخطوتين لا بخطوة**: القيدُ يمنع الدلوَ من السلب، فنقلُ وديعةٍ لم
        تُودَع بعدُ يُرفض في القاعدة. والإيداعُ ثم النقلُ يجعل كلَّ حركةٍ قيداً
        حقيقياً في التاريخ بدل رصيدٍ يُكتب جاهزاً — وهو المبدأ الحاكم نفسُه.
        """
        rows = list(read_table(path, "insurance_deposits"))
        self.stdout.write(f"\nالودائع: {len(rows):,} صفّاً في المصدر")

        prepared = []
        for row in rows:
            legacy = str(row.get("id") or "")
            owner = self.users.get(str(row.get("user_id") or ""))
            if owner is None:
                self._note("وديعة: حسابٌ غير مُرحَّل", legacy, row.get("user_id"))
                continue
            amount = _decimal(row.get("amount"))
            if amount is None or amount <= 0:
                self._note("وديعة: مبلغٌ غير موجب", legacy, row.get("amount"))
                continue
            prepared.append(
                {
                    "legacy": legacy,
                    "user_id": owner,
                    "amount": amount.quantize(CENT),
                    "status": str(row.get("status") or ""),
                    "auction": self.auctions.get(str(row.get("linked_auction_id") or "")),
                    "created_at": moment(row.get("created_at")),
                    "reason": str(row.get("void_reason") or ""),
                }
            )

        # بترتيبها الزمنيّ — الطوابعُ تروي المسار، لا الحالةُ الأخيرة وحدها.
        prepared.sort(key=lambda d: (str(d["created_at"] or ""), int(d["legacy"] or 0)))

        if self.dry:
            self.stdout.write(f"  سيُودَع: {len(prepared):,}")
            for status, count in Counter(d["status"] for d in prepared).most_common():
                self.stdout.write(f"    {status:<14} {count:>6,}")
            return

        from django.contrib.auth import get_user_model

        User = get_user_model()
        wanted = {d["user_id"] for d in prepared}
        people = {u.pk: u for u in User.objects.filter(pk__in=wanted)}
        deposited = moved = 0
        # خَتمُ الخطوة الثانية. بلاه يسقط D5 — راجع صدر الوحدة.
        stamped = set() if self._resettle else set(LegacyRef.resolve(SETTLED))
        fresh: dict[str, int] = {}

        for draft in prepared:
            user = people[draft["user_id"]]
            try:
                with transaction.atomic():
                    services.deposit_insurance(
                        user=user,
                        amount=draft["amount"],
                        source="cash",
                        # المفتاحُ مشتقٌّ من معرّف v1 — فإعادةُ التشغيل لا
                        # تُودع مرّتين (القاعدة ٢ وD5).
                        reference=f"v1-deposit-{draft['legacy']}",
                        occurred_at=draft["created_at"],
                        memo=f"ترحيل وديعة v1 #{draft['legacy']}",
                    )
                deposited += 1
            except Exception as exc:  # noqa: BLE001 — الرفضُ بيانٌ لا انهيار
                self._note(f"إيداع مرفوض: {type(exc).__name__}", draft["legacy"], exc)
                continue

            if draft["legacy"] in stamped:
                continue
            if self._settle(user, draft):
                moved += 1
            # يُختم نجح أو تعذّر: الفارقُ بين تشغيلتين أسوأ من محاولةٍ ضائعة،
            # و`--resettle` هو البابُ الصريح لإعادتها.
            fresh[draft["legacy"]] = user.pk

        if fresh:
            LegacyRef.remember(SETTLED, fresh)
        skipped = len(stamped & {d["legacy"] for d in prepared})
        self.stdout.write(
            f"  أُودع: {deposited:,} · نُقل إلى دلوه: {moved:,}"
            + (f" · مختومٌ سابقاً فتُخطّي: {skipped:,}" if skipped else "")
        )

    def _settle(self, user, draft: dict) -> bool:
        """انقل الوديعةَ إلى دلوها الأخير — بحالتها كما هي، بلا تصحيحٍ صامت.

        «ودائعُ وهميةٌ ومصادَرة **تُرحَّل بحالتها ولا تُصحَّح صامتاً**»
        (`spec.md`). فالمصادَرةُ تُصادَر والمستردَّةُ تُستردّ، ولو بدت خطأً —
        وتصحيحُها هنا يمحو الدليلَ الذي يبني عليه تقريرُ T313.
        """
        status, legacy = draft["status"], draft["legacy"]
        why = draft["reason"] or "بلا سبب مسجَّل"
        try:
            with transaction.atomic():
                if status == "held":
                    if draft["auction"] is None:
                        self._note("محجوزة: مزادٌ غير مُرحَّل", legacy, None)
                        return False
                    services.hold_for_auction(
                        user=user,
                        auction=_auction(draft["auction"]),
                        amount=draft["amount"],
                    )
                elif status == "locked":
                    invoice = self._invoice_for(user, draft)
                    if invoice is None:
                        self._note("مرهونة: لا فاتورةَ حيّةٌ تقابلها", legacy, None)
                        return False
                    # **بلا `amount`** — والخدمةُ تقرّر ما تحتاجه الفاتورة.
                    #
                    # كان يُمرَّر مبلغُ الوديعة كاملاً (١٠٬٠٠٠) فيُرهن كلُّه ولو
                    # كان الدَّينُ ٠٫٢٥ ريال. وأمسكه `verify_ledger` بثلاث
                    # ملاحظاتِ `locked_not_above_dues` بعد أوّل تصفيرٍ نظيف:
                    # «المقفول ١٠٬٠٠٠ والمستحقّ ٣٬٢٠٥٫٥٠».
                    #
                    # والقاعدةُ مكتوبةٌ في الفحص نفسِه: «الرهنُ ضمانٌ لا عقوبة.
                    # وحجزُ أكثرَ من الدَّين مالٌ يُنتزع من متناول العميل بلا
                    # ما نُدافع به أمامه — واستردادٌ كان من حقّه ولم يأخذه».
                    # وما يفيض عن الدَّين يبقى في «المتاح»، وهو موضعُه الصحيح.
                    services.lock_for_invoice(user=user, invoice=invoice)
                elif status == "refunded":
                    services.refund_insurance(
                        user=user,
                        amount=draft["amount"],
                        reference=f"v1-refund-{legacy}",
                        memo=f"استرداد v1 #{legacy} ({why})",
                    )
                elif status == "confiscated":
                    # المصادرةُ عندنا تقع على **حجزٍ** قائم، والوديعةُ المصادَرة
                    # في v1 قد لا تحمل مزاداً (٧٤ من ٨٠). فتُبنى حركةُ خروجٍ
                    # بمفتاحها الخاصّ عبر الدفتر نفسه — لا `confiscate` التي
                    # تطلب `Hold` و`by` بشريّاً لا وجود له في التاريخ.
                    services.post(
                        kind=TransactionKind.INSURANCE_CONFISCATE,
                        idempotency_key=f"v1-confiscate-{legacy}",
                        memo=f"مصادرة v1 #{legacy} ({why})",
                        legs=[
                            services.Leg(
                                services.account_for(user, "insurance_free"),
                                -draft["amount"],
                            ),
                            services.Leg(
                                services.system_account("confiscated"), draft["amount"]
                            ),
                        ],
                    )
                elif status != "free":
                    self._note("وديعة: حالةٌ غير معروفة", legacy, status)
                    return False
        except Exception as exc:  # noqa: BLE001
            self._note(f"نقلٌ مرفوض ({status}): {type(exc).__name__}", legacy, exc)
            return False
        return status != "free"

    def _invoice_for(self, user, draft: dict) -> Invoice | None:
        """فاتورةُ العميل الحيّة في مزاد هذه الوديعة — HR-01: الرهنُ بالمزاد."""
        if draft["auction"] is None:
            return None
        return (
            Invoice.objects.filter(
                customer=user,
                vehicle__auction_id=draft["auction"],
                state__in=[InvoiceState.OPEN, InvoiceState.PARTIAL],
            )
            .order_by("issued_at")
            .first()
        )

    # -- دفعات الفواتير -----------------------------------------------------

    def _payments(self, path: Path) -> None:
        """الدفعاتُ المرحَّلةُ وحدها، وكلُّ واحدةٍ إلى حدِّ المستحقّ لا فوقه."""
        bridge = LegacyRef.resolve("money.invoice")
        if not bridge:
            self.stdout.write(
                self.style.WARNING("\nلا جسرَ للفواتير — تُخطّى الدفعات.")
            )
            return

        # **الوصلةُ عبر `invoices_odoo.invoice_id` لا عبر `odoo_record_id`.**
        # الجدولان يحملان عمودَين لأودو، و`payments_odoo.invoice_id` يقابل
        # الأوّلَ منهما. وأوّلُ تشغيلٍ استعمل الثاني فرُفضت **١٠٬١٩٠ دفعةً**
        # بحجّة «فاتورةٌ غير معروفة» — وهي معروفةٌ كلُّها، والوصلةُ هي الخطأ.
        #
        # فيُبنى الجسرُ على خطوتين: رقمُ أودو ⟶ معرّفُ صفّ v1 (من النسخة)،
        # ثم معرّفُ الصفّ ⟶ فاتورتُنا (من `LegacyRef`, وهو المصدرُ المعتمَد).
        odoo_to_legacy = {
            str(row.get("invoice_id") or ""): str(row.get("id") or "")
            for row in read_table(path, "invoices_odoo")
            if row.get("invoice_id") not in (None, "", "/")
        }
        by_odoo = {
            odoo_id: bridge[legacy]
            for odoo_id, legacy in odoo_to_legacy.items()
            if legacy in bridge
        }

        rows = []
        skipped_unposted = 0
        for row in read_table(path, "payments_odoo"):
            if str(row.get("status")) != POSTED:
                skipped_unposted += 1
                continue
            amount = _decimal(row.get("amount"))
            invoice_pk = by_odoo.get(str(row.get("invoice_id") or ""))
            if amount is None or amount <= 0 or invoice_pk is None:
                self._note(
                    "دفعة: فاتورةٌ غير معروفة أو مبلغٌ غير موجب",
                    row.get("id"),
                    row.get("invoice_id"),
                )
                continue
            rows.append(
                {
                    "legacy": str(row.get("id") or ""),
                    "invoice_pk": invoice_pk,
                    "amount": amount.quantize(CENT),
                    "at": moment(row.get("created_at")),
                }
            )

        rows.sort(key=lambda d: (str(d["at"] or ""), int(d["legacy"] or 0)))
        self.stdout.write(
            f"\nالدفعات: {len(rows):,} مرحَّلةً · {skipped_unposted:,} غيرَ مرحَّلةٍ لم تُطبَّق"
        )
        if self.dry:
            return

        applied = 0
        for draft in rows:
            try:
                with transaction.atomic():
                    invoice = Invoice.objects.select_for_update().get(
                        pk=draft["invoice_pk"]
                    )
                    outstanding = invoice.outstanding
                    if outstanding <= Decimal("0.00"):
                        self.excess.append(
                            (invoice.number, draft["amount"], Decimal("0.00"))
                        )
                        continue
                    payable = min(draft["amount"], outstanding)
                    if payable < draft["amount"]:
                        self.excess.append(
                            (invoice.number, draft["amount"], payable)
                        )
                    # البابُ الواحد نفسُه الذي يمرّ به أودو وملفُّ الشريك
                    # وواجهةُ العميل — **ولا يحرّك هنا مركبةً واحدة**، وذلك
                    # مقصود: الترحيلُ لا يُرسي، فمركباتُه كلُّها `draft`
                    # (‏١١٬٩٥٥ منها يوم كُتب هذا) وجدولُ الانتقالات لا يعرف
                    # `draft ⇦ paid`. فقفزُ ١١٬٤٩٤ فاتورةً مسدَّدةً إلى
                    # مركباتٍ «مسدَّدة» يخترع تاريخاً لم يقع ويملأ طابورَ
                    # الخروج بسيّاراتٍ لم تُرسَ على أحد.
                    #
                    # ويمرّ من الباب مع ذلك لا حوله: يومَ يُرحَّل نظامٌ فيه
                    # ترسياتٌ حقيقيّة، تلحق المركبةُ بفاتورتها بلا سطرٍ
                    # يُكتب هنا. والامتناعُ قرارُ آلة الحالات لا نسيانُ
                    # مستدعٍ.
                    settlement.record_vehicle_payment(
                        invoice=invoice,
                        amount=payable,
                        source="cash",
                        reference=f"v1-payment-{draft['legacy']}",
                        occurred_at=draft["at"],
                    )
                applied += 1
            except Exception as exc:  # noqa: BLE001
                self._note(f"دفعة مرفوضة: {type(exc).__name__}", draft["legacy"], exc)

        self.stdout.write(f"  طُبِّق: {applied:,}")

    # -- التقرير -----------------------------------------------------------

    def _note(self, why: str, legacy, sample) -> None:
        self.notes[why] += 1
        self.samples.setdefault(why, f"صفّ {legacy} — {str(sample)[:60]}")

    def _report(self) -> None:
        if self.notes:
            self.stdout.write("\nما لم يُبنَ، بسببه:")
            for why, count in self.notes.most_common():
                self.stdout.write(f"  {count:>6}  {why}   ({self.samples[why]})")

        if self.excess:
            over = sum(a - p for _, a, p in self.excess)
            self.stdout.write(
                self.style.WARNING(
                    f"\nدفعاتٌ تتجاوز المستحقّ: {len(self.excess):,} — "
                    f"الفائضُ {over:,} ريال، سُدِّد حتى الحدّ ولم يُخترَع له سبب."
                )
            )
            for number, paid, payable in self.excess[:15]:
                self.stdout.write(
                    f"  {number}: الدفعة {paid} · سُدِّد {payable} · فائض {paid - payable}"
                )
            self.stdout.write(
                "وهذه مادّةُ T311 و T313: تشوّهٌ في بيانات v1 (أضعافُ عشرةٍ ومئةٍ "
                "وألف)، يُعرض ولا يُصحَّح صامتاً."
            )

        if self.dry:
            return
        self.stdout.write("\nفحصُ الدفتر:")
        from apps.money.verification import verify_ledger

        findings = verify_ledger()
        if findings:
            self.stdout.write(self.style.ERROR(f"  {len(findings)} ملاحظة:"))
            for finding in findings[:20]:
                self.stdout.write(f"    {finding}")
        else:
            self.stdout.write(self.style.SUCCESS("  نظيف — D3."))


def _auction(pk: int):
    from apps.auctions.models import Auction

    return Auction.objects.get(pk=pk)
