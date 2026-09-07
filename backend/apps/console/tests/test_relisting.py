"""T828 — سيارةٌ رفضها مالكها تعود لمزادٍ لاحق، بزرّ.

جرد التكافؤ، القسم (ب): «أعيد عرض مركبة في مزاد لاحق — `settlement.relist_vehicle`
**بلا مستدعٍ**. وهي الخطوة التالية المكتوبة لـرفض المالك».

فما يقع اليوم: الشريك يرفض السعر، فتصير المركبة `rejected` — **ثم لا شيء**.
الدالّة التي تعيدها إلى الدورة مبنيّةٌ ومختبَرة ولا يبلغها موظّف، فالسيارة
تبقى في مزادٍ منتهٍ إلى أن ينتبه أحد.

**والقاعدة التي تحرسها هذه الشاشة أدقّ من «انقلها»:** الاستبعاد يخصّ الدورة
التي وقع فيها. مزايدٌ رُفض على هذه السيارة في مارس ليس مرفوضاً عليها في أبريل،
والترسيةُ السابقة **لا تسافر** — سيارةٌ معروضةٌ في أبريل تُظهر فائز مارس هي
الطريقة التي يُقال بها لعميلٍ إنه يملك ما لا يملك.

**ولا تُعاد إلى مزادٍ حيّ.** إدخال سيارةٍ إلى مزادٍ تجري المزايدة فيه يعني
لوتاً يظهر بعد أن قرأ الناس القائمة.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.core.models import AuditLog
from apps.core.permissions import Role

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def operator(client):
    client.force_login(staff(Role.OPERATIONS, "966500000401"))
    return client


def an_auction(number: int, state: str) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=number,
        title=f"مزاد {number}",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=2),
        state=state,
        deposit_required=Decimal("10000.00"),
    )


@pytest.fixture
def ended(db) -> Auction:
    return an_auction(8801, AuctionState.ENDED)


@pytest.fixture
def upcoming(db) -> Auction:
    return an_auction(8802, AuctionState.DRAFT)


def a_car(auction: Auction, lot: int, state: str) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=state,
        reserve_price=Decimal("50000.00"),
    )


def test_a_rejected_car_offers_the_move(operator, ended, upcoming):
    """الزرّ يظهر حيث تسمح الآلة، لا حيث كُتب في القالب."""
    car = a_car(ended, 1, VehicleState.REJECTED)

    body = operator.get(reverse("console:vehicle-detail", args=[car.pk])).content.decode()

    assert reverse("console:vehicle-relist", args=[car.pk]) in body


def test_relisting_moves_the_car_and_drops_the_old_award(operator, ended, upcoming):
    """الترسية لا تسافر: سيارةٌ في أبريل تُظهر فائز مارس تقول لعميلٍ إنه يملك
    ما لا يملك."""
    winner = User.objects.create_user(phone="966585050505", full_name="فائز مارس")
    car = a_car(ended, 1, VehicleState.REJECTED)
    Vehicle.objects.filter(pk=car.pk).update(
        awarded_to=winner, awarded_price=Decimal("45000.00"), awarded_at=timezone.now()
    )

    operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": upcoming.pk, "lot_number": "7", "reason": "رفض المالك السعر"},
    )

    car.refresh_from_db()
    assert car.auction_id == upcoming.pk
    assert car.lot_number == 7
    assert car.awarded_to_id is None
    assert car.awarded_price is None


def test_relisting_leaves_a_row_in_the_audit_log(operator, ended, upcoming):
    car = a_car(ended, 1, VehicleState.REJECTED)

    operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": upcoming.pk, "lot_number": "7", "reason": "رفض المالك السعر"},
    )

    entry = AuditLog.objects.get(action="console.relist_vehicle")
    assert entry.note == "رفض المالك السعر"
    assert entry.before["auction_id"] == ended.pk
    assert entry.after["auction_id"] == upcoming.pk


def test_a_live_auction_is_not_offered_as_a_destination(operator, ended):
    """لوتٌ يظهر بعد أن قرأ الناس القائمة."""
    live = an_auction(8803, AuctionState.LIVE)
    car = a_car(ended, 1, VehicleState.REJECTED)

    operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": live.pk, "lot_number": "7", "reason": "محاولة"},
    )

    car.refresh_from_db()
    assert car.auction_id == ended.pk, "أُدخلت سيارةٌ إلى مزادٍ حيّ"


def test_a_taken_lot_number_is_a_sentence_beside_the_box(operator, ended, upcoming):
    """القاعدة ترفضه بقيد (T405)؛ وهذا كي يرى المشغّل لماذا."""
    a_car(upcoming, 7, VehicleState.LISTED)
    car = a_car(ended, 1, VehicleState.REJECTED)

    response = operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": upcoming.pk, "lot_number": "7", "reason": "رفض المالك"},
    )

    car.refresh_from_db()
    assert car.auction_id == ended.pk
    assert response.status_code in (200, 302)


def test_a_car_that_was_paid_for_is_not_relisted(operator, ended, upcoming):
    """آلةُ الحالات لا تسمح، والشاشة لا تلتفّ عليها: سيارةٌ سُدّدت فاتورتها
    ليست معروضةً للبيع مرّةً ثانية."""
    car = a_car(ended, 1, VehicleState.PAID)

    operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": upcoming.pk, "lot_number": "7", "reason": "محاولة"},
    )

    car.refresh_from_db()
    assert car.auction_id == ended.pk


def test_relisting_with_no_reason_is_refused(operator, ended, upcoming):
    car = a_car(ended, 1, VehicleState.REJECTED)

    operator.post(
        reverse("console:vehicle-relist", args=[car.pk]),
        {"auction": upcoming.pk, "lot_number": "7", "reason": "  "},
    )

    car.refresh_from_db()
    assert car.auction_id == ended.pk
