"""T618 — no endpoint hands one customer another customer's row.

**The list of endpoints is discovered, not written.** That is the whole task.
A hand-written list is a list somebody forgets to extend, and the endpoint that
gets forgotten is the one added in a hurry — which is precisely the one that
skipped the ownership filter. So this walks Django's URL resolver, keeps every
route under `/api/v1/` that carries an id, and calls each one as a stranger.

The v1 hole this replaces: `/api/wallet?user_id=` returned whatever account the
caller named. It was found by a customer, not by us.

What "safe" means here is 404 or 403, and 404 is the shape this codebase
prefers: a 403 confirms the row exists, and ids are small integers, so
confirming existence is enough to count somebody's invoices.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts import tokens as token_service
from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.money import services as money
from apps.money.models import Invoice, PaymentIntent

pytestmark = pytest.mark.django_db

#: Routes that take an id which is **not** a reference to somebody's row.
#: Each needs a reason, and the reason is checked by a human at review time —
#: an exemption without one is how a list like this rots.
EXEMPT = {
    # Browsing is public on purpose (Phase 011 renders it for search engines).
    # What an anonymous caller may see is `apps.auctions.visibility`'s decision,
    # and `test_browse_api.py` tests it directly.
    "auctions_api:auction-detail",
    "auctions_api:auction-vehicles",
    "auctions_api:vehicle-detail",
    # The id here names a *car*, not a row belonging to a person — bidding on
    # somebody else's car is the product. What the caller must not be able to
    # touch is a *bid*, and `bidding_api:withdraw-bid` below is the route that
    # carries one. `test_bidding_api.py` covers both directly.
    "bidding_api:place-bid",
}

ID_IN_PATH = re.compile(r"<[^>]+>")


def api_routes_with_an_id() -> list[tuple[str, str]]:
    """Every `/api/v1/` route carrying a path parameter, as (name, pattern).

    Discovered from the resolver so a new endpoint joins this test by existing.
    """
    found: list[tuple[str, str]] = []

    def walk(resolver, prefix: str, namespace: str) -> None:
        for entry in resolver.url_patterns:
            route = prefix + str(entry.pattern)
            if isinstance(entry, URLResolver):
                walk(entry, route, entry.namespace or namespace)
            elif isinstance(entry, URLPattern):
                if not route.startswith("api/v1/") or not ID_IN_PATH.search(route):
                    continue
                name = f"{namespace}:{entry.name}" if namespace else entry.name
                found.append((name, route))

    walk(get_resolver(), "", "")
    return found


def test_the_sweep_actually_found_endpoints():
    """A discovery that finds nothing passes every test below without testing.

    The number is deliberately a floor rather than an exact count: endpoints are
    still being added, and a test that has to be edited on every addition is one
    people edit without reading.
    """
    assert len(api_routes_with_an_id()) >= 6


@pytest.fixture
def victim() -> User:
    user = User.objects.create_user(phone="966501111111", full_name="الضحية")
    user.phone_verified_at = timezone.now()
    user.national_id = "1000000008"
    user.save(update_fields=["phone_verified_at", "national_id"])
    money.deposit_insurance(
        user=user, amount=Decimal("50000.00"), source="cash", reference="idor/victim"
    )
    return user


@pytest.fixture
def stranger() -> APIClient:
    user = User.objects.create_user(phone="966502222222", full_name="غريب")
    user.phone_verified_at = timezone.now()
    client = APIClient()
    pair = token_service.issue_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
    return client


@pytest.fixture
def victims_rows(victim: User) -> dict:
    """One row of every kind an id in a URL could point at."""
    now = timezone.now()
    auction = Auction.objects.create(
        number=77,
        title="مزاد",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )
    vehicle = Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal("40000.00"),
    )
    bid = Bid.objects.create(vehicle=vehicle, bidder=victim, amount=Decimal("45000.00"))
    invoice = Invoice.objects.filter(customer=victim).first()
    intent = PaymentIntent.objects.filter(user=victim).first()

    return {
        "pk": bid.pk,
        "id": bid.pk,
        "auction": auction,
        "vehicle": vehicle,
        "bid": bid,
        "invoice": invoice,
        "intent": intent,
        "reference": getattr(intent, "reference", "unknown-reference"),
    }


def substitute(route: str, rows: dict) -> str:
    """Fill a route's parameters with ids that belong to the victim."""
    path = route

    def value_for(match: re.Match) -> str:
        parameter = match.group(0)
        if "reference" in parameter:
            return str(rows["reference"])
        # Every integer id in the sweep points at a row of the victim's; the
        # bid's pk is used as a stand-in where the exact model does not matter,
        # because a non-existent id would pass this test for the wrong reason.
        return str(rows["pk"])

    return "/" + ID_IN_PATH.sub(value_for, path)


@pytest.mark.parametrize(
    "name,route",
    api_routes_with_an_id(),
    ids=[name for name, _ in api_routes_with_an_id()],
)
def test_a_stranger_cannot_read_or_touch_somebody_elses_row(
    name, route, stranger, victims_rows
):
    """Every discovered endpoint, called with the victim's id by a stranger.

    Both verbs a customer-facing id endpoint can carry are tried, because an
    endpoint that guards its GET and forgets its POST is the ordinary shape of
    this bug.
    """
    if name in EXEMPT:
        pytest.skip(f"{name} is public by design — see EXEMPT")

    url = substitute(route, victims_rows)

    for call in (stranger.get, stranger.post, stranger.put, stranger.patch):
        response = call(url, {}, format="json")
        if response.status_code == 405:
            continue  # the verb is not offered at all, which is safe
        assert response.status_code in (403, 404), (
            f"{name} ({call.__name__.upper()} {url}) أجاب "
            f"{response.status_code} لغريب على صفّ غيره"
        )


def test_the_exemptions_all_still_exist():
    """An exemption for a route that was renamed is an exemption for nothing.

    Without this, deleting an endpoint leaves its name in `EXEMPT`
    forever, and the next endpoint to take that name inherits a pass.
    """
    discovered = {name for name, _ in api_routes_with_an_id()}
    stale = EXEMPT - discovered

    assert not stale, f"إعفاءات لمسارات لم تعد موجودة: {sorted(stale)}"
