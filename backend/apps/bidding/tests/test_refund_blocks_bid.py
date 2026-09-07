"""ف1 — طلبُ استردادٍ قائم يمنع المزايدة بالوديعة نفسها.

**الخصم مؤجَّل، وتلك هي الفجوة.** طلبُ الاسترداد لا يحرّك الدفتر: المال يبقى
في ``insurance_free`` حتى تؤكّد المحاسبة الصرف. فبين اللحظتين كانت العشرة آلاف
نفسها تُحجَز لمزادٍ **ثم** تُصرَف استرداداً — خرج المال مرتين على وديعةٍ واحدة.

وهي حادثة v1 بالحرف (``PENDING_REFUND_BLOCKS_BID``): «بوابة المزايدة تمنع
استعمال وديعة عليها طلب قائم، وإلا خرج المال مرتين».

**والمنع بالمبلغ لا بوجود الطلب.** من طلب عشرة آلاف وله ثلاثون يزايد
بالعشرين الباقية — والمنع الكامل عقوبةٌ على من لم يفعل شيئاً.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding.eligibility import check_eligibility, money_snapshot
from apps.bidding.models import RefusalReason
from apps.money import services as money
from apps.money.models import AccountKind, RefundRequestState

pytestmark = pytest.mark.django_db

DEPOSIT = Decimal("10000.00")


@pytest.fixture
def auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=7701,
        title="مزاد الاسترداد",
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


def a_bidder(django_user_model, phone: str, funds: Decimal = DEPOSIT):
    user = django_user_model.objects.create_user(
        phone=phone, full_name="مزايد", national_id=phone[-10:]
    )
    user.phone_verified_at = timezone.now()
    user.save(update_fields=["phone_verified_at"])
    money.deposit_insurance(
        user=user, amount=funds, source="cash", reference=f"seed/{phone}"
    )
    return user


def test_an_open_refund_holds_the_deposit_out_of_reach(car, django_user_model):
    """العطل نفسه: الوديعة في الدفتر، ومطلوبةٌ للخروج، فلا تُحجز لمزاد."""
    bidder = a_bidder(django_user_model, "966571111111")
    money.request_refund(user=bidder, amount=DEPOSIT, client_key="r1")

    verdict = check_eligibility(user=bidder, vehicle=car, amount=Decimal("41000.00"))

    assert not verdict.allowed
    assert verdict.reason == RefusalReason.REFUND_PENDING
    #: الرقمان معاً في الرسالة: ما في الدفتر، وما تبقّى للإنفاق.
    assert "10000.00" in verdict.detail
    #: والدفتر لم يتحرّك — الخصم مؤجَّل، وهذا ما يجعل المنع لازماً.
    assert money.account_for(bidder, AccountKind.INSURANCE_FREE).balance == DEPOSIT


def test_the_bid_itself_is_refused_not_only_the_check(car, django_user_model):
    """البوابة على مسار الكتابة، لا على شاشةٍ تسأل قبله."""
    bidder = a_bidder(django_user_model, "966572222222")
    money.request_refund(user=bidder, amount=DEPOSIT, client_key="r2")

    with pytest.raises(bidding.BidRefused) as refusal:
        bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))

    assert refusal.value.code == RefusalReason.REFUND_PENDING
    #: ولا حجز نشأ — المال لم يتحرّك في المحاولة الفاشلة.
    assert money.account_for(bidder, AccountKind.INSURANCE_HELD).balance == Decimal(
        "0.00"
    )


def test_what_is_left_over_still_bids(car, django_user_model):
    """المنع بالمبلغ: من طلب عشرة وله ثلاثون يزايد بالعشرين الباقية."""
    bidder = a_bidder(django_user_model, "966573333333", funds=Decimal("30000.00"))
    money.request_refund(user=bidder, amount=DEPOSIT, client_key="r3")

    verdict = check_eligibility(user=bidder, vehicle=car, amount=Decimal("41000.00"))

    assert verdict.allowed, verdict.detail


def test_a_settled_request_no_longer_blocks(car, django_user_model):
    """الطلب المرفوض أو الملغى ليس ديناً على الوديعة — تعود للمزايدة."""
    bidder = a_bidder(django_user_model, "966574444444")
    request = money.request_refund(user=bidder, amount=DEPOSIT, client_key="r4")

    request.state = RefundRequestState.REJECTED
    request.save(update_fields=["state"])

    assert check_eligibility(user=bidder, vehicle=car, amount=Decimal("41000.00")).allowed


def test_a_bidder_already_in_the_auction_is_not_blocked(car, django_user_model):
    """وديعته محجوزةٌ لهذا المزاد أصلاً، فمزايدته الثانية لا تأخذ ريالاً جديداً.

    ولا يقع التعارض: `request_refund` لا يصرف إلا من الحرّ، والمحجوز خارجه.
    """
    bidder = a_bidder(django_user_model, "966575555555", funds=Decimal("20000.00"))
    bidding.place_bid(user=bidder, vehicle=car, amount=Decimal("41000.00"))
    money.request_refund(user=bidder, amount=DEPOSIT, client_key="r5")

    second = Vehicle.objects.create(
        auction=car.auction,
        lot_number=2,
        make="نيسان",
        model="التيما",
        year=2021,
        state=VehicleState.LISTED,
        reserve_price=Decimal("30000.00"),
    )

    assert check_eligibility(
        user=bidder, vehicle=second, amount=Decimal("31000.00")
    ).allowed


def test_the_snapshot_carries_the_pending_amount(django_user_model):
    """لقطةُ الرفض تحمل الرقمين، فيقرأ الدعم أيّهما منع."""
    bidder = a_bidder(django_user_model, "966576666666")
    money.request_refund(user=bidder, amount=DEPOSIT, client_key="r6")

    snapshot = money_snapshot(bidder)

    assert snapshot.insurance_free == DEPOSIT
    assert snapshot.refund_pending == DEPOSIT
    assert snapshot.spendable_insurance == Decimal("0.00")
