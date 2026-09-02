"""T617 — what the customer bought, what they owe, and how they settle it.

The design decision this file guards: **a purchase is never paid by card.** A
card charge can be reversed months later, against a vehicle that has already
left the yard. The absence of that path is asserted structurally, not just at
the edge, so nobody can add one without a test going red.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.auctions.models import Vehicle, VehicleState
from apps.money import services
from apps.money.models import (
    AccountKind,
    Invoice,
    InvoiceState,
    PaymentMethod,
    PaymentPurpose,
)

from .conftest import free_balance, parsed_without_floats

pytestmark = pytest.mark.django_db

FIFTY_K = Decimal("50000.00")


@pytest.fixture
def won_vehicle(bidder, live_auction):
    from django.utils import timezone

    return Vehicle.objects.create(
        auction=live_auction,
        lot_number=4,
        make="تويوتا",
        model="لاندكروزر",
        year=2022,
        state=VehicleState.INVOICED,
        awarded_to=bidder,
        awarded_price=FIFTY_K,
        awarded_at=timezone.now(),
    )


@pytest.fixture
def invoice(bidder, won_vehicle):
    return Invoice.objects.create(
        customer=bidder,
        number="INV/2026/044",
        amount=FIFTY_K,
        state=InvoiceState.OPEN,
        vehicle=won_vehicle,
        issued_at="2026-02-01T00:00:00Z",
    )


@pytest.fixture
def able_to_pay(bidder, invoice):
    """A winner with enough deposited: part locked on the invoice, part free."""
    services.deposit_insurance(
        user=bidder, amount=Decimal("60000.00"), source="cash", reference="PCSH/9"
    )
    services.lock_for_invoice(user=bidder, invoice=invoice)
    return bidder


class TestPurchases:
    def test_it_lists_what_this_customer_won_with_its_invoice(
        self, as_bidder, won_vehicle, invoice
    ):
        body = parsed_without_floats(as_bidder.get(reverse("money:purchase-list")))

        assert body["count"] == 1
        purchase = body["results"][0]
        assert purchase["lot_number"] == won_vehicle.lot_number
        assert purchase["awarded_price"] == "50000.00"
        assert purchase["auction"]["number"] == won_vehicle.auction.number
        assert purchase["invoice"]["number"] == invoice.number
        assert purchase["invoice"]["outstanding"] == "50000.00"

    def test_it_never_lists_another_customers_purchase(
        self, as_bidder, won_vehicle, stranger
    ):
        won_vehicle.awarded_to = stranger
        won_vehicle.save(update_fields=["awarded_to"])

        body = parsed_without_floats(as_bidder.get(reverse("money:purchase-list")))

        assert body["count"] == 0

    def test_an_invoice_of_another_customer_is_not_found(
        self, as_bidder, invoice, stranger
    ):
        invoice.customer = stranger
        invoice.save(update_fields=["customer"])

        response = as_bidder.get(reverse("money:invoice-detail", args=[invoice.pk]))

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


class TestSettlingFromBalance:
    def test_it_spends_the_lock_first_and_then_the_free_balance(
        self, as_bidder, able_to_pay, invoice
    ):
        response = as_bidder.post(
            reverse("money:invoice-pay", args=[invoice.pk]),
            {"method": "balance"},
            format="json",
        )
        body = parsed_without_floats(response)

        assert response.status_code == 200
        assert body["invoice"]["state"] == InvoiceState.PAID
        assert body["invoice"]["outstanding"] == "0.00"
        assert body["transaction"]
        assert free_balance(able_to_pay) == Decimal("10000.00")
        assert services.account_for(
            able_to_pay, AccountKind.INSURANCE_LOCKED
        ).balance == Decimal("0.00")
        assert services.system_account(AccountKind.REVENUE).balance == FIFTY_K
        assert services.verify_ledger() == []

    def test_paying_twice_settles_once(self, as_bidder, able_to_pay, invoice):
        url = reverse("money:invoice-pay", args=[invoice.pk])

        as_bidder.post(url, {"method": "balance"}, format="json")
        as_bidder.post(url, {"method": "balance"}, format="json")

        invoice.refresh_from_db()
        assert invoice.amount_paid == FIFTY_K
        assert free_balance(able_to_pay) == Decimal("10000.00")

    def test_not_enough_money_is_refused_with_the_numbers(
        self, as_bidder, bidder, invoice
    ):
        services.deposit_insurance(
            user=bidder, amount=Decimal("1000.00"), source="cash", reference="PCSH/8"
        )

        response = as_bidder.post(
            reverse("money:invoice-pay", args=[invoice.pk]),
            {"method": "balance"},
            format="json",
        )
        error = response.json()["error"]

        assert response.status_code == 409
        assert error["code"] == "insufficient_funds"
        assert error["detail"]["outstanding"] == "50000.00"
        assert error["detail"]["available"] == "1000.00"
        assert free_balance(bidder) == Decimal("1000.00")

    def test_another_customers_invoice_cannot_be_paid(self, as_bidder, invoice, stranger):
        invoice.customer = stranger
        invoice.save(update_fields=["customer"])

        response = as_bidder.post(
            reverse("money:invoice-pay", args=[invoice.pk]),
            {"method": "balance"},
            format="json",
        )

        assert response.status_code == 404


class TestNoCardForPurchases:
    def test_the_endpoint_refuses_a_card(self, as_bidder, able_to_pay, invoice):
        response = as_bidder.post(
            reverse("money:invoice-pay", args=[invoice.pk]),
            {"method": "card"},
            format="json",
        )

        assert response.status_code == 400
        assert "غير مدعومة" in response.json()["error"]["message"]
        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.OPEN

    def test_no_card_method_exists_to_be_chosen(self):
        """Structural, not behavioural: there is nothing to select."""
        assert set(PaymentMethod.values) == {"balance", "bank_transfer"}

    def test_no_card_payment_purpose_can_name_an_invoice(self):
        """A card intent can only ever be a deposit, never a purchase."""
        assert set(PaymentPurpose.values) == {"insurance_deposit"}

    def test_the_invoice_shows_only_the_two_allowed_methods(self, as_bidder, invoice):
        body = parsed_without_floats(
            as_bidder.get(reverse("money:invoice-detail", args=[invoice.pk]))
        )

        assert [row["method"] for row in body["payment_methods"]] == [
            "balance",
            "bank_transfer",
        ]

    def test_a_bank_transfer_is_not_settled_by_the_customer_saying_so(
        self, as_bidder, able_to_pay, invoice
    ):
        """Article 2-4 — the bank confirms a transfer, the payer does not."""
        response = as_bidder.post(
            reverse("money:invoice-pay", args=[invoice.pk]),
            {"method": "bank_transfer"},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "unsupported_payment_method"
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("0.00")
