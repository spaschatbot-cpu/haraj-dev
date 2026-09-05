"""The money engine.

Every riyal in the system lives in exactly one *bucket* at any moment, and the
only way it moves is a balanced :class:`Transaction` made of signed
:class:`Entry` rows that sum to zero.

Reading the sign convention
---------------------------
An account's balance is simply *how many riyals are sitting in that bucket*, and
for anything belonging to a customer it can never go below zero. Money entering
or leaving the platform is represented by an ``EXTERNAL_*`` account, which goes
negative by exactly as much as has entered. So a 10,000 cash deposit is::

    EXTERNAL_CASH               -10,000
    <customer>.insurance_free   +10,000

That is the whole model. No debit/credit vocabulary to memorise: anyone can read
a transaction and see where the money went.

What this design refuses to repeat, from v1
-------------------------------------------
* A balance is a *cache*. It is moved by the difference under a row lock, by
  :mod:`apps.money.services` and nothing else, and re-derived from the entries
  by :func:`apps.money.verification.verify_ledger` — so the cache is checked
  rather than trusted. v1's mistake was not the cache; it was that nothing ever
  recomputed it, so nobody could tell a stale balance from a real one.
* A customer bucket carries a database CHECK that it cannot go negative, so an
  over-debit aborts the transaction instead of silently creating a hole.
* Nothing is ever updated or deleted. A mistake is corrected by a *reversing*
  transaction that points back at the one it reverses, so history stays whole.
* Status fields keep the raw third-party word alongside our own enum, so a value
  we have never seen can never abort the write that carries it.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q

MONEY = {"max_digits": 14, "decimal_places": 2}
ZERO = Decimal("0.00")


class AccountKind(models.TextChoices):
    """The buckets money can sit in."""

    # ---- customer-owned buckets (balance >= 0, always) --------------------
    WALLET = "wallet", "المحفظة"
    INSURANCE_FREE = "insurance_free", "تأمين متاح"
    INSURANCE_HELD = "insurance_held", "تأمين محجوز لمزاد"
    INSURANCE_LOCKED = "insurance_locked", "تأمين مقفول لمستحقات"

    # ---- platform-owned buckets -------------------------------------------
    CONFISCATED = "confiscated", "تأمين مصادَر"
    REVENUE = "revenue", "إيرادات"
    SUSPENSE = "suspense", "معلّق — وصلنا ولم نعرف صاحبه"

    # ---- the outside world (balance goes negative by design) --------------
    EXTERNAL_CASH = "external_cash", "خارجي — تحويل بنكي"
    EXTERNAL_CARD = "external_card", "خارجي — بطاقة"
    EXTERNAL_REFUND = "external_refund", "خارجي — استرداد مدفوع"

    @classmethod
    def customer_owned(cls) -> tuple[str, ...]:
        return (
            cls.WALLET.value,
            cls.INSURANCE_FREE.value,
            cls.INSURANCE_HELD.value,
            cls.INSURANCE_LOCKED.value,
        )

    @classmethod
    def external(cls) -> tuple[str, ...]:
        return (
            cls.EXTERNAL_CASH.value,
            cls.EXTERNAL_CARD.value,
            cls.EXTERNAL_REFUND.value,
        )


class Account(models.Model):
    """One bucket. Customer buckets have an owner; the rest are singletons."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    kind = models.CharField(max_length=32, choices=AccountKind.choices)

    #: Cached sum of this account's entries. Written only by
    #: :func:`apps.money.services.post`, always inside the posting transaction
    #: and always under this row's ``SELECT ... FOR UPDATE`` lock, by adding the
    #: movement's delta. :func:`apps.money.verification.check_cached_balances`
    #: recomputes it from the entries and reports any drift.
    balance = models.DecimalField(**MONEY, default=ZERO)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "kind"],
                name="one_account_per_owner_and_kind",
            ),
            models.UniqueConstraint(
                fields=["kind"],
                condition=Q(owner__isnull=True),
                name="one_singleton_account_per_kind",
            ),
            # A customer's bucket cannot go negative. This single constraint is
            # what makes an over-debit impossible rather than merely unlikely.
            models.CheckConstraint(
                condition=(
                    ~Q(kind__in=AccountKind.customer_owned()) | Q(balance__gte=ZERO)
                ),
                name="customer_buckets_never_go_negative",
            ),
            # Suspense holds money that arrived; it cannot hold less than none
            # of it. Without this the only guard was a Python read-then-post in
            # `attribute`, which two concurrent operators walked straight
            # through — 20,000 attributed against 10,000 that had arrived, and
            # `post`'s own floor does not apply because suspense is not a
            # customer bucket (Article 3-3).
            models.CheckConstraint(
                condition=~Q(kind=AccountKind.SUSPENSE) | Q(balance__gte=ZERO),
                name="suspense_never_goes_negative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(owner__isnull=False, kind__in=AccountKind.customer_owned())
                    | Q(owner__isnull=True)
                ),
                name="customer_buckets_must_have_an_owner",
            ),
        ]
        indexes = [models.Index(fields=["owner", "kind"])]

    def __str__(self) -> str:
        who = self.owner_id or "system"
        return f"{who}:{self.kind} = {self.balance}"


class TransactionKind(models.TextChoices):
    """Why money moved. Every business event that touches money has one."""

    INSURANCE_TOPUP = "insurance_topup", "إيداع تأمين"
    INSURANCE_HOLD = "insurance_hold", "حجز تأمين لمزاد"
    INSURANCE_RELEASE = "insurance_release", "فك حجز التأمين"
    INSURANCE_LOCK = "insurance_lock", "قفل التأمين على مستحقات"
    INSURANCE_UNLOCK = "insurance_unlock", "فك القفل بعد السداد"
    INSURANCE_REFUND = "insurance_refund", "استرداد تأمين"
    INSURANCE_CONFISCATE = "insurance_confiscate", "مصادرة تأمين"
    WALLET_TOPUP = "wallet_topup", "شحن المحفظة"
    WALLET_WITHDRAW = "wallet_withdraw", "سحب من المحفظة"
    INVOICE_PAYMENT = "invoice_payment", "سداد فاتورة"
    UNATTRIBUTED_RECEIPT = "unattributed_receipt", "مبلغ وصل بلا صاحب"
    ATTRIBUTION = "attribution", "نسب مبلغ معلّق لصاحبه"
    CORRECTION = "correction", "تصحيح"
    REVERSAL = "reversal", "عكس قيد"


class Transaction(models.Model):
    """A balanced, append-only money event.

    Never updated after posting. A wrong transaction is answered with a
    reversing one that names it in :attr:`reverses`.
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    kind = models.CharField(max_length=32, choices=TransactionKind.choices)

    #: The natural key of the real-world event this represents — an Odoo payment
    #: id, a Moyasar id, ``refund:552``. Posting twice with the same key is a
    #: no-op, which is what makes every inbound handler safely replayable.
    idempotency_key = models.CharField(max_length=200, unique=True)

    #: When the money actually moved in the world, which is not when we heard
    #: about it. Reports use this; ``created_at`` is for forensics only.
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    memo = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
        help_text="The operator who caused this, when a human did.",
    )
    reverses = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
    )

    class Meta:
        indexes = [
            models.Index(fields=["kind", "-occurred_at"]),
            models.Index(fields=["-created_at"]),
        ]
        ordering = ["-occurred_at", "-id"]

    def __str__(self) -> str:
        return f"{self.kind} {self.idempotency_key}"

    @property
    def total(self) -> Decimal:
        """The size of the movement — the sum of the positive entries."""
        return sum((e.amount for e in self.entries.all() if e.amount > 0), start=ZERO)


class Entry(models.Model):
    """One signed leg of a transaction. Positive means money arrived here."""

    transaction = models.ForeignKey(
        Transaction, on_delete=models.PROTECT, related_name="entries"
    )
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="entries")
    amount = models.DecimalField(**MONEY)

    #: Copied from the account so a customer's whole history is one index scan.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(amount=ZERO), name="entry_is_not_zero"),
        ]
        indexes = [
            models.Index(fields=["account", "id"]),
            models.Index(fields=["owner", "id"]),
        ]

    def __str__(self) -> str:
        return f"{self.account_id} {self.amount:+}"


class HoldReason(models.TextChoices):
    BIDDING = "bidding", "ضمان المزايدة"
    DUES = "dues", "مقابل مستحقات غير مسدَّدة"


class HoldState(models.TextChoices):
    ACTIVE = "active", "قائم"
    RELEASED = "released", "مفكوك"
    CONSUMED = "consumed", "استُهلك"


class Hold(models.Model):
    """A named claim on part of a customer's insurance.

    The money has already moved into ``insurance_held`` or ``insurance_locked``
    by the transaction that created the hold; this row records *why*, so the
    platform can answer "which auction is this 10,000 securing?" instead of
    inferring it.

    In v1 that question had no stored answer, and two holds silently pinned
    themselves to the same debt. Here a hold names its subject, and
    ``verify_ledger`` asserts the held total equals the sum of active holds.
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="holds"
    )
    amount = models.DecimalField(**MONEY)
    reason = models.CharField(max_length=16, choices=HoldReason.choices)
    state = models.CharField(
        max_length=16, choices=HoldState.choices, default=HoldState.ACTIVE
    )

    auction = models.ForeignKey(
        "auctions.Auction",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="holds",
    )
    invoice = models.ForeignKey(
        "money.Invoice",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="holds",
    )

    created_by_transaction = models.ForeignKey(
        Transaction, on_delete=models.PROTECT, related_name="holds_created"
    )
    ended_by_transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="holds_ended",
    )

    #: An operator may deliberately let one hold secure a second debt. In v1
    #: this was done by hand-editing two columns and left no trace; here it is
    #: a decision with a name attached to it.
    exception_note = models.TextField(blank=True)
    exception_granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=ZERO), name="hold_is_positive"),
            models.CheckConstraint(
                condition=(
                    Q(state=HoldState.ACTIVE, ended_by_transaction__isnull=True)
                    | ~Q(state=HoldState.ACTIVE)
                ),
                name="active_hold_has_not_ended",
            ),
            # One active hold per (customer, auction) — the over-lock race that
            # pinned two deposits to one debt cannot be expressed here.
            models.UniqueConstraint(
                fields=["owner", "auction"],
                condition=Q(state="active", auction__isnull=False),
                name="one_active_hold_per_customer_and_auction",
            ),
            # And one per (customer, invoice), for the same reason on the dues
            # side. Without this the auction case was guarded and the debt case
            # was not, which is exactly the asymmetry that let v1 lock one
            # deposit against a debt twice.
            models.UniqueConstraint(
                fields=["owner", "invoice"],
                condition=Q(state="active", invoice__isnull=False),
                name="one_active_hold_per_customer_and_invoice",
            ),
            # A hold names what it secures. A row that points at neither an
            # auction nor an invoice is money pinned for no stated reason —
            # the thing this table exists to make impossible.
            models.CheckConstraint(
                condition=Q(auction__isnull=False) | Q(invoice__isnull=False),
                name="a_hold_names_its_subject",
            ),
        ]
        indexes = [models.Index(fields=["owner", "state"])]

    def __str__(self) -> str:
        return f"hold {self.amount} {self.reason} ({self.state})"


class InvoiceState(models.TextChoices):
    DRAFT = "draft", "مسودة"
    OPEN = "open", "مستحقة"
    PARTIAL = "partial", "مسدَّدة جزئياً"
    PAID = "paid", "مسدَّدة"
    CANCELLED = "cancelled", "ملغاة"


#: An invoice the customer still owes something on.
#:
#: Defined here, beside the enum, because three modules ask the same question —
#: eligibility ("does this person owe us?"), settlement ("may this deposit go
#: back?") and the console — and a fourth list of states is a fourth chance for
#: one of them to forget `partial` (Article 4-5).
UNPAID_INVOICE_STATES = (InvoiceState.OPEN, InvoiceState.PARTIAL)


class InvoiceSource(models.TextChoices):
    """Where an invoice was born — and therefore what its ``amount`` means.

    This is the whole of HR-05. ``PHASE_03`` §2 calls it the finest trap in the
    v1 files: an invoice we raise carries amounts **before** tax, and one Odoo
    sends back carries amounts **including** it. Applying the same 15% equation
    to both charges the customer 15% on top of a figure that already had it —
    silently, and on every Odoo invoice.

    So the source is recorded at birth, before anything computes tax, because
    the day something does the answer has to already exist. A column added
    afterwards can only guess at rows already written.
    """

    LOCAL = "local", "محلية"
    ODOO_SYNC = "odoo_sync", "من أودو"


class Invoice(models.Model):
    """What a customer owes us.

    v1 mirrored Odoo's invoice into a status column written once at insert and
    never again, so every mirrored invoice read ``draft`` forever and no code
    could safely branch on it. Here the state is **derived** from the payments
    recorded against the invoice, and Odoo's own word is kept beside it as
    evidence rather than as truth.
    """

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="invoices"
    )
    number = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(**MONEY)
    amount_paid = models.DecimalField(**MONEY, default=ZERO)

    state = models.CharField(
        max_length=16, choices=InvoiceState.choices, default=InvoiceState.DRAFT
    )
    #: Odoo's literal state string, whatever it happens to be. Recorded, never
    #: branched on, never allowed to fail a write.
    odoo_state_raw = models.CharField(max_length=64, blank=True)
    odoo_invoice_id = models.CharField(max_length=64, blank=True, db_index=True)

    #: Deliberately without a default. A default here would be the trap itself:
    #: an Odoo invoice created by a caller who forgot would be filed as `local`,
    #: read as pre-tax, and taxed a second time — quietly, and correctly as far
    #: as any code could tell. A CHECK refuses the empty value instead, so
    #: forgetting is an IntegrityError at the write rather than a wrong number
    #: on a customer's invoice (Article 3-3).
    source = models.CharField(max_length=16, choices=InvoiceSource.choices)

    vehicle = models.ForeignKey(
        "auctions.Vehicle",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="invoices",
    )

    issued_at = models.DateTimeField()
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=ZERO), name="invoice_amount_not_negative"
            ),
            models.CheckConstraint(
                condition=Q(amount_paid__gte=ZERO), name="invoice_paid_not_negative"
            ),
            # And not above the invoice either. `record_payment` refuses to
            # over-pay, but the mirror from Odoo writes `amount` without looking
            # at what has been paid — lowering a settled 20,000 invoice to 5,000
            # made 15,000 of real dues vanish from every report, because
            # `outstanding` clamps at zero and the derived state reads PAID.
            models.CheckConstraint(
                condition=Q(amount_paid__lte=F("amount")),
                name="invoice_paid_not_above_amount",
            ),
            # One live invoice per vehicle. v1's duplication incident produced
            # 786 invoices from a loop; this makes the 787th impossible.
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(vehicle__isnull=False) & ~Q(state="cancelled"),
                name="one_live_invoice_per_vehicle",
            ),
            # Every invoice says where it came from, because that is what says
            # whether its amount already carries tax (HR-05). An unnamed source
            # is not a small gap: it is a figure nobody can compute correctly.
            models.CheckConstraint(
                condition=Q(source__in=["local", "odoo_sync"]),
                name="invoice_names_its_source",
            ),
        ]
        indexes = [models.Index(fields=["customer", "state"])]

    def __str__(self) -> str:
        return f"{self.number} {self.amount} ({self.state})"

    @property
    def outstanding(self) -> Decimal:
        if self.state == InvoiceState.CANCELLED:
            return ZERO
        return max(self.amount - self.amount_paid, ZERO)


class PaymentMethod(models.TextChoices):
    """How a customer may settle an invoice.

    There is deliberately no card member. A purchase is settled from money the
    customer has already deposited, or by a bank transfer the bank confirms —
    never by a card charge that can be reversed months later against a vehicle
    that has already left the yard.
    """

    BALANCE = "balance", "من الرصيد"
    BANK_TRANSFER = "bank_transfer", "تحويل بنكي"


class PaymentPurpose(models.TextChoices):
    """What a card payment is for.

    Also deliberately narrow: topping up insurance is the only thing a card ever
    pays for here, which is what makes "no card for purchases" a property of the
    schema rather than a rule somebody has to keep remembering.
    """

    INSURANCE_DEPOSIT = "insurance_deposit", "إيداع تأمين"


class PaymentIntentState(models.TextChoices):
    PENDING = "pending", "بانتظار الدفع"
    SUCCEEDED = "succeeded", "تمت"
    FAILED = "failed", "فشلت"
    CANCELLED = "cancelled", "ألغاها العميل"
    EXPIRED = "expired", "انتهت مهلتها"
    DISPUTED = "disputed", "محل نزاع"


class PaymentIntent(models.Model):
    """What we decided a customer would pay, written down before they pay it.

    The row exists *before* the customer reaches the gateway, and it is the only
    thing that says whose money a returning payment is. The gateway does not
    carry our user id, and v1 tried to recover it from whatever came back in the
    query string — which is both losable and forgeable. Here attribution is a
    lookup on :attr:`reference` against a row the server wrote itself.

    :attr:`amount` is likewise the server's number. A request that tries to name
    its own amount is refused at the edge.
    """

    #: Our identifier, handed to the gateway as metadata and echoed back.
    reference = models.CharField(max_length=64, unique=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_intents"
    )
    amount = models.DecimalField(**MONEY)
    currency = models.CharField(max_length=3, default="SAR")

    purpose = models.CharField(max_length=32, choices=PaymentPurpose.choices)
    auction = models.ForeignKey(
        "auctions.Auction",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_intents",
        help_text="المزاد الذي طُلب التأمين من أجله، إن وُجد",
    )

    state = models.CharField(
        max_length=16,
        choices=PaymentIntentState.choices,
        default=PaymentIntentState.PENDING,
    )

    gateway = models.CharField(max_length=32, default="moyasar")
    gateway_payment_id = models.CharField(max_length=128, blank=True, db_index=True)
    #: The gateway's literal status word. Recorded, never branched on, never
    #: allowed to fail the write that carries it.
    gateway_status_raw = models.CharField(max_length=64, blank=True)

    resulting_transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_intents",
    )
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=ZERO), name="payment_intent_is_positive"
            ),
            # One gateway payment answers at most one intent, so a replayed
            # callback cannot credit a second deposit.
            models.UniqueConstraint(
                fields=["gateway", "gateway_payment_id"],
                condition=~Q(gateway_payment_id=""),
                name="one_intent_per_gateway_payment",
            ),
            # Article 1-6: a succeeded payment can always be traced to the
            # entries it created.
            models.CheckConstraint(
                condition=(
                    ~Q(state="succeeded") | Q(resulting_transaction__isnull=False)
                ),
                name="a_succeeded_intent_names_its_transaction",
            ),
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.reference} {self.amount} ({self.state})"


class RefundRequestState(models.TextChoices):
    REQUESTED = "requested", "مُقدَّم"
    SENT = "sent", "أُرسل للمحاسبة"
    CONFIRMED = "confirmed", "نُفِّذ"
    REJECTED = "rejected", "مرفوض"
    CANCELLED = "cancelled", "ألغاه العميل"

    @classmethod
    def open_states(cls) -> tuple[str, ...]:
        """The states in which a request may still cost us money.

        Named once, because the constraint below and the service that produces
        the Arabic refusal must mean exactly the same set (Article 4-5).
        """
        return (cls.REQUESTED.value, cls.SENT.value)


class RefundRequest(models.Model):
    """A customer asking for their free insurance back.

    Asking moves no money. The ledger moves only when the accounting system
    confirms the payout, through the inbound path — v1 credited optimistically
    and then had to chase what never left the bank.

    The unique :attr:`reference` is what stops a retry cron from opening a second
    request at Odoo for one customer decision.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="refund_requests"
    )
    amount = models.DecimalField(**MONEY)
    reference = models.CharField(max_length=64, unique=True)

    state = models.CharField(
        max_length=16,
        choices=RefundRequestState.choices,
        default=RefundRequestState.REQUESTED,
    )

    outbox_message = models.ForeignKey(
        "odoo.OutboxMessage",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="refund_requests",
    )
    resulting_transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="refund_requests",
    )
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=ZERO), name="refund_request_is_positive"
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(state="confirmed") | Q(resulting_transaction__isnull=False)
                ),
                name="a_confirmed_refund_names_its_transaction",
            ),
            # One open request per customer. Asking moves no money, so the
            # balance a request is checked against does not move either — ten
            # requests each passed the same check against the same untouched
            # 10,000 and instructed accounting to pay out 100,000. The rule
            # lives here rather than in the service because a service check
            # against an unchanging number is not a reservation.
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(state__in=("requested", "sent")),
                name="one_open_refund_request_per_customer",
            ),
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"refund {self.reference} {self.amount} ({self.state})"
