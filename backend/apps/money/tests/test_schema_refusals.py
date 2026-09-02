"""The constraints, proven by going around the service entirely.

Article 4-2: «القيد الذي لا يُختبر تحت إعدادات الإنتاج غير موجود». A constraint
reached only through the service that already pre-checks the same rule is a
constraint nothing in the suite would miss if it were dropped — and B6 asks
specifically for a *direct insert*.

Every test here writes the row the way a stray admin action, a migration script
or a future service would, and asserts the database says no by name. Matching on
the constraint's name and not just on `IntegrityError` is deliberate: a test that
accepts any integrity failure passes for the wrong reason the day a different
index fires first.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.money import services
from apps.money.models import (
    Hold,
    HoldReason,
    HoldState,
    PaymentIntent,
    PaymentIntentState,
    PaymentPurpose,
    RefundRequest,
    RefundRequestState,
)

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def a_transaction(customer):
    """Any real transaction — the holds below need one to point at."""
    return services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="SEED/SCHEMA"
    )


def refuses(name: str):
    """Assert the next insert is refused by this constraint, by name."""
    return pytest.raises(IntegrityError, match=name)


class TestHoldRefusals:
    def test_a_hold_must_name_what_it_secures(self, customer, a_transaction):
        """Money pinned for no stated reason is the thing this table exists to
        make impossible — in v1 the question had no stored answer at all."""
        with refuses("a_hold_names_its_subject"), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                amount=TEN_K,
                reason=HoldReason.BIDDING,
                created_by_transaction=a_transaction,
            )

    def test_a_hold_of_zero_is_refused(self, customer, auction, a_transaction):
        with refuses("hold_is_positive"), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                auction=auction,
                amount=Decimal("0.00"),
                reason=HoldReason.BIDDING,
                created_by_transaction=a_transaction,
            )

    def test_a_negative_hold_is_refused(self, customer, auction, a_transaction):
        with refuses("hold_is_positive"), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                auction=auction,
                amount=Decimal("-1.00"),
                reason=HoldReason.BIDDING,
                created_by_transaction=a_transaction,
            )

    def test_an_active_hold_cannot_already_have_ended(
        self, customer, auction, a_transaction
    ):
        """A claim that is both standing and finished is unreadable: nobody can
        say whether the money is still pinned."""
        with refuses("active_hold_has_not_ended"), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                auction=auction,
                amount=TEN_K,
                reason=HoldReason.BIDDING,
                state=HoldState.ACTIVE,
                created_by_transaction=a_transaction,
                ended_by_transaction=a_transaction,
            )

    def test_a_second_active_hold_on_one_auction_is_refused(
        self, customer, auction, a_transaction
    ):
        """`hold_for_auction` pre-checks with `_active_hold` first, so this
        index is never reached through the service — drop it and
        `test_twenty_concurrent_calls_produce_one_hold` still passes on most
        runs. Reached directly, it is what actually holds."""
        services.hold_for_auction(user=customer, auction=auction, amount=TEN_K)

        with refuses("one_active_hold_per_customer_and_auction"), transaction.atomic():
            Hold.objects.create(
                owner=customer,
                auction=auction,
                amount=Decimal("1.00"),
                reason=HoldReason.BIDDING,
                created_by_transaction=a_transaction,
            )


class TestPaymentIntentRefusals:
    def test_an_intent_for_zero_is_refused(self, customer):
        with refuses("payment_intent_is_positive"), transaction.atomic():
            PaymentIntent.objects.create(
                reference="topup-zero",
                user=customer,
                amount=Decimal("0.00"),
                purpose=PaymentPurpose.INSURANCE_DEPOSIT,
            )

    def test_one_gateway_payment_cannot_answer_two_intents(self, customer):
        """The double-credit shape the constraint's own comment names.

        The nearest existing test is stopped by the inbound delivery-id dedup
        long before this index is reached, so dropping it changed nothing in the
        suite while allowing one payment to credit two deposits.
        """
        PaymentIntent.objects.create(
            reference="topup-a",
            user=customer,
            amount=TEN_K,
            purpose=PaymentPurpose.INSURANCE_DEPOSIT,
            gateway="moyasar",
            gateway_payment_id="PAY-1",
        )

        with refuses("one_intent_per_gateway_payment"), transaction.atomic():
            PaymentIntent.objects.create(
                reference="topup-b",
                user=customer,
                amount=TEN_K,
                purpose=PaymentPurpose.INSURANCE_DEPOSIT,
                gateway="moyasar",
                gateway_payment_id="PAY-1",
            )

    def test_two_intents_may_both_be_waiting_for_a_payment_id(self, customer):
        """The index is partial on purpose: pending intents have no id yet, and
        a blank one must not collide with another blank one."""
        for reference in ("topup-c", "topup-d"):
            PaymentIntent.objects.create(
                reference=reference,
                user=customer,
                amount=TEN_K,
                purpose=PaymentPurpose.INSURANCE_DEPOSIT,
            )

        assert PaymentIntent.objects.filter(gateway_payment_id="").count() == 2

    def test_a_succeeded_intent_must_name_its_transaction(self, customer):
        """Article 1-6 in the schema: a number a customer sees is traceable to
        the entries that produced it, or it is not written down at all."""
        with refuses("a_succeeded_intent_names_its_transaction"), transaction.atomic():
            PaymentIntent.objects.create(
                reference="topup-e",
                user=customer,
                amount=TEN_K,
                purpose=PaymentPurpose.INSURANCE_DEPOSIT,
                state=PaymentIntentState.SUCCEEDED,
            )


class TestRefundRequestRefusals:
    def test_a_request_for_zero_is_refused(self, customer):
        with refuses("refund_request_is_positive"), transaction.atomic():
            RefundRequest.objects.create(
                user=customer, amount=Decimal("0.00"), reference="refund-zero"
            )

    def test_a_confirmed_refund_must_name_its_transaction(self, customer):
        with refuses("a_confirmed_refund_names_its_transaction"), transaction.atomic():
            RefundRequest.objects.create(
                user=customer,
                amount=TEN_K,
                reference="refund-confirmed",
                state=RefundRequestState.CONFIRMED,
            )

    def test_a_confirmed_refund_that_names_one_is_accepted(self, customer, a_transaction):
        row = RefundRequest.objects.create(
            user=customer,
            amount=TEN_K,
            reference="refund-ok",
            state=RefundRequestState.CONFIRMED,
            resulting_transaction=a_transaction,
        )

        assert row.pk is not None
