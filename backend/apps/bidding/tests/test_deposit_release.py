"""HR-04 — three endings for a deposit, and the middle one is the incident.

``PHASE_02`` §1-4 and ``PHASE_05`` §1-2, §2-3 give the table in three rows, not
two:

===============================  ==========================================
lost every car in the auction    released **at once** into ``free``
an offer still open on any car   **never released** — pending, or accepted
                                 with no invoice yet
won a car                        ``locked`` **the moment the invoice exists**
===============================  ==========================================

**The incident:** "in auctions 1004 and 1006 the deposits of more than **230
winners** were released by mistake before their invoices were issued, so they
spent them in later auctions and left their cars with no insurance cover."

Read that sentence again for what it actually says. The damage was not the
release — it was **spending**. A deposit that comes back into ``free`` is a
deposit the customer withdraws or bids with, and by the time the invoice is
written the money is in another auction. So a test that asserts a ``Hold`` row
still exists asserts the smaller half. Every "kept" row here is asserted
**unspendable**: nothing free, no refund, and refused at the next auction's
gate — which is what the 230 did and could not have done.

And the last test is the sequel that made 1004 expensive: the owner accepts a
day later. In v1 the deposit was gone by then. Here it is still where the bid
put it, and the invoice issues.

Every amount is production: the auction asks ten thousand and each bidder
deposited ten thousand, because a cushion is what hid HR-01 for a whole phase
(``HR-01ب``).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.bidding.eligibility import check_eligibility
from apps.bidding.models import RefusalReason
from apps.money import services as money
from apps.money.models import AccountKind, Hold, HoldReason, HoldState
from apps.money.services import InsufficientFunds
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db

DEPOSIT = Decimal("10000.00")
NOTHING = Decimal("0.00")


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=1004,  # the incident's own number
        title="مزاد الودائع",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=DEPOSIT,
    )


@pytest.fixture
def next_auction(db) -> Auction:
    """Where the 230 spent what they should not have had."""
    now = timezone.now()
    return Auction.objects.create(
        number=1006,
        title="المزاد التالي",
        starts_at=now - timezone.timedelta(minutes=30),
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=DEPOSIT,
    )


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


def a_bidder(django_user_model, phone: str):
    """Funded with **exactly** the deposit — no cushion (``HR-01ب``)."""
    user = django_user_model.objects.create_user(
        phone=phone, full_name="مزايد", national_id=phone[-10:]
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(
        user=user, amount=DEPOSIT, source="cash", reference=f"seed/{phone}"
    )
    return user


def buckets(user) -> dict[str, Decimal]:
    return {
        "free": money.account_for(user, AccountKind.INSURANCE_FREE).balance,
        "held": money.account_for(user, AccountKind.INSURANCE_HELD).balance,
        "locked": money.account_for(user, AccountKind.INSURANCE_LOCKED).balance,
    }


def bidding_hold(user, auction) -> Hold | None:
    return Hold.objects.filter(
        owner=user, auction=auction, reason=HoldReason.BIDDING, state=HoldState.ACTIVE
    ).first()


def cannot_spend_it(user, next_auction: Auction) -> None:
    """The assertion the incident is actually about.

    Three ways the 230 got at their money, all refused: it is not in ``free``,
    it cannot be withdrawn, and it does not open the next auction's gate. Any
    one of these passing alone would leave the other two as the hole.
    """
    assert buckets(user)["free"] == NOTHING, "عاد التأمين إلى الحرّ فصار قابلاً للصرف"

    with pytest.raises(InsufficientFunds):
        money.request_refund(user=user, amount=DEPOSIT)

    car_next_door = a_car(next_auction, 1)
    verdict = check_eligibility(user, car_next_door, amount=Decimal("45000.00"))

    assert not verdict.allowed
    assert verdict.reason == RefusalReason.NO_DEPOSIT


# ---------------------------------------------------------------------------
# The three rows of the table, in one settlement
# ---------------------------------------------------------------------------


@pytest.fixture
def settled(auction, django_user_model):
    """One auction, one bidder per row of the table, settled once.

    Three separate settlements would be three separate stories; the incident
    was one run of one job over a mixed field, and the middle row is only
    interesting when the other two are in the same report.
    """
    lost = a_car(auction, 1, reserve="40000.00")
    undecided = a_car(auction, 2, reserve="90000.00")
    won = a_car(auction, 3, reserve="40000.00")

    loser = a_bidder(django_user_model, "966501111101")
    top = a_bidder(django_user_model, "966501111102")
    hopeful = a_bidder(django_user_model, "966501111103")
    winner = a_bidder(django_user_model, "966501111104")

    bidding.place_bid(user=loser, vehicle=lost, amount=Decimal("41000.00"))
    bidding.place_bid(user=top, vehicle=lost, amount=Decimal("45000.00"))
    #: Below the reserve — so the car goes to its owner to decide, and this
    #: bidder is the middle row: neither won nor lost.
    bidding.place_bid(user=hopeful, vehicle=undecided, amount=Decimal("50000.00"))
    bidding.place_bid(user=winner, vehicle=won, amount=Decimal("70000.00"))

    report = settlement.settle_auction(auction)

    return {
        "report": report,
        "loser": loser,
        "hopeful": hopeful,
        "winner": winner,
        "undecided": undecided,
        "won": won,
    }


def test_a_bidder_who_lost_everything_gets_it_back_at_once(settled, auction):
    """Row one. Nothing is outstanding, so nothing is held."""
    loser = settled["loser"]

    assert bidding_hold(loser, auction) is None
    assert buckets(loser) == {"free": DEPOSIT, "held": NOTHING, "locked": NOTHING}
    assert loser.pk in {row.owner_id for row in settled["report"].released}
    assert verify_ledger() == []


def test_a_bidder_whose_offer_is_still_open_keeps_it_and_cannot_spend_it(
    settled, auction, next_auction
):
    """Row two — the incident. Pending is neither won nor lost.

    v1 released this deposit because the bidder was not the top bid on anything
    that settled. The owner then accepted, and the platform had to ask for
    money that in some cases had already gone.
    """
    hopeful = settled["hopeful"]
    settled["undecided"].refresh_from_db()

    assert settled["undecided"].state == VehicleState.AWAITING_DECISION
    assert bidding_hold(hopeful, auction) is not None, "أُفرج عن وديعة عرضٍ معلّق"
    assert buckets(hopeful) == {"free": NOTHING, "held": DEPOSIT, "locked": NOTHING}
    assert hopeful.pk in {row.owner_id for row in settled["report"].kept}

    cannot_spend_it(hopeful, next_auction)
    assert verify_ledger() == []


def test_a_winner_awaiting_their_invoice_keeps_it_and_cannot_spend_it(
    settled, auction, next_auction
):
    """Row two again, its other half: **accepted with no invoice yet**.

    This is the half the incident names — "released before their invoices were
    issued". Between the award and the invoice there is no debt row to lock
    against, and that gap is exactly where 230 deposits left.
    """
    winner = settled["winner"]
    settled["won"].refresh_from_db()

    assert settled["won"].state == VehicleState.AWARDED
    assert bidding_hold(winner, auction) is not None, "أُفرج عن وديعة فائزٍ بلا فاتورة"
    assert buckets(winner) == {"free": NOTHING, "held": DEPOSIT, "locked": NOTHING}

    cannot_spend_it(winner, next_auction)
    assert verify_ledger() == []


def test_the_invoice_locks_it_rather_than_returning_it(settled, auction):
    """Row three. The deposit moves across into ``locked``, **in place**.

    Asserted on the row's identity, not only on the buckets. Releasing on
    settlement and locking again on invoicing arrives at the same three
    balances by a different route — through ``free``, where a refund or a bid
    in the next auction can take it. That route is the incident restated as a
    design, and the end balances cannot tell the two apart. The hold's primary
    key can.
    """
    winner = settled["winner"]
    settled["won"].refresh_from_db()
    pledged = bidding_hold(winner, auction)
    assert pledged is not None

    invoice = settlement.invoice_award(settled["won"])

    assert invoice.amount > NOTHING
    assert buckets(winner) == {"free": NOTHING, "held": NOTHING, "locked": DEPOSIT}

    pledged.refresh_from_db()
    assert pledged.state == HoldState.ACTIVE, "أُفرج عن الحجز ثم أُنشئ غيره"
    assert pledged.reason == HoldReason.DUES, "الحجز نفسه لم يتحوّل إلى مستحقات"
    assert (
        Hold.objects.filter(owner=winner, auction=auction, state=HoldState.ACTIVE).count()
        == 1
    )
    assert verify_ledger() == []


def test_every_deposit_is_accounted_for_in_the_report(settled):
    """No fourth ending, and no bidder without a row.

    Support's question is "why is mine still held?", and a bidder missing from
    the report is a question nobody can answer.
    """
    report = settled["report"]
    reported = {row.owner_id for row in report.kept} | {
        row.owner_id for row in report.released
    }
    holders = set(
        Hold.objects.filter(reason=HoldReason.BIDDING).values_list("owner_id", flat=True)
    )

    assert reported == holders
    assert all(row.reason for row in report.kept), "صفٌّ مُبقًى بلا سبب مكتوب"


# ---------------------------------------------------------------------------
# The sequel that made 1004 expensive
# ---------------------------------------------------------------------------


def test_the_owner_accepting_a_day_later_still_finds_the_deposit(
    settled, django_user_model
):
    """The whole point of not releasing it.

    In v1 the acceptance arrived after the release, so the invoice was raised
    against a customer whose insurance had already gone into another auction.
    Here the deposit is still where the bid put it, so the acceptance turns
    into an invoice with nothing to chase.
    """
    hopeful = settled["hopeful"]
    undecided = settled["undecided"]
    undecided.refresh_from_db()

    #: The state the acceptance arrives into, and the reason it is safe. Read
    #: **before** the award: afterwards the balances are the same whether the
    #: deposit waited in `held` or was released and re-taken from `free`, and
    #: it is the waiting that this test is about. Without this line the test
    #: passes with the rule removed, and a test that cannot fail is decoration.
    waiting = bidding_hold(hopeful, settled["undecided"].auction)
    assert waiting is not None, "لم تكن الوديعة محجوزة أصلاً حين وصل القبول"
    assert buckets(hopeful)["held"] == DEPOSIT

    settlement.award_to(undecided, bidder=hopeful, price=Decimal("50000.00"))
    undecided.refresh_from_db()
    invoice = settlement.invoice_award(undecided)

    assert invoice.customer_id == hopeful.pk
    assert buckets(hopeful) == {"free": NOTHING, "held": NOTHING, "locked": DEPOSIT}
    waiting.refresh_from_db()
    assert waiting.state == HoldState.ACTIVE, "لم تكن الفاتورة على الوديعة نفسها"
    assert verify_ledger() == []
