"""T116–T118 — invoices, and the state that is computed rather than copied.

The v1 failure this file exists to prevent: the state column was written once
at insert and never again, so every mirrored invoice read `draft` forever.
Every gate that branched on it — including the one meant to stop a debtor
withdrawing their deposit — was reading a value frozen at creation time.
"""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.money import services
from apps.money.models import (
    AccountKind,
    Hold,
    HoldState,
    Invoice,
    InvoiceSource,
    InvoiceState,
    Transaction,
    TransactionKind,
)
from apps.money.services import MoneyError, derive_invoice_state
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")
SEVEN_K = Decimal("7000.00")


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def locked(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_LOCKED).balance


def fund(user, amount=TEN_K):
    return services.deposit_insurance(
        user=user, amount=amount, source="cash", reference=f"SEED:{user.pk}"
    )


@pytest.fixture
def invoice(customer, vehicle):
    return Invoice.objects.create(
        customer=customer,
        number="INV/2026/0001",
        amount=SEVEN_K,
        vehicle=vehicle,
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.LOCAL,
    )


# ---------------------------------------------------------------------------
# T116 — the state is derived
# ---------------------------------------------------------------------------


class TestDerivedState:
    def test_a_partial_payment_makes_it_partial(self, customer, invoice):
        fund(customer)

        services.record_payment(
            invoice=invoice,
            amount=Decimal("3000.00"),
            source="cash",
            reference="P/1",
        )

        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.PARTIAL
        assert invoice.amount_paid == Decimal("3000.00")
        assert invoice.outstanding == Decimal("4000.00")

    def test_paying_the_rest_makes_it_paid(self, customer, invoice):
        fund(customer)
        services.record_payment(
            invoice=invoice, amount=Decimal("3000.00"), source="cash", reference="P/2a"
        )

        services.record_payment(
            invoice=invoice, amount=Decimal("4000.00"), source="cash", reference="P/2b"
        )

        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.PAID
        assert invoice.outstanding == Decimal("0.00")

    def test_an_unknown_odoo_word_changes_nothing_and_drops_no_write(self, invoice):
        """Article 2-3. A status string we have never seen is recorded and
        ignored — it must not abort the write that carries it, which is
        exactly what an enum column did in v1 when the webhook 'stopped'."""
        invoice.odoo_state_raw = "posted_and_then_some_new_odoo_word"
        invoice.save(update_fields=["odoo_state_raw"])

        invoice.refresh_from_db()
        assert invoice.odoo_state_raw == "posted_and_then_some_new_odoo_word"
        assert invoice.state == InvoiceState.OPEN
        assert derive_invoice_state(invoice) == InvoiceState.OPEN

    def test_the_derivation_ignores_the_stored_state_when_money_says_otherwise(
        self, customer, invoice
    ):
        """Someone hand-edits the column to `draft` on a half-paid invoice.
        The next derivation corrects it from the numbers, because the numbers
        are the fact and the column is a cache of it."""
        invoice.amount_paid = Decimal("3000.00")
        invoice.state = InvoiceState.DRAFT

        assert derive_invoice_state(invoice) == InvoiceState.PARTIAL

    def test_a_cancelled_invoice_stays_cancelled(self, invoice):
        invoice.state = InvoiceState.CANCELLED

        assert derive_invoice_state(invoice) == InvoiceState.CANCELLED
        assert invoice.outstanding == Decimal("0.00")

    def test_a_cancelled_invoice_cannot_be_paid(self, customer, invoice):
        fund(customer)
        invoice.state = InvoiceState.CANCELLED
        invoice.save(update_fields=["state"])

        with pytest.raises(MoneyError, match="ملغاة"):
            services.record_payment(
                invoice=invoice, amount=Decimal("100.00"), source="cash", reference="P/3"
            )


# ---------------------------------------------------------------------------
# T117 — recording a payment
# ---------------------------------------------------------------------------


class TestRecordPayment:
    def test_the_money_reaches_revenue(self, customer, invoice):
        fund(customer)

        services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="cash", reference="P/4"
        )

        assert services.system_account(AccountKind.REVENUE).balance == SEVEN_K

    def test_paying_from_locked_insurance_empties_the_lock(self, customer, invoice):
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)
        assert locked(customer) == SEVEN_K

        services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="insurance", reference="P/5"
        )

        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.PAID
        assert locked(customer) == Decimal("0.00")
        assert free(customer) == Decimal("3000.00")

    def test_paying_from_outside_hands_the_locked_deposit_back(self, customer, invoice):
        """The debt is settled with fresh money, so the deposit that was
        securing it is the customer's again — automatically, in the same
        atomic block. Leaving it locked is how v1 produced customers who owed
        nothing and still could not withdraw."""
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)
        assert free(customer) == Decimal("3000.00")

        services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="cash", reference="P/6"
        )

        assert locked(customer) == Decimal("0.00")
        assert free(customer) == TEN_K
        assert Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE).count() == 0

    def test_a_partial_payment_leaves_the_lock_alone(self, customer, invoice):
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)

        services.record_payment(
            invoice=invoice, amount=Decimal("1000.00"), source="cash", reference="P/7"
        )

        assert locked(customer) == SEVEN_K
        assert Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE).count() == 1

    def test_overpaying_is_refused_with_both_numbers(self, customer, invoice):
        fund(customer)

        with pytest.raises(MoneyError, match="أكبر منه") as raised:
            services.record_payment(
                invoice=invoice, amount=TEN_K, source="cash", reference="P/8"
            )

        assert "7000.00" in str(raised.value)
        invoice.refresh_from_db()
        assert invoice.amount_paid == Decimal("0.00")

    def test_a_zero_or_negative_payment_is_refused(self, customer, invoice):
        with pytest.raises(MoneyError, match="أكبر من صفر"):
            services.record_payment(
                invoice=invoice, amount=Decimal("0.00"), source="cash", reference="P/9"
            )

    def test_an_unknown_source_is_refused(self, customer, invoice):
        with pytest.raises(MoneyError, match="مصدر سداد غير معروف"):
            services.record_payment(
                invoice=invoice, amount=SEVEN_K, source="crypto", reference="P/10"
            )

    def test_the_same_payment_reference_is_recorded_once(self, customer, invoice):
        fund(customer)

        services.record_payment(
            invoice=invoice, amount=Decimal("1000.00"), source="cash", reference="P/11"
        )
        first_paid = Invoice.objects.get(pk=invoice.pk).amount_paid

        # The retry cron replays the same Odoo payment.
        txn = services.record_payment(
            invoice=invoice, amount=Decimal("1000.00"), source="cash", reference="P/11"
        )

        invoice.refresh_from_db()
        assert txn.kind == TransactionKind.INVOICE_PAYMENT
        assert (
            Transaction.objects.filter(
                idempotency_key=f"payment:{invoice.pk}:P/11"
            ).count()
            == 1
        )
        assert invoice.amount_paid == first_paid, (
            "a replayed payment moved no money, so it must not add to the "
            "paid total either"
        )
        assert verify_ledger() == []

    def test_the_ledger_is_clean_after_a_full_settlement(self, customer, invoice):
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)

        services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="insurance", reference="P/12"
        )

        assert verify_ledger() == []


# ---------------------------------------------------------------------------
# T118 — one live invoice per vehicle
# ---------------------------------------------------------------------------


class TestOneLiveInvoicePerVehicle:
    def test_a_second_live_invoice_for_one_vehicle_fails_in_the_database(
        self, customer, vehicle, invoice
    ):
        """A loop in v1 produced 786 invoices for the same vehicle. This makes
        the 787th impossible at the schema level, not at the caller's."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Invoice.objects.create(
                customer=customer,
                number="INV/2026/0002",
                amount=SEVEN_K,
                vehicle=vehicle,
                state=InvoiceState.OPEN,
                issued_at=timezone.now(),
                source=InvoiceSource.LOCAL,
            )

    def test_a_cancelled_invoice_frees_the_vehicle_for_a_new_one(
        self, customer, vehicle, invoice
    ):
        """Cancelling is the legitimate way to re-invoice a vehicle — a winner
        was replaced, a price was wrong. The partial index allows exactly that
        and nothing else."""
        invoice.state = InvoiceState.CANCELLED
        invoice.save(update_fields=["state"])

        replacement = Invoice.objects.create(
            customer=customer,
            number="INV/2026/0003",
            amount=SEVEN_K,
            vehicle=vehicle,
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
            source=InvoiceSource.LOCAL,
        )

        assert replacement.pk != invoice.pk

    def test_two_vehicles_can_each_have_their_own_invoice(
        self, customer, auction, invoice
    ):
        from apps.auctions.models import Vehicle, VehicleState

        second_vehicle = Vehicle.objects.create(
            auction=auction,
            lot_number=2,
            make="نيسان",
            model="التيما",
            year=2021,
            state=VehicleState.LISTED,
        )

        second = Invoice.objects.create(
            customer=customer,
            number="INV/2026/0004",
            amount=SEVEN_K,
            vehicle=second_vehicle,
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
            source=InvoiceSource.LOCAL,
        )

        assert second.pk != invoice.pk


# ---------------------------------------------------------------------------
# A lock is a claim on money that is there
# ---------------------------------------------------------------------------


class TestTheClaimShrinksWithTheMoneyItClaims:
    """Paying part of a debt out of the locked bucket must shrink the lock.

    Every one of these was measured on PostgreSQL before the fix, and each is a
    refusal a customer would have met with no way round it.
    """

    def test_a_partial_insurance_payment_leaves_the_hold_matching_the_bucket(
        self, customer, invoice
    ):
        fund(customer)
        hold = services.lock_for_invoice(user=customer, invoice=invoice)

        services.record_payment(
            invoice=invoice,
            amount=Decimal("3000.00"),
            source="insurance",
            reference="p1",
        )

        hold.refresh_from_db()
        assert locked(customer) == Decimal("4000.00")
        assert hold.amount == Decimal("4000.00")
        assert hold.state == HoldState.ACTIVE
        # The drift used to be reported here and nowhere else, after the money
        # had already moved.
        assert verify_ledger() == []

    def test_settling_the_rest_in_cash_is_not_refused(self, customer, invoice):
        """The whole atomic block used to roll back.

        `_release_holds_on` released the hold's *original* figure out of a
        bucket the partial payment had already drained, `post` refused with
        InsufficientFunds, and a legitimate cash payment was rejected — leaving
        an invoice that could never reach `paid`.
        """
        fund(customer)
        services.lock_for_invoice(user=customer, invoice=invoice)
        services.record_payment(
            invoice=invoice,
            amount=Decimal("3000.00"),
            source="insurance",
            reference="p1",
        )

        services.record_payment(
            invoice=invoice,
            amount=Decimal("4000.00"),
            source="cash",
            reference="p2",
        )

        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.PAID
        assert locked(customer) == Decimal("0.00")
        # The 4,000 that was locked comes back; the 3,000 went to revenue.
        assert free(customer) == Decimal("7000.00")
        assert verify_ledger() == []

    def test_a_fully_spent_hold_names_the_payment_that_ended_it(self, customer, invoice):
        fund(customer, SEVEN_K)
        hold = services.lock_for_invoice(user=customer, invoice=invoice)

        txn = services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="insurance", reference="p1"
        )

        hold.refresh_from_db()
        assert hold.state == HoldState.CONSUMED
        assert hold.ended_by_transaction_id == txn.pk
        assert verify_ledger() == []

    def test_a_second_deposit_can_still_settle_what_is_left(self, customer, invoice):
        """The permanent failure: an invoice that could never be paid.

        The customer could only cover 4,000 at first, so that is what was
        locked and spent. `lock_for_invoice` then found the exhausted hold still
        ACTIVE, returned it having locked nothing, and every later insurance
        payment failed on an empty bucket — on the first attempt and on every
        retry after it.
        """
        fund(customer, Decimal("4000.00"))
        services.lock_for_invoice(user=customer, invoice=invoice)
        services.record_payment(
            invoice=invoice,
            amount=Decimal("4000.00"),
            source="insurance",
            reference="p1",
        )

        services.deposit_insurance(
            user=customer, amount=Decimal("3000.00"), source="cash", reference="SEED-2"
        )
        services.lock_for_invoice(user=customer, invoice=invoice)
        services.record_payment(
            invoice=invoice,
            amount=Decimal("3000.00"),
            source="insurance",
            reference="p2",
        )

        invoice.refresh_from_db()
        assert invoice.state == InvoiceState.PAID
        assert invoice.amount_paid == SEVEN_K
        assert free(customer) == Decimal("0.00")
        assert verify_ledger() == []

    def test_an_existing_lock_is_topped_up_to_the_debt_and_no_further(
        self, customer, invoice
    ):
        """Locking more than the debt would be a penalty; this bucket is a
        guarantee. So the top-up stops at what is still owed."""
        fund(customer, Decimal("2000.00"))
        hold = services.lock_for_invoice(user=customer, invoice=invoice)
        assert hold.amount == Decimal("2000.00")

        services.deposit_insurance(
            user=customer, amount=TEN_K, source="cash", reference="SEED-TOPUP"
        )
        services.lock_for_invoice(user=customer, invoice=invoice)

        hold.refresh_from_db()
        assert hold.amount == SEVEN_K
        assert locked(customer) == SEVEN_K
        assert verify_ledger() == []


class TestPayingFromBalanceReadsTheRowItPaysFor:
    def test_a_concurrently_settled_invoice_is_not_paid_twice(self, customer, invoice):
        """The view loads the invoice when the request arrives; an Odoo webhook
        can settle it before the service runs.

        Without the re-read under the row lock, `outstanding` came off the stale
        copy, a second full payment went to revenue, and the write-back
        overwrote the webhook's — so 14,000 was taken for a 7,000 invoice that
        then read exactly 7,000 paid, with no trace of the over-payment on it.
        """
        fund(customer, Decimal("20000.00"))
        as_the_view_loaded_it = Invoice.objects.get(pk=invoice.pk)

        services.record_payment(
            invoice=invoice, amount=SEVEN_K, source="cash", reference="odoo-webhook"
        )

        with pytest.raises(MoneyError, match="nothing outstanding") as refused:
            services.pay_invoice_from_balance(
                user=customer, invoice=as_the_view_loaded_it
            )
        assert "لا يوجد مبلغ مستحق" in refused.value.user_message

        invoice.refresh_from_db()
        assert invoice.amount_paid == SEVEN_K
        assert services.system_account(AccountKind.REVENUE).balance == SEVEN_K
        assert free(customer) == Decimal("20000.00")
        assert verify_ledger() == []

    def test_the_state_it_writes_is_the_derived_one(self, customer, invoice):
        """One function decides this column, whoever paid.

        The branch that used to stand here knew neither CANCELLED nor DRAFT, so
        the two payment paths were two decision points for one rule.
        """
        fund(customer)

        services.pay_invoice_from_balance(user=customer, invoice=invoice)

        invoice.refresh_from_db()
        assert invoice.state == derive_invoice_state(invoice)
        assert invoice.state == InvoiceState.PAID
