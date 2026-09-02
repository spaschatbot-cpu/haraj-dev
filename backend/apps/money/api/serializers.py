"""How money looks on the wire.

One rule governs this module: **an amount is a decimal string, never a JSON
number.** A float cannot hold 0.10 exactly, and a client that parses one has
already lost the halalas before it renders them. :class:`MoneyField` takes its
precision from the same ``MONEY`` definition the columns use, so there is one
place that says "14 digits, 2 places".
"""

from __future__ import annotations

from rest_framework import serializers

from apps.money.models import (
    MONEY,
    AccountKind,
    Hold,
    HoldReason,
    Invoice,
    InvoiceState,
    PaymentIntent,
    PaymentIntentState,
    PaymentMethod,
    PaymentPurpose,
    RefundRequest,
    RefundRequestState,
    TransactionKind,
)


class MoneyField(serializers.DecimalField):
    """A ``Decimal(14, 2)`` that always crosses the wire as a string."""

    def __init__(self, **kwargs):
        kwargs.setdefault("max_digits", MONEY["max_digits"])
        kwargs.setdefault("decimal_places", MONEY["decimal_places"])
        kwargs.setdefault("coerce_to_string", True)
        super().__init__(**kwargs)


def label_for(choices_class, value: str, fallback: str) -> str:
    """The Arabic label for an enum value, without ever showing the raw key.

    Article 3-5 keeps these enums wide, and a value we have not seen must not
    reach a customer as an English identifier — it degrades to a generic Arabic
    word instead.
    """
    try:
        return choices_class(value).label
    except ValueError:
        return fallback


# ---------------------------------------------------------------------------
# Wallet
# ---------------------------------------------------------------------------


class BucketSerializer(serializers.Serializer):
    """One named pot, with the count of entries that add up to it."""

    kind = serializers.CharField()
    label = serializers.CharField()
    amount = MoneyField()
    entry_count = serializers.IntegerField()
    statement = serializers.SerializerMethodField()

    def get_statement(self, bucket) -> str:
        """Where to read the exact entries behind this number (Article 1-6)."""
        return self.context["statement_url"] + f"?bucket={bucket.kind}"


class HoldSerializer(serializers.ModelSerializer):
    """A claim on part of the customer's insurance, and what it is claimed for."""

    amount = MoneyField()
    reason_label = serializers.SerializerMethodField()
    auction = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()

    class Meta:
        model = Hold
        fields = [
            "id",
            "amount",
            "reason",
            "reason_label",
            "auction",
            "invoice",
            "created_at",
        ]

    def get_reason_label(self, hold) -> str:
        return label_for(HoldReason, hold.reason, "حجز")

    def get_auction(self, hold) -> dict | None:
        if hold.auction_id is None:
            return None
        return {
            "id": hold.auction_id,
            "number": hold.auction.number,
            "title": hold.auction.title,
        }

    def get_invoice(self, hold) -> dict | None:
        if hold.invoice_id is None:
            return None
        return {"id": hold.invoice_id, "number": hold.invoice.number}


class WalletSerializer(serializers.Serializer):
    currency = serializers.CharField()
    total = MoneyField()
    available = MoneyField()
    held_for_auctions = MoneyField()
    locked_for_dues = MoneyField()
    buckets = BucketSerializer(many=True)
    holds = HoldSerializer(many=True)
    as_of = serializers.DateTimeField()


class StatementQuerySerializer(serializers.Serializer):
    """Validates the statement filter against the same tuple the ledger uses."""

    bucket = serializers.ChoiceField(
        choices=[(kind, kind) for kind in AccountKind.customer_owned()],
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": "نوع الرصيد المطلوب غير معروف."},
    )


class LedgerEntrySerializer(serializers.Serializer):
    """One line of the statement, read straight off an ``Entry`` row."""

    id = serializers.IntegerField()
    transaction = serializers.UUIDField(source="transaction.uuid")
    kind = serializers.CharField(source="transaction.kind")
    description = serializers.SerializerMethodField()
    bucket = serializers.CharField(source="account.kind")
    bucket_label = serializers.SerializerMethodField()
    amount = MoneyField()
    direction = serializers.SerializerMethodField()
    occurred_at = serializers.DateTimeField(source="transaction.occurred_at")
    memo = serializers.CharField(source="transaction.memo")

    def get_description(self, entry) -> str:
        return label_for(TransactionKind, entry.transaction.kind, "حركة مالية")

    def get_bucket_label(self, entry) -> str:
        return label_for(AccountKind, entry.account.kind, "رصيد")

    def get_direction(self, entry) -> str:
        return "in" if entry.amount > 0 else "out"


# ---------------------------------------------------------------------------
# Top-ups
# ---------------------------------------------------------------------------

#: Anything a client might call "the amount". Naming them explicitly lets the
#: refusal say *why*, instead of silently ignoring a field the caller believed
#: in — a silent ignore is how the v1 tampering went unnoticed for a release.
AMOUNT_ALIASES = frozenset({"amount", "value", "total", "sum", "currency", "price"})


class TopupCreateSerializer(serializers.Serializer):
    """A request to start a card top-up. It carries no amount, by design."""

    auction = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        supplied = AMOUNT_ALIASES & set(self.initial_data or {})
        if supplied:
            raise serializers.ValidationError(
                {
                    field: "المبلغ يحدده النظام ولا يُرسَل مع الطلب."
                    for field in sorted(supplied)
                }
            )
        return attrs


class PaymentIntentSerializer(serializers.ModelSerializer):
    amount = MoneyField(read_only=True)
    purpose_label = serializers.SerializerMethodField()
    state_label = serializers.SerializerMethodField()

    class Meta:
        model = PaymentIntent
        fields = [
            "reference",
            "amount",
            "currency",
            "purpose",
            "purpose_label",
            "state",
            "state_label",
            "gateway",
            "gateway_status_raw",
            "created_at",
            "updated_at",
        ]

    def get_purpose_label(self, intent) -> str:
        return label_for(PaymentPurpose, intent.purpose, "دفعة")

    def get_state_label(self, intent) -> str:
        return label_for(PaymentIntentState, intent.state, "قيد المتابعة")


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


class RefundRequestCreateSerializer(serializers.Serializer):
    #: No bound is declared here. What may leave is decided by the free bucket
    #: in ``services.request_refund``; a second copy of that rule at the edge
    #: would be a second place to keep in step with it.
    amount = MoneyField()


class RefundRequestSerializer(serializers.ModelSerializer):
    amount = MoneyField(read_only=True)
    state_label = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = ["id", "reference", "amount", "state", "state_label", "created_at"]

    def get_state_label(self, request) -> str:
        return label_for(RefundRequestState, request.state, "قيد المعالجة")


# ---------------------------------------------------------------------------
# Invoices and purchases
# ---------------------------------------------------------------------------


class InvoiceSerializer(serializers.ModelSerializer):
    amount = MoneyField(read_only=True)
    amount_paid = MoneyField(read_only=True)
    outstanding = MoneyField(read_only=True)
    state_label = serializers.SerializerMethodField()
    payment_methods = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            "id",
            "number",
            "amount",
            "amount_paid",
            "outstanding",
            "state",
            "state_label",
            "issued_at",
            "due_at",
            "payment_methods",
        ]

    def get_state_label(self, invoice) -> str:
        return label_for(InvoiceState, invoice.state, "فاتورة")

    def get_payment_methods(self, invoice) -> list[dict]:
        """The only two ways a purchase is ever paid for. Card is not one."""
        return [
            {"method": value, "label": label} for value, label in PaymentMethod.choices
        ]


class InvoicePaySerializer(serializers.Serializer):
    """``method`` accepts only what :class:`PaymentMethod` declares.

    ``card`` is not a member, so the schema itself rejects it and there is no
    branch anywhere that could accidentally grow one.
    """

    method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.BALANCE,
        error_messages={
            "invalid_choice": "طريقة السداد غير مدعومة. المشتريات تُسدَّد من الرصيد "
            "أو بتحويل بنكي فقط.",
        },
    )


class PurchaseSerializer(serializers.Serializer):
    """A vehicle this customer won, with the invoice that followed it."""

    id = serializers.IntegerField()
    lot_number = serializers.IntegerField()
    make = serializers.CharField()
    model = serializers.CharField()
    year = serializers.IntegerField()
    state = serializers.CharField()
    awarded_price = MoneyField()
    awarded_at = serializers.DateTimeField()
    auction = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()

    def get_auction(self, vehicle) -> dict:
        return {
            "id": vehicle.auction_id,
            "number": vehicle.auction.number,
            "title": vehicle.auction.title,
        }

    def get_invoice(self, vehicle) -> dict | None:
        invoice = next(
            (
                candidate
                for candidate in vehicle.invoices.all()
                if candidate.state != InvoiceState.CANCELLED
            ),
            None,
        )
        if invoice is None:
            return None
        return InvoiceSerializer(invoice, context=self.context).data
