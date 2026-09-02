"""T807 — partner decisions, and the number the screen must not recompute.

Two v1 failures shape this file:

* **The screen showed the highest bid where the accepted offer belonged.** It
  recomputed the maximum on every render, so a car awarded to the second bidder
  displayed the first bidder's number — and that number went into the invoice
  conversation with a partner.
* **A cancelled invoice hid a car forever.** The exclusion was stored against
  the car rather than against the cycle it happened in, so a lot that failed to
  sell once never appeared again. The acceptance criterion names this case
  directly, and it is tested across two auctions.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.core.models import AuditLog
from apps.core.permissions import Role
from apps.money import services as money
from apps.money.verification import verify_ledger

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str = "966500000031") -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def decider(client):
    user = staff(Role.OPERATIONS)
    client.force_login(user)
    return user


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=990,
        title="مزاد الشركاء",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


def a_car(auction: Auction, lot: int, reserve: str = "80000.00", **extra) -> Vehicle:
    fields = {
        "auction": auction,
        "lot_number": lot,
        "make": "لكزس",
        "model": "ES",
        "year": 2021,
        "state": VehicleState.LISTED,
        "reserve_price": Decimal(reserve),
    }
    fields.update(extra)
    return Vehicle.objects.create(**fields)


def a_bidder(phone: str, name: str) -> User:
    user = User.objects.create_user(phone=phone, full_name=name)
    user.phone_verified_at = timezone.now()
    user.national_id = phone[-10:]
    user.save(update_fields=["phone_verified_at", "national_id"])
    money.deposit_insurance(
        user=user, amount=Decimal("60000.00"), source="cash", reference=f"seed/{phone}"
    )
    return user


@pytest.fixture
def waiting(auction) -> dict:
    """A car whose best bid is under the reserve — the case this screen exists for."""
    car = a_car(auction, 1, reserve="80000.00")
    first = a_bidder("966501111111", "أعلى مزايد")
    second = a_bidder("966502222222", "ثاني مزايد")

    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("65000.00"))
    settlement.decide_vehicle(car)
    car.refresh_from_db()

    return {"car": car, "first": first, "second": second}


def body_of(client, url) -> str:
    response = client.get(url)
    assert response.status_code == 200, f"{url} أجاب {response.status_code}"
    return response.content.decode()


# ---------------------------------------------------------------------------
# The list
# ---------------------------------------------------------------------------


def test_a_car_waiting_on_its_owner_is_on_the_list(client, decider, waiting):
    body = body_of(client, reverse("console:partner-decisions"))

    assert waiting["car"].state == VehicleState.AWAITING_DECISION
    assert "لكزس" in body


def test_a_car_nobody_is_waiting_on_is_not(client, decider, auction, waiting):
    a_car(auction, 2, make="تويوتا", state=VehicleState.LISTED)

    body = body_of(client, reverse("console:partner-decisions"))

    assert "تويوتا" not in body


def test_an_empty_list_says_so(client, decider, auction):
    body = body_of(client, reverse("console:partner-decisions"))

    assert "لا مركبة تنتظر قراراً" in body


def test_the_longest_wait_comes_first(client, decider, auction):
    """The question is "what has been sitting longest", and a lot number
    answers nothing about that."""
    old = a_car(auction, 9, state=VehicleState.AWAITING_DECISION)
    Vehicle.objects.filter(pk=old.pk).update(
        updated_at=timezone.now() - timezone.timedelta(days=3)
    )
    a_car(auction, 1, state=VehicleState.AWAITING_DECISION)

    body = body_of(client, reverse("console:partner-decisions"))

    # By the row's own link, not by a bare number: `>9<` also matches a year or
    # a count somewhere else on the page, and a test that passes on the wrong
    # match is a test that proves nothing about the ordering.
    assert body.index(reverse("console:partner-offers", args=[old.pk])) < body.index(
        reverse("console:partner-offers", args=[Vehicle.objects.get(lot_number=1).pk])
    )


# ---------------------------------------------------------------------------
# The offers — every bidder, and the accepted one read not recomputed
# ---------------------------------------------------------------------------


def test_every_bidder_is_shown_not_only_the_top_one(client, decider, waiting):
    """A partner refusing 70,000 wants to know what the second offer was."""
    body = body_of(client, reverse("console:partner-offers", args=[waiting["car"].pk]))

    assert "أعلى مزايد" in body
    assert "ثاني مزايد" in body
    assert "70000.00" in body
    assert "65000.00" in body


def test_an_unawarded_car_shows_no_accepted_offer(client, decider, waiting):
    """Putting the highest bid in that slot is exactly the v1 confusion."""
    body = body_of(client, reverse("console:partner-offers", args=[waiting["car"].pk]))

    assert "لم تُقبل بعد" in body


def test_the_accepted_offer_is_the_award_not_the_highest_bid(client, decider, waiting):
    """The v1 failure, stated exactly.

    The screen there recomputed the maximum on every render, so a car awarded to
    the second bidder displayed the first bidder's number — and that number went
    into the invoice conversation with a partner.
    """
    car, second = waiting["car"], waiting["second"]

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {
            "bid": car.bids.filter(bidder=second).get().pk,
            "reason": "المالك قبل العرض الثاني",
        },
    )

    car.refresh_from_db()
    body = body_of(client, reverse("console:partner-offers", args=[car.pk]))

    assert car.awarded_to_id == second.pk
    assert car.awarded_price == Decimal("65000.00")
    assert "65000.00 — ثاني مزايد" in body.replace("\n", " ").replace("  ", " ")


# ---------------------------------------------------------------------------
# Awarding
# ---------------------------------------------------------------------------


def test_the_partner_can_accept_the_second_offer(client, decider, waiting):
    """v1 could not record this at all.

    There an operator cancelled the auction and relisted the car, which cost
    every other bidder their place.
    """
    car, second = waiting["car"], waiting["second"]

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": car.bids.filter(bidder=second).get().pk, "reason": "قرار المالك"},
    )

    car.refresh_from_db()
    assert car.state == VehicleState.AWARDED
    assert car.awarded_to_id == second.pk
    assert verify_ledger() == []


def test_awarding_records_who_decided_and_why(client, decider, waiting):
    car, first = waiting["car"], waiting["first"]

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": car.bids.filter(bidder=first).get().pk, "reason": "المالك وافق"},
    )

    entry = AuditLog.objects.get(action="console.award_vehicle")
    assert entry.actor_id == decider.pk
    assert entry.note == "المالك وافق"
    assert entry.after["awarded_to_id"] == first.pk


def test_an_award_without_a_reason_is_refused(client, decider, waiting):
    car, first = waiting["car"], waiting["first"]

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": car.bids.filter(bidder=first).get().pk, "reason": "  "},
    )

    car.refresh_from_db()
    assert car.awarded_to_id is None


def test_a_withdrawn_bid_cannot_be_awarded(client, decider, waiting):
    """A partner's decision is still a decision about an offer that exists."""
    car, second = waiting["car"], waiting["second"]
    bid = car.bids.filter(bidder=second).get()
    bidding.withdraw_bid(user=second, bid=bid)

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": bid.pk, "reason": "محاولة"},
    )

    car.refresh_from_db()
    assert car.awarded_to_id is None


def test_moving_an_award_to_another_bidder_moves_the_money_with_it(
    client, decider, waiting
):
    """The second award goes through `replace_winner`, which cancels the first
    invoice and frees the first winner's lock in one transaction."""
    car, first, second = waiting["car"], waiting["first"], waiting["second"]

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": car.bids.filter(bidder=first).get().pk, "reason": "الأول"},
    )
    car.refresh_from_db()
    settlement.invoice_award(car)
    car.refresh_from_db()

    client.post(
        reverse("console:partner-award", args=[car.pk]),
        {"bid": car.bids.filter(bidder=second).get().pk, "reason": "الأول لم يسدّد"},
    )

    car.refresh_from_db()
    assert car.awarded_to_id == second.pk
    assert verify_ledger() == []


def test_a_get_does_not_award(client, decider, waiting):
    """An award reachable by a link is an award a crawler makes."""
    client.get(reverse("console:partner-award", args=[waiting["car"].pk]))

    waiting["car"].refresh_from_db()
    assert waiting["car"].awarded_to_id is None


# ---------------------------------------------------------------------------
# Rejecting — and the acceptance criterion about a later cycle
# ---------------------------------------------------------------------------


def test_the_partner_rejecting_is_recorded_as_rejected_not_withdrawn(
    client, decider, waiting
):
    """Two different facts with opposite next steps, and v1 lost the distinction."""
    car = waiting["car"]

    client.post(
        reverse("console:partner-reject", args=[car.pk]),
        {"reason": "المالك رفض السعر"},
    )

    car.refresh_from_db()
    assert car.state == VehicleState.REJECTED
    assert AuditLog.objects.filter(action="console.reject_vehicle").exists()


def test_a_rejected_car_returns_in_a_later_cycle(client, decider, waiting):
    """T807's acceptance criterion, across two cycles.

    v1 stored the exclusion against the car, so a lot that failed to sell once
    never appeared again — and the partner's stock quietly shrank.
    """
    car = waiting["car"]
    client.post(
        reverse("console:partner-reject", args=[car.pk]), {"reason": "رفض المالك"}
    )
    car.refresh_from_db()

    now = timezone.now()
    next_cycle = Auction.objects.create(
        number=991,
        title="الدورة التالية",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )
    settlement.relist_vehicle(car, into=next_cycle, lot_number=1)
    car.refresh_from_db()

    body = body_of(client, reverse("console:auction-detail", args=[next_cycle.pk]))

    assert car.state == VehicleState.LISTED
    assert car.auction_id == next_cycle.pk
    assert "لكزس" in body


def test_a_rejection_without_a_reason_is_refused(client, decider, waiting):
    client.post(
        reverse("console:partner-reject", args=[waiting["car"].pk]), {"reason": ""}
    )

    waiting["car"].refresh_from_db()
    assert waiting["car"].state == VehicleState.AWAITING_DECISION


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_reading_the_console_does_not_admit_you_to_a_partner_decision(client, waiting):
    """`partners.decide` is its own capability: choosing an offer commits money."""
    reader = staff(Role.SUPPORT, phone="966500000032")
    client.force_login(reader)
    car, first = waiting["car"], waiting["first"]

    assert client.get(reverse("console:partner-decisions")).status_code == 403
    assert (
        client.post(
            reverse("console:partner-award", args=[car.pk]),
            {"bid": car.bids.filter(bidder=first).get().pk, "reason": "محاولة"},
        ).status_code
        == 403
    )

    car.refresh_from_db()
    assert car.awarded_to_id is None


def test_a_partner_with_a_company_is_named_on_the_list(client, decider, auction):
    owner = User.objects.create_user(phone="966505555555", full_name="ممثل")
    company = Company.objects.create(user=owner, name="شركة الشريك")
    a_car(auction, 4, state=VehicleState.AWAITING_DECISION, owner_company=company)

    body = body_of(client, reverse("console:partner-decisions"))

    assert "شركة الشريك" in body
