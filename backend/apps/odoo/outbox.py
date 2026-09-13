"""Everything we owe Odoo, written down before we try to send it.

No caller reaches Odoo directly. A decision that needs to reach them becomes a
row here, and one worker drains the table. That indirection is what makes a
retry safe: the row carries a reference Odoo treats as unique, so sending it
twice cannot act twice.

v1's retry cron had no such reference and opened a second refund on a
customer's account — the same customer then saw three refund requests, two
theirs and one ours.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.money.models import Invoice, Transaction

from . import envelope
from .client import OdooUnreachable, call
from .models import OutboxMessage, OutboxState

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
BACKOFF_MINUTES = [1, 5, 25, 125, 360, 720, 1440, 1440]


def enqueue(
    *,
    endpoint: str,
    payload: dict,
    reference: str,
    source_transaction: Transaction | None = None,
) -> OutboxMessage:
    """Record an intention to tell Odoo something.

    The reference is unique in this table, so queuing the same intention twice
    returns the existing row rather than creating a second one. Two callers
    racing to record the same decision is ordinary; two rows would mean two
    calls to Odoo.
    """
    # الإدراجُ ينادي الإرسال: لا شيء بعده ينتظر استطلاعاً. والحجزُ بعد نجاح
    # الكتابة لا داخلها — مهمّةٌ تبدأ قبل أن تُثبَّت المعاملةُ تقرأ صفّاً لا وجود له.
    try:
        with db_transaction.atomic():
            message = OutboxMessage.objects.create(
                endpoint=endpoint,
                payload=payload,
                reference=reference,
                source_transaction=source_transaction,
            )
    except IntegrityError:
        existing = OutboxMessage.objects.filter(reference=reference).first()
        if existing is None:
            raise
        log.info("outbox: %s already queued as %s", reference, existing.pk)
        return existing

    # **بعد ثبات المعاملة لا داخلها**: مهمّةٌ تبدأ قبل الـcommit تقرأ صفّاً لا
    # وجود له بعد. و`on_commit` يضمن أن الحجز لا يقع إن رجعت المعاملة.
    def _go() -> None:
        from .tasks import dispatch

        dispatch(message)

    db_transaction.on_commit(_go)
    return message


def payment_reference(invoice: Invoice, payment: Transaction) -> str:
    """The reference Odoo will see for one payment against one invoice.

    Distinct per payment is the whole point. Odoo rejects a second payment
    carrying a reference it has already seen, and in v1 every partial payment on
    an invoice reused the invoice's own memo — 223 attempts across 26 invoices
    were refused for exactly this, and the money sat unapplied while the log
    filled with retries that could never succeed.

    The distinguishing half is the *payment's own identity*, not a position in a
    sequence. A counted sequence was derived from ``COUNT(*)`` taken before the
    insert, so two payments recorded on one invoice at the same moment both read
    the same count, both built ``INV/1/P1``, and :func:`enqueue` — right to
    treat a repeated caller-supplied reference as already queued — handed the
    loser the winner's row and its payload. Our ledger held two payments, Odoo
    heard about one, and nothing was left to replay. Article 1-5 asks for a key
    derived from the event's identity, and ``txn.uuid`` is that identity.
    """
    return f"{invoice.number}/P{payment.uuid}"


def due(now=None) -> list[OutboxMessage]:
    """Queued or failed messages whose backoff has elapsed."""
    now = now or timezone.now()
    candidates = OutboxMessage.objects.filter(
        state__in=[OutboxState.PENDING, OutboxState.FAILED],
        attempts__lt=MAX_ATTEMPTS,
    ).order_by("created_at")

    ready = []
    for message in candidates:
        if message.attempts == 0:
            ready.append(message)
            continue
        index = min(message.attempts, len(BACKOFF_MINUTES) - 1)
        last = message.sent_at or message.created_at
        if last + timedelta(minutes=BACKOFF_MINUTES[index]) <= now:
            ready.append(message)
    return ready


def send(message: OutboxMessage) -> OutboxMessage:
    """Deliver one message, and record honestly what happened.

    The outcomes are kept apart on purpose:

    * **confirmed** — Odoo took it, and whatever they told us in reply has been
      written back (an invoice id, a partner id).
    * **not ready** — the body cannot be built yet, almost always because the
      customer has no Odoo link. `failed`, with the reason, **and no attempt
      spent**: the thing that fixes it is a person linking the account, and
      burning the eight attempts while waiting would abandon a real invoice for
      a reason no retry was ever going to solve.
    * **failed** — could not reach them, or they were broken. Retry: the
      unique reference means a second attempt cannot act twice, and *not
      reaching them proves nothing about whether they acted* (Article 2-4).
    * **abandoned** — Odoo considered it and said no. Retrying sends the same
      thing again and gets the same answer, so it stops and waits for a
      person.
    """
    try:
        path, body = compose(message)
    except NotReadyToSend as exc:
        message.state = OutboxState.FAILED
        message.last_error = str(exc)
        message.save(update_fields=["state", "last_error"])
        log.info("outbox: %s not ready — %s", message.reference, exc)
        return message

    message.attempts += 1
    message.sent_at = timezone.now()
    message.state = OutboxState.SENT
    message.save(update_fields=["attempts", "sent_at", "state"])

    try:
        response = call(path, body, reference=message.reference)
    except OdooUnreachable as exc:
        message.state = OutboxState.FAILED
        message.last_error = str(exc)
        message.save(update_fields=["state", "last_error"])
        log.warning("outbox: %s unreachable — %s", message.reference, exc)
        return message
    except Exception as exc:  # noqa: BLE001 — a refusal is data, not a crash
        message.state = (
            OutboxState.ABANDONED if isinstance(exc, ValueError) else OutboxState.FAILED
        )
        message.last_error = f"{type(exc).__name__}: {exc}"
        message.save(update_fields=["state", "last_error"])
        log.error("outbox: %s refused — %s", message.reference, exc)
        return message

    if not envelope.accepted(response):
        # وصل، وقالوا لا — بكلمةٍ لا برمز HTTP. `abandoned` لأن إعادةَ إرسالِ
        # نفسِ الجسم تعطي نفسَ الجواب، ولأن الهجرَ يُرى في الصندوق ويُقرأ.
        message.state = OutboxState.ABANDONED
        message.response = response
        said = envelope.read(response, "status", "state")
        message.last_error = f"أودو ردّ برفضٍ: {said!r}"
        message.save(update_fields=["state", "response", "last_error"])
        log.error(
            "outbox: %s rejected by odoo — %s", message.reference, message.last_error
        )
        return message

    message.state = OutboxState.CONFIRMED
    message.response = response
    message.last_error = ""
    message.save(update_fields=["state", "response", "last_error"])
    apply_reply(message, response)
    log.info("outbox: %s confirmed", message.reference)
    return message


# ---------------------------------------------------------------------------
# من نيّةٍ عندنا إلى جسمٍ عند أودو — وبالعكس
# ---------------------------------------------------------------------------


class NotReadyToSend(RuntimeError):
    """الجسمُ لا يُبنى بعد، والسببُ لا يُصلحه تكرارُ المحاولة."""


def compose(message: OutboxMessage) -> tuple[str, dict]:
    """مسارُ أودو وجسمُه لهذه الرسالة — **يُبنى لحظةَ الإرسال لا لحظةَ الإدراج**.

    وهذا هو القرار الذي تقوم عليه الوحدة كلُّها. الصفُّ يحمل **نيّتنا** بحقولنا
    (رقمُ الفاتورة عندنا، مبلغٌ، مستخدم)، لا جسمَ أودو جاهزاً. ولذلك سببان
    عمليّان لا جماليّان:

    * **صفٌّ أُدرج قبل ربط العميل يُرسَل صحيحاً بعد ربطه.** رقمُ العميل في أودو
      لا يكون معروفاً وقتَ الإدراج دائماً؛ ولو خُتم الجسمُ حينها لبقيت الرسالة
      بلا `customer_id` إلى الأبد، ولوجب تعديلُ صفوفٍ مخزَّنة — وتعديلُ صفٍّ في
      طابورٍ ماليّ بابٌ لا يُفتح.
    * **وتغييرُ عقد أودو لا يُبطل ما في الصندوق.** الصفوفُ المدرَجة بالعقد
      القديم (وفيها صفوفٌ اليوم) تُرسَل بالعقد الجديد بلا هجرةِ بيانات.
    """
    path, method = envelope.path_and_method(message.endpoint)
    builder = _BUILDERS.get(message.endpoint)
    if builder is None:  # pragma: no cover — يمنعه `path_and_method` أصلاً
        raise NotReadyToSend(f"لا بانِيَ لجسم {message.endpoint!r}")
    return path, envelope.wrap(method, builder(message))


def _odoo_customer_id(user) -> str:
    """رقمُ هذا العميل عند أودو، أو توقُّفٌ بسببٍ مكتوب.

    من `CustomerLink` الأساسيّ وحده. ولا استنتاجَ من جوّالٍ ولا اسم — ذلك عينُ
    ما يُغلقه T218، وهو ما جعل صفّاً واحداً بجوّالٍ فارغٍ في v1 يطابق الجميع.
    """
    from .models import CustomerLink

    link = CustomerLink.objects.filter(user=user, is_primary=True).first()
    if link is None:
        raise NotReadyToSend(
            f"العميل {user.pk} غير مربوطٍ بحسابٍ أساسيّ في أودو — "
            "يُربط من ملفّ العميل ثم تُعاد المحاولة"
        )
    return link.odoo_customer_id


def _user_of(message: OutboxMessage):
    from django.contrib.auth import get_user_model

    user_id = message.payload.get("user")
    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        raise NotReadyToSend(f"لا مستخدمَ بالرقم {user_id!r} في الرسالة")
    return user


def _payment_params(message: OutboxMessage) -> dict:
    """دفعةٌ على فاتورة — `create/payments` بحقول v1 كاملةً.

    `payment_code` و`customer_id` و`partner_id` كانت **غائبةً كلُّها** قبل هذا،
    وهي إلزاميّةٌ في عقدهم. و`memo` يحمل مرجعَنا الفريد: هو ما يجعل إعادةَ
    الإرسال لا تُنشئ دفعةً ثانية، وهو ما لم يكن لدى كرون v1 فأنشأ استرداداً
    مكرَّراً على حساب عميل.
    """
    invoice = Invoice.objects.filter(pk=message.payload.get("invoice")).first()
    if invoice is None:
        raise NotReadyToSend(f"لا فاتورةَ بالرقم {message.payload.get('invoice')!r}")
    odoo_id = _odoo_customer_id(invoice.customer)
    if not invoice.odoo_invoice_id:
        raise NotReadyToSend(
            f"الفاتورة {invoice.number} لم تصل أودو بعد (لا `odoo_invoice_id`) — "
            "تُرسَل الفاتورة أولاً ثم دفعتُها"
        )
    return {
        "payment_code": settings.ODOO_PAYMENT_CODE,
        "customer_id": odoo_id,
        "partner_id": odoo_id,
        "invoice_id": invoice.odoo_invoice_id,
        "amount": message.payload["amount"],
        "currency": message.payload.get("currency", settings.CURRENCY),
        "memo": message.reference,
        "payment_reference": message.reference,
    }


def _refund_params(message: OutboxMessage) -> dict:
    odoo_id = _odoo_customer_id(_user_of(message))
    return {
        "payment_code": settings.ODOO_PAYMENT_CODE,
        "customer_id": odoo_id,
        "partner_id": odoo_id,
        "amount": message.payload["amount"],
        "currency": message.payload.get("currency", settings.CURRENCY),
        "memo": f"Insurance wallet refund {message.payload['reference']}",
        "payment_reference": message.payload["reference"],
    }


def _banktopup_params(message: OutboxMessage) -> dict:
    """شحنُ تأمينٍ بتحويلٍ بنكيّ — نقطةُ الاشتراك نفسُها التي يستعملها v1.

    **بلا `receipt_base64`.** v1 يرسل الإيصال مضمَّناً في الجسم، وصورةُ هاتفٍ
    تصير ميغابايتين نصّاً في صفٍّ مخزَّن وفي كل إعادة إرسال. والإيصالُ عندنا
    ملفٌّ على `BankTopupRequest`، والمالية تفتحه من اللوحة — **قرارُ مالك
    ٢٠٢٦-٠٩-٠٨: الترحيل يقع في أودو، واللوحة لا تعتمد**.
    """
    user = _user_of(message)
    odoo_id = _odoo_customer_id(user)
    return {
        "payment_code": settings.ODOO_PAYMENT_CODE,
        "customer_id": odoo_id,
        "amount": message.payload["amount"],
        "currency": message.payload.get("currency", settings.CURRENCY),
        "full_name": user.full_name or user.phone,
        "payment_reference": message.payload["reference"],
        "memo": message.payload["reference"],
    }


def _customer_params(message: OutboxMessage) -> dict:
    """إنشاءُ شريكٍ في أودو — النقطةُ التي لم تكن موجودة.

    بلا هذه لا يوجد شريكٌ لعميلٍ جديد أصلاً، فلا `customer_id` يُربط به، فكلُّ
    دفعةٍ تعود من أودو تقع في المعلَّق. وهي الطرفُ الآخر لكاتب `CustomerLink`
    (T221): ذاك يربط برقمٍ يعرفه موظّف، وهذه تُنشئ الرقمَ فيُكتب الربطُ من ردّ
    أودو لا من قرارِ أحد.

    و`operation_code` يفرّق الشركةَ عن الفرد كما في v1، والشركةُ تحمل حقولها.
    """
    user = _user_of(message)
    company = getattr(user, "company", None)
    is_company = company is not None
    address = getattr(user, "national_address", None)

    data = {
        "name": (company.name if is_company else "") or user.full_name or user.phone,
        "mobile": user.phone,
        "identity_number": user.national_id or "",
        "city": getattr(address, "city", "") or "",
    }
    if is_company:
        data.update(
            {
                "company_name": company.name,
                "cr_number": company.commercial_register or "",
                "cr_no": company.commercial_register or "",
                "tax_number": company.vat_number or "",
                "vat_number": company.vat_number or "",
            }
        )
    if address is not None:
        data["address"] = (
            f"{address.district} - {address.street} - {address.building_number}"
        ).strip(" -")

    return {
        "operation_code": "company" if is_company else "personal",
        "customer_data": data,
    }


def _invoice_params(message: OutboxMessage) -> dict:
    """فاتورةُ الفائز إلى أودو — وهي **لم تكن ترحل إليهم إطلاقاً**.

    `odoo_invoice_id` كان يُكتب من رسالةٍ **واردة** وحدها، أي أن المحاسبة كانت
    تنتظر مستنداً لا يرسله أحد؛ ودفعةٌ على فاتورةٍ لا يعرفها أودو مرفوضةٌ عندهم
    بالتعريف. وحقولُ المركبة في العقد ليست زينة: شاشةُ المحاسبة تُعرّف الفاتورة
    باللوحة والشاصي، لا برقمٍ من نظامٍ آخر.
    """
    invoice = Invoice.objects.filter(pk=message.payload.get("invoice")).first()
    if invoice is None:
        raise NotReadyToSend(f"لا فاتورةَ بالرقم {message.payload.get('invoice')!r}")
    odoo_id = _odoo_customer_id(invoice.customer)

    vehicle = invoice.vehicle
    params = {
        "customer_id": odoo_id,
        "partner_id": odoo_id,
        # **الإجماليُّ شاملَ الضريبة والرسم**، وهو ما تُصدره `issue_invoice`
        # في `amount`. وإرسالُ الصافي هنا كان سيجعل أودو يضيف ضريبتَه فوق
        # ضريبتنا — وهو HR-05 من الجهة الصادرة.
        "amount": str(invoice.amount),
        "currency": settings.CURRENCY,
        "memo": f"Auction winner invoice {invoice.number}",
        "payment_reference": message.reference,
    }
    if vehicle is not None:
        auction = getattr(vehicle, "auction", None)
        params.update(
            {
                "vehicle_id": vehicle.pk,
                "auction_id": str(getattr(auction, "pk", "") or ""),
                "Plate_number": vehicle.plate_number or "",
                "chasis_number": vehicle.vin or "",
                # أسماءُ أودو على يسار النقطتين وأسماؤنا على يمينها:
                # `vehicle_brand` عندهم هو `make` عندنا، و`car_color` هو
                # `colour`. والأخيرُ **بتسميته المعروضة** لا برمزه المخزَّن
                # (`white`): مستندُ المحاسبة يقرؤه إنسان، وv1 يرسل الاسم.
                "vehicle_brand": vehicle.make or "",
                "model": vehicle.model or "",
                "car_color": vehicle.get_colour_display() if vehicle.colour else "",
                "vehicle_name": str(vehicle),
            }
        )
    return params


_BUILDERS = {
    "payments": _payment_params,
    "refund.request": _refund_params,
    "banktopup.submit": _banktopup_params,
    "customer": _customer_params,
    "invoice": _invoice_params,
}


def apply_reply(message: OutboxMessage, response: dict) -> None:
    """اكتب ما أعطانا أودو في ردّه — وإلا كان النداءُ بلا أثر.

    نصفُ النداء هو الردّ. `create/customer` يعطي رقمَ الشريك و`create/invoice`
    يعطي رقمَ الفاتورة، وبلا كتابتِهما يبقى العميلُ غيرَ مربوطٍ وتبقى الفاتورةُ
    بلا `odoo_invoice_id` — فتُرسَل ثانيةً غداً وتُنشئ نسخةً ثانية عندهم.

    ولا يُرمى من هنا: الرسالةُ **مؤكَّدةٌ فعلاً** (أودو أخذها)، وخطأٌ في قراءة
    الردّ لا يجوز أن يقلبها فاشلةً فتُرسَل مرّةً أخرى.
    """
    try:
        if message.endpoint == "customer":
            _apply_customer(message, response)
        elif message.endpoint == "invoice":
            _apply_invoice(message, response)
    except Exception:  # noqa: BLE001 — الردُّ محفوظٌ في الصفّ ويُقرأ يدوياً
        log.exception(
            "outbox: %s confirmed but its reply could not be applied", message.reference
        )


def _apply_customer(message: OutboxMessage, response: dict) -> None:
    from .models import CustomerLink

    customer_id = envelope.read(response, "customer_id", "partner_id", "id")
    if not customer_id:
        log.error("outbox: %s — أودو لم يُعِد رقم عميل", message.reference)
        return
    user = _user_of(message)
    has_primary = CustomerLink.objects.filter(user=user, is_primary=True).exists()
    CustomerLink.objects.get_or_create(
        user=user,
        odoo_customer_id=str(customer_id),
        defaults={
            # أساسيٌّ إن لم يكن له أساسيٌّ بعد. ولا يُنتزع أساسيٌّ قائم: ذاك
            # قرارُ إنسان (T221)، وانتزاعُه هنا يحوّل مالاً بلا أن يقرأ أحد.
            "is_primary": not has_primary,
            "note": f"من ردّ أودو على {message.reference}",
        },
    )
    log.info(
        "outbox: %s linked user %s to odoo %s", message.reference, user.pk, customer_id
    )


def _apply_invoice(message: OutboxMessage, response: dict) -> None:
    invoice_id = envelope.read(response, "invoice_id", "move_id", "id")
    if not invoice_id:
        log.error("outbox: %s — أودو لم يُعِد رقم فاتورة", message.reference)
        return
    invoice = Invoice.objects.filter(pk=message.payload.get("invoice")).first()
    if invoice is None:
        return
    invoice.odoo_invoice_id = str(invoice_id)[:64]
    invoice.odoo_state_raw = str(envelope.read(response, "state") or "")[:64]
    invoice.save(update_fields=["odoo_invoice_id", "odoo_state_raw", "updated_at"])
    log.info(
        "outbox: %s stamped invoice %s as odoo %s",
        message.reference,
        invoice.number,
        invoice_id,
    )


# ---------------------------------------------------------------------------
# من يُدرج ماذا
# ---------------------------------------------------------------------------


def queue_payment(invoice: Invoice, amount: Decimal, *, source_transaction: Transaction):
    """Tell Odoo about a payment we recorded, with its own reference.

    ``source_transaction`` has no default on purpose: it is what the reference
    is built from, and without it two simultaneous payments on one invoice
    collapse into one message.
    """
    return enqueue(
        endpoint="payments",
        payload={
            "invoice": invoice.pk,
            # A string, not a float. Article 3-2 does not stop at our boundary.
            "amount": str(amount),
            "currency": settings.CURRENCY,
        },
        reference=payment_reference(invoice, source_transaction),
        source_transaction=source_transaction,
    )


def queue_customer(user):
    """اطلب من أودو شريكاً لهذا العميل، مرّةً واحدة.

    المرجعُ من مفتاح العميل عندنا لا من وقتٍ ولا عدّاد، فـ`enqueue` يردّ الصفَّ
    القائم بدل أن يُنشئ ثانياً — وشريكان لعميلٍ واحدٍ في أودو هو بالضبط ما جعل
    مالاً مفتاحُه أودو يقابل ودائعَ مفتاحُها المستخدم، فخُصم ٢٠٬٠٠٠ مرّتين.
    """
    return enqueue(
        endpoint="customer",
        payload={"user": user.pk},
        reference=f"customer:{user.pk}",
    )


def queue_invoice(invoice: Invoice):
    """أرسل فاتورةً أصدرناها إلى أودو، مرّةً واحدةً برقمها.

    لا تُدرَج لفاتورةٍ جاءت **منهم** (`InvoiceSource.ODOO_SYNC`): إعادتُها
    إليهم تُنشئ نسخةً ثانيةً لمستندٍ هو مستندُهم — وهو صدى HR-10 في الاتجاه
    الآخر.
    """
    from apps.money.models import InvoiceSource

    if invoice.source == InvoiceSource.ODOO_SYNC:
        return None
    if invoice.odoo_invoice_id:
        return None
    return enqueue(
        endpoint="invoice",
        payload={"invoice": invoice.pk},
        reference=f"invoice:{invoice.number}",
    )
