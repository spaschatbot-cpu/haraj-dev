"""T805 — the auction and vehicle screens, read rather than counted.

**I6 is meant literally.** In v1 a page shipped that rendered an empty list and
looked healthy by every check there was: `php -l` clean, md5 matching, status
302 — because 302 was the login redirect and said nothing about the page. The
owner found it, not the checks.

So every test here reads the body: the row that should be on the page is
asserted by its content, the row that should not be is asserted absent, and the
ordering that gives the screen its value is asserted as an ordering.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import StaffGrant, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.core.models import AuditLog
from apps.core.permissions import Capability, Role

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str = "966500000011") -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def operator(client):
    user = staff(Role.OPERATIONS)
    client.force_login(user)
    return user


@pytest.fixture
def live(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=501,
        title="مزاد الرياض",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=Decimal("10000.00"),
    )


@pytest.fixture
def draft(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=502,
        title="مسودّة جدة",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.DRAFT,
        deposit_required=Decimal("10000.00"),
    )


def a_car(auction: Auction, lot: int, **extra) -> Vehicle:
    fields = {
        "auction": auction,
        "lot_number": lot,
        "make": "تويوتا",
        "model": "كامري",
        "year": 2020,
        "state": VehicleState.LISTED,
        "reserve_price": Decimal("55000.00"),
    }
    fields.update(extra)
    return Vehicle.objects.create(**fields)


def body_of(client, url, **params) -> str:
    response = client.get(url, params)
    assert response.status_code == 200, f"{url} أجاب {response.status_code}"
    return response.content.decode()


# ---------------------------------------------------------------------------
# The auction list
# ---------------------------------------------------------------------------


def test_the_auction_list_shows_the_rows_not_merely_a_200(client, operator, live):
    a_car(live, 1)
    a_car(live, 2)

    body = body_of(client, reverse("console:auctions"))

    assert "مزاد الرياض" in body
    assert "501" in body
    # The counts, which is what an operator opens this page for.
    assert ">2<" in body.replace(" ", "").replace("\n", "")


def test_an_empty_list_says_so_instead_of_rendering_nothing(client, operator):
    """The v1 failure exactly: a page that renders an empty table and looks fine."""
    body = body_of(client, reverse("console:auctions"))

    assert "لا مزادات مطابقة" in body


def test_staff_see_the_draft_that_customers_do_not(client, operator, live, draft):
    body = body_of(client, reverse("console:auctions"))

    assert "مسودّة جدة" in body


def test_the_state_filter_narrows_the_page(client, operator, live, draft):
    body = body_of(client, reverse("console:auctions"), state=AuctionState.DRAFT)

    assert "مسودّة جدة" in body
    assert "مزاد الرياض" not in body


def test_searching_by_number_finds_one_auction(client, operator, live, draft):
    body = body_of(client, reverse("console:auctions"), q="502")

    assert "مسودّة جدة" in body
    assert "مزاد الرياض" not in body


def test_a_limit_beyond_the_ceiling_does_not_become_a_table_scan(client, operator, live):
    """An operator's session is not a reason to allow `?limit=100000`."""
    for lot in range(1, 6):
        a_car(live, lot)

    response = client.get(reverse("console:vehicles"), {"limit": 100000})

    assert response.status_code == 200
    assert response.context["page"].paginator.per_page <= 100


# ---------------------------------------------------------------------------
# The auction detail — what needs a decision comes first
# ---------------------------------------------------------------------------


def test_a_car_awaiting_its_owners_decision_is_listed_before_the_others(
    client, operator, live
):
    """The ordering *is* the screen's value.

    In v1 a car waiting on a decision sat in lot order on page four until
    somebody went looking — and nobody was being paid for it meanwhile.
    """
    a_car(live, 1)
    a_car(live, 2)
    waiting = a_car(live, 9, state=VehicleState.AWAITING_DECISION)

    body = body_of(client, reverse("console:auction-detail", args=[live.pk]))

    assert body.index(f">{waiting.lot_number}<") < body.index(">1<")


def test_the_auction_detail_shows_its_cars(client, operator, live):
    a_car(live, 1, make="نيسان", model="التيما")

    body = body_of(client, reverse("console:auction-detail", args=[live.pk]))

    assert "نيسان" in body
    assert "التيما" in body


def test_an_auction_with_no_cars_says_so(client, operator, live):
    body = body_of(client, reverse("console:auction-detail", args=[live.pk]))

    assert "لا مركبات في هذا المزاد" in body


# ---------------------------------------------------------------------------
# The vehicle list and detail
# ---------------------------------------------------------------------------


def test_the_vehicle_list_finds_a_car_by_make(client, operator, live):
    a_car(live, 1, make="تويوتا")
    a_car(live, 2, make="نيسان", model="التيما")

    body = body_of(client, reverse("console:vehicles"), q="نيسان")

    assert "التيما" in body
    assert "كامري" not in body


def test_the_vehicle_detail_reads_the_car_back(client, operator, live):
    car = a_car(live, 7, odometer_km=120000)

    body = body_of(client, reverse("console:vehicle-detail", args=[car.pk]))

    assert "120000" in body
    assert "55000.00" in body
    assert "مزاد الرياض" in body


def test_only_the_moves_the_state_machine_allows_are_offered(client, operator, live):
    """A button for a refused transition is a button that produces an error."""
    car = a_car(live, 1, state=VehicleState.LISTED)

    body = body_of(client, reverse("console:vehicle-detail", args=[car.pk]))

    assert "بدأت المزايدة عليها" in body
    # `listed → paid` does not exist, so it must not be offered.
    assert "سُدّدت الفاتورة" not in body


# ---------------------------------------------------------------------------
# The one write on these screens
# ---------------------------------------------------------------------------


def test_moving_a_car_records_who_did_it_and_why(client, operator, live):
    car = a_car(live, 1)

    client.post(
        reverse("console:vehicle-state", args=[car.pk]),
        {"target": VehicleState.WITHDRAWN, "reason": "الشريك سحبها"},
    )

    car.refresh_from_db()
    entry = AuditLog.objects.get(action="console.move_vehicle")

    assert car.state == VehicleState.WITHDRAWN
    assert entry.actor_id == operator.pk
    assert entry.note == "الشريك سحبها"
    assert entry.before["state"] == VehicleState.LISTED
    assert entry.after["state"] == VehicleState.WITHDRAWN


def test_a_move_without_a_reason_is_refused(client, operator, live):
    """A car that moved and nobody can say why is the row support cannot explain."""
    car = a_car(live, 1)

    client.post(
        reverse("console:vehicle-state", args=[car.pk]),
        {"target": VehicleState.WITHDRAWN, "reason": "   "},
    )

    car.refresh_from_db()
    assert car.state == VehicleState.LISTED
    assert not AuditLog.objects.filter(action="console.move_vehicle").exists()


def test_a_move_the_machine_refuses_shows_its_own_sentence(client, operator, live):
    """The state machine already says whether a move does not exist or is not
    ready yet, and rewording it here would lose the distinction."""
    car = a_car(live, 1, state=VehicleState.LISTED)

    response = client.post(
        reverse("console:vehicle-state", args=[car.pk]),
        {"target": VehicleState.PAID, "reason": "محاولة"},
        follow=True,
    )

    car.refresh_from_db()
    assert car.state == VehicleState.LISTED
    assert "لا يمكن نقل المركبة" in response.content.decode()


def test_a_get_on_the_state_endpoint_changes_nothing(client, operator, live):
    """A state change reachable by a link is a state change a crawler makes."""
    car = a_car(live, 1)

    client.get(reverse("console:vehicle-state", args=[car.pk]))

    car.refresh_from_db()
    assert car.state == VehicleState.LISTED


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_reading_the_screens_does_not_imply_changing_them(client, live):
    """`auctions.view` and `auctions.manage` are different trusts.

    v1 had one flag for both, so anybody who could check a date could cancel a
    lot.
    """
    reader = staff(Role.SUPPORT, phone="966500000012")
    client.force_login(reader)
    car = a_car(live, 1)

    assert client.get(reverse("console:auctions")).status_code == 200
    assert (
        client.post(
            reverse("console:vehicle-state", args=[car.pk]),
            {"target": VehicleState.WITHDRAWN, "reason": "محاولة"},
        ).status_code
        == 403
    )

    car.refresh_from_db()
    assert car.state == VehicleState.LISTED


def test_a_revoked_grant_closes_the_screens_immediately(client, operator, live):
    StaffGrant.objects.create(
        user=operator,
        capability=Capability.AUCTIONS_VIEW,
        granted=False,
        reason="تحت المراجعة",
    )

    assert client.get(reverse("console:auctions")).status_code == 403
