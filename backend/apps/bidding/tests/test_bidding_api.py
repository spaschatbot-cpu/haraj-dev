"""T610 and T611 — bidding over HTTP, and the meter on it.

The endpoints add no rule. Every refusal below is raised by
`apps.bidding.services` because `apps.bidding.eligibility` said so, and the
tests here check the two things only the HTTP edge can get wrong:

* the refusal reaches the customer as a **named code and an Arabic sentence**,
  not a 500 and not a generic "refused";
* the caller can only ever act on, and see, **their own** bids.

T506's two-step — a lower bid refused once, accepted when confirmed — is the
one behaviour with a shape of its own here, so it gets both halves tested.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.cache import caches
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import tokens as token_service
from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.money import services as money

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _empty_cache():
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture
def auction() -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=1,
        title="مزاد",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


@pytest.fixture
def vehicle(auction: Auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal("50000.00"),
    )


def a_bidder(phone: str, *, funded: bool = True) -> User:
    user = User.objects.create_user(phone=phone, full_name="مزايد")
    user.phone_verified_at = timezone.now()
    user.national_id = phone[-10:]
    user.save(update_fields=["phone_verified_at", "national_id"])
    if funded:
        money.deposit_insurance(
            user=user,
            amount=Decimal("20000.00"),
            source="cash",
            reference=f"seed:{phone}",
        )
    return user


def signed_in(user: User) -> APIClient:
    api = APIClient()
    pair = token_service.issue_pair(user)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return api


def place(api: APIClient, vehicle: Vehicle, amount: str, **extra):
    return api.post(
        reverse("bidding_api:place-bid", args=[vehicle.pk]),
        {"amount": amount, **extra},
        format="json",
    )


# ---------------------------------------------------------------------------
# Placing
# ---------------------------------------------------------------------------


def test_a_funded_bidder_places_a_bid(vehicle):
    api = signed_in(a_bidder("966501111111"))

    response = place(api, vehicle, "55000.00")

    assert response.status_code == 201
    assert response.data["amount"] == "55000.00"
    assert Bid.objects.live().count() == 1


def test_the_amount_comes_back_as_a_string(vehicle):
    """Article 3-2. `55000.50` read as a JSON number is already a float."""
    api = signed_in(a_bidder("966501111111"))

    response = place(api, vehicle, "55000.50")

    assert isinstance(response.data["amount"], str)
    assert response.data["amount"] == "55000.50"


@pytest.mark.parametrize(
    "amount",
    [
        pytest.param("1e5", id="scientific notation"),
        pytest.param("55_000", id="an underscore separator"),
        pytest.param("-100", id="a negative amount"),
        pytest.param("55000.555", id="more than two decimals"),
        pytest.param("abc", id="not a number at all"),
    ],
)
def test_an_amount_that_is_not_riyals_and_halalas_is_refused_by_name(vehicle, amount):
    """Refused as a field error before `Decimal` ever sees it."""
    api = signed_in(a_bidder("966501111111"))

    response = place(api, vehicle, amount)

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"


def test_an_unfunded_bidder_is_refused_with_the_reason_and_the_numbers(vehicle):
    """The refusal is an answer, in Arabic, with this customer's own figures."""
    api = signed_in(a_bidder("966502222222", funded=False))

    response = place(api, vehicle, "55000.00")

    assert response.status_code == 409
    error = response.data["error"]
    assert error["code"] != "bidding_error", "الرفض جاء عاماً بلا سبب مسمّى"
    assert error["message"]
    assert "required" in error["detail"]
    assert Bid.objects.count() == 0


def test_bidding_on_a_car_you_cannot_see_is_a_404(auction):
    """Same answer as a car that does not exist — so the endpoint is no probe."""
    hidden = Vehicle.objects.create(
        auction=auction,
        lot_number=2,
        make="نيسان",
        model="التيما",
        year=2021,
        state=VehicleState.DRAFT,
        reserve_price=Decimal("40000.00"),
    )
    api = signed_in(a_bidder("966501111111"))

    assert place(api, hidden, "55000.00").status_code == 404


def test_an_anonymous_caller_cannot_bid(vehicle):
    assert place(APIClient(), vehicle, "55000.00").status_code in (401, 403)


# ---------------------------------------------------------------------------
# T506 — lowering takes two steps
# ---------------------------------------------------------------------------


def test_lowering_is_refused_once_then_accepted_when_confirmed(vehicle):
    """Lowering is a real feature of a sealed auction, and also a fat finger."""
    api = signed_in(a_bidder("966501111111"))
    place(api, vehicle, "55000.00")

    refused = place(api, vehicle, "51000.00")

    assert refused.status_code == 409
    assert refused.data["error"]["code"] == "lower_needs_confirm"

    confirmed = place(api, vehicle, "51000.00", confirm_lower=True)

    assert confirmed.status_code == 201
    assert confirmed.data["amount"] == "51000.00"


def test_the_refused_lower_bid_changed_nothing(vehicle):
    api = signed_in(a_bidder("966501111111"))
    place(api, vehicle, "55000.00")

    place(api, vehicle, "51000.00")

    live = Bid.objects.live().get()
    assert live.amount == Decimal("55000.00")


# ---------------------------------------------------------------------------
# Withdrawing and listing — the caller's own, and nobody else's
# ---------------------------------------------------------------------------


def test_a_bidder_withdraws_their_own_bid(vehicle):
    api = signed_in(a_bidder("966501111111"))
    bid_id = place(api, vehicle, "55000.00").data["id"]

    response = api.post(reverse("bidding_api:withdraw-bid", args=[bid_id]))

    assert response.status_code == 200
    assert response.data["is_withdrawn"] is True
    # Marked, never deleted — the history stays whole (T507).
    assert Bid.objects.filter(pk=bid_id).exists()


def test_somebody_elses_bid_is_a_404_not_a_403(vehicle):
    """A 403 would confirm the bid exists, and its id is a small integer."""
    owner = signed_in(a_bidder("966501111111"))
    bid_id = place(owner, vehicle, "55000.00").data["id"]

    stranger = signed_in(a_bidder("966502222222"))
    response = stranger.post(reverse("bidding_api:withdraw-bid", args=[bid_id]))

    assert response.status_code == 404
    assert Bid.objects.get(pk=bid_id).is_withdrawn is False


def test_my_bids_lists_only_my_own(vehicle, auction):
    mine = signed_in(a_bidder("966501111111"))
    theirs = signed_in(a_bidder("966502222222"))
    other_car = Vehicle.objects.create(
        auction=auction,
        lot_number=2,
        make="فورد",
        model="تورس",
        year=2019,
        state=VehicleState.LISTED,
        reserve_price=Decimal("30000.00"),
    )
    place(mine, vehicle, "55000.00")
    place(theirs, other_car, "35000.00")

    page = mine.get(reverse("bidding_api:my-bids")).data

    assert page["total"] == 1
    assert page["results"][0]["vehicle_id"] == vehicle.pk


def test_a_revised_bid_shows_once_until_history_is_asked_for(vehicle):
    """Five revisions on one car are one live bid, not six rows on a screen."""
    api = signed_in(a_bidder("966501111111"))
    place(api, vehicle, "55000.00")
    place(api, vehicle, "60000.00")

    current = api.get(reverse("bidding_api:my-bids")).data
    everything = api.get(reverse("bidding_api:my-bids"), {"include_history": "true"}).data

    assert current["total"] == 1
    assert current["results"][0]["amount"] == "60000.00"
    assert everything["total"] == 2


def test_there_is_no_endpoint_that_lists_the_bids_on_a_car():
    """A sealed auction's whole property, checked as an absence.

    Not a permission somebody could relax later — no route exists at all.
    """
    from django.urls import NoReverseMatch

    with pytest.raises(NoReverseMatch):
        reverse("bidding_api:vehicle-bids", args=[1])


# ---------------------------------------------------------------------------
# T611 — the meter
# ---------------------------------------------------------------------------


def a_cache(location: str) -> dict:
    return {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": location,
        }
    }


@override_settings(
    BID_THROTTLE_RATES={"bid_caller": "3/hour"}, CACHES=a_cache("bid-limit")
)
def test_a_script_racing_the_close_is_metered(vehicle):
    api = signed_in(a_bidder("966501111111"))

    for amount in ("55000.00", "56000.00", "57000.00"):
        assert place(api, vehicle, amount).status_code == 201

    refused = place(api, vehicle, "58000.00")

    assert refused.status_code == 429
    assert refused.data["error"]["code"] == "throttled"


@override_settings(
    BID_THROTTLE_RATES={"bid_caller": "3/hour"}, CACHES=a_cache("bid-not-lost")
)
def test_the_bids_inside_the_limit_are_not_lost(vehicle):
    """T611's acceptance criterion: 429 without losing what was already placed."""
    api = signed_in(a_bidder("966501111111"))
    for amount in ("55000.00", "56000.00", "57000.00"):
        place(api, vehicle, amount)

    place(api, vehicle, "58000.00")

    live = Bid.objects.live().get()
    assert live.amount == Decimal("57000.00")


@override_settings(
    BID_THROTTLE_RATES={"bid_caller": "2/hour"}, CACHES=a_cache("bid-per-account")
)
def test_the_meter_is_per_account_not_shared(vehicle, auction):
    """Bidders share offices and share NAT; one must not exhaust another."""
    first = signed_in(a_bidder("966501111111"))
    second = signed_in(a_bidder("966502222222"))

    place(first, vehicle, "55000.00")
    place(first, vehicle, "56000.00")
    assert place(first, vehicle, "57000.00").status_code == 429

    assert place(second, vehicle, "58000.00").status_code == 201


def test_the_suite_runs_with_bidding_unmetered(settings):
    """Same decision as the OTP limits, asserted where it can be seen."""
    assert settings.BID_THROTTLE_RATES == {}


@override_settings(BID_THROTTLE_RATES={})
def test_a_deployed_environment_without_the_limit_is_flagged():
    from apps.bidding.checks import bidding_is_metered_in_a_deployed_environment

    findings = bidding_is_metered_in_a_deployed_environment(None)

    assert [finding.id for finding in findings] == ["bidding.W001"]
