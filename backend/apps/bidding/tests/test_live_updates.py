"""التحديث الحي — وأهمّ ما فيه أنه لا يحمل رقم أحدٍ غيرك.

الطلب كُتب «مزايدة تظهر خلال ثانيتين»، والقراءة البديهية له **خاطئة**: شريطُ
أسعار يعرض مزايدات الآخرين لحظةَ وضعها. وهذه المنصّة لا تملك واحداً، والسبب ليس
قصوراً بل هو المنتج نفسه —

    apps/bidding/api/views.py، أول فقرة:
    «لا نقطة تسرد المزايدات على مركبة. خاصيّةُ المزاد المغلق كلّها أن المزايدين
     لا يرون أرقام بعضهم.»

فبثٌّ حيٌّ لأرقام المنافسين كان سيهدم في نقطةٍ واحدة الخاصيّةَ التي بُنيت الفيز
006 كلها لحفظها — وسيفعل ذلك وهو يبدو استجابةً لطلب ميزة.

فأوّل اختبار هنا وأهمّها: **مزايدة منافس تُوضَع، ولا شيء منها يصل البثّ** — لا
المبلغ، ولا أنها حدثت. وما يصل شيئان: مزايدات المتصل نفسه، وحالاتٌ عامة يقرأها
أي متصفّح أصلاً.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from apps.auctions.models import Vehicle
from apps.auctions.states import VehicleState
from apps.bidding import live
from apps.bidding import services as bidding
from apps.money import services as money

pytestmark = pytest.mark.django_db


def payload(snapshot: live.Snapshot) -> dict:
    """The frame this snapshot would put on the wire, parsed back."""
    frame = snapshot.as_event()
    data_line = next(line for line in frame.splitlines() if line.startswith("data: "))
    return json.loads(data_line[len("data: ") :])


@pytest.fixture
def funded(customer, auction):
    money.deposit_insurance(
        user=customer, amount=Decimal("50000.00"), source="cash", reference="live/1"
    )
    customer.national_id = "1000000001"
    from django.utils import timezone

    customer.phone_verified_at = timezone.now()
    customer.save(update_fields=["national_id", "phone_verified_at"])
    return customer


@pytest.fixture
def rival(django_user_model, auction):
    from django.utils import timezone

    user = django_user_model.objects.create_user(
        phone="966500000801",
        full_name="منافس",
        password="x",
        national_id="1000000002",
        phone_verified_at=timezone.now(),
    )
    money.deposit_insurance(
        user=user, amount=Decimal("50000.00"), source="cash", reference="live/2"
    )
    return user


@pytest.fixture
def car(auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2022,
        reserve_price=Decimal("20000.00"),
        state=VehicleState.LISTED,
    )


# ---------------------------------------------------------------------------
# The one that matters
# ---------------------------------------------------------------------------


def test_a_rivals_bid_reaches_the_stream_in_no_form_at_all(funded, rival, car):
    """Not the amount. Not that it happened. Not a count.

    A live feed of competitors' numbers would demolish the sealed auction in one
    endpoint, while looking like a feature request being satisfied.
    """
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    bidding.place_bid(user=rival, vehicle=car, amount=Decimal("45000.00"))

    body = payload(live.snapshot_for(funded))
    text = json.dumps(body, ensure_ascii=False)

    assert "45000" not in text
    assert str(rival.pk) not in [str(row["id"]) for row in body["bids"]]
    assert len(body["bids"]) == 1
    assert body["bids"][0]["amount"] == "30000.00"


def test_a_rivals_bid_does_not_even_change_the_digest(funded, rival, car):
    """Because a change in the digest *is* a notification.

    A stream that emitted an empty frame whenever a rival bid would be telling
    the caller that somebody bid — which is the secret, minus the number.
    """
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    before = live.snapshot_for(funded).digest

    bidding.place_bid(user=rival, vehicle=car, amount=Decimal("45000.00"))

    assert live.snapshot_for(funded).digest == before


def test_no_winning_or_losing_field_anywhere(funded, rival, car):
    """The sealed auction's secret wearing a friendly name.

    «أنت الأعلى» is derived from other people's numbers, and it is the exact
    field a well-meaning ticket asks for.
    """
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    bidding.place_bid(user=rival, vehicle=car, amount=Decimal("45000.00"))

    text = json.dumps(payload(live.snapshot_for(funded)), ensure_ascii=False)

    for leak in ("winning", "is_highest", "rank", "position", "bid_count", "highest"):
        assert leak not in text


# ---------------------------------------------------------------------------
# What does cross
# ---------------------------------------------------------------------------


def test_the_callers_own_bid_appears(funded, car):
    """J6 read literally: bid on one device, see it on the other."""
    empty = live.snapshot_for(funded)
    assert empty.bids == []

    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.50"))
    after = live.snapshot_for(funded)

    assert after.digest != empty.digest
    assert after.bids[0]["amount"] == "30000.50"


def test_the_amount_crosses_as_a_string(funded, car):
    """Article 3-2 reaches the wire too."""
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.50"))

    body = payload(live.snapshot_for(funded))

    assert body["bids"][0]["amount"] == "30000.50"
    assert isinstance(body["bids"][0]["amount"], str)


def test_withdrawing_changes_the_picture(funded, car):
    bid = bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    before = live.snapshot_for(funded).digest

    bidding.withdraw_bid(user=funded, bid=bid)

    after = live.snapshot_for(funded)
    assert after.digest != before
    assert after.bids == []


def test_a_public_state_change_on_a_watched_car_crosses(funded, car):
    """Already readable by anybody browsing; sending it sooner tells nobody
    anything new — and it is what stops a customer bidding into a closed lot."""
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    before = live.snapshot_for(funded)
    assert before.vehicles[0]["state"] == VehicleState.BIDDING

    from apps.auctions import services as auction_services

    auction_services.move_vehicle(car, VehicleState.AWAITING_DECISION)

    after = live.snapshot_for(funded)
    assert after.digest != before.digest
    assert after.vehicles[0]["state"] == VehicleState.AWAITING_DECISION
    assert after.vehicles[0]["state_label"]


def test_a_car_the_caller_never_bid_on_is_absent(funded, car, auction):
    """The stream is about what this customer is in, not about the catalogue."""
    Vehicle.objects.create(
        auction=auction,
        lot_number=2,
        make="نيسان",
        model="التيما",
        year=2021,
        state=VehicleState.LISTED,
    )
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))

    body = payload(live.snapshot_for(funded))

    assert [row["id"] for row in body["vehicles"]] == [car.pk]


# ---------------------------------------------------------------------------
# The digest, and why it is a digest
# ---------------------------------------------------------------------------


def test_nothing_changing_produces_the_same_digest(funded, car):
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))

    assert live.snapshot_for(funded).digest == live.snapshot_for(funded).digest


def test_a_change_back_to_a_previous_value_still_registers(funded, car):
    """What a `max(updated_at)` cursor would miss.

    Withdraw and re-bid the same amount: to the customer that is two events, and
    a timestamp cursor would call the second one "nothing happened".
    """
    first = bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    with_bid = live.snapshot_for(funded).digest

    bidding.withdraw_bid(user=funded, bid=first)
    withdrawn = live.snapshot_for(funded).digest
    assert withdrawn != with_bid

    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))
    again = live.snapshot_for(funded).digest

    assert again != withdrawn


def test_one_customers_picture_is_not_anothers(funded, rival, car):
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))

    assert live.snapshot_for(funded).digest != live.snapshot_for(rival).digest


def test_the_snapshot_costs_a_fixed_number_of_queries(
    funded, auction, django_assert_max_num_queries
):
    """A stream re-derives on every tick, so the cost per tick is the design.

    It must not grow with how much the customer has bid on — that would make an
    active bidder the expensive one, which is backwards.
    """
    for lot in range(1, 6):
        vehicle = Vehicle.objects.create(
            auction=auction,
            lot_number=lot,
            make="تويوتا",
            model="كامري",
            year=2022,
            reserve_price=Decimal("20000.00"),
            state=VehicleState.LISTED,
        )
        bidding.place_bid(user=funded, vehicle=vehicle, amount=Decimal("30000.00"))

    with django_assert_max_num_queries(4):
        snapshot = live.snapshot_for(funded)

    assert len(snapshot.bids) == 5


# ---------------------------------------------------------------------------
# The frame on the wire
# ---------------------------------------------------------------------------


def test_the_frame_is_a_well_formed_sse_event(funded, car):
    bidding.place_bid(user=funded, vehicle=car, amount=Decimal("30000.00"))

    frame = live.snapshot_for(funded).as_event()

    assert frame.startswith("id: ")
    assert "\nevent: state\n" in frame
    assert frame.endswith("\n\n")


def test_the_endpoint_needs_a_session():
    from django.urls import reverse
    from rest_framework.test import APIClient

    response = APIClient().get(reverse("bidding_api:live-updates"))

    assert response.status_code in (401, 403)
