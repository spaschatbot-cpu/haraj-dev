"""T515 — letting a debtor bid, by a decision with a name on it.

In v1 the exception was granted by editing two columns by hand. Nobody could
say afterwards who had allowed it, or why, and the deposit rule quietly stopped
applying to whoever had a friend in the office. Here it is a call that refuses
to happen without both facts, and it leaves an audit row.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bidding import services
from apps.bidding.eligibility import check_eligibility
from apps.bidding.models import RefusalReason
from apps.core.models import AuditLog
from apps.money import services as money
from apps.money.models import Hold, HoldState, Invoice, InvoiceState
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

BID = Decimal("30000.00")
DUE = Decimal("5000.00")


@pytest.fixture
def debtor(verified):
    """A bidder with plenty of insurance and one unpaid invoice locked on it."""
    money.deposit_insurance(
        user=verified,
        amount=Decimal("20000.00"),
        source="cash",
        reference="dep/debtor",
    )
    invoice = Invoice.objects.create(
        customer=verified,
        number="INV-EXC-1",
        amount=DUE,
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
    )
    hold = money.lock_for_invoice(user=verified, invoice=invoice)
    return verified, invoice, hold


def test_a_debtor_is_refused_until_the_owner_says_otherwise(debtor, vehicle, staff):
    user, _invoice, hold = debtor

    assert check_eligibility(user, vehicle, amount=BID).reason == (
        RefusalReason.UNPAID_DUES
    )

    services.grant_bidding_exception(
        hold=hold, note="اتفاق سداد موقّع مع العميل", by=staff
    )

    assert check_eligibility(user, vehicle, amount=BID).allowed
    bid = services.place_bid(user=user, vehicle=vehicle, amount=BID)
    assert bid.pk is not None
    assert verify_ledger() == []


def test_the_debt_is_still_a_debt_in_the_record(debtor, vehicle, staff):
    """The exception excuses the bidder; it does not erase what they owe."""
    user, _invoice, hold = debtor
    services.grant_bidding_exception(hold=hold, note="قرار المالك", by=staff)

    decision = check_eligibility(user, vehicle, amount=BID)

    assert decision.allowed
    assert decision.money.outstanding_dues == DUE
    assert decision.money.insurance_locked == DUE


def test_the_exception_names_its_grantor_and_its_reason(debtor, staff):
    _user, _invoice, hold = debtor

    services.grant_bidding_exception(hold=hold, note="  تسوية متفق عليها  ", by=staff)

    granted = Hold.objects.filter(
        pk=hold.pk, exception_granted_by=staff, exception_note="تسوية متفق عليها"
    )
    assert granted.exists()

    entry = AuditLog.objects.filter(action="bidding.exception_granted").first()
    assert entry is not None
    assert entry.actor_id == staff.pk
    assert entry.entity_id == str(hold.pk)
    assert entry.note == "تسوية متفق عليها"
    assert entry.after["exception_granted_by"] == str(staff.pk)


@pytest.mark.parametrize(
    ("note", "by"),
    [("", "staff"), ("   ", "staff"), ("سبب مكتوب", None)],
    ids=["no reason", "blank reason", "no grantor"],
)
def test_an_exception_without_a_name_or_a_reason_is_refused(debtor, staff, note, by):
    _user, _invoice, hold = debtor

    with pytest.raises(services.BiddingError):
        services.grant_bidding_exception(hold=hold, note=note, by=staff if by else None)

    assert not Hold.objects.filter(
        pk=hold.pk, exception_granted_by__isnull=False
    ).exists()
    assert not AuditLog.objects.filter(action="bidding.exception_granted").exists()


def test_an_exception_belongs_on_a_dues_lock(bidder, vehicle, staff):
    """A bidding hold secures nothing that could be excused."""
    services.place_bid(user=bidder, vehicle=vehicle, amount=BID)
    hold = Hold.objects.get(owner=bidder, state=HoldState.ACTIVE)

    with pytest.raises(services.BiddingError):
        services.grant_bidding_exception(hold=hold, note="محاولة", by=staff)


def test_one_excused_debt_does_not_excuse_another(debtor, vehicle, staff):
    user, _invoice, hold = debtor
    services.grant_bidding_exception(hold=hold, note="قرار المالك", by=staff)

    Invoice.objects.create(
        customer=user,
        number="INV-EXC-2",
        amount=Decimal("1000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
    )

    decision = check_eligibility(user, vehicle, amount=BID)

    assert decision.reason == RefusalReason.UNPAID_DUES
    assert decision.money.outstanding_dues == DUE + Decimal("1000.00")
