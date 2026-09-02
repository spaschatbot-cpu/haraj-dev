"""The HTTP edge of the wallet.

Every view here does the same four things and nothing else: read the customer
from the token, hand the request to a service, serialise what comes back, pick a
status code. No view computes an amount, decides who owns a row, formats an
error body, or writes an entry.

Ownership is never taken from the path or the query. A view that needs a
specific row filters by ``request.user`` first, so asking for somebody else's
invoice is indistinguishable from asking for one that does not exist.
"""

from __future__ import annotations

import hmac
import json
import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.models import Auction, Vehicle
from apps.core.exceptions import envelope
from apps.money import services
from apps.money.models import (
    AccountKind,
    Entry,
    Invoice,
    InvoiceState,
    PaymentIntent,
    RefundRequest,
)
from apps.odoo.models import InboundMessage, InboundState

from .serializers import (
    InvoicePaySerializer,
    InvoiceSerializer,
    LedgerEntrySerializer,
    PaymentIntentSerializer,
    PurchaseSerializer,
    RefundRequestCreateSerializer,
    RefundRequestSerializer,
    StatementQuerySerializer,
    TopupCreateSerializer,
    WalletSerializer,
)

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# T612 — the wallet, itemised
# ---------------------------------------------------------------------------


class WalletView(APIView):
    """The customer's money, split by the pot it is actually sitting in."""

    @extend_schema(responses=WalletSerializer)
    def get(self, request):
        snapshot = services.wallet_snapshot(request.user)
        by_kind = {bucket.kind: bucket.amount for bucket in snapshot.buckets}
        payload = {
            "currency": settings.CURRENCY,
            "total": snapshot.total,
            "available": by_kind[AccountKind.INSURANCE_FREE],
            "held_for_auctions": by_kind[AccountKind.INSURANCE_HELD],
            "locked_for_dues": by_kind[AccountKind.INSURANCE_LOCKED],
            "buckets": snapshot.buckets,
            "holds": snapshot.holds,
            "as_of": snapshot.as_of,
        }
        context = {
            "request": request,
            "statement_url": request.build_absolute_uri(
                reverse("money:wallet-statement")
            ),
        }
        return Response(WalletSerializer(payload, context=context).data)


# ---------------------------------------------------------------------------
# T613 — the statement
# ---------------------------------------------------------------------------


class WalletStatementView(ListAPIView):
    """Every ledger line belonging to the caller, newest first, paginated."""

    serializer_class = LedgerEntrySerializer
    #: Empty on purpose — the real rows come from get_queryset, filtered by the
    #: authenticated customer. This attribute only tells the schema its model.
    queryset = Entry.objects.none()

    def get_queryset(self):
        query = StatementQuerySerializer(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        return services.statement_entries(
            self.request.user, bucket=query.validated_data.get("bucket") or None
        )


# ---------------------------------------------------------------------------
# T614 / T615 — card top-up: intent, return, callback
# ---------------------------------------------------------------------------


class TopupListCreateView(APIView):
    """Start a card top-up, or list the ones this customer started."""

    @extend_schema(responses=PaymentIntentSerializer(many=True))
    def get(self, request):
        intents = PaymentIntent.objects.filter(user=request.user)
        return Response(PaymentIntentSerializer(intents, many=True).data)

    @extend_schema(request=TopupCreateSerializer, responses=PaymentIntentSerializer)
    def post(self, request):
        form = TopupCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        auction_id = form.validated_data.get("auction")
        auction = (
            get_object_or_404(Auction, pk=auction_id) if auction_id is not None else None
        )
        intent = services.start_topup(
            user=request.user,
            auction=auction,
            client_key=request.headers.get("Idempotency-Key") or None,
        )
        return Response(
            PaymentIntentSerializer(intent).data, status=status.HTTP_201_CREATED
        )


class TopupDetailView(RetrieveAPIView):
    """Where the customer lands on return from the gateway.

    It reads one stored row and answers with it. Not a single query parameter is
    consulted — a return URL is under the payer's thumb, and in v1 that was
    enough to make the app believe a payment had succeeded. Money moves in
    :class:`PaymentCallbackView` and nowhere else.
    """

    serializer_class = PaymentIntentSerializer
    lookup_field = "reference"
    queryset = PaymentIntent.objects.none()

    def get_queryset(self):
        return PaymentIntent.objects.filter(user=self.request.user)


class PaymentCallbackView(APIView):
    """The gateway telling us what happened. The only path that credits a card.

    Stored raw and acknowledged before anything interprets it (Article 2-1), and
    never dropped: a message we cannot use is kept with the reason written on it
    (Article 2-2).
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses=None)
    def post(self, request):
        secret = settings.PAYMENT_WEBHOOK_SECRET
        raw = request.body

        if not secret:
            # Off unless an operator turned it on for this environment. An
            # unauthenticated endpoint that credits wallets must not exist by
            # default just because a default was convenient.
            log.error("payment callback refused: PAYMENT_WEBHOOK_SECRET is unset")
            return Response(
                envelope(
                    "payments_disabled",
                    "استقبال الدفعات غير مفعّل في هذه البيئة.",
                ),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        signature = request.headers.get("X-Signature", "")
        expected = hmac.new(secret.encode(), raw, "sha256").hexdigest()
        signature_ok = hmac.compare_digest(signature, expected)

        # ``parse_float=Decimal`` is the whole reason this is parsed by hand: a
        # plain json.loads would turn an amount into a float before any of our
        # code could refuse it.
        try:
            payload = json.loads(raw or b"{}", parse_float=Decimal)
        except ValueError:
            payload = {}

        message = self._store(payload, signature_ok=signature_ok, headers=request.headers)

        if not signature_ok:
            log.warning("payment callback with a bad signature, stored as %s", message.pk)
            return Response(
                envelope("bad_signature", "توقيع الرسالة غير صحيح."),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        self._interpret(message, payload)
        return Response({"received": True})

    def _store(self, payload: dict, *, signature_ok: bool, headers) -> InboundMessage:
        """Write the message down before understanding it.

        Deduplication is on the gateway's own delivery id, never on what the
        message is about: three notifications about one payment are three
        messages, and in v1 collapsing them swallowed the only useful one.
        """
        reference = str((payload.get("metadata") or {}).get("reference", ""))[:128]
        message = InboundMessage(
            source="payment_gateway",
            event=str(payload.get("type") or payload.get("status") or "")[:64],
            delivery_id=str(payload.get("id", ""))[:128],
            subject_ref=reference,
            payload=json.loads(json.dumps(payload, default=str)),
            headers={"X-Signature": headers.get("X-Signature", "")},
        )
        if not signature_ok:
            message.state = InboundState.FAILED
            message.note = "توقيع غير صحيح — محفوظة للتحقيق ولم تُفسَّر."
        try:
            # A savepoint, so a duplicate delivery costs us this insert and not
            # the surrounding transaction.
            with transaction.atomic():
                message.save()
        except IntegrityError:
            # Same delivery, heard twice. The first copy is the record.
            message = InboundMessage.objects.get(
                source="payment_gateway", delivery_id=message.delivery_id
            )
        return message

    def _interpret(self, message: InboundMessage, payload: dict) -> None:
        if message.state != InboundState.RECEIVED:
            return  # already dealt with, or stored for investigation

        try:
            amount = Decimal(str(payload.get("amount", "0")))
        except (InvalidOperation, ValueError):
            amount = None

        reference = str((payload.get("metadata") or {}).get("reference", ""))
        status_raw = str(payload.get("status", ""))

        if amount is None or amount <= 0:
            message.state = InboundState.FAILED
            message.note = f"مبلغ غير مفهوم في الرسالة: {payload.get('amount')!r}"
        else:
            outcome = services.apply_gateway_payment(
                reference=reference,
                payment_id=str(payload.get("id", "")),
                amount=amount,
                status_raw=status_raw,
                succeeded=status_raw in settings.PAYMENT_SUCCESS_STATUSES,
            )
            message.state = {
                "credited": InboundState.PROCESSED,
                "suspense": InboundState.PROCESSED,
                "ignored": InboundState.IGNORED,
            }.get(outcome.disposition, InboundState.FAILED)
            message.note = outcome.note
            message.resulting_transaction = outcome.transaction

        message.attempts += 1
        message.processed_at = timezone.now()
        message.save(
            update_fields=[
                "state",
                "note",
                "resulting_transaction",
                "attempts",
                "processed_at",
            ]
        )


# ---------------------------------------------------------------------------
# T616 — asking for a refund
# ---------------------------------------------------------------------------


class RefundRequestListCreateView(APIView):
    @extend_schema(responses=RefundRequestSerializer(many=True))
    def get(self, request):
        requests = RefundRequest.objects.filter(user=request.user)
        return Response(RefundRequestSerializer(requests, many=True).data)

    @extend_schema(
        request=RefundRequestCreateSerializer, responses=RefundRequestSerializer
    )
    def post(self, request):
        form = RefundRequestCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        refund = services.request_refund(
            user=request.user,
            amount=form.validated_data["amount"],
            client_key=request.headers.get("Idempotency-Key") or None,
        )
        return Response(
            RefundRequestSerializer(refund).data, status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------------------------
# T617 — purchases, invoices, settling
# ---------------------------------------------------------------------------


class PurchaseListView(ListAPIView):
    """Vehicles awarded to the caller, each with its live invoice."""

    serializer_class = PurchaseSerializer
    queryset = Vehicle.objects.none()

    def get_queryset(self):
        return (
            Vehicle.objects.filter(awarded_to=self.request.user)
            .select_related("auction")
            .prefetch_related("invoices")
            .order_by("-awarded_at", "-id")
        )


class InvoiceListView(ListAPIView):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.none()

    def get_queryset(self):
        return Invoice.objects.filter(customer=self.request.user).exclude(
            state=InvoiceState.DRAFT
        )


class InvoiceDetailView(RetrieveAPIView):
    serializer_class = InvoiceSerializer
    queryset = Invoice.objects.none()

    def get_queryset(self):
        return Invoice.objects.filter(customer=self.request.user)


class InvoicePayView(APIView):
    """Settle one invoice from the balance the customer already has with us.

    There is no card branch here and no card purpose to reach for: a purchase is
    paid from deposited money or by a bank transfer the bank confirms.
    """

    @extend_schema(request=InvoicePaySerializer, responses=InvoiceSerializer)
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, customer=request.user)

        form = InvoicePaySerializer(data=request.data)
        form.is_valid(raise_exception=True)

        txn = services.pay_invoice_from_balance(
            user=request.user, invoice=invoice, method=form.validated_data["method"]
        )
        invoice.refresh_from_db()
        return Response(
            {
                "invoice": InvoiceSerializer(invoice, context={"request": request}).data,
                "transaction": str(txn.uuid),
            }
        )
