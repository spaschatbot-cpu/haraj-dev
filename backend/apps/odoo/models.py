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

from django.conf import settings
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


class InboundMessage(models.Model):
    """A message from Odoo (or a payment gateway), exactly as it arrived."""

    source = models.CharField(max_length=32, help_text="odoo | moyasar | manual")
    event = models.CharField(max_length=64, blank=True)

    #: The sender's own identifier for this delivery. Two deliveries with the
    #: same one are the same message; a *different* one about the same object is
    #: a new message and must never be deduplicated away.
    delivery_id = models.CharField(max_length=128, blank=True)

    #: What the message is about — an invoice number, a payment id. Indexed so
    #: the full conversation about one object can be read in order.
    subject_ref = models.CharField(max_length=128, blank=True, db_index=True)

    payload = models.JSONField()
    headers = models.JSONField(default=dict, blank=True)

    state = models.CharField(
        max_length=16, choices=InboundState.choices, default=InboundState.RECEIVED
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
            models.UniqueConstraint(
                fields=["source", "delivery_id"],
                condition=~Q(delivery_id=""),
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
    payload = models.JSONField()

    #: The reference Odoo will see. Unique here so the same intent cannot be
    #: queued twice, whatever calls us.
    reference = models.CharField(max_length=128, unique=True)

    state = models.CharField(
        max_length=16, choices=OutboxState.choices, default=OutboxState.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    response = models.JSONField(null=True, blank=True)

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
