"""المفضّلة — علامةٌ تعيش في القاعدة، لا في متصفّح.

الجملة التي تقرّر التصميم كلّه: **مفضّلة يراها العميل على الموقع ولا يجدها في
التطبيق عيبٌ في المنتج، لا مزامنةٌ ناقصة.** فالعلامة صفٌّ، والقناتان تقرآن
النقطة نفسها — وهذا ما تختبره أول حالة هنا.

وما عداها يختبر ثلاثة أشياء تُكسَر بصمت في ميزات «قائمة المتابعة»:

* **التكرار غير مؤذٍ.** ضغطتان على القلب ضغطةٌ واحدة، وإزالةُ ما ليس موجوداً
  ليست خطأً — وكلاهما ما ينتجه زرٌّ يُضغط مرتين وطلبٌ يُعاد.
* **العلامة ليست ادّعاءً.** لا تحجز مركبة، ولا تعطي أولوية، ولا ترى ما لا يُرى:
  مركبةٌ عُلّمت ثم سُحبت لا تظهر.
* **صفحةٌ واحدة باستعلامات ثابتة.** استعلامٌ لكل صفّ هو ما يحوّل قائمةً إلى
  صفحة بطيئة في الإنتاج بلا أن يلاحظ أحد.
"""

from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auctions import services as auction_services
from apps.auctions.cards import VEHICLE_CARD_FIELDS
from apps.auctions.favourites import Favourite, favourite_ids, mark, unmark
from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def other_customer(django_user_model):
    """Somebody else entirely — every ownership test needs one."""
    return django_user_model.objects.create_user(
        phone="966500000902", full_name="عميل آخر", password="x"
    )


def list_url() -> str:
    return reverse("auctions_api:favourite-list")


def mark_url(vehicle) -> str:
    return reverse("auctions_api:favourite-detail", args=[vehicle.pk])


@pytest.fixture
def car(auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2022,
        state=VehicleState.LISTED,
    )


@pytest.fixture
def other_car(auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=2,
        make="نيسان",
        model="التيما",
        year=2021,
        state=VehicleState.LISTED,
    )


# ---------------------------------------------------------------------------
# The reason the row exists at all
# ---------------------------------------------------------------------------


def test_the_mark_is_stored_on_the_server_so_both_channels_see_it(
    api_client, customer, car
):
    """The whole design brief in one test.

    Marked through one client, read back through another session entirely —
    which is what "the same customer on their phone" is. A favourite kept in
    `localStorage` passes no version of this.
    """
    api_client.force_authenticate(customer)
    assert api_client.put(mark_url(car)).status_code == 204

    other_device = APIClient()
    other_device.force_authenticate(customer)
    body = other_device.get(list_url()).json()

    assert body["total"] == 1
    assert body["results"][0]["id"] == car.pk


def test_the_list_is_rendered_by_the_one_card_builder(api_client, customer, car):
    """Same fields as every other list of vehicles, by construction.

    A favourites screen that assembled its own row would be the second card
    builder `ops/checks/one_vehicle_card.py` exists to refuse — and the field
    that went missing from it would be missing only here.
    """
    api_client.force_authenticate(customer)
    api_client.put(mark_url(car))

    card = api_client.get(list_url()).json()["results"][0]

    assert set(card) == set(VEHICLE_CARD_FIELDS)


# ---------------------------------------------------------------------------
# Repetition is harmless — both ways
# ---------------------------------------------------------------------------


def test_marking_twice_marks_once(api_client, customer, car):
    api_client.force_authenticate(customer)

    assert api_client.put(mark_url(car)).status_code == 204
    assert api_client.put(mark_url(car)).status_code == 204

    assert Favourite.objects.filter(user=customer, vehicle=car).count() == 1


def test_unmarking_something_unmarked_is_not_an_error(api_client, customer, car):
    """What a retried request produces. The customer's intent is satisfied."""
    api_client.force_authenticate(customer)

    assert api_client.delete(mark_url(car)).status_code == 204
    assert Favourite.objects.filter(user=customer).count() == 0


def test_marking_then_unmarking_leaves_nothing(api_client, customer, car):
    api_client.force_authenticate(customer)

    api_client.put(mark_url(car))
    api_client.delete(mark_url(car))

    assert api_client.get(list_url()).json()["total"] == 0


def test_a_race_between_two_taps_still_leaves_one_row(customer, car):
    """The uniqueness is the database's, not a read-then-write in the service.

    A check against a row that a second request is inserting at the same moment
    is not a check — so `mark` lets the unique index settle it and treats losing
    the race as success.
    """
    first = mark(user=customer, vehicle=car)
    second = mark(user=customer, vehicle=car)

    assert first.pk == second.pk
    assert Favourite.objects.filter(user=customer, vehicle=car).count() == 1


# ---------------------------------------------------------------------------
# A favourite is a bookmark, never a claim
# ---------------------------------------------------------------------------


def test_a_withdrawn_car_leaves_the_list(api_client, customer, car):
    """Marking does not grant sight of a row its owner may no longer show."""
    api_client.force_authenticate(customer)
    api_client.put(mark_url(car))
    assert api_client.get(list_url()).json()["total"] == 1

    # Withdrawn through the state machine, not by writing the column:
    # `auction_state_single_writer` refuses a second writer, and a test that
    # forced the value would be testing a state the machine may never produce.
    auction_services.move_vehicle(car, VehicleState.WITHDRAWN)

    assert api_client.get(list_url()).json()["total"] == 0


def test_a_withdrawn_car_can_still_be_unmarked(api_client, customer, car):
    """Otherwise the customer keeps a mark they can neither see nor remove."""
    api_client.force_authenticate(customer)
    api_client.put(mark_url(car))
    auction_services.move_vehicle(car, VehicleState.WITHDRAWN)

    assert api_client.delete(mark_url(car)).status_code == 204
    assert Favourite.objects.filter(user=customer).count() == 0


def test_one_customers_marks_are_not_anothers(api_client, customer, other_customer, car):
    api_client.force_authenticate(customer)
    api_client.put(mark_url(car))

    api_client.force_authenticate(other_customer)

    assert api_client.get(list_url()).json()["total"] == 0


def test_marking_needs_a_session(api_client, car):
    assert api_client.put(mark_url(car)).status_code in (401, 403)
    assert api_client.get(list_url()).status_code in (401, 403)


def test_marking_a_car_that_is_not_visible_is_a_404(api_client, customer, car):
    """A 403 would confirm the row exists, which is enough to enumerate an
    auction before it opens — the same reasoning as the vehicle detail view."""
    # Born a draft rather than pushed back into one: a draft is where a car
    # starts, and the state machine has no move that returns it there.
    hidden = Vehicle.objects.create(
        auction=car.auction,
        lot_number=99,
        make="مازدا",
        model="٦",
        year=2020,
        state=VehicleState.DRAFT,
    )
    api_client.force_authenticate(customer)

    assert api_client.put(mark_url(hidden)).status_code == 404


# ---------------------------------------------------------------------------
# Ordering and cost
# ---------------------------------------------------------------------------


def test_the_newest_mark_comes_first(api_client, customer, car, other_car):
    """This screen answers «ماذا حفظت؟», and the newest save is what is sought.

    Not lot order: the customer is not browsing an auction here, they are
    returning to something they set aside.
    """
    api_client.force_authenticate(customer)
    api_client.put(mark_url(car))
    api_client.put(mark_url(other_car))

    results = api_client.get(list_url()).json()["results"]

    assert [row["id"] for row in results] == [other_car.pk, car.pk]


def test_a_page_of_marks_costs_a_fixed_number_of_queries(
    api_client, customer, auction, django_assert_max_num_queries
):
    """A query per row is how a listing goes quietly from fast to slow.

    Twelve cars, and the count must not move with the number of them — the card
    queryset joins and prefetches exactly as it does for every other list.
    """
    cars = [
        Vehicle.objects.create(
            auction=auction,
            lot_number=number,
            make="تويوتا",
            model="كامري",
            year=2022,
            state=VehicleState.LISTED,
        )
        for number in range(10, 22)
    ]
    for vehicle in cars:
        mark(user=customer, vehicle=vehicle)

    api_client.force_authenticate(customer)

    with django_assert_max_num_queries(10):
        body = api_client.get(list_url()).json()

    assert body["total"] == 12


def test_favourite_ids_answers_a_whole_page_in_one_query(
    customer, car, other_car, django_assert_max_num_queries
):
    """Used to put a heart on a browse list without a query per card."""
    mark(user=customer, vehicle=car)

    with django_assert_max_num_queries(1):
        marked = favourite_ids(customer, [car, other_car])

    assert marked == {car.pk}


def test_an_anonymous_visitor_has_no_favourites_and_asking_is_not_an_error(car):
    """The browse pages are public and the same code renders for both."""
    from django.contrib.auth.models import AnonymousUser

    assert favourite_ids(AnonymousUser(), [car]) == set()
    assert favourite_ids(None, [car]) == set()


def test_unmark_accepts_an_id_without_loading_the_row(customer, car):
    mark(user=customer, vehicle=car)

    assert unmark(user=customer, vehicle_id=car.pk) is True
    assert unmark(user=customer, vehicle_id=car.pk) is False
