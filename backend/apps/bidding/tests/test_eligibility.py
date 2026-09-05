"""T501 / T502 — one gate, every reason, and a refusal that keeps its evidence.

There is a test per enumerated reason (F2), and each one goes through
`place_bid` rather than calling `check_eligibility` directly: what has to be
proven is not that the function can say no, but that the *bidding path* cannot
get past it — and that saying no leaves a record behind.
"""

from __future__ import annotations

import pathlib
import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Company
from apps.auctions.models import Auction, AuctionState, VehicleState
from apps.bidding import services
from apps.bidding.eligibility import check_eligibility
from apps.bidding.models import Bid, BidRefusal, RefusalReason
from apps.money import services as money
from apps.money.models import Invoice, InvoiceSource, InvoiceState
from apps.money.verification import verify_ledger

from .conftest import TEN_K, make_user, make_vehicle

pytestmark = pytest.mark.django_db

BID = Decimal("25000.00")


def refuse(user, vehicle, amount=BID) -> BidRefusal:
    """Place a bid that must be refused, and hand back the record it left."""
    with pytest.raises(services.BidRefused) as raised:
        services.place_bid(user=user, vehicle=vehicle, amount=amount)

    refusal = BidRefusal.objects.filter(bidder=user, vehicle=vehicle).first()
    assert refusal is not None, "a refusal must always be written down"
    assert refusal.reason == raised.value.code
    assert not Bid.objects.filter(bidder=user, vehicle=vehicle).exists()
    return refusal


# ---------------------------------------------------------------------------
# One test per reason — the enum is the checklist
# ---------------------------------------------------------------------------


def test_a_scheduled_auction_is_not_open_yet(bidder, db):
    now = timezone.now()
    later = Auction.objects.create(
        number=700,
        title="مزاد بكرة",
        starts_at=now + timedelta(days=1),
        ends_at=now + timedelta(days=2),
        state=AuctionState.SCHEDULED,
        deposit_required=TEN_K,
    )

    assert refuse(bidder, make_vehicle(later)).reason == RefusalReason.AUCTION_NOT_LIVE


def test_an_auction_past_its_end_takes_no_more_bids(bidder, db):
    now = timezone.now()
    over = Auction.objects.create(
        number=701,
        title="مزاد انتهى",
        starts_at=now - timedelta(hours=3),
        ends_at=now - timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )

    assert refuse(bidder, make_vehicle(over)).reason == RefusalReason.AUCTION_ENDED


def test_a_withdrawn_car_takes_no_bids(bidder, live_auction):
    vehicle = make_vehicle(live_auction, lot=9, state=VehicleState.WITHDRAWN)

    assert refuse(bidder, vehicle).reason == RefusalReason.VEHICLE_NOT_BIDDABLE


def test_you_cannot_bid_on_your_own_car(bidder, live_auction):
    company = Company.objects.create(user=bidder, name="شركة المزايد")
    vehicle = make_vehicle(live_auction, lot=10, owner_company=company)

    assert refuse(bidder, vehicle).reason == RefusalReason.OWN_VEHICLE


def test_an_unverified_phone_cannot_bid(db, django_user_model, vehicle):
    stranger = make_user(
        django_user_model, phone="966501000009", national_id="1000000009"
    )
    money.deposit_insurance(
        user=stranger, amount=TEN_K, source="cash", reference="dep/unverified"
    )

    assert refuse(stranger, vehicle).reason == RefusalReason.PHONE_NOT_VERIFIED


def test_an_incomplete_profile_cannot_bid(db, django_user_model, vehicle):
    nameless = make_user(
        django_user_model, phone="966501000008", phone_verified_at=timezone.now()
    )
    money.deposit_insurance(
        user=nameless, amount=TEN_K, source="cash", reference="dep/incomplete"
    )

    assert refuse(nameless, vehicle).reason == RefusalReason.PROFILE_INCOMPLETE


def test_a_bid_under_the_floor_is_refused(bidder, vehicle):
    refusal = refuse(bidder, vehicle, amount=Decimal("500.00"))

    assert refusal.reason == RefusalReason.BELOW_FLOOR
    assert refusal.amount == Decimal("500.00")


def test_without_a_deposit_there_is_no_bid(verified, vehicle):
    refusal = refuse(verified, vehicle)

    assert refusal.reason == RefusalReason.NO_DEPOSIT
    assert refusal.insurance_free == Decimal("0.00")


def test_a_debtor_cannot_bid(bidder, vehicle):
    Invoice.objects.create(
        customer=bidder,
        number="INV-DUE-1",
        amount=Decimal("4000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.LOCAL,
    )

    refusal = refuse(bidder, vehicle)

    assert refusal.reason == RefusalReason.UNPAID_DUES
    assert refusal.outstanding_dues == Decimal("4000.00")


def test_every_reason_in_the_enum_has_a_test():
    """The enum is the checklist, so the checklist cannot silently grow.

    A new reason added to the model and exercised nowhere fails this — a rule
    nobody exercised is a rule nobody knows works.

    The reasons are **read off the tests themselves** rather than listed here.
    A second list went stale the first time it was tried: `REFUND_PENDING` was
    added to the enum and tested in `test_refund_blocks_bid.py`, and this test
    went red because the list beside it had not been edited — reporting "no
    test" for a reason that had one. A checklist maintained by hand is a
    checklist that reports on itself, not on the suite.
    """
    named = set()
    for source in pathlib.Path(__file__).parent.glob("test_*.py"):
        named |= set(re.findall(r"RefusalReason\.([A-Z_]+)", source.read_text("utf-8")))

    untested = {reason for reason in RefusalReason if reason.name not in named}

    assert not untested, f"أسباب رفض بلا اختبار: {sorted(r.name for r in untested)}"


# ---------------------------------------------------------------------------
# T502 — the snapshot is a photograph, not a window
# ---------------------------------------------------------------------------


def test_the_snapshot_does_not_move_when_the_balances_do(verified, vehicle):
    refusal = refuse(verified, vehicle)
    assert refusal.insurance_free == Decimal("0.00")

    money.deposit_insurance(
        user=verified, amount=TEN_K, source="cash", reference="dep/after-refusal"
    )
    services.place_bid(user=verified, vehicle=vehicle, amount=BID)

    refusal.refresh_from_db()
    assert refusal.insurance_free == Decimal("0.00"), (
        "the refusal must keep saying what was true when it happened"
    )
    assert refusal.insurance_held == Decimal("0.00")
    assert verify_ledger() == []


def test_a_refusal_carries_the_whole_money_picture(bidder, vehicle):
    """Held and locked matter as much as free: "المتاح صفر" without them is the
    v1 answer that sent support looking through three more tables."""
    invoice = Invoice.objects.create(
        customer=bidder,
        number="INV-DUE-2",
        amount=Decimal("3000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.LOCAL,
    )
    money.lock_for_invoice(user=bidder, invoice=invoice)

    refusal = refuse(bidder, vehicle)

    assert refusal.reason == RefusalReason.UNPAID_DUES
    assert refusal.insurance_locked == Decimal("3000.00")
    assert refusal.insurance_free == Decimal("7000.00")
    assert refusal.outstanding_dues == Decimal("3000.00")


# ---------------------------------------------------------------------------
# The gate answers the same way whether or not anyone is writing
# ---------------------------------------------------------------------------


def test_a_screen_can_ask_before_a_number_is_typed(bidder, vehicle):
    """`amount=None` skips only the amount-shaped rule, and nothing else."""
    assert check_eligibility(bidder, vehicle).allowed
    assert not check_eligibility(bidder, vehicle, amount=Decimal("1.00")).allowed


def test_asking_creates_nothing(verified, vehicle):
    """A bidder with no deposit has no accounts, and asking must not make any."""
    from apps.money.models import Account

    decision = check_eligibility(verified, vehicle, amount=BID)

    assert decision.reason == RefusalReason.NO_DEPOSIT
    assert not Account.objects.filter(owner=verified).exists()
