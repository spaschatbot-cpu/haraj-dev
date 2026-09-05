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


# ---------------------------------------------------------------------------
# Creating and editing — and the v1 lesson about how a save fails
# ---------------------------------------------------------------------------


def auction_payload(**extra) -> dict:
    fields = {
        "number": "777",
        "title": "مزاد جديد",
        "starts_at": "2026-10-01T10:00",
        "ends_at": "2026-10-02T10:00",
        "deposit_required": "10000.00",
        "reason": "مزاد الربع الأخير",
    }
    fields.update(extra)
    return fields


def vehicle_payload(auction: Auction, **extra) -> dict:
    fields = {
        "auction": auction.pk,
        "lot_number": "12",
        "make": "هوندا",
        "model": "أكورد",
        "year": "2021",
        "plate_type": "private",
        "transmission": "unknown",
        "fuel_type": "unknown",
        "condition": "unknown",
        "reserve_price": "42000.00",
        "reason": "وصلت من الشريك",
    }
    fields.update(extra)
    return fields


def test_an_auction_can_be_created_and_is_born_a_draft(client, operator):
    """The state is not a field: an auction reaches every other state through
    the service, whose guards refuse — among other things — scheduling one with
    no cars in it."""
    response = client.post(reverse("console:auction-new"), auction_payload(), follow=True)

    auction = Auction.objects.get(number=777)
    assert response.status_code == 200
    assert auction.state == AuctionState.DRAFT
    assert AuditLog.objects.filter(action="console.create_auction").exists()


def test_creating_records_who_did_it_and_why(client, operator):
    client.post(reverse("console:auction-new"), auction_payload())

    entry = AuditLog.objects.get(action="console.create_auction")

    assert entry.actor_id == operator.pk
    assert entry.note == "مزاد الربع الأخير"


def test_a_creation_without_a_reason_is_refused(client, operator):
    client.post(reverse("console:auction-new"), auction_payload(reason="  "))

    assert not Auction.objects.filter(number=777).exists()


def test_the_times_are_read_as_riyadh_wall_clocks(client, operator):
    """An operator typing 10:00 means 10:00 in Riyadh (Article 3-1)."""
    client.post(reverse("console:auction-new"), auction_payload())

    auction = Auction.objects.get(number=777)
    # 10:00 Riyadh is 07:00 UTC, and the stored value is UTC.
    assert auction.starts_at.hour == 7


def test_an_end_before_a_start_is_named_on_the_field(client, operator):
    """An operator fixing a date wants to know which box is wrong."""
    response = client.post(
        reverse("console:auction-new"),
        auction_payload(starts_at="2026-10-05T10:00", ends_at="2026-10-01T10:00"),
    )

    body = response.content.decode()
    assert "وقت الانتهاء لازم يكون بعد وقت البدء" in body
    assert not Auction.objects.filter(number=777).exists()


def test_a_duplicate_auction_number_is_a_message_not_a_500(client, operator, live):
    response = client.post(
        reverse("console:auction-new"), auction_payload(number=str(live.number))
    )

    assert response.status_code == 200
    assert "مستعمل" in response.content.decode()


def test_editing_an_auction_keeps_the_before_and_after(client, operator, live):
    client.post(
        reverse("console:auction-edit", args=[live.pk]),
        auction_payload(number=str(live.number), title="عنوان مصحَّح"),
    )

    live.refresh_from_db()
    entry = AuditLog.objects.get(action="console.edit_auction")

    assert live.title == "عنوان مصحَّح"
    assert entry.before["title"] == "مزاد الرياض"
    assert entry.after["title"] == "عنوان مصحَّح"


def test_one_bad_field_does_not_abort_the_whole_edit(client, operator, live):
    """The v1 failure, checked as a property of the form.

    Under `STRICT_TRANS_TABLES` v1 aborted the *entire* update when one value
    did not fit its column, so an operator correcting six fields lost all six
    because the seventh had a stray character — and the message named the
    statement, not the box.

    Here the bad field is named, nothing is written, and every good value the
    operator typed is still in the form waiting for them.
    """
    response = client.post(
        reverse("console:auction-edit", args=[live.pk]),
        auction_payload(number="ليس رقماً", title="عنوان مصحَّح"),
    )
    body = response.content.decode()

    live.refresh_from_db()
    assert live.title == "مزاد الرياض", "حُفظ جزء من التعديل رغم خطأ في حقل"
    assert "عنوان مصحَّح" in body, "ضاع ما كتبه المشغّل في الحقول السليمة"
    assert not AuditLog.objects.filter(action="console.edit_auction").exists()


def test_a_vehicle_can_be_created(client, operator, live):
    client.post(reverse("console:vehicle-new"), vehicle_payload(live), follow=True)

    vehicle = Vehicle.objects.get(auction=live, lot_number=12)
    assert vehicle.make == "هوندا"
    assert vehicle.state == VehicleState.DRAFT
    assert AuditLog.objects.filter(action="console.create_vehicle").exists()


def test_a_repeated_lot_number_is_a_sentence_beside_the_box(client, operator, live):
    """The database refuses it too (T405); this is so the operator sees why."""
    a_car(live, 12)

    response = client.post(reverse("console:vehicle-new"), vehicle_payload(live))

    assert response.status_code == 200
    assert "رقم اللوت مستعمل" in response.content.decode()


def test_a_repeated_vin_is_a_sentence_beside_the_box(client, operator, live):
    """HR-11 — الطريق الثالث إلى القيد نفسه، وهو الذي تُنسى فيه الشاشة.

    القيد `one_vin_per_auction` **جزئي** (`~Q(vin="")`)، وقيدٌ جزئي لا يظهر في
    PostgreSQL بوصفه `CONSTRAINT` بل فهرساً بشرط `WHERE`. فالسؤال الذي يجيبه
    هذا الاختبار ليس «هل القاعدة ترفض؟» — تلك يجيبها `test_vin_uniqueness.py`
    بـSQL خام — بل **هل يرى المشغّل جملةً بجانب الخانة أم صفحة ٥٠٠؟**

    وقراءة مصدر Django تقول إن `full_clean` يتحقّق من القيود الشرطية، لكن
    قراءةً لمصدر مكتبةٍ ليست تشغيلاً: التحقّق يُستثنى صامتاً إن كان أحد حقلَي
    القيد خارج النموذج، و`auction` قد يخرج منه غداً بقرارٍ لا علاقة له بهذا.
    """
    a_car(live, 7, vin="JT1234567890")

    response = client.post(
        reverse("console:vehicle-new"),
        vehicle_payload(live, vin="JT1234567890"),
    )

    assert response.status_code == 200, "المكرَّر انتهى إلى صفحة خطأ لا إلى الاستمارة"
    assert not Vehicle.objects.filter(lot_number=12).exists()


def test_editing_a_car_onto_its_neighbour_vin_is_refused_too(client, operator, live):
    """ولا يحتاج المشغّل صفّاً جديداً ليكرّر شاصياً: تكفي خانةٌ يعدّلها."""
    a_car(live, 7, vin="JT1234567890")
    other = a_car(live, 8, vin="JT0987654321")

    response = client.post(
        reverse("console:vehicle-edit", args=[other.pk]),
        vehicle_payload(live, lot_number="8", vin="JT1234567890"),
    )

    assert response.status_code == 200
    other.refresh_from_db()
    assert other.vin == "JT0987654321", "حُفظ شاصٍ مكرَّر"


def test_the_edit_form_offers_no_way_to_type_an_award(client, operator, live):
    """An award typed by hand is an award with no bid behind it.

    Correcting one is `replace_winner`, which moves the invoice and the deposit
    with it.
    """
    car = a_car(live, 3)

    body = body_of(client, reverse("console:vehicle-edit", args=[car.pk]))

    assert "awarded_to" not in body
    assert "awarded_price" not in body
    assert 'name="state"' not in body


def test_the_auction_form_offers_no_way_to_type_a_state(client, operator, live):
    body = body_of(client, reverse("console:auction-edit", args=[live.pk]))

    assert 'name="state"' not in body


def test_reading_the_screens_does_not_admit_you_to_the_forms(client, live):
    reader = staff(Role.SUPPORT, phone="966500000013")
    client.force_login(reader)

    assert client.get(reverse("console:auction-new")).status_code == 403
    assert (
        client.post(reverse("console:auction-new"), auction_payload()).status_code == 403
    )
    assert not Auction.objects.filter(number=777).exists()
