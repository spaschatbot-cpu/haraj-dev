"""The boundary with Odoo — the book of record for money.

Receive first, interpret second
-------------------------------
Every message Odoo sends is stored raw and acknowledged *before* anything tries
to understand it. Interpretation is a separate, replayable step.

This inverts v1's order, where a message was parsed on arrival and dropped if it
did not fit. Three of the worst incidents came out of that single decision: a
deduplication rule silently discarded the third webhook — the only one carrying
the invoice link; an unrecognised enum value rolled back the whole insert; and a
five-second timeout was read as proof that no cash had moved. A stored message
can be re-read after the bug is fixed. A discarded one is gone.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Q


class MessageDirection(models.TextChoices):
    INBOUND = "in", "وارد"
    OUTBOUND = "out", "صادر"


class InboundState(models.TextChoices):
    RECEIVED = "received", "مستلَمة"
    PROCESSED = "processed", "معالَجة"
    IGNORED = "ignored", "متجاهَلة عمداً"
    FAILED = "failed", "فشلت — قابلة لإعادة التشغيل"

    #: A message whose signature did not verify. It is *stored* rather than
    #: dropped: a burst of these is how an attack or a rotated secret makes
    #: itself visible, and there is nothing to investigate if we threw them
    #: away (Article 2-2).
    REJECTED_SIGNATURE = "rejected_signature", "توقيع مرفوض"


class InboundMessage(models.Model):
    """A message from Odoo (or a payment gateway), exactly as it arrived."""

    source = models.CharField(max_length=32, help_text="odoo | moyasar | manual")
    event = models.CharField(max_length=64, blank=True)

    #: Which Odoo database sent this. A message from the staging database
    #: arriving at production is stored and ignored, never acted on: in v1 two
    #: invented invoices from a test environment blocked a real bidder for
    #: three and a half hours.
    odoo_database = models.CharField(max_length=64, blank=True, db_index=True)

    #: The sender's own identifier for this delivery. Two deliveries with the
    #: same one are the same message; a *different* one about the same object is
    #: a new message and must never be deduplicated away.
    delivery_id = models.CharField(max_length=128, blank=True)

    #: What the message is about — an invoice number, a payment id. Indexed so
    #: the full conversation about one object can be read in order.
    subject_ref = models.CharField(max_length=128, blank=True, db_index=True)

    #: ``DjangoJSONEncoder`` because the body is decoded with
    #: ``parse_float=Decimal`` (Article 3-2) and a Decimal has to survive being
    #: written down. It stores one as a *string*, which is exactly right: the
    #: figure that comes back out is the sender's digits, not a float's nearest
    #: approximation of them.
    payload = models.JSONField(encoder=DjangoJSONEncoder)

    #: The body exactly as it arrived, before any parsing. Kept because a
    #: message we could not parse is precisely the one worth re-reading after
    #: the parser is fixed.
    raw_body = models.TextField(blank=True)
    headers = models.JSONField(default=dict, blank=True)

    state = models.CharField(
        max_length=24, choices=InboundState.choices, default=InboundState.RECEIVED
    )
    #: Why it is in that state. For FAILED this is the error; for IGNORED it is
    #: the human decision. Never empty for either.
    note = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    resulting_transaction = models.ForeignKey(
        "money.Transaction",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="from_messages",
    )

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # A delivery id identifies a delivery **the sender vouched for**.
            #
            # The `rejected_signature` clause is the whole of T913's finding.
            # Both boundaries store an unsigned message rather than dropping it
            # (Article 2-2), and both derive its delivery id from a body a
            # stranger wrote. With that row inside the index, posting
            # `{"id": 4711}` at either webhook *reserves* delivery 4711: when
            # the genuine, correctly-signed 4711 arrives, the insert collides,
            # the boundary reads "already stored", and the real message is
            # never stored and never interpreted. Odoo's ids are small
            # integers, so reserving a year of them is an afternoon's work —
            # and the messages lost that way are invoices and payments.
            #
            # So an unverified row is kept, and owns nothing.
            models.UniqueConstraint(
                fields=["source", "delivery_id"],
                condition=~Q(delivery_id="") & ~Q(state=InboundState.REJECTED_SIGNATURE),
                name="one_row_per_delivery",
            ),
        ]
        indexes = [
            models.Index(fields=["state", "received_at"]),
            models.Index(fields=["source", "event", "-received_at"]),
        ]
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.source}/{self.event} {self.subject_ref} ({self.state})"


class OutboxState(models.TextChoices):
    PENDING = "pending", "بالانتظار"
    SENT = "sent", "أُرسلت"
    CONFIRMED = "confirmed", "مؤكَّدة من أودو"
    FAILED = "failed", "فشلت"
    ABANDONED = "abandoned", "متروكة بقرار"


class OutboxMessage(models.Model):
    """Something we owe Odoo, written down before we try to send it.

    A retry cron that re-sends from this table is safe because the payload
    carries a reference Odoo treats as unique. v1's retry cron had no such
    guarantee and opened a duplicate refund on a customer's account.
    """

    endpoint = models.CharField(max_length=120)
    payload = models.JSONField(encoder=DjangoJSONEncoder)

    #: The reference Odoo will see. Unique here so the same intent cannot be
    #: queued twice, whatever calls us.
    reference = models.CharField(max_length=128, unique=True)

    state = models.CharField(
        max_length=16, choices=OutboxState.choices, default=OutboxState.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    #: Odoo's reply, kept as they sent it. Same encoder as the payload: their
    #: reply carries their amounts, and this row is read back during
    #: reconciliation.
    response = models.JSONField(null=True, blank=True, encoder=DjangoJSONEncoder)

    source_transaction = models.ForeignKey(
        "money.Transaction",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="outbox_messages",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["state", "created_at"])]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.endpoint} {self.reference} ({self.state})"


class CustomerLink(models.Model):
    """The bridge between an Odoo partner and a platform account.

    It is deliberately many-to-one in both directions: v1 assumed an Odoo
    customer id identified exactly one account, and when three customers turned
    out to have two or three accounts each, money keyed by Odoo was paired with
    deposits keyed by user and 20,000 was debited twice.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="odoo_links"
    )
    odoo_customer_id = models.CharField(max_length=64, db_index=True)

    is_primary = models.BooleanField(
        default=False, help_text="الحساب الذي تُنسب إليه الحركات الجديدة"
    )
    note = models.TextField(blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "odoo_customer_id"], name="one_link_per_pair"
            ),
            models.UniqueConstraint(
                fields=["odoo_customer_id"],
                condition=Q(is_primary=True),
                name="one_primary_account_per_odoo_customer",
            ),
        ]

    def __str__(self) -> str:
        return f"user {self.user_id} ↔ odoo {self.odoo_customer_id}"


class BalanceCheck(models.Model):
    """A comparison of our ledger against Odoo's own balance for one customer.

    v1 could prove the ledger agreed with itself and had no way to ask whether
    it agreed with the accounts. A customer showed 10,000 and bid with it while
    Odoo's ledger for him closed at zero. This table is where that question gets
    an answer, on a schedule.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="balance_checks"
    )
    ours = models.DecimalField(max_digits=14, decimal_places=2)
    theirs = models.DecimalField(max_digits=14, decimal_places=2)
    difference = models.DecimalField(max_digits=14, decimal_places=2)

    #: How we obtained Odoo's figure, so a stale method can be spotted later.
    method = models.CharField(max_length=64)
    detail = models.JSONField(default=dict, blank=True)

    checked_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-checked_at"]),
            models.Index(fields=["-checked_at"]),
        ]
        ordering = ["-checked_at"]

    def __str__(self) -> str:
        return f"user {self.user_id}: ours {self.ours} vs odoo {self.theirs}"


class RefundShortfall(models.Model):
    """Odoo asked us to pay back a deposit that is not free to leave. HR-09.

    ``PHASE_02`` §4-3: a pledged deposit is **never** refunded automatically, and
    a request to do so «تُسجل الحالة فوراً في طابور عجز لمراجعة الإدارة ولا تُنفذ
    آلياً».

    The incident it comes from: v1 paid back a deposit that was securing a car
    the customer had already won **and collected**, "مما ترك الشركة دون أي غطاء
    قانوني أو مالي". There was no money left to hold and no claim left to make.

    Refusing it is not enough on its own. The ledger already refuses — the free
    bucket has nothing in it and the CHECK stops the posting — but a refusal
    that lands as one more `failed` message says only that something went wrong.
    This row says **what** went wrong, **how short** it was, and what the
    customer's money looked like at that moment, so the answer to "why has my
    refund not arrived?" takes seconds.

    Nothing here is corrected automatically, for the same reason `BalanceCheck`
    is not: the platform's own arithmetic cannot decide whether a car was
    delivered. A person closes it, and says how.
    """

    message = models.ForeignKey(
        InboundMessage,
        on_delete=models.PROTECT,
        related_name="refund_shortfalls",
        help_text="الرسالة الواردة التي طلبت السحب",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="refund_shortfalls",
    )

    #: Odoo's own identifier for the refund, so their side can be found.
    refund_ref = models.CharField(max_length=128, db_index=True)

    requested = models.DecimalField(max_digits=14, decimal_places=2)

    #: A snapshot, not a join. The buckets will have moved by the time anybody
    #: reads this, and the question is what they were **when the request came**
    #: — the same reason `BidRefusal` photographs them (T502).
    free = models.DecimalField(max_digits=14, decimal_places=2)
    held = models.DecimalField(max_digits=14, decimal_places=2)
    locked = models.DecimalField(max_digits=14, decimal_places=2)

    #: How much of the request the free bucket could not answer.
    shortfall = models.DecimalField(max_digits=14, decimal_places=2)

    note = models.TextField(blank=True)

    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        verbose_name = "عجز استرداد"
        verbose_name_plural = "طابور عجز الاسترداد"
        constraints = [
            models.CheckConstraint(
                condition=Q(shortfall__gt=Decimal("0.00")),
                name="a_shortfall_is_a_shortfall",
            ),
            # One row per refund request. Odoo retries, and a queue that grows a
            # row per retry is a queue nobody reads — which is the same as not
            # having one.
            models.UniqueConstraint(
                fields=["refund_ref"], name="one_shortfall_per_refund_request"
            ),
            # A closed case says who closed it and how. `BalanceCheck` learned
            # this the same way: a resolved row with an empty resolution is a
            # decision nobody can be asked about.
            models.CheckConstraint(
                condition=Q(resolved_at__isnull=True)
                | (~Q(resolution="") & Q(resolved_by__isnull=False)),
                name="a_closed_shortfall_names_its_decision",
            ),
        ]
        indexes = [models.Index(fields=["resolved_at", "opened_at"])]

    def __str__(self) -> str:
        return f"عجز {self.shortfall} على استرداد {self.refund_ref}"
