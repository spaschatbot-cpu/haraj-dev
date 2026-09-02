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
* Balances are never written by ``± delta``. They are recomputed from the
  entries by :mod:`apps.money.services`, which is the only writer.
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
from django.db.models import Q

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
    #: :func:`apps.money.services.post`, always inside the posting transaction,
    #: always recomputed rather than adjusted.
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
            # One live invoice per vehicle. v1's duplication incident produced
            # 786 invoices from a loop; this makes the 787th impossible.
            models.UniqueConstraint(
                fields=["vehicle"],
                condition=Q(vehicle__isnull=False) & ~Q(state="cancelled"),
                name="one_live_invoice_per_vehicle",
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
