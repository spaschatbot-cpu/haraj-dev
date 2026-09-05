"""HR-14 — the v1 partner attack fails here, proven four ways.

v1's incident, twice over: a partner typed an invoice link or a customer's
phone number into the browser and reached it, and sent an acceptance on a car
that was not theirs with a direct POST. In v2 there is no `company` role and
no `/partner` gate to contain — so this file does not test a containment that
does not exist. It proves the attack itself fails, on the four partner
endpoints, against the four kinds of caller:

* anonymous — sent to sign-in, and the test names *where*, not just 302;
* an authenticated non-staff customer (a company owner: the v1 actor) — 403;
* staff without `partners.decide` — 403;
* staff with it — through, and the decision lands (a guard that refuses
  everyone is indistinguishable from a broken one).

The forged POST uses a **live bid on another company's car** — exactly the v1
shape, not a random id.
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


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


def company_owner(phone: str, person: str, company: str) -> User:
    """The v1 actor, as v2 models them: a customer who owns a company.

    Not staff, so the console owes them nothing — which is the assertion.
    """
    user = User.objects.create_user(phone=phone, full_name=person)
    Company.objects.create(user=user, name=company)
    return user


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=980,
        title="مزاد الاحتواء",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


def a_car(auction: Auction, lot: int, company: Company) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="لكزس",
        model="ES",
        year=2021,
        state=VehicleState.LISTED,
        reserve_price=Decimal("80000.00"),
        owner_company=company,
    )


def a_bidder(phone: str, name: str) -> User:
    user = User.objects.create_user(phone=phone, full_name=name)
    user.phone_verified_at = timezone.now()
    user.national_id = phone[-10:]
    user.save(update_fields=["phone_verified_at", "national_id"])
    money.deposit_insurance(
        user=user, amount=Decimal("10000.00"), source="cash", reference=f"seed/{phone}"
    )
    return user


@pytest.fixture
def two_companies(db) -> dict:
    """Two partners, one car of the second with live bids awaiting decision."""
    attacker = company_owner("966503333331", "شريك أ", "شركة أ")
    owner_b = company_owner("966503333332", "ممثل ب", "شركة ب")
    company_b = owner_b.company
    return {"attacker": attacker, "company_b": company_b}


@pytest.fixture
def foreign_car(auction, two_companies) -> dict:
    """Company B's car, with live bids, waiting on a decision — the v1 target."""
    car = a_car(auction, 1, two_companies["company_b"])
    first = a_bidder("966503333333", "مزايد أول")
    second = a_bidder("966503333334", "مزايد ثان")

    bidding.place_bid(user=first, vehicle=car, amount=Decimal("70000.00"))
    bidding.place_bid(user=second, vehicle=car, amount=Decimal("65000.00"))
    settlement.decide_vehicle(car)
    car.refresh_from_db()

    assert car.state == VehicleState.AWAITING_DECISION
    return {"car": car, "live_bid": car.bids.filter(bidder=first).get()}


def endpoints(car_pk: int) -> dict:
    return {
        "decisions": reverse("console:partner-decisions"),
        "offers": reverse("console:partner-offers", args=[car_pk]),
        "award": reverse("console:partner-award", args=[car_pk]),
        "reject": reverse("console:partner-reject", args=[car_pk]),
    }


AWARD_FORM = {"reason": "قرار"}


def test_anonymous_is_sent_to_sign_in_on_all_four(client, foreign_car) -> None:
    """The T821 lesson: assert *where*, not just 302 — a redirect to a 404
    once passed a test that only checked the status."""
    urls = endpoints(foreign_car["car"].pk)
    sign_in = reverse("admin-login")

    assert sign_in in client.get(urls["decisions"])["Location"]
    assert sign_in in client.get(urls["offers"])["Location"]
    assert sign_in in client.post(urls["award"], AWARD_FORM)["Location"]
    assert sign_in in client.post(urls["reject"], AWARD_FORM)["Location"]

    foreign_car["car"].refresh_from_db()
    assert foreign_car["car"].awarded_to_id is None
    assert foreign_car["car"].state == VehicleState.AWAITING_DECISION


def test_a_company_owner_is_refused_on_all_four(client, foreign_car, two_companies) -> None:
    """The v1 actor, typing links and posting directly: 403 four times, and
    nothing moves."""
    client.force_login(two_companies["attacker"])
    urls = endpoints(foreign_car["car"].pk)
    car = foreign_car["car"]

    assert client.get(urls["decisions"]).status_code == 403
    assert client.get(urls["offers"]).status_code == 403
    assert (
        client.post(
            urls["award"],
            {"bid": foreign_car["live_bid"].pk, "reason": "أقبلها"},
        ).status_code
        == 403
    )
    assert client.post(urls["reject"], {"reason": "أرفضها"}).status_code == 403

    car.refresh_from_db()
    assert car.awarded_to_id is None
    assert car.state == VehicleState.AWAITING_DECISION
    assert not AuditLog.objects.filter(action__startswith="console.").exists()
    assert verify_ledger() == []


def test_staff_without_the_capability_is_refused_on_all_four(
    client, foreign_car
) -> None:
    reader = staff(Role.SUPPORT, phone="966503333335")
    client.force_login(reader)
    urls = endpoints(foreign_car["car"].pk)

    assert client.get(urls["decisions"]).status_code == 403
    assert client.get(urls["offers"]).status_code == 403
    assert client.post(urls["award"], AWARD_FORM).status_code == 403
    assert client.post(urls["reject"], AWARD_FORM).status_code == 403

    foreign_car["car"].refresh_from_db()
    assert foreign_car["car"].awarded_to_id is None


def test_staff_with_the_capability_passes_and_the_decision_lands(
    client, foreign_car
) -> None:
    """The gate opens for the right key: reads answer 200, and the award is
    executed, not merely admitted."""
    decider = staff(Role.OPERATIONS, phone="966503333336")
    client.force_login(decider)
    urls = endpoints(foreign_car["car"].pk)
    car = foreign_car["car"]

    assert client.get(urls["decisions"]).status_code == 200
    assert client.get(urls["offers"]).status_code == 200

    response = client.post(
        urls["award"],
        {"bid": foreign_car["live_bid"].pk, "reason": "المالك وافق"},
    )

    assert response.status_code == 302
    car.refresh_from_db()
    assert car.awarded_to_id == foreign_car["live_bid"].bidder_id
    entry = AuditLog.objects.get(action="console.award_vehicle")
    assert entry.actor_id == decider.pk
    assert verify_ledger() == []


def test_a_forged_rejection_of_another_companys_car_changes_nothing(
    client, foreign_car, two_companies
) -> None:
    client.force_login(two_companies["attacker"])
    car = foreign_car["car"]

    response = client.post(
        reverse("console:partner-reject", args=[car.pk]), {"reason": "ليست لي"}
    )

    assert response.status_code == 403
    car.refresh_from_db()
    assert car.state == VehicleState.AWAITING_DECISION
    assert not AuditLog.objects.filter(action="console.reject_vehicle").exists()
