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
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auctions.models import Auction, Vehicle
from apps.core import jsonio, ratelimit
from apps.core.exceptions import envelope
from apps.core.net import client_ip
from apps.money import gateway, inbound, services
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


class TopupCheckoutView(APIView):
    """Hand the customer over to the gateway. One hop, decided on the server.

    A redirect and not a JSON body carrying a url: the client's whole job is to
    send the customer here, and a `302` is what a browser and a webview both
    already know how to follow. It also means the gateway's address never
    reaches either client, which is the point of `apps.money.gateway` — see the
    module docstring for why a "gateway url" field would have been the wrong
    shape.

    Nothing is charged here and no money moves. This is a signpost; the ledger
    is touched by :class:`PaymentCallbackView` and by nothing else.
    """

    @extend_schema(request=None, responses={302: None, 409: None, 503: None})
    def get(self, request, reference: str):
        intent = get_object_or_404(PaymentIntent, reference=reference, user=request.user)

        try:
            target = gateway.checkout_target(intent)
        except gateway.CheckoutUnavailable as refusal:
            # 409 rather than 404: the intent exists and is this customer's, and
            # it is the *state of the world* that refuses. A 404 would tell them
            # their own top-up does not exist, which is both untrue and alarming
            # when there is money involved.
            return Response(
                envelope("checkout_unavailable", refusal.user_message),
                status=status.HTTP_409_CONFLICT,
            )

        log.info("topup checkout: intent %s -> gateway", intent.reference)
        return HttpResponseRedirect(target)


class PaymentCallbackView(APIView):
    """The gateway telling us what happened. The only path that credits a card.

    Stored raw and acknowledged before anything interprets it (Article 2-1), and
    never dropped: a message we cannot use is kept with the reason written on it
    (Article 2-2).
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    #: No authentication stands in front of this endpoint by design — the
    #: gateway holds a shared secret, not a token — so the only thing bounding
    #: how many rows a stranger can write here is this ceiling. Until T914 there
    #: was none: every request from anybody who could reach the path stored a
    #: message, signature or not.
    throttle_scope = "payment_callback"

    # `responses=None`, unchanged by T914 and deliberately so. This path is
    # called by the payment gateway, never by a generated client — the schema is
    # the *client* contract, and widening it here would churn `web/lib/api` and
    # the Flutter client for an endpoint neither of them can call. The 429 is
    # described where its readers are: this docstring, and the test that proves it.
    @extend_schema(request=None, responses=None)
    def post(self, request):
        if not ratelimit.consume(self.throttle_scope, client_ip(request)).allowed:
            log.warning("payment callback: rate limited %s", client_ip(request))
            return Response(
                envelope("rate_limited", "معدّل الطلبات تجاوز الحدّ."),
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

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

        # ``jsonio.loads`` is the whole reason this is parsed by hand: a plain
        # json.loads would turn an amount into a float before any of our code
        # could refuse it (Article 3-2, one decoder for both boundaries).
        try:
            payload = jsonio.loads(raw or b"{}")
        except ValueError:
            payload = {}

        message = self._store(payload, raw=raw, signature_ok=signature_ok)

        if not signature_ok:
            log.warning("payment callback with a bad signature, stored as %s", message.pk)
            return Response(
                envelope("bad_signature", "توقيع الرسالة غير صحيح."),
                status=status.HTTP_401_UNAUTHORIZED,
            )

        self._interpret(message, payload)
        return Response({"received": True})

    def _store(self, payload: dict, *, raw: bytes, signature_ok: bool) -> InboundMessage:
        """Write the message down before understanding it.

        Deduplication is on the gateway's own delivery id, never on what the
        message is about: three notifications about one payment are three
        messages, and in v1 collapsing them swallowed the only useful one.

        ``raw_body`` is stored for the same reason the Odoo boundary stores it,
        and it matters most in exactly the case that used to lose it: a body we
        could not parse got ``payload={}``, no ``raw_body``, and blank
        everything else — a row that exists in name only, with nothing in it to
        re-read after the parser is fixed. Money arrived and left no trace.

        The verified signature is *not* kept. It is a keyed digest of the body
        stored beside it, so a reader of this table who does not hold the secret
        would be handed an unlimited supply of verified (message, MAC) pairs —
        which is why ``apps/odoo/views._safe_headers`` strips its own.
        """
        reference = str((payload.get("metadata") or {}).get("reference", ""))[:128]
        message = InboundMessage(
            source="payment_gateway",
            event=str(payload.get("type") or payload.get("status") or "")[:64],
            delivery_id=str(payload.get("id", ""))[:128],
            subject_ref=reference,
            payload=payload,
            raw_body=raw.decode("utf-8", errors="replace"),
            headers={"signature_ok": signature_ok},
        )
        if not signature_ok:
            # `rejected_signature`, not `failed`. The two words look
            # interchangeable and are not: `failed` is the retry queue, and a
            # body nobody signed sitting in the retry queue is a body the retry
            # cron interprets a minute later as though it had been signed. That
            # was a live, unauthenticated path from this endpoint into
            # `apps.odoo.processing._handle_payment` — see T913.
            message.state = InboundState.REJECTED_SIGNATURE
            message.note = "توقيع غير صحيح — محفوظة للتحقيق ولم تُفسَّر."
        try:
            # A savepoint, so a duplicate delivery costs us this insert and not
            # the surrounding transaction.
            with transaction.atomic():
                message.save()
        except IntegrityError:
            # Same delivery, heard twice. The first copy is the record.
            #
            # Only a *verified* row can be that record: the unique index skips
            # rejected ones on purpose, because otherwise a stranger who posts
            # `{"id": "<a guess>"}` here reserves that delivery id and the
            # gateway's genuine notification for it is answered with the forged
            # row — a payment the customer made and we never credit (T913).
            existing = (
                InboundMessage.objects.filter(
                    source="payment_gateway", delivery_id=message.delivery_id
                )
                .exclude(state=InboundState.REJECTED_SIGNATURE)
                .first()
            )
            if existing is None:
                # We collided with a row this query cannot see, which means the
                # index and this filter disagree. Raising is the honest answer:
                # a `None` travelling on as a message would be a 500 three
                # frames later with nothing pointing back here.
                raise
            message = existing
        return message

    def _interpret(self, message: InboundMessage, payload: dict) -> None:
        """Hand the stored row to the gateway's interpreter and nothing else.

        The interpretation itself lives in `apps.money.inbound`, not here, and
        that move is the fix rather than tidiness: a message stored by this
        request has to be interpretable again later — by the console button and
        by `tasks.retry_failed_gateway` — and code that only a view can reach is
        code a failed payment can never come back to.

        `payload` is no longer read: the interpreter reads the row it was given.
        On a duplicate delivery `message` is the *first* copy, and the body in
        hand here never became it.
        """
        inbound.interpret(message)


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
