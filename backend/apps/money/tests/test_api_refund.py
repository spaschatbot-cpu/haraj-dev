"""T616 — asking for a refund.

Only free insurance can leave. A debtor's request fails on the arithmetic of the
free bucket, not on a "is this customer a debtor?" gate — because a gate is a
call somebody can forget to make, and in v1 somebody did.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.money import services
from apps.money.models import (
    Invoice,
    InvoiceSource,
    InvoiceState,
    RefundRequest,
    Transaction,
)
from apps.odoo.models import OutboxMessage, OutboxState

from .conftest import TEN_K, free_balance, parsed_without_floats

pytestmark = pytest.mark.django_db

URL = "money:refund-request-list"


def url() -> str:
    return reverse(URL)


@pytest.fixture
def funded(bidder):
    services.deposit_insurance(
        user=bidder, amount=TEN_K, source="cash", reference="PCSH/1"
    )
    return bidder


@pytest.fixture
def debtor(funded):
    invoice = Invoice.objects.create(
        customer=funded,
        number="INV/2026/900",
        amount=Decimal("50000.00"),
        state=InvoiceState.OPEN,
        issued_at="2026-01-01T00:00:00Z",
        source=InvoiceSource.LOCAL,
    )
    services.lock_for_invoice(user=funded, invoice=invoice)
    return funded


class TestAskingForARefund:
    def test_it_queues_the_request_without_moving_the_ledger(self, as_bidder, funded):
        """Odoo's confirmation moves money. Asking does not."""
        before = Transaction.objects.count()

        response = as_bidder.post(url(), {"amount": "4000.00"}, format="json")
        body = parsed_without_floats(response)

        assert response.status_code == 201
        assert body["amount"] == "4000.00"
        assert body["state"] == "requested"
        assert body["state_label"] != body["state"]
        assert free_balance(funded) == TEN_K
        assert Transaction.objects.count() == before

    def test_the_request_goes_to_the_outbox_not_to_odoo(self, as_bidder, funded):
        as_bidder.post(url(), {"amount": "4000.00"}, format="json")

        outbox = OutboxMessage.objects.get()
        assert outbox.state == OutboxState.PENDING
        assert outbox.endpoint == "refund.request"
        assert outbox.payload["amount"] == "4000.00"
        assert isinstance(outbox.payload["amount"], str)

    def test_a_retry_with_the_same_key_does_not_open_a_second_request(
        self, as_bidder, funded
    ):
        """The v1 incident: a retry cron gave one customer three open refunds."""
        for _ in range(3):
            as_bidder.post(
                url(),
                {"amount": "4000.00"},
                format="json",
                HTTP_IDEMPOTENCY_KEY="one-decision",
            )

        assert RefundRequest.objects.count() == 1
        assert OutboxMessage.objects.count() == 1


class TestWhatCannotLeave:
    def test_a_debtor_is_refused_with_the_locked_amount_in_the_message(
        self, as_bidder, debtor
    ):
        response = as_bidder.post(url(), {"amount": "5000.00"}, format="json")
        error = response.json()["error"]

        assert response.status_code == 409
        assert error["code"] == "insufficient_funds"
        assert "مقفولة على مستحقات" in error["message"]
        assert "10000.00" in error["message"]
        assert error["detail"]["locked_for_dues"] == "10000.00"
        assert error["detail"]["available"] == "0.00"
        assert not RefundRequest.objects.exists()
        assert not OutboxMessage.objects.exists()

    def test_money_held_for_a_live_auction_cannot_be_asked_for(
        self, as_bidder, funded, live_auction
    ):
        services.hold_for_auction(user=funded, auction=live_auction)

        response = as_bidder.post(url(), {"amount": "1000.00"}, format="json")

        assert response.status_code == 409
        assert "محجوزة لمزادات" in response.json()["error"]["message"]

    def test_more_than_the_free_balance_is_refused(self, as_bidder, funded):
        response = as_bidder.post(url(), {"amount": "10000.01"}, format="json")

        assert response.status_code == 409
        assert response.json()["error"]["detail"]["available"] == "10000.00"

    def test_zero_is_refused_in_arabic(self, as_bidder, funded):
        response = as_bidder.post(url(), {"amount": "0.00"}, format="json")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "invalid_amount"
        assert "أكبر من صفر" in response.json()["error"]["message"]


class TestOneOpenRequestAtATime:
    """Asking moves no money, so the balance a request is checked against does
    not move either — which is why *checking* it was never enough."""

    def test_ten_requests_for_the_whole_balance_do_not_queue_ten_payouts(
        self, as_bidder, funded
    ):
        """Measured before the fix: ten rows, ten outbox messages, 100,000
        instructed against a 10,000 deposit.

        Each call took the `uuid4` branch of the reference builder, so the
        uniqueness check never matched; and because nothing is posted,
        `free.balance` was still 10,000 on every pass. Our own ledger could not
        stop it either: `refund_insurance` runs later, on the inbound
        confirmation, and the second one raises *after* the money has left the
        bank.
        """
        codes = [
            as_bidder.post(url(), {"amount": "10000.00"}, format="json").status_code
            for _ in range(10)
        ]

        assert codes[0] == 201
        assert set(codes[1:]) == {409}
        assert RefundRequest.objects.count() == 1
        assert OutboxMessage.objects.count() == 1

    def test_the_refusal_names_the_request_already_standing(self, as_bidder, funded):
        as_bidder.post(url(), {"amount": "4000.00"}, format="json")

        response = as_bidder.post(url(), {"amount": "1000.00"}, format="json")
        error = response.json()["error"]

        assert response.status_code == 409
        assert "طلب استرداد قائم" in error["message"]
        assert error["detail"]["open_amount"] == "4000.00"

    def test_the_schema_refuses_a_second_open_request(self, funded):
        """B6, by going around the service entirely.

        Without this index the only thing standing between one deposit and ten
        payout instructions is a service that reads a number nothing moves.
        """
        from django.db import IntegrityError, transaction

        first = services.request_refund(user=funded, amount=Decimal("1000.00"))

        with pytest.raises(IntegrityError, match="one_open_refund_request"):
            with transaction.atomic():
                RefundRequest.objects.create(
                    user=funded, amount=Decimal("1000.00"), reference="refund-forged"
                )

        assert first.state == "requested"

    def test_a_settled_request_frees_the_customer_to_ask_again(self, as_bidder, funded):
        """The rule is one *open* request, not one request ever."""
        first = services.request_refund(user=funded, amount=Decimal("1000.00"))
        first.state = "rejected"
        first.save(update_fields=["state"])

        response = as_bidder.post(url(), {"amount": "1000.00"}, format="json")

        assert response.status_code == 201
        assert RefundRequest.objects.count() == 2


class TestOwnership:
    def test_the_list_shows_only_the_callers_own_requests(
        self, as_bidder, funded, stranger
    ):
        services.deposit_insurance(
            user=stranger, amount=TEN_K, source="cash", reference="PCSH/2"
        )
        services.request_refund(user=stranger, amount=Decimal("100.00"))
        services.request_refund(user=funded, amount=Decimal("200.00"))

        body = parsed_without_floats(as_bidder.get(url()))

        assert [row["amount"] for row in body] == ["200.00"]

    def test_it_needs_a_signed_in_customer(self, api_client):
        response = api_client.post(url(), {"amount": "1.00"}, format="json")

        assert response.status_code in (401, 403)
