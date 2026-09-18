"""بانِي طلبات الاسترداد — T934. الصفوفُ وحدَها، ولا ريالَ يتحرّك.

    python manage.py build_refund_requests --dump D:/tmp/…_data_….sql.gz --dry-run
    python manage.py build_refund_requests --dump …                      # يكتب
    python manage.py build_refund_requests --dump … --write-json out.json
    python manage.py build_refund_requests --from-json out.json          # على الخادم

## لماذا أمرٌ مستقلّ عن `build_ledger`

`build_ledger` يقول بالحرف: «**و`refunds_requests` لا يحرّك ريالاً هنا** — …
الوديعةُ المستردَّة تحمل `status='refunded'` وفي الوقت نفسه يوجد صفُّ طلبٍ
بـ`deducted_at`. وبناءُ الاثنين يخصم المالَ مرّتين». وذلك القرارُ يبقى كما هو:
**هذا الأمرُ لا ينادي `apps.money.services` ولا مرّةً واحدة**، ولا يكتب قيداً
ولا يمسّ حساباً. يكتب صفوفَ `RefundRequest` — أي **تاريخَ من طلب ماذا وما صار
إليه** — ولا شيءَ غيرَها.

وهو ما كانت الشاشةُ تفتقده: على الإنتاج صفرُ طلبات، وفي الدفتر ١٬١٥٥ قيدَ
استرداد. فالأثرُ مُرحَّلٌ والطلبُ غائب.

## القياسُ الذي حسم كلَّ قرارٍ هنا (نسخة ٢٠٢٦-٠٩-٠٥)

| | |
|---|---|
| الصفوف | **3,289** |
| `status` | `approved` **3,121** · `rejected` **111** · `pending` **57** |
| `payment_state` | `posted` 3,122 · `cancelled` **101** · `cancel` **9** · `draft` 57 |
| `deducted_at` مملوء | 1,090 |
| `odoo_payment_id` مملوء | 3,288 من 3,289 |
| عملاءُ متميّزون | 2,068 |
| **أكثرُ من طلبٍ `pending` لعميل** | **صفر** — وأكبرُ عددٍ لعميلٍ واحد **1** |
| مبلغٌ ≤ صفر | **صفر** |

وثلاثةٌ من هذه الأرقام هي التي جعلت الترحيل ممكناً أصلاً:

**١) لا عميلَ له طلبان مفتوحان.** القيدُ
``one_open_refund_request_per_customer`` كان سيرفض الترحيل لو وُجد واحد،
ويُجبرنا على اختيار أيِّهما يُسقَط — أي على تخمين. فلا تخمين، والـ٥٧ تدخل
كلُّها `requested`.

**٢) `payment_state` فيه `cancelled` **و**`cancel` معاً** — ١٠١ و٩. وهو الفخُّ
المكتوبُ في `field-map.md` §"أيُّ شرطٍ يقارن بواحدةٍ منهما يفوته الآخر". فلا
يُقرَأ منه شرطٌ هنا إطلاقاً: `status` وحدَه يقرّر، و`payment_state` يُكتب نصّاً
في سجلّ القرار.

**٣) كلُّ المبالغ موجبة**، فلا صفَّ يسقط على `refund_request_is_positive`.
وليست كلُّها ١٠٬٠٠٠: ٣٬٢٣٧ كذلك، والباقي ٢٥٬٠٠٠ و٢٠٬٠٠٠ و١٫٠٠ و٩٬٠٠٠… فيُنقل
المبلغُ كما هو.

## لماذا `approved` ⟶ `v1_paid` لا `confirmed`

`confirmed` تشترط حركةً في دفترنا (``a_confirmed_refund_names_its_transaction``)،
**ولا حركةَ تقابل هذه الصفوف**. وقِيس المرشَّحُ الوحيدُ للربط — تطابقُ
``odoo_payment_id`` بين `refunds_requests` و`insurance_deposits` — فكانت
النتيجة **صفرَ تطابقٍ من ٣٬٢٨٨**. وليس ذلك خطأَ صيغة: عمودُ الوديعة يحمل
معرّفَ دفعةِ **الشحن** الداخلة (`moyasar_…` أو رقمَ إيداع)، وعمودُ الطلب
معرّفَ دفعةِ **الصرف** الخارجة. حدثان مختلفان.

فحالةٌ سادسةٌ تقول ما جرى بلا ادّعاء: «صُرف في v1». وسندُ أودو يُكتب في
`decision_note`، فالسؤالُ «أين ذهبت العشرةُ آلاف؟» جوابُه في الصفّ نفسِه.

## والمفتاحُ من v1 لا من عندنا

`reference` هو ``v1-refund-request-<id>`` بمعرّف v1 — وهو ما يجعل إعادةَ
التشغيل بلا أثر. والدرسُ من `backfill_awards`: ملفُّ JSON مفاتيحُه **معرّفاتُ
v1**، لأن مفاتيحَنا تختلف بين قاعدةٍ وأخرى — وملفٌّ بمفاتيحنا طُبِّق على
الإنتاج كان سيكتب على صفوفٍ أخرى.

**ولا يُلمس صفٌّ قائم.** الطلبُ الذي فُتح في نظامنا الجديد ليس من v1، والكتابةُ
فوقه محوٌ لا ترحيل. فما له `reference` مطابقٌ يُتخطّى ويُعدّ.
"""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.migration.dumpfile import read_table
from apps.migration.models import LegacyRef
from apps.money.models import RefundRequest, RefundRequestState
from apps.odoo.models import CustomerLink

from .import_v1 import moment

#: الجدولُ في v1.
TABLE = "refunds_requests"

#: ما يُنقل إلى JSON — **خامٌ كما في v1، بلا تفسير**. والتفسيرُ في هذا الملفّ
#: وحدَه، فيُقرأ في المراجعة ويُصحَّح في الشيفرة لا في ملفِّ بيانات.
#:
#: و`iban_image` **ليس فيها**: مسارُ ملفٍّ على خادم v1 لا نملكه، ونقلُه يعني
#: عموداً يشير إلى لا شيء. وصورةُ الآيبان عندنا مستندٌ في ملفّ العميل.
CARRY = (
    "id",
    "customer_id",
    "amount",
    "memo",
    "payment_code",
    "created_at",
    "odoo_payment_id",
    "status",
    "payment_name",
    "payment_state",
    "iban_account",
    "deducted_at",
)

#: حالةُ v1 ⟶ حالتُنا. **من `status` وحدَه** — انظر رأس الملفّ (§٢).
STATE = {
    "pending": RefundRequestState.REQUESTED.value,
    "approved": RefundRequestState.PAID_IN_V1.value,
    "rejected": RefundRequestState.REJECTED.value,
}

#: كم مثالاً يُطبع من كلِّ سببِ رفض.
SHOW = 5


def amount_of(raw) -> Decimal | None:
    """المبلغُ `Decimal` من النصّ مباشرةً، أو `None` لما ليس مبلغاً موجباً."""
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, TypeError):
        return None
    return value if value > Decimal("0.00") else None


def note_of(row: dict) -> str:
    """ما كتبه العميلُ ومعه آيبانُه — عمودُ «ما كتبه العميل» في الشاشة.

    و`memo` في v1 مولَّدٌ آلياً غالباً («طلب استرداد مبلغ التأمين للعميل …»)،
    لكنه **ما كُتب هناك**، فيُنقل كما هو. و`iban_account` مملوءٌ في ٩٧١ صفّاً
    فقط، ويُلحق حين يوجد لأن المحاسبةَ تسأل عنه أوّلَ شيء.
    """
    parts = [str(row.get("memo") or "").strip()]
    iban = str(row.get("iban_account") or "").strip()
    if iban:
        parts.append(f"الآيبان: {iban}")
    return " · ".join(part for part in parts if part)[:1000]


def decision_of(row: dict, state: str) -> str:
    """سجلُّ القرار: ما قاله v1 عن مصير الطلب، بسندِه.

    وهو ما يجعل `a_refused_refund_names_its_decision` قابلاً للتحقّق على صفٍّ
    مُرحَّل: v1 لا يكتب سبباً للرفض، **فيُقال ذلك صراحةً** بدل أن يُخترع سبب.
    """
    pay_state = str(row.get("payment_state") or "").strip()
    odoo = str(row.get("odoo_payment_id") or "").strip()

    # `payment_name` يأتي أحياناً `"/"` — وهو نائبُ أودو عن «مسوّدةٌ بلا اسم»،
    # لا اسمُ سند. وكتابتُه يعطي «سندُ أودو /» وهو سطرٌ يُقرأ ولا يقول شيئاً.
    name = str(row.get("payment_name") or "").strip()
    if name in ("", "/", "-"):
        name = ""

    sanad = " · ".join(
        bit
        for bit in (f"سندُ أودو {name}" if name else "", f"#{odoo}" if odoo else "")
        if bit
    )

    if state == RefundRequestState.PAID_IN_V1.value:
        head = "صُرف في v1"
    elif state == RefundRequestState.REJECTED.value:
        # الصفُّ الوحيدُ الذي `status='rejected'` و`payment_state='posted'`
        # يُقال كما هو، ولا يُصحَّح: تناقضُ v1 بيانٌ لا عطلٌ نُخفيه.
        head = "رُفض في v1 — ولا سببَ مسجَّلاً هناك"
    else:
        return ""

    tail = f"حالةُ أودو: {pay_state}" if pay_state else ""
    return " · ".join(bit for bit in (head, tail, sanad) if bit)[:1000]


class Command(BaseCommand):
    help = "يرحّل طلبات الاسترداد من v1 — صفوفاً لا قيوداً مالية. T934"

    def add_arguments(self, parser):
        parser.add_argument("--dump", help="مسارُ نسخة v1 (`.sql` أو `.sql.gz`)")
        parser.add_argument("--from-json", help="ملفُّ صفوفٍ كُتب بـ`--write-json`")
        parser.add_argument("--write-json", help="اكتب الصفوفَ الخام ولا تكتب في القاعدة")
        parser.add_argument("--dry-run", action="store_true", help="يعدّ ولا يكتب")

    # -- المصدر ------------------------------------------------------------

    def _rows(self, options) -> list[dict]:
        """صفوفُ v1 الخام — من النسخة أو من ملفّ JSON."""
        dump, path = options.get("dump"), options.get("from_json")
        if bool(dump) == bool(path):
            raise CommandError("مرّر `--dump` أو `--from-json`، واحداً منهما.")

        if path:
            source = Path(path)
            if not source.exists():
                raise CommandError(f"لا ملفّ: {source}")
            return json.loads(source.read_text(encoding="utf-8"))

        source = Path(dump)
        if not source.exists():
            raise CommandError(f"لا نسخة: {source}")
        return [{key: row.get(key) for key in CARRY} for row in read_table(source, TABLE)]

    # -- التنفيذ -----------------------------------------------------------

    def handle(self, *args, **options):
        rows = self._rows(options)
        self.stdout.write(f"صفوفُ v1: {len(rows):,}")

        out = options.get("write_json")
        if out:
            Path(out).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"كُتبت {len(rows):,} صفّاً في {out}"))
            return

        dry = options["dry_run"]

        # جسرُ العميل: `refunds_requests.customer_id` معرّفُ **أودو**، لا
        # `userss.id` — فخُّ `field-map.md` §١٥٤. ويُترجم من `CustomerLink`
        # الذي بناه `build_identity_map` من `customer_links` نفسِه.
        #
        # **والأساسيُّ وحدَه.** عميلُ أودو الذي له حسابان يُكتب ربطُه بلا
        # `is_primary` عمداً — «المتنازَعُ عليه لا يُحسَم آلياً»
        # (`build_identity_map`)، وهي القاعدةُ التي وُضعت بعد أن خُصم ٢٠٬٠٠٠
        # مرّتين في v1. فطلبُه يُرفض ويُعدّ، ولا يُسند إلى أحد الحسابين رمياً.
        by_odoo = {
            str(link["odoo_customer_id"]): link["user_id"]
            for link in CustomerLink.objects.filter(is_primary=True).values(
                "odoo_customer_id", "user_id"
            )
        }
        self.stdout.write(f"جسورُ عملاء أودو: {len(by_odoo):,}")

        known = set(
            RefundRequest.objects.filter(
                reference__startswith="v1-refund-request-"
            ).values_list("reference", flat=True)
        )

        drafts: list[RefundRequest] = []
        when: dict[str, dict] = {}
        refused: Counter = Counter()
        examples: dict[str, list] = {}
        states: Counter = Counter()
        seen_already = 0

        def refuse(why: str, row: dict) -> None:
            refused[why] += 1
            examples.setdefault(why, [])
            if len(examples[why]) < SHOW:
                examples[why].append(row.get("id"))

        for row in rows:
            legacy = str(row.get("id") or "").strip()
            if not legacy.isdigit():
                refuse("معرّفٌ لا يُقرأ", row)
                continue

            reference = f"v1-refund-request-{legacy}"
            if reference in known:
                seen_already += 1
                continue

            state = STATE.get(str(row.get("status") or "").strip())
            if state is None:
                refuse("حالةٌ غير معروفة", row)
                continue

            amount = amount_of(row.get("amount"))
            if amount is None:
                refuse("مبلغٌ ليس موجباً", row)
                continue

            user_pk = by_odoo.get(str(row.get("customer_id") or "").strip())
            if user_pk is None:
                # لا يُخمَّن ولا يُطرح بالجوّال: v1 فيه جوّالاتٌ مكرَّرة،
                # والمطابقةُ بها تخلط حسابين (المادة ٢-٣).
                refuse("عميلُ أودو بلا جسرٍ عندنا", row)
                continue

            decided_at = moment(row.get("deducted_at"))
            drafts.append(
                RefundRequest(
                    user_id=user_pk,
                    amount=amount,
                    reference=reference,
                    state=state,
                    note=note_of(row),
                    decision_note=decision_of(row, state),
                    # `decided_by` يبقى فارغاً: v1 لا يسجّل من قرّر، ونسبةُ
                    # القرار إلى أحدٍ اختراعُ واقعة.
                    decided_at=decided_at,
                )
            )
            when[reference] = {
                "created": moment(row.get("created_at")),
                "legacy": legacy,
            }
            states[state] += 1

        self.stdout.write("")
        for state, count in states.most_common():
            label = RefundRequestState(state).label
            self.stdout.write(f"  {count:>6,}  {label}")
        if seen_already:
            self.stdout.write(f"  {seen_already:>6,}  مُرحَّلٌ من قبل — يُتخطّى")

        if refused:
            self.stdout.write(self.style.WARNING("\nمرفوضٌ ومعدود:"))
            for why, count in refused.most_common():
                self.stdout.write(f"  {count:>6,}  {why} — مثالٌ: {examples[why]}")

        if dry or not drafts:
            self.stdout.write(self.style.WARNING("\nوضعُ العدّ — لم يُكتب شيء."))
            return

        with transaction.atomic():
            RefundRequest.objects.bulk_create(drafts, batch_size=500)

            # `created_at` عليه `auto_now_add`، فكلُّ صفٍّ يُكتب بلحظة الترحيل
            # ووقتُه الحقيقيّ يضيع — وهو عمودُ الترتيب في الشاشة، فالجدولُ
            # كلُّه يصير من لحظةٍ واحدة. و`reference` فريدٌ فالمطابقةُ به
            # مباشرةٌ ومضمونة (خلافاً لحيلة `import_v1` مع المزايدات).
            saved = {
                row.reference: row.pk
                for row in RefundRequest.objects.filter(reference__in=list(when)).only(
                    "pk", "reference"
                )
            }
            fixed = []
            for reference, pk in saved.items():
                created = when[reference]["created"]
                if created is not None:
                    fixed.append(RefundRequest(pk=pk, created_at=created))
            if fixed:
                RefundRequest.objects.bulk_update(fixed, ["created_at"], batch_size=500)

            bridged = LegacyRef.remember(
                "money.refundrequest",
                {when[ref]["legacy"]: pk for ref, pk in saved.items()},
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nكُتب {len(drafts):,} طلباً · صُحّح تاريخُ {len(fixed):,} · "
                f"جُسر {bridged:,} مفتاحاً."
            )
        )
        self.stdout.write("ولم يُكتب قيدٌ واحدٌ في الدفتر — وهذا مقصود.")
