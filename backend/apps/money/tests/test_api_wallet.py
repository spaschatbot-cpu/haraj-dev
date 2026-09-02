"""T612 and T613 — the wallet screen and the statement behind it.

The single incident behind this file: a v1 customer read "رصيدك 10,000",
believed it was his to withdraw, and it was pinned to a live bid. Every test
here exists so that sentence can never be rendered again.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.money import services
from apps.money.models import (
    AccountKind,
    Entry,
    Invoice,
    InvoiceState,
    TransactionKind,
)

from .conftest import TEN_K, parsed_without_floats

pytestmark = pytest.mark.django_db


@pytest.fixture
def invoice(bidder):
    return Invoice.objects.create(
        customer=bidder,
        number="INV/2026/001",
        amount=Decimal("50000.00"),
        state=InvoiceState.OPEN,
        issued_at="2026-01-01T00:00:00Z",
    )


class TestWalletIsItemised:
    def test_it_names_every_bucket_instead_of_one_number(
        self, as_bidder, bidder, live_auction
    ):
        services.deposit_insurance(
            user=bidder, amount=Decimal("30000.00"), source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet")))

        assert body["available"] == "20000.00"
        assert body["held_for_auctions"] == "10000.00"
        assert body["locked_for_dues"] == "0.00"
        assert body["total"] == "30000.00"
        assert body["currency"] == "SAR"
        assert {bucket["kind"] for bucket in body["buckets"]} == set(
            AccountKind.customer_owned()
        )

    def test_the_total_equals_what_the_ledger_says(
        self, as_bidder, bidder, live_auction, invoice
    ):
        """G5. The screen's total is recomputed from the entries, not trusted."""
        services.deposit_insurance(
            user=bidder, amount=Decimal("30000.00"), source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)
        services.lock_for_invoice(user=bidder, invoice=invoice)

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet")))

        from_entries = sum(
            entry.amount
            for entry in Entry.objects.filter(owner=bidder)
            if entry.account.kind in AccountKind.customer_owned()
        )
        assert Decimal(body["total"]) == from_entries
        assert services.verify_ledger() == []

    def test_every_held_riyal_says_what_is_holding_it(
        self, as_bidder, bidder, live_auction, invoice
    ):
        services.deposit_insurance(
            user=bidder, amount=Decimal("30000.00"), source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)
        services.lock_for_invoice(user=bidder, invoice=invoice)

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet")))
        holds = {hold["reason"]: hold for hold in body["holds"]}

        assert holds["bidding"]["auction"]["number"] == live_auction.number
        assert holds["bidding"]["auction"]["title"] == live_auction.title
        assert holds["dues"]["invoice"]["number"] == invoice.number
        assert all(hold["reason_label"] != hold["reason"] for hold in body["holds"])

    def test_each_number_points_at_the_entries_behind_it(self, as_bidder, bidder):
        """Article 1-6: "الرقم ده جاي منين" has an answer on the response."""
        services.deposit_insurance(
            user=bidder, amount=TEN_K, source="cash", reference="P1"
        )

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet")))
        free = next(b for b in body["buckets"] if b["kind"] == AccountKind.INSURANCE_FREE)

        assert free["entry_count"] == 1
        assert free["statement"].endswith(f"?bucket={AccountKind.INSURANCE_FREE}")

    def test_a_wallet_never_shows_another_customers_money(
        self, as_bidder, bidder, stranger
    ):
        """The v1 IDOR: the wallet took its owner from a parameter."""
        services.deposit_insurance(
            user=stranger, amount=Decimal("99999.00"), source="cash", reference="P2"
        )

        body = parsed_without_floats(
            as_bidder.get(
                reverse("money:wallet"), {"user": stranger.pk, "id": stranger.pk}
            )
        )

        assert body["total"] == "0.00"

    def test_it_needs_a_signed_in_customer(self, api_client):
        response = api_client.get(reverse("money:wallet"))

        assert response.status_code in (401, 403)
        assert response.json()["error"]["message"]


class TestStatement:
    def test_it_reads_the_entries_themselves(self, as_bidder, bidder, live_auction):
        services.deposit_insurance(
            user=bidder, amount=TEN_K, source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet-statement")))

        assert body["count"] == Entry.objects.filter(owner=bidder).count() == 3
        amounts = {row["amount"] for row in body["results"]}
        assert "10000.00" in amounts and "-10000.00" in amounts

    def test_no_row_shows_its_english_key(self, as_bidder, bidder, live_auction):
        services.deposit_insurance(
            user=bidder, amount=TEN_K, source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)

        body = parsed_without_floats(as_bidder.get(reverse("money:wallet-statement")))

        for row in body["results"]:
            assert row["description"] != row["kind"]
            assert row["bucket_label"] != row["bucket"]
            assert row["description"].strip()

    def test_every_transaction_kind_has_an_arabic_description(self):
        """A new kind must not be able to reach a screen as an English word."""
        for kind in TransactionKind:
            assert kind.label != kind.value
            assert any("؀" <= ch <= "ۿ" for ch in kind.label)

    def test_it_pages(self, as_bidder, bidder):
        for index in range(3):
            services.deposit_insurance(
                user=bidder, amount=TEN_K, source="cash", reference=f"P{index}"
            )

        body = parsed_without_floats(
            as_bidder.get(reverse("money:wallet-statement"), {"limit": 2})
        )

        assert len(body["results"]) == 2
        assert body["count"] == 3
        assert body["next"]

    def test_it_filters_to_one_bucket(self, as_bidder, bidder, live_auction):
        services.deposit_insurance(
            user=bidder, amount=TEN_K, source="cash", reference="P1"
        )
        services.hold_for_auction(user=bidder, auction=live_auction)

        body = parsed_without_floats(
            as_bidder.get(
                reverse("money:wallet-statement"),
                {"bucket": AccountKind.INSURANCE_HELD},
            )
        )

        assert body["count"] == 1
        assert body["results"][0]["bucket"] == AccountKind.INSURANCE_HELD

    def test_an_unknown_bucket_is_refused_in_arabic(self, as_bidder):
        response = as_bidder.get(reverse("money:wallet-statement"), {"bucket": "revenue"})

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "validation_error"
        assert "غير معروف" in response.json()["error"]["message"]

    def test_it_never_leaks_another_customers_lines(self, as_bidder, bidder, stranger):
        services.deposit_insurance(
            user=stranger, amount=TEN_K, source="cash", reference="P2"
        )

        body = parsed_without_floats(
            as_bidder.get(reverse("money:wallet-statement"), {"user": stranger.pk})
        )

        assert body["count"] == 0
