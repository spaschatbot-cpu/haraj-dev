"""سجل الدفعات — كل محاولة سدادٍ وما صارت إليه. T835.

الشاشة من لوحة v1 (`/payments`)، وأعمدتها هناك أربعة: رقم الفاتورة، والمبلغ،
والحالة، ومعرّف الصفّ. وهذه تعرض ما لم يكن هناك، لأن الأسئلة التي فُتحت لأجلها
الشاشة في v1 لم تكن تُجاب منها:

* **المحاولة الفاشلة تُعرَض.** v1 يعرض ما نجح، فيسأل العميل «دفعتُ ولم يصل»
  ولا صفَّ يُرى. و`PaymentIntent` يحمل `state` بستّ قيمٍ منها `failed`
  و`expired` و`disputed` — والفاشلةُ هي الصفُّ الذي يُبحث عنه، لا الناجحة.
* **الحركة الناتجة مربوطة.** `resulting_transaction` يقول أي قيدٍ في الدفتر
  نتج عن هذه الدفعة — وهو الجسر بين «العميل يقول دفع» و«الدفتر يقول ماذا».
  وكُتب هنا أوّلاً فرعٌ يصرخ «نجحت بلا قيد»، ثم حُذف: القاعدة نفسها فيها
  `a_succeeded_intent_names_its_transaction`، فالصفُّ لا يُكتب أصلاً. الحارس
  في القاعدة لا في القالب، وفرعٌ لا يقع أبداً يُقرأ حالةً ممكنة.
* **جواب البوابة الخام لا يُعرَض هنا.** `gateway_status_raw` سلسلةٌ من مزوّد
  الدفع تُقرأ في `console:audit` عند الخلاف؛ وضعُها في جدولٍ من ٥٠ صفّاً يجعل
  الصفَّ سطرين ولا يُقرأ.

لا شيء في هذه الشاشة يكتب
==========================
تسجيلُ دفعةٍ بيد موظّف **غير مبنيّ** في v2 — وهو مكتوبٌ صراحةً في
`apps/core/permissions.py` عند حذف `invoices.manage`. فهذه الشاشة تقرأ، ويوم
يُبنى الفعل يأتي بقدرته وصفحته معاً. زرٌّ هنا اليوم يعني قاعدةَ مالٍ في وحدة
عرض، وهو ما يرفضه `ops/checks/money_single_writer.py` أصلاً.

وشاشتان هنا لا واحدة
=====================
«سجل الدفعات» يقرأ ما قُيِّد (:class:`~apps.money.models.Payment`)، و«محاولات
الدفع» تقرأ ما جرت محاولتُه (:class:`~apps.money.models.PaymentIntent`) —
والفرقُ بينهما هو الجواب عن «دفعتُ ولم يصل»، فالمحاولةُ الفاشلة ليست دفعة.
وهما في وحدةٍ واحدة لأن سؤال الدعم واحد، ومن يفتح إحداهما يحتاج الأخرى في
النفَس نفسه.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.services import display_name, find_by_phone
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.money.models import (
    Invoice,
    PaymentIntent,
    PaymentIntentState,
    Transaction,
    TransactionKind,
)
from apps.money.services import wallet_snapshot

from . import sensitive
from .exports import export, wants_export
from .manual_payment import find_invoices, record_payment
from .paging import paged, pager
from .tones import with_tones
from .views import console_page

#: صفوفٌ في الصفحة. أكبر من قوائم الإدارة لأن هذه تُقرأ مسحاً بحثاً عن مرجعٍ
#: بعينه، والمرجع يُلصَق من رسالةٍ لا يُتصفَّح إليه.
PAGE_SIZE = 50

#: حالات الدفعة كما يعرّفها النموذج — تُقرأ منه ولا تُكرَّر هنا. قائمةٌ مكتوبةٌ
#: بيدٍ تتوقّف عن عرض حالةٍ يوم تُضاف واحدة، والحالة التي لا تُرشَّح هي الحالة
#: التي لا يجدها أحد.
STATES = {value for value, _ in PaymentIntent._meta.get_field("state").choices}


def search(*, text: str = "", state: str = ""):
    """الدفعات، منقّاةً بما كُتب. مفصولةٌ عن العرض ليسألها الاختبار مباشرةً."""
    rows = PaymentIntent.objects.select_related(
        "user", "auction", "resulting_transaction"
    )

    state = (state or "").strip()
    if state in STATES:
        rows = rows.filter(state=state)

    text = (text or "").strip()
    if text:
        # ثلاثة مداخل، لأن ثلاثةً هي ما يصل به السؤال: المرجع من إشعار
        # البوابة، والجوّال من العميل على الهاتف، والاسم حين لا يُتذكّر غيره.
        matches = search_q(text, "reference", "user__full_name")
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(user=person)
        rows = rows.filter(matches)

    return rows.order_by("-created_at")


#: أنواعُ القيود التي هي **سدادُ فاتورة** — لا كلُّ حركةِ مالٍ في الدفتر.
#: شحنُ التأمين وفكُّ حجزه حركاتٌ لها شاشاتُها (سجل المحفظة)، وهذه الشاشة
#: تجيب سؤالَ v1 وحدَه: «ماذا دُفع على الفواتير؟».
PAYMENT_KINDS = (TransactionKind.INVOICE_PAYMENT,)

#: بادئتا مفتاحِ المنع اللتان يكتبهما كودُنا لسدادِ فاتورة، ومنهما يُعرف
#: **أيُّ فاتورةٍ** — `services.record_payment` يكتب `payment:<pk>:<ref>`،
#: و`services.pay_invoice_from_balance` يكتب `invoice-payment:<number>:<ref>`.
#:
#: وقراءةُ المفتاح ليست تحليلَ نصٍّ حرّ: هو مفتاحٌ **نكتبه نحن** بشكلٍ ثابت،
#: والبديلُ عمودُ فاتورةٍ على `Transaction` — أي هجرةٌ على ١٧ ألف صفٍّ لأجل
#: عرض. ويوم يُبنى نموذجُ `Payment` الموعودُ في رأس هذه الوحدة يُقرأ منه.
KEY_BY_PK = "payment:"
KEY_BY_NUMBER = "invoice-payment:"


def invoice_of(key: str) -> tuple[str, str | int | None]:
    """من مفتاح المنع: بأيّ شكلٍ كُتب، وأيُّ فاتورةٍ يشير إليها."""
    if key.startswith(KEY_BY_PK):
        rest = key[len(KEY_BY_PK) :].split(":", 1)[0]
        return ("pk", int(rest)) if rest.isdigit() else ("", None)
    if key.startswith(KEY_BY_NUMBER):
        return ("number", key[len(KEY_BY_NUMBER) :].split(":", 1)[0])
    return ("", None)


def source_of(key: str) -> str:
    """مصدرُ الدفعة — عمودُ «المصدر» في v1، مشتقّاً لا مخزَّناً.

    v1 يحمله عموداً (`payments_test` مقابل `payments_odoo`)، وعندنا يُقرأ من
    مرجع الدفعة: ما جاء من الترحيل مرجعُه `v1-payment-…`، وما سُدِّد من
    الرصيد مرجعُه `balance:…`، وما عداهما قيدُ موظّفٍ أو بوّابة.
    """
    tail = key.rsplit(":", 1)[-1]
    if tail.startswith("v1-payment-"):
        return "مُرحَّلة من v1"
    if tail.startswith("balance:") or key.startswith("invoice-payment:"):
        return "من رصيد العميل"
    return "قيدُ موظّف"


def recorded(*, text: str = ""):
    """ما قُيِّد سداداً على فاتورة — الأحدثُ أوّلاً.

    **وهذه هي شاشةُ «إدارة المدفوعات» في v1 حرفاً.** كانت هنا تعرض
    `PaymentIntent` — أي **محاولاتِ** الدفع عبر البوّابة — وهي صفرٌ على
    الإنتاج بينما في الدفتر ١٣٬٨٦٣ قيدَ سداد. فالموظّفُ يفتح الشاشةَ التي
    اسمُها «إدارة المدفوعات» فيقرأ «لا دفعات»، وقد دُفعت.
    """
    rows = Transaction.objects.filter(kind__in=PAYMENT_KINDS).prefetch_related(
        "entries__owner"
    )
    text = (text or "").strip()
    if text:
        matches = Q(idempotency_key__icontains=text) | search_q(text, "memo")
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(entries__owner=person)
        else:
            matches |= Q(entries__owner__full_name__icontains=text)
        rows = rows.filter(matches).distinct()
    return rows.order_by("-occurred_at", "-id")


def decorate(page_rows) -> None:
    """يعلّق على كلّ قيدٍ ما تعرضه الشاشة: العميلُ والفاتورةُ والمبلغ.

    والفواتيرُ تُقرأ **باستعلامين للصفحة** لا باستعلامٍ لكل صفّ — الشاشةُ
    تُفتح على خمسين صفّاً، وخمسون رحلةً إلى القاعدة لعمودٍ واحد هي ما يجعل
    الصفحةَ تُحمَّل في ثانيتين بدل جزءٍ من ثانية.
    """
    by_pk, by_number = set(), set()
    for row in page_rows:
        shape, value = invoice_of(row.idempotency_key)
        row.invoice_ref = (shape, value)
        if shape == "pk":
            by_pk.add(value)
        elif shape == "number":
            by_number.add(value)

    # `select_related` على العميل: عمودُ «الاسم» يُقرأ منه — انظر أدناه.
    found = {
        ("pk", invoice.pk): invoice
        for invoice in Invoice.objects.filter(pk__in=by_pk).select_related("customer")
    }
    found |= {
        ("number", invoice.number): invoice
        for invoice in Invoice.objects.filter(number__in=by_number).select_related(
            "customer"
        )
    }

    for row in page_rows:
        row.invoice = found.get(row.invoice_ref)
        row.source = source_of(row.idempotency_key)
        # المرجعُ هو «اسم الدفعة» في v1 — ذيلُ المفتاح بعد الفاتورة.
        #
        # **وقصّاً من اليسار مرّةً واحدة، لا `rsplit` من اليمين.** المرجعُ نفسُه
        # قد يحمل نقطتين: `pay_invoice_from_balance` يكتب `balance:<txn>`،
        # فيُقرأ بـ`rsplit` رقماً عارياً — «١» في عمود المرجع، ولا يدلّ على
        # شيء. والمفتاحُ ثلاثةُ أجزاء: بادئةٌ ثم فاتورةٌ ثم المرجعُ كلُّه.
        row.reference = row.idempotency_key.split(":", 2)[-1]
        # **العميلُ من فاتورته، لا من قيود الحركة.** كُتب أوّلاً أنه صاحبُ
        # القيد الذي على حسابِ عميل — **وقِيس ففشل في مئتي صفٍّ من مئتين**:
        # سدادُ فاتورةٍ بتحويلٍ بنكيّ يمرّ من `external_cash` إلى الإيراد،
        # ولا يلمس محفظةَ العميل أصلاً، فلا قيدَ له مالك. والسدادُ من الرصيد
        # وحدَه يخصم من محفظته — فهو الاستثناءُ الذي يُقرأ من القيد.
        owned = [entry for entry in row.entries.all() if entry.owner_id]
        row.customer = (
            row.invoice.customer
            if row.invoice is not None
            else (owned[0].owner if owned else None)
        )
        row.amount = sum(entry.amount for entry in row.entries.all() if entry.amount > 0)


def _recorded_screen(request):
    """التبويبُ الافتراضيّ: ما قُيِّد سداداً على الفواتير.

    **وقيدُ الدفعة من هنا، لا من صفحةٍ ثانية** (قرار المالك، ١٨ سبتمبر
    ٢٠٢٦): «بدل ما أدخل على صفحة إنشاء دفعة، عايز زرار فوق في إدارة
    المدفوعات يعمل الدفعة». والقيدُ خطوتان — بحثٌ عن فاتورةٍ ثم تقييدٌ
    عليها — فالنافذةُ تحملهما: `find` يبحث والنافذةُ تُعاد مفتوحةً بنتيجته،
    و`op=create` يقيّد. ولا جافاسكربت في أيٍّ منهما.
    """
    text = request.GET.get("q", "")
    rows = recorded(text=text)

    if wants_export(request):
        page_rows = list(rows[:5000])
        decorate(page_rows)
        return export(
            page_rows,
            name="المدفوعات",
            headers=[
                "المعرّف",
                "المصدر",
                "رقم العميل",
                "الاسم",
                "الجوال",
                "رقم الفاتورة",
                "المبلغ",
                "اسم الدفعة",
                "التاريخ",
            ],
            cell=lambda row: [
                row.pk,
                row.source,
                row.customer.pk if row.customer else "",
                row.customer.full_name if row.customer else "",
                row.customer.phone if row.customer else "",
                row.invoice.number if row.invoice else "",
                row.amount,
                row.reference,
                row.occurred_at,
            ],
        )

    # نافذةُ القيد: تُفتح بزرّ، وتُعاد مفتوحةً بنتيجة بحثها.
    looking = request.GET.get("find", "")
    found = find_invoices(looking) if looking else None
    seen = sensitive.shown_to(request.user)

    page = paged(request, rows)
    decorate(page.object_list)
    return render(
        request,
        "console/payments.html",
        {
            "which": "recorded",
            "may_record": can(request.user, Capability.PAYMENTS_RECORD),
            "looking": looking,
            "candidates": [
                {
                    "invoice": invoice,
                    "name": display_name(invoice.customer),
                    # الجوّالُ عَرَضٌ هنا لا موضوع — فيمرّ بحارسه.
                    "phone": invoice.customer.phone if seen.customer else "",
                    # قاموسٌ بأسماء الدلاء — الشكلُ القديم (`insurance_free.balance`)
                    # كان يُرسم فارغاً بلا خطأ. انظر `manual_payment.py`.
                    "wallet": (
                        {
                            bucket.kind: bucket.amount
                            for bucket in wallet_snapshot(invoice.customer).buckets
                        }
                        if seen.wallet
                        else None
                    ),
                }
                for invoice in (found or [])
            ],
            "searched": found is not None,
            "opens": "payCreate" if looking else "",
            "page": page,
            "pager": pager(request, page, "دفعةً مقيَّدة"),
            "q": text,
            "export_url": f"?which=recorded&q={text}&export=1",
        },
    )


@console_page("console:payments")
def payments(request):
    """إدارة المدفوعات: ما قُيِّد سداداً، ومحاولاتُ البوّابة في تبويبٍ ثانٍ.

    **والافتراضيُّ ما قُيِّد** — وهو ما تعرضه شاشةُ v1. والمحاولاتُ خلف
    `?which=intents`: هي جوابُ «دفعتُ ولم يصل»، ولا تُخلط بالمقيَّد لأن
    محاولةً فاشلةً ليست دفعة.
    """
    # القيدُ من نافذة هذه الشاشة — والحارسُ هنا صراحةً: الصفحةُ تُفتح
    # بـ`invoices.view`، والقيدُ يحتاج `payments.record`. فمن يقرأ الجدول لا
    # يقيّد منه، ولو وصل إلى الاستمارة بيده.
    if request.method == "POST":
        if not can(request.user, Capability.PAYMENTS_RECORD):
            raise PermissionDenied("payments.record غير مسموحة لهذا المستخدم")
        return record_payment(request)

    which = request.GET.get("which", "")
    if which != "intents":
        return _recorded_screen(request)

    rows = search(
        text=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="سجل-الدفعات",
            headers=[
                "المرجع",
                "العميل",
                "الجوال",
                "المبلغ",
                "العملة",
                "الغرض",
                "المزاد",
                "البوابة",
                "الحالة",
                "الحركة الناتجة",
                "متى",
            ],
            cell=lambda row: [
                row.reference,
                row.user.full_name,
                row.user.phone,
                row.amount,
                row.currency,
                row.get_purpose_display(),
                row.auction.number if row.auction_id else "",
                row.gateway,
                row.get_state_display(),
                row.resulting_transaction_id or "",
                row.created_at,
            ],
        )

    page = paged(request, rows)
    with_tones(page.object_list)

    return render(
        request,
        "console/payments.html",
        {
            "which": "intents",
            "page": page,
            "pager": pager(request, page, "محاولةَ دفع"),
            "export_url": "?which=intents&export=1",
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "states": PaymentIntent._meta.get_field("state").choices,
        },
    )


# -------------------------------------------------------------------------
# محاولات الدفع عبر البوابة — الجواب عن «دفعتُ ولم يصل». T827
# -------------------------------------------------------------------------

STALE_AFTER = timezone.timedelta(hours=1)

#: كم صفّاً يُعرض بلا بحث. الشاشة تُفتح بسؤالٍ عن عميلٍ بعينه غالباً، وقائمةٌ
#: طويلة بلا سؤال ليست تشخيصاً.
LIMIT = 100


@console_page("console:payment-attempts")
def payment_attempts(request):
    """محاولاتُ الدفع، وأحدثُها أوّلاً؛ ويُبحَث بجوّالٍ أو مرجع.

    البحث بالجوّال لأن سؤال الدعم يبدأ منه: العميل يعرف رقمه ولا يعرف
    `reference` كتبه الخادم لنفسه.
    """
    query = (request.GET.get("q") or "").strip()

    rows = PaymentIntent.objects.select_related("user", "resulting_transaction")
    if query:
        rows = rows.filter(
            search_q(query, "user__phone", "reference", "gateway_payment_id")
        )

    cutoff = timezone.now() - STALE_AFTER
    attempts = []
    for intent in rows.order_by("-created_at")[:LIMIT]:
        stale = intent.state == PaymentIntentState.PENDING and intent.created_at < cutoff
        # نجحت ولم تُقيَّد: يمنعها قيدٌ في القاعدة، وتُحسب هنا ليكون الصفر
        # جواباً لا صمتاً.
        unposted = (
            intent.state == PaymentIntentState.SUCCEEDED
            and intent.resulting_transaction_id is None
        )
        attempts.append({"intent": intent, "stale": stale, "unposted": unposted})

    return render(
        request,
        "console/payment_attempts.html",
        {"attempts": attempts, "q": query, "stale_after_hours": 1},
    )
