"""HR-03 — the deposit is a unit, not a balance.

``PHASE_02`` §1-1: the deposit is 10,000 exactly, and insurance is topped up in
multiples of it **and in nothing else**. Two v1 incidents come from treating it
as an elastic pile of riyals instead:

* "التعامل مع التأمين كرصيد مرن (ريالات) فتح ثغرات استخدام كسور المبالغ
  للمزايدة دون دفع التأمين الكامل";
* a **one-riyal test deposit** counted as answering a 10,000 refund, "مما خلق
  عجزاً لم يكتشف لأسابيع".

The rule lives at the three places a **decision** is made, and deliberately not
at the one place it looks like it belongs:

* ``start_topup`` never offers the customer the choice — the amount comes from
  ``deposit_amount_for``. Half of v1's hole was already closed here.
* ``credit_payment`` is the door for money arriving. A fractional payment is
  **not refused**: a bank transfer cannot be un-received and Article 2-2
  forbids dropping it, so it waits in suspense — refused as *insurance*, kept
  as *money*, until a person says what it was.
* ``attribute`` is the way out of suspense and into ``insurance_free``, so it
  refuses a fraction. Without it, suspense is the way round the rule.

``deposit_insurance`` itself stays a plain recorder. It writes down that money
became insurance; it does not rule on whether the platform should have taken
it. The property tests generate arbitrary movements to prove the ledger's
invariants, and phase 004 rebuilds v1's history — which contains the one-riyal
deposit this rule exists because of.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import override_settings

from apps.money import services
from apps.money.models import AccountKind
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

UNIT = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966501234567", full_name="عميل", national_id="1234567890"
    )


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def suspense() -> Decimal:
    return services.system_account(AccountKind.SUSPENSE).balance


# ---------------------------------------------------------------------------
# The unit itself
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "amount,expected",
    [
        ("10000.00", 1),
        ("20000.00", 2),
        ("100000.00", 10),
        ("3000.00", None),
        ("10000.01", None),
        ("9999.99", None),
        ("1.00", None),  # the test deposit that cost v1 weeks
        ("0.00", None),
        ("-10000.00", None),
    ],
)
def test_what_counts_as_whole_deposits(amount, expected):
    result = services.whole_deposits_in(Decimal(amount))

    assert result == (None if expected is None else Decimal(expected))


def test_the_unit_follows_the_setting_not_a_number_in_the_code():
    """One definition, and it is the one `deposit_amount_for` already serves."""
    with override_settings(INSURANCE_DEPOSIT_AMOUNT="5000.00"):
        assert services.whole_deposits_in(Decimal("15000.00")) == 3
        assert services.whole_deposits_in(Decimal("10000.01")) is None


# ---------------------------------------------------------------------------
# The two doors into insurance_free
# ---------------------------------------------------------------------------


def test_the_refusal_names_both_numbers(customer):
    services.receive_unattributed(
        amount=Decimal("3000.00"), source="cash", reference="t/1"
    )

    with pytest.raises(services.NotWholeDeposits) as raised:
        services.attribute(user=customer, amount=Decimal("3000.00"), reference="t/1")

    assert "10000.00" in str(raised.value)
    assert "3000.00" in str(raised.value)


def test_the_ledger_primitive_is_not_where_the_rule_lives(customer):
    """`deposit_insurance` records; it does not decide. Deliberate — HR-03.

    The rule is about what the platform accepts, and this function is what
    writes down that money became insurance. Two callers need it to stay a
    plain recorder: the property tests generate arbitrary movements to prove
    the ledger's invariants, and phase 004 rebuilds v1's history — which
    contains the one-riyal deposit this rule exists because of. A ledger that
    cannot express what happened cannot be reconciled against it.
    """
    services.deposit_insurance(
        user=customer, amount=Decimal("3000.00"), source="cash", reference="t/2"
    )

    assert free(customer) == Decimal("3000.00")
    assert verify_ledger() == []


def test_a_whole_deposit_still_goes_through(customer):
    services.credit_payment(
        user=customer, amount=UNIT * 2, source="cash", reference="t/3"
    )

    assert free(customer) == UNIT * 2
    assert verify_ledger() == []


def test_suspense_is_not_a_way_round_the_unit(customer):
    """The whole reason the rule guards the bucket and not the caller."""
    services.receive_unattributed(
        amount=Decimal("3000.00"), source="cash", reference="t/9"
    )

    with pytest.raises(services.NotWholeDeposits):
        services.attribute(user=customer, amount=Decimal("3000.00"), reference="t/9")

    assert free(customer) == Decimal("0.00")
    assert suspense() == Decimal("3000.00"), "المبلغ ما زال محفوظاً"
    assert verify_ledger() == []


def test_attributing_a_whole_deposit_out_of_suspense_works(customer):
    services.receive_unattributed(amount=UNIT, source="cash", reference="t/4")

    services.attribute(user=customer, amount=UNIT, reference="t/4")

    assert free(customer) == UNIT
    assert suspense() == Decimal("0.00")
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# Money that has already arrived is never dropped
# ---------------------------------------------------------------------------


def test_a_fractional_payment_that_arrived_is_kept_not_refused(customer):
    """Article 2-2. The transfer happened; refusing it would lose real money."""
    txn = services.credit_payment(
        user=customer, amount=Decimal("3000.00"), source="cash", reference="odoo/77"
    )

    assert txn is not None
    assert free(customer) == Decimal("0.00"), "دخلت التأمين رغم أنها ليست وديعة"
    assert suspense() == Decimal("3000.00"), "أُسقط مبلغ وصل فعلاً"
    assert verify_ledger() == []


def test_hearing_the_same_fractional_payment_twice_keeps_one(customer):
    services.credit_payment(
        user=customer, amount=Decimal("3000.00"), source="cash", reference="odoo/78"
    )
    services.credit_payment(
        user=customer, amount=Decimal("3000.00"), source="cash", reference="odoo/78"
    )

    assert suspense() == Decimal("3000.00")
    assert verify_ledger() == []


def test_a_whole_payment_still_becomes_insurance(customer):
    services.credit_payment(
        user=customer, amount=UNIT, source="cash", reference="odoo/79"
    )

    assert free(customer) == UNIT
    assert suspense() == Decimal("0.00")
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# The customer's own path never offered the choice
# ---------------------------------------------------------------------------


def test_a_card_topup_is_one_deposit_and_the_customer_never_names_it(customer):
    """Half of the v1 hole was already closed here — pinned so it stays closed."""
    intent = services.start_topup(user=customer)

    assert intent.amount == UNIT
    assert services.whole_deposits_in(intent.amount) == 1
