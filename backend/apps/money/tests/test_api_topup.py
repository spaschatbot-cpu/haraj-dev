"""T614 and T615 — paying by card, and what comes back.

Two v1 failures are pinned down here. A pen test moved insurance amounts by
editing them in the request, so the server decides the amount and refuses one it
is handed. And the gateway carries no user id, so v1 read attribution out of the
return URL — which is under the payer's thumb. Here the return URL moves nothing
at all, and the callback attributes from a row the server wrote before the
customer ever reached the gateway.
"""

from __future__ import annotations

import hmac
import json
from decimal import Decimal
from unittest import mock

import pytest
from django.urls import reverse

from apps.money import services
from apps.money.models import (
    AccountKind,
    PaymentIntent,
    PaymentIntentState,
    Transaction,
)
from apps.money.verification import verify_ledger
from apps.odoo.models import InboundMessage, InboundState

from .conftest import TEN_K, free_balance, parsed_without_floats

pytestmark = pytest.mark.django_db

SECRET = "test-webhook-secret"
CALLBACK = "money:payment-callback"


@pytest.fixture
def payments_on(settings):
    settings.PAYMENT_WEBHOOK_SECRET = SECRET
    settings.PAYMENT_SUCCESS_STATUSES = ["paid"]
    return settings


def send_callback(api_client, payload: dict, *, secret: str = SECRET):
    """Post a gateway notification exactly as the gateway would sign it."""
    raw = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), raw, "sha256").hexdigest()
    return api_client.post(
        reverse(CALLBACK),
        data=raw,
        content_type="application/json",
        HTTP_X_SIGNATURE=signature,
    )


def gateway_says(reference: str, *, amount: str, status: str = "paid", pid="pay_1"):
    return {
        "id": pid,
        "status": status,
        "amount": amount,
        "currency": "SAR",
        "metadata": {"reference": reference},
    }


class TestStartingATopup:
    def test_the_server_decides_the_amount(self, as_bidder, live_auction):
        live_auction.deposit_required = Decimal("15000.00")
        live_auction.save(update_fields=["deposit_required"])

        response = as_bidder.post(
            reverse("money:topup-list"), {"auction": live_auction.pk}, format="json"
        )

        assert response.status_code == 201
        assert parsed_without_floats(response)["amount"] == "15000.00"

    def test_an_amount_in_the_request_is_refused_not_ignored(
        self, as_bidder, live_auction
    ):
        """v1's tampering path. Silence would hide it; this says no, loudly."""
        response = as_bidder.post(
            reverse("money:topup-list"),
            {"auction": live_auction.pk, "amount": "1.00"},
            format="json",
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "validation_error"
        assert "المبلغ يحدده النظام" in response.json()["error"]["message"]
        assert not PaymentIntent.objects.exists()

    def test_the_intent_is_recorded_before_the_gateway_is_involved(
        self, as_bidder, bidder
    ):
        as_bidder.post(reverse("money:topup-list"), {}, format="json")

        intent = PaymentIntent.objects.get()
        assert intent.user_id == bidder.pk
        assert intent.state == PaymentIntentState.PENDING
        assert intent.amount == TEN_K
        assert free_balance(bidder) == Decimal("0.00")

    def test_a_double_tapped_button_starts_one_payment(self, as_bidder):
        for _ in range(2):
            as_bidder.post(
                reverse("money:topup-list"),
                {},
                format="json",
                HTTP_IDEMPOTENCY_KEY="tap-1",
            )

        assert PaymentIntent.objects.count() == 1


class TestTheReturnUrl:
    def test_tampering_with_the_return_parameters_moves_nothing(
        self, as_bidder, bidder, stranger
    ):
        """The heart of T615. The return URL is evidence of nothing."""
        intent = services.start_topup(user=bidder)

        response = as_bidder.get(
            reverse("money:topup-detail", args=[intent.reference]),
            {
                "status": "paid",
                "amount": "999999.00",
                "user": stranger.pk,
                "user_id": stranger.pk,
            },
        )
        body = parsed_without_floats(response)

        assert body["state"] == PaymentIntentState.PENDING
        assert body["amount"] == "10000.00"
        assert free_balance(bidder) == Decimal("0.00")
        assert free_balance(stranger) == Decimal("0.00")
        assert not Transaction.objects.exists()

    def test_one_customer_cannot_read_anothers_payment(self, as_bidder, stranger):
        intent = services.start_topup(user=stranger)

        response = as_bidder.get(reverse("money:topup-detail", args=[intent.reference]))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestTheCallback:
    def test_a_paid_callback_credits_the_customer_named_by_the_intent(
        self, api_client, payments_on, bidder
    ):
        intent = services.start_topup(user=bidder)

        response = send_callback(
            api_client, gateway_says(intent.reference, amount="10000.00")
        )

        assert response.status_code == 200
        assert free_balance(bidder) == TEN_K
        intent.refresh_from_db()
        assert intent.state == PaymentIntentState.SUCCEEDED
        assert intent.resulting_transaction is not None
        assert intent.gateway_status_raw == "paid"
        assert verify_ledger() == []

    def test_attribution_ignores_whoever_the_payload_claims_to_be(
        self, api_client, payments_on, bidder, stranger
    ):
        intent = services.start_topup(user=bidder)
        payload = gateway_says(intent.reference, amount="10000.00")
        payload["metadata"]["user"] = stranger.pk
        payload["customer_id"] = stranger.pk

        send_callback(api_client, payload)

        assert free_balance(bidder) == TEN_K
        assert free_balance(stranger) == Decimal("0.00")

    def test_a_payment_we_cannot_place_is_kept_in_suspense(self, api_client, payments_on):
        """Article 2-2 — money without an owner is stored, never dropped."""
        response = send_callback(
            api_client, gateway_says("topup-nobody", amount="7500.00")
        )

        assert response.status_code == 200
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("7500.00")
        message = InboundMessage.objects.get()
        assert message.state == InboundState.PROCESSED
        assert "المعلّق" in message.note
        assert message.resulting_transaction is not None

    def test_an_amount_that_disagrees_with_the_intent_is_not_credited(
        self, api_client, payments_on, bidder
    ):
        intent = services.start_topup(user=bidder)

        send_callback(api_client, gateway_says(intent.reference, amount="1.00"))

        assert free_balance(bidder) == Decimal("0.00")
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("1.00")
        intent.refresh_from_db()
        assert intent.state == PaymentIntentState.DISPUTED

    def test_the_same_notification_twice_credits_once(
        self, api_client, payments_on, bidder
    ):
        intent = services.start_topup(user=bidder)
        payload = gateway_says(intent.reference, amount="10000.00")

        send_callback(api_client, payload)
        send_callback(api_client, payload)

        assert free_balance(bidder) == TEN_K
        assert InboundMessage.objects.count() == 1

    def test_a_failed_payment_moves_nothing_and_is_still_recorded(
        self, api_client, payments_on, bidder
    ):
        intent = services.start_topup(user=bidder)

        send_callback(
            api_client,
            gateway_says(intent.reference, amount="10000.00", status="failed"),
        )

        assert free_balance(bidder) == Decimal("0.00")
        intent.refresh_from_db()
        assert intent.state == PaymentIntentState.FAILED
        assert intent.gateway_status_raw == "failed"
        assert InboundMessage.objects.get().state == InboundState.IGNORED

    def test_a_forged_callback_is_refused_and_kept_for_investigation(
        self, api_client, payments_on, bidder
    ):
        """Kept, and out of the retry queue — the two are not the same thing.

        This test asserted `FAILED` until T913, and that one word was the whole
        vulnerability: `failed` is what `odoo.retry_failed` picks up, so a body
        nobody signed was re-offered to an interpreter a minute later and
        interpreted as though it had been. `rejected_signature` keeps the
        evidence (Article 2-2) without keeping the invitation.
        `tests/test_pentest_T913.py` walks that attack end to end.
        """
        intent = services.start_topup(user=bidder)

        response = send_callback(
            api_client,
            gateway_says(intent.reference, amount="10000.00"),
            secret="not-the-secret",
        )

        assert response.status_code == 401
        assert free_balance(bidder) == Decimal("0.00")
        message = InboundMessage.objects.get()
        assert message.state == InboundState.REJECTED_SIGNATURE
        assert message.note

    def test_with_no_secret_configured_the_endpoint_refuses_everything(
        self, api_client, settings, bidder
    ):
        settings.PAYMENT_WEBHOOK_SECRET = ""
        intent = services.start_topup(user=bidder)

        response = send_callback(
            api_client, gateway_says(intent.reference, amount="10000.00")
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "payments_disabled"
        assert free_balance(bidder) == Decimal("0.00")


class TestACallbackThatBeatItsOwnIntent:
    """The gateway can be faster than our own row.

    T615 was marked done with no test for this ordering, and the ordering was
    the bug: the suspense receipt and the attributed deposit shared one
    idempotency key, so the retry marked the intent SUCCEEDED while the money
    stayed in suspense. Measured before the fix: disposition `credited`, intent
    `succeeded`, resulting transaction kind `unattributed_receipt`, customer
    free 0.00, suspense 10000.00 — and `verify_ledger` stayed clean throughout,
    because suspense is a platform bucket and nothing in the system reports it.
    """

    def test_the_customer_ends_up_credited_exactly_once(
        self, api_client, payments_on, bidder
    ):
        """Two deliveries about one payment, the intent created between them.

        The gateway sends no payment id of its own here, so `apply_gateway_payment`
        falls back to our reference — and the blank delivery id is tolerated by
        the partial index on purpose («better a duplicate row than a collapsed
        one»), which is what lets both deliveries be interpreted.
        """
        reference = f"topup-{bidder.pk}-early"
        payload = {
            "status": "paid",
            "amount": "10000.00",
            "currency": "SAR",
            "metadata": {"reference": reference},
        }

        # Delivery one: the intent is not visible yet, so the money is kept.
        send_callback(api_client, payload)
        assert services.system_account(AccountKind.SUSPENSE).balance == TEN_K
        assert free_balance(bidder) == Decimal("0.00")

        intent = PaymentIntent.objects.create(
            reference=reference,
            user=bidder,
            amount=TEN_K,
            purpose="insurance_deposit",
            gateway=payments_on.PAYMENT_GATEWAY,
        )

        # Delivery two: the same payment, now placeable.
        send_callback(api_client, payload)

        intent.refresh_from_db()
        assert free_balance(bidder) == TEN_K
        assert services.system_account(AccountKind.SUSPENSE).balance == Decimal("0.00")
        assert intent.state == PaymentIntentState.SUCCEEDED
        assert intent.resulting_transaction is not None
        assert intent.resulting_transaction.kind != "unattributed_receipt"
        # One payment arrived, so the card account is charged once.
        assert services.system_account(AccountKind.EXTERNAL_CARD).balance == -TEN_K
        assert verify_ledger() == []


class TestWhatTheStoredMessageKeeps:
    def test_an_unparseable_body_is_stored_whole_so_it_can_be_reread(
        self, api_client, payments_on
    ):
        """Article 2-2. Before this the row existed in name only: `payload={}`,
        no `raw_body`, blank event, blank delivery id — money arrived and left
        nothing behind that a fixed parser could ever read again."""
        raw = b'{"amount": 10000.00, "status": "paid"'  # truncated on the wire
        signature = hmac.new(SECRET.encode(), raw, "sha256").hexdigest()

        response = api_client.post(
            reverse(CALLBACK),
            data=raw,
            content_type="application/json",
            HTTP_X_SIGNATURE=signature,
        )

        assert response.status_code == 200
        message = InboundMessage.objects.get()
        assert message.raw_body == raw.decode()
        assert message.state == InboundState.FAILED
        assert message.note

    def test_the_signature_is_not_stored_beside_the_body_it_signs(
        self, api_client, payments_on, bidder
    ):
        """Keeping a verified digest next to the bytes it authenticates hands
        anyone who can read this table an unlimited supply of working samples —
        which is exactly why the Odoo boundary strips its own."""
        intent = services.start_topup(user=bidder)

        send_callback(api_client, gateway_says(intent.reference, amount="10000.00"))

        message = InboundMessage.objects.get()
        assert "X-Signature" not in message.headers
        assert SECRET not in json.dumps(message.headers)
        assert message.headers["signature_ok"] is True

    def test_a_raise_while_interpreting_leaves_a_failed_row_not_a_silent_one(
        self, api_client, payments_on, bidder
    ):
        """A raise used to escape before state, note and attempts were written,
        so the row stayed RECEIVED with an empty note — and nothing in the
        system ever looks at a gateway message again."""
        intent = services.start_topup(user=bidder)

        with mock.patch.object(
            services, "apply_gateway_payment", side_effect=RuntimeError("قاعدة سقطت")
        ):
            response = send_callback(
                api_client, gateway_says(intent.reference, amount="10000.00")
            )

        assert response.status_code == 200
        message = InboundMessage.objects.get()
        assert message.state == InboundState.FAILED
        assert "RuntimeError" in message.note
        assert message.attempts == 1
