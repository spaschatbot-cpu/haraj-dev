"""T508–T511 — what an ending auction does to everybody's money.

The acceptance criteria are F4–F7, and F4 is the one this module exists for: a
bidder still competing on an unresolved car keeps their hold. In v1
``settleAuction`` released everyone who was not the top bid, so a bidder whose
only car was waiting on its owner's decision had their deposit released — and
when the owner accepted a day later, the platform had to ask for money that in
some cases had already been withdrawn.

`verify_ledger` is asserted clean after every scenario that moves money, because
a settlement that balances the buckets but not the ledger is the failure this
project's whole first phase was built to make impossible.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.money import services as money
from apps.money.models import (
    AccountKind,
    Hold,
    HoldReason,
    HoldState,
    Invoice,
    InvoiceSource,
)
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=900,
        title="مزاد التسوية",
        starts_at=now - timezone.timedelta(hours=2),
        # Still open while the bids are placed. Settlement is what happens when
        # it ends, and every test below arranges its bids first — a fixture that
        # started already closed would be testing the eligibility gate instead.
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


def ended(auction: Auction) -> Auction:
    """End ``auction`` through the state machine — cancelling goes via ending.

    Phase 005 refuses `live → cancelled` on purpose: deposits are held against
    a live auction and releasing them is settlement's job, not a state flip
    (`test_a_live_auction_cannot_be_cancelled`). So every cancellation test
    here ends the auction first, the way an operator would.
    """
    from apps.auctions import services as auctions

    Auction.objects.filter(pk=auction.pk).update(
        ends_at=timezone.now() - timezone.timedelta(minutes=1)
    )
    auction.refresh_from_db()
    return auctions.end(auction)


def a_car(auction: Auction, lot: int, reserve: str = "40000.00") -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal(reserve),
    )


def a_bidder(django_user_model, phone: str, funds: str | None = None):
    """A bidder who deposited **what the auction asks** — nothing more. HR-01ب.

    The default was ``"50000.00"`` against an auction asking ten thousand, so
    forty thousand stayed free after the bidding hold and every settlement test
    ran with a cushion no real bidder has. That cushion hid HR-01: a winner who
    deposited exactly the deposit had nothing free left, and invoicing raised
    rather than issuing. The fixture was green on a state that does not occur.

    A test that needs more says so, and says why — funds are an argument, not a
    default, so the exception is visible at the call site.
    """
    funds = funds or str(TEN_K)
    user = django_user_model.objects.create_user(
        phone=phone, full_name="مزايد", national_id=phone[-10:]
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(
        user=user, amount=Decimal(funds), source="cash", reference=f"seed/{phone}"
    )
    return user


def free_balance(user) -> Decimal:
    return money.account_for(user, AccountKind.INSURANCE_FREE).balance


def active_hold(user, auction) -> Hold | None:
    return Hold.objects.filter(
        owner=user, auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).first()


# ---------------------------------------------------------------------------
# Deciding one car — three endings, no fourth
# ---------------------------------------------------------------------------


def test_a_car_nobody_bid_on_is_rejected(auction):
    car = a_car(auction, 1)

    outcome = settlement.decide_vehicle(car)

    car.refresh_from_db()
    assert outcome.outcome == "rejected"
    assert car.state == VehicleState.REJECTED


def test_a_bid_at_or_above_the_reserve_wins(auction, django_user_model):
    car = a_car(auction, 1, reserve="40000.00")
    bidder = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("45000.00"))

    outcome = settlement.decide_vehicle(car)

    car.refresh_from_db()
    assert outcome.outcome == "awarded"
    assert car.state == VehicleState.AWARDED
    assert car.awarded_to_id == bidder.pk
    assert car.awarded_price == Decimal("45000.00")


def test_a_bid_below_the_reserve_goes_to_the_owner_not_to_the_bin(
    auction, django_user_model
):
    """A bid under the reserve is real money somebody offered."""
    car = a_car(auction, 1, reserve="60000.00")
    bidder = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("45000.00"))

    outcome = settlement.decide_vehicle(car)

    car.refresh_from_db()
    assert outcome.outcome == "awaiting_decision"
    assert car.state == VehicleState.AWAITING_DECISION


def test_the_highest_live_bid_wins_and_a_withdrawn_one_does_not(
    auction, django_user_model
):
    car = a_car(auction, 1)
    high = a_bidder(django_user_model, "966501111111")
    low = a_bidder(django_user_model, "966502222222")

    high_bid = bidding.place_bid(user=high, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=low, vehicle=car, amount=Decimal("50000.00"))
    bidding.withdraw_bid(user=high, bid=high_bid)

    outcome = settlement.decide_vehicle(car)

    assert outcome.winner_id == low.pk


# ---------------------------------------------------------------------------
# F4 — the rule v1 got wrong
# ---------------------------------------------------------------------------


def test_a_competitor_on_an_unresolved_car_keeps_their_hold(auction, django_user_model):
    """The acceptance criterion, and the whole reason this module is careful.

    One bidder, two cars: one resolves, the other goes to its owner. v1 would
    have released this deposit because the bidder was not the top bid on
    anything settled — and then asked for it back when the owner accepted.
    """
    resolved = a_car(auction, 1, reserve="40000.00")
    unresolved = a_car(auction, 2, reserve="90000.00")

    winner = a_bidder(django_user_model, "966501111111")
    hopeful = a_bidder(django_user_model, "966502222222")

    bidding.place_bid(user=winner, vehicle=resolved, amount=Decimal("45000.00"))
    bidding.place_bid(user=hopeful, vehicle=unresolved, amount=Decimal("50000.00"))

    report = settlement.settle_auction(auction)

    unresolved.refresh_from_db()
    assert unresolved.state == VehicleState.AWAITING_DECISION
    assert active_hold(hopeful, auction) is not None, "أُفرج عن حجز منافس"

    kept = {row.owner_id for row in report.kept}
    assert hopeful.pk in kept
    assert verify_ledger() == []


def test_a_loser_with_nothing_outstanding_gets_their_deposit_back(
    auction, django_user_model
):
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    loser = a_bidder(django_user_model, "966502222222")

    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=loser, vehicle=car, amount=Decimal("50000.00"))
    before = free_balance(loser)

    report = settlement.settle_auction(auction)

    assert active_hold(loser, auction) is None
    assert free_balance(loser) == before + TEN_K
    assert loser.pk in {row.owner_id for row in report.released}
    assert verify_ledger() == []


def test_a_winner_keeps_their_hold_until_the_invoice_exists(auction, django_user_model):
    """Releasing now and locking again on invoicing leaves a refundable window."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))

    settlement.settle_auction(auction)

    assert active_hold(winner, auction) is not None
    assert verify_ledger() == []


def test_a_withdrawn_bidder_is_not_a_competitor(auction, django_user_model):
    """Withdrawing is what withdrawing means."""
    car = a_car(auction, 1, reserve="90000.00")
    gone = a_bidder(django_user_model, "966501111111")
    bid = bidding.place_bid(user=gone, vehicle=car, amount=Decimal("50000.00"))
    bidding.withdraw_bid(user=gone, bid=bid)

    assert settlement.competitors_in(auction) == set()


def test_every_hold_is_reported_even_when_nothing_happened_to_it(
    auction, django_user_model
):
    """Support's question is "why is my deposit still held?", not "what changed?"."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))

    report = settlement.settle_auction(auction)

    assert len(report.holds) == 1
    assert report.holds[0].reason


# ---------------------------------------------------------------------------
# T509 — the award becomes an invoice, and the deposit follows it
# ---------------------------------------------------------------------------


def test_awarding_then_invoicing_locks_the_deposit_against_the_debt(
    auction, django_user_model
):
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()

    invoice = settlement.invoice_award(car)

    car.refresh_from_db()
    assert invoice.amount == Decimal("70000.00")
    assert invoice.vehicle_id == car.pk
    assert car.state == VehicleState.INVOICED
    # Pinned by the auction's own deposit, which names the auction and not the
    # invoice: one deposit answers every car this winner takes in this auction
    # (HR-01). What matters here is that the money is not free, and why.
    assert Hold.objects.filter(
        owner=winner,
        auction=auction,
        reason=HoldReason.DUES,
        state=HoldState.ACTIVE,
    ).exists()
    assert not Hold.objects.filter(owner=winner, invoice=invoice).exists()
    assert verify_ledger() == []


def test_the_database_refuses_a_second_invoice_for_one_car(auction, django_user_model):
    """F5. The guarantee is the constraint, not a Python check that races."""
    from django.db.utils import IntegrityError

    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)

    with pytest.raises(IntegrityError):
        Invoice.objects.create(
            customer=winner,
            number="duplicate",
            amount=Decimal("70000.00"),
            vehicle=car,
            issued_at=timezone.now(),
            source=InvoiceSource.LOCAL,
        )


def test_a_car_that_was_not_awarded_cannot_be_invoiced(auction):
    car = a_car(auction, 1)

    with pytest.raises(ValueError):
        settlement.invoice_award(car)


def test_a_winner_with_another_unresolved_car_keeps_the_auction_hold(
    auction, django_user_model
):
    """Invoicing one car must not free a deposit still doing its first job."""
    won = a_car(auction, 1, reserve="40000.00")
    pending = a_car(auction, 2, reserve="90000.00")
    winner = a_bidder(django_user_model, "966501111111")

    bidding.place_bid(user=winner, vehicle=won, amount=Decimal("45000.00"))
    bidding.place_bid(user=winner, vehicle=pending, amount=Decimal("50000.00"))
    settlement.settle_auction(auction)
    won.refresh_from_db()

    settlement.invoice_award(won)

    # Still there, and still this auction's — pledged against the invoice now,
    # while it also covers the bid on the car that has not been decided. One
    # deposit, both jobs.
    surviving = Hold.objects.filter(
        owner=winner, auction=auction, state=HoldState.ACTIVE
    ).first()
    assert surviving is not None, "أُفرج عن الوديعة ومركبة أخرى لم تُحسم"
    assert surviving.reason == HoldReason.DUES
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# Running it twice, and closing the auction
# ---------------------------------------------------------------------------


def test_settling_twice_changes_nothing_the_second_time(auction, django_user_model):
    """The caller is a task, and a task runs again when a worker dies."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    loser = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=loser, vehicle=car, amount=Decimal("50000.00"))

    settlement.settle_auction(auction)
    after_first = free_balance(loser)

    settlement.settle_auction(auction)

    assert free_balance(loser) == after_first
    assert verify_ledger() == []


def test_an_auction_with_an_unresolved_car_cannot_be_closed(auction, django_user_model):
    car = a_car(auction, 1, reserve="90000.00")
    bidder = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("50000.00"))
    settlement.settle_auction(auction)

    with pytest.raises(ValueError):
        settlement.close_auction(auction)


def test_an_auction_whose_cars_are_all_resolved_closes(auction, django_user_model):
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)

    from apps.auctions import services as auctions

    # The fixture is still open so the bids above could be placed. Ending is a
    # real transition with a real precondition, so move the clock rather than
    # write the state directly — a test that bypasses the state machine proves
    # nothing about the state machine.
    Auction.objects.filter(pk=auction.pk).update(
        ends_at=timezone.now() - timezone.timedelta(minutes=1)
    )
    auction.refresh_from_db()
    auctions.end(auction)
    settlement.close_auction(auction)

    auction.refresh_from_db()
    assert auction.state == AuctionState.SETTLED


# ---------------------------------------------------------------------------
# F7 — a whole auction, and the ledger after it
# ---------------------------------------------------------------------------


def test_a_full_auction_settles_and_the_ledger_stays_clean(auction, django_user_model):
    """Twenty bidders, ten cars, and every deposit either freed or kept by name."""
    cars = [a_car(auction, lot, reserve="40000.00") for lot in range(1, 11)]
    bidders = [a_bidder(django_user_model, f"96650{index:07d}") for index in range(1, 21)]

    for index, bidder in enumerate(bidders):
        car = cars[index % len(cars)]
        bidding.place_bid(
            user=bidder, vehicle=car, amount=Decimal("45000.00") + index * 100
        )

    report = settlement.settle_auction(auction)

    assert len(report.vehicles) == 10
    assert len(report.holds) == 20
    # Every hold is accounted for — no silent third category.
    assert len(report.released) + len(report.kept) == 20
    for row in report.holds:
        assert row.reason, f"حجز {row.hold_id} بلا سبب مكتوب"

    assert verify_ledger() == []


def test_nobody_loses_a_riyal_across_a_whole_settlement(auction, django_user_model):
    """The sum every customer holds is the sum they deposited, before and after."""
    cars = [a_car(auction, lot) for lot in range(1, 4)]
    bidders = [a_bidder(django_user_model, f"96651{index:07d}") for index in range(1, 7)]
    for index, bidder in enumerate(bidders):
        bidding.place_bid(
            user=bidder, vehicle=cars[index % 3], amount=Decimal("45000.00") + index
        )

    def total_for(user) -> Decimal:
        return sum(
            money.account_for(user, kind).balance
            for kind in (
                AccountKind.INSURANCE_FREE,
                AccountKind.INSURANCE_HELD,
                AccountKind.INSURANCE_LOCKED,
            )
        )

    before = {user.pk: total_for(user) for user in bidders}

    settlement.settle_auction(auction)

    for user in bidders:
        assert total_for(user) == before[user.pk], f"تغيّر إجمالي {user.pk}"
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# T510 — moving an award, money and all
# ---------------------------------------------------------------------------


def test_replacing_the_winner_moves_the_award_and_the_money(auction, django_user_model):
    """F6. Four effects, one transaction — v1 did this by hand in four screens."""
    car = a_car(auction, 1)
    first = a_bidder(django_user_model, "966501111111")
    second = a_bidder(django_user_model, "966502222222")

    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("65000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    first_invoice = settlement.invoice_award(car)
    car.refresh_from_db()

    settlement.replace_winner(car, new_winner=second, reason="الفائز الأول لم يسدّد")

    car.refresh_from_db()
    first_invoice.refresh_from_db()

    assert car.awarded_to_id == second.pk
    assert car.awarded_price == Decimal("65000.00")
    # Cancelled, never deleted: a month that showed an invoice which later
    # vanished is a month nobody can reconcile.
    assert first_invoice.state == "cancelled"
    assert verify_ledger() == []


def test_the_first_winner_is_left_owing_nothing(auction, django_user_model):
    """The v1 failure: a customer who never got a car carried a blocking debt."""
    car = a_car(auction, 1)
    first = a_bidder(django_user_model, "966501111111")
    second = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("65000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)
    car.refresh_from_db()

    settlement.replace_winner(car, new_winner=second, reason="تعذّر السداد")

    assert not Hold.objects.filter(owner=first, state=HoldState.ACTIVE).exists(), (
        "بقي تأمين الأول مرهوناً على فاتورة أُلغيت"
    )
    assert verify_ledger() == []


def test_the_new_winner_can_be_invoiced_after_the_replacement(auction, django_user_model):
    """The unique constraint must not treat the cancelled invoice as live."""
    car = a_car(auction, 1)
    first = a_bidder(django_user_model, "966501111111")
    second = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("65000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)
    car.refresh_from_db()
    settlement.replace_winner(car, new_winner=second, reason="تعذّر السداد")
    car.refresh_from_db()

    new_invoice = settlement.invoice_award(car)

    assert new_invoice.customer_id == second.pk
    assert new_invoice.amount == Decimal("65000.00")
    assert verify_ledger() == []


def test_replacing_a_winner_with_themselves_is_refused(auction, django_user_model):
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()

    with pytest.raises(ValueError):
        settlement.replace_winner(car, new_winner=winner, reason="لا شيء")


def test_replacing_with_somebody_who_never_bid_is_refused(auction, django_user_model):
    """Otherwise an operator's typo awards a car to a stranger at no price."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    outsider = a_bidder(django_user_model, "966503333333")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()

    with pytest.raises(ValueError):
        settlement.replace_winner(car, new_winner=outsider, reason="خطأ إدخال")


def test_a_car_with_no_award_cannot_have_its_winner_replaced(auction, django_user_model):
    car = a_car(auction, 1)
    somebody = a_bidder(django_user_model, "966501111111")

    with pytest.raises(ValueError):
        settlement.replace_winner(car, new_winner=somebody, reason="لا ترسية")


# ---------------------------------------------------------------------------
# T513 — the auction that should not have run
# ---------------------------------------------------------------------------


def test_cancelling_an_auction_frees_every_deposit(auction, django_user_model):
    """The acceptance criterion: after cancelling, no hold on this auction stands."""
    car = a_car(auction, 1)
    first = a_bidder(django_user_model, "966501111111")
    second = a_bidder(django_user_model, "966502222222")
    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("50000.00"))

    ended(auction)
    report = settlement.cancel_auction(auction, reason="حُمِّلت اللوتات الخطأ")

    assert not Hold.objects.filter(
        auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).exists()
    assert len(report["holds_released"]) == 2
    assert verify_ledger() == []


def test_cancelling_voids_an_unpaid_invoice_and_frees_its_lock(
    auction, django_user_model
):
    """Nobody owes us anything because of an event that did not happen."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    invoice = settlement.invoice_award(car)

    ended(auction)
    report = settlement.cancel_auction(auction, reason="سُحبت الشحنة")

    invoice.refresh_from_db()
    assert invoice.state == "cancelled"
    assert invoice.number in report["invoices_cancelled"]
    assert not Hold.objects.filter(invoice=invoice, state=HoldState.ACTIVE).exists()
    assert verify_ledger() == []


def test_a_paid_invoice_is_reported_not_silently_voided(auction, django_user_model):
    """Un-taking money somebody handed over is a refund, and a refund needs a human."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    invoice = settlement.invoice_award(car)
    money.record_payment(
        invoice=invoice,
        amount=Decimal("70000.00"),
        source="cash",
        reference="paid/1",
    )

    ended(auction)
    report = settlement.cancel_auction(auction, reason="تأجّل المزاد")

    invoice.refresh_from_db()
    assert invoice.state != "cancelled"
    assert invoice.number in report["invoices_left_paid"]
    assert verify_ledger() == []


def test_a_cancelled_auction_is_marked_cancelled(auction, django_user_model):
    a_car(auction, 1)

    ended(auction)
    settlement.cancel_auction(auction, reason="خطأ في التاريخ")

    auction.refresh_from_db()
    assert auction.state == AuctionState.CANCELLED


# ---------------------------------------------------------------------------
# T514 — an exclusion belongs to the cycle it happened in
# ---------------------------------------------------------------------------


def a_second_auction(number: int = 901) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=number,
        title="الدورة التالية",
        starts_at=now - timezone.timedelta(minutes=5),
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


def test_a_rejected_car_can_be_offered_again_in_a_new_cycle(auction, django_user_model):
    car = a_car(auction, 1)
    settlement.settle_auction(auction)
    car.refresh_from_db()
    assert car.state == VehicleState.REJECTED

    next_auction = a_second_auction()
    settlement.relist_vehicle(car, into=next_auction, lot_number=7)

    car.refresh_from_db()
    assert car.auction_id == next_auction.pk
    assert car.lot_number == 7
    assert car.state == VehicleState.LISTED


def test_the_previous_cycles_award_does_not_travel_with_the_car(
    auction, django_user_model
):
    """A car listed in April showing March's winner tells somebody they own it."""
    car = a_car(auction, 1)
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)
    car.refresh_from_db()
    # The award comes undone the way a real relist begins: the invoice is
    # voided and the car goes back on offer.
    ended(auction)
    settlement.cancel_auction(auction, reason="لم يُسدَّد")

    next_auction = a_second_auction()
    settlement.relist_vehicle(car, into=next_auction, lot_number=3)

    car.refresh_from_db()
    assert car.awarded_to_id is None
    assert car.awarded_price is None


def test_a_bidder_refused_in_one_cycle_is_not_refused_in_the_next(
    auction, django_user_model
):
    """T514's acceptance criterion, across two cycles.

    v1 stored the exclusion against the car, so a lot that failed once carried
    its history forever and the bidder who had been outbid could not see it
    listed again.
    """
    car = a_car(auction, 1)
    outbid = a_bidder(django_user_model, "966502222222")
    winner = a_bidder(django_user_model, "966501111111")
    bidding.place_bid(user=winner, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=outbid, vehicle=car, amount=Decimal("50000.00"))
    ended(auction)
    settlement.cancel_auction(auction, reason="أُلغيت الدورة")

    next_auction = a_second_auction()
    settlement.relist_vehicle(car, into=next_auction, lot_number=1)
    car.refresh_from_db()

    fresh = bidding.place_bid(user=outbid, vehicle=car, amount=Decimal("60000.00"))

    assert fresh.amount == Decimal("60000.00")
    assert verify_ledger() == []


def test_the_old_bids_stay_with_the_old_auction(auction, django_user_model):
    """They are the record of what happened in March, not a claim on April."""
    car = a_car(auction, 1)
    bidder = a_bidder(django_user_model, "966501111111")
    old_bid = bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("70000.00"))
    ended(auction)
    settlement.cancel_auction(auction, reason="أُلغيت")

    next_auction = a_second_auction()
    settlement.relist_vehicle(car, into=next_auction, lot_number=1)

    old_bid.refresh_from_db()
    assert old_bid.vehicle_id == car.pk
    assert settlement.competitors_in(auction) == set()


def test_a_car_cannot_be_relisted_into_the_auction_it_is_already_in(auction):
    car = a_car(auction, 1)

    with pytest.raises(ValueError):
        settlement.relist_vehicle(car, into=auction, lot_number=2)
