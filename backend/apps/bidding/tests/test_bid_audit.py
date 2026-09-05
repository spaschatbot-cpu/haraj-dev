"""HR-07 — كل حركة على مزايدة تُكتب، وفي نفس المعاملة.

v1 لم يكن يستطيع الردّ على «أنا لم أخفض السعر» ولا على «المشرف عدّل عرضي»:
الصفّ يحمل المبلغ الأخير وحده، فالادّعاء والنفي متساويان في الدليل. وسجلّ
الإحلال عندنا يحفظ الصفّ القديم — لكنه لا يقول **من** فعلها، والشكوى عن
الفاعل لا عن الرقم.

و`AuditLog` مضاف-فقط بالبناء (`apps/core/models.py`): `save` على صفٍّ قائم
و`delete` كلاهما يرفض. فالمطلوب هنا أن تُكتب الحركة، لا أن يُبنى سجلٌّ جديد.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.core.models import AuditLog
from apps.money import services as money

pytestmark = pytest.mark.django_db

DEPOSIT = Decimal("10000.00")


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=8801,
        title="مزاد التدقيق",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=2),
        state=AuctionState.LIVE,
        deposit_required=DEPOSIT,
    )


@pytest.fixture
def car(auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2022,
        state=VehicleState.LISTED,
        reserve_price=Decimal("40000.00"),
    )


@pytest.fixture
def bidder(django_user_model):
    user = django_user_model.objects.create_user(
        phone="966581111111", full_name="مزايد", national_id="6581111111"
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(user=user, amount=DEPOSIT, source="cash", reference="audit/1")
    return user


def entries(action: str | None = None):
    rows = AuditLog.objects.filter(action__startswith="bidding.bid_").order_by("pk")
    return list(rows.filter(action=action) if action else rows)


def test_placing_a_bid_is_written(car, bidder):
    bid = bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))

    (row,) = entries("bidding.bid_placed")
    assert row.actor_id == bidder.pk
    assert row.entity_id == str(bid.pk)
    #: لا حال قبلها — وصفرٌ في مكان «لم يكن» ادّعاء.
    assert row.before is None
    assert row.after["amount"] == "41000.00"


def test_a_raise_and_a_downgrade_are_told_apart(car, bidder):
    """التمييز بالفعل لا بمقارنة رقمين عند القراءة — «كم خفضاً؟» سؤالٌ يُسأل."""
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("45000.00"))
    bidding.place_bid(
        user=bidder, vehicle=car, amount=Decimal("42000.00"), confirm_lower=True
    )

    assert [row.action for row in entries()] == [
        "bidding.bid_placed",
        "bidding.bid_raised",
        "bidding.bid_lowered",
    ]


def test_the_downgrade_carries_both_amounts(car, bidder):
    """الدليل في النزاع: ما كان، وما صار، ومن فعلها."""
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("49000.00"))
    bidding.place_bid(
        user=bidder, vehicle=car, amount=Decimal("40000.00"), confirm_lower=True
    )

    (row,) = entries("bidding.bid_lowered")

    assert row.before["amount"] == "49000.00"
    assert row.after["amount"] == "40000.00"
    assert row.actor_id == bidder.pk


def test_withdrawing_is_written_too(car, bidder):
    """السحب أكثر ما يُنازَع فيه: «لم أسحبها»."""
    bid = bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))

    bidding.withdraw_bid(user=bidder, bid=bid)

    (row,) = entries("bidding.bid_withdrawn")
    assert row.before["is_withdrawn"] is False
    assert row.after["is_withdrawn"] is True
    assert row.actor_id == bidder.pk


def test_a_refused_bid_writes_no_audit_row(car, django_user_model):
    """الرفض ليس حركةً على مزايدة — له سجلّه (`BidRefusal`) ولا يلوّث هذا."""
    broke = django_user_model.objects.create_user(
        phone="966582222222", full_name="بلا تأمين", national_id="6582222222"
    )
    broke.phone_verified_at = timezone.now()
    broke.save(update_fields=["phone_verified_at"])

    with pytest.raises(bidding.BidRefused):
        bidding.place_bid(user=broke, vehicle=car, amount=Decimal("41000.00"))

    assert entries() == []


def test_the_row_cannot_be_edited_or_deleted(car, bidder):
    """مضاف-فقط: سجلٌّ يمكن تعديله لا يثبت شيئاً عن الأثر الذي وُجد ليحميه."""
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))
    (row,) = entries("bidding.bid_placed")

    row.after = {"amount": "1.00"}
    with pytest.raises(Exception):
        row.save()

    with pytest.raises(Exception):
        row.delete()
