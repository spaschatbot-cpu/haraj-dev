"""T823 — للمزاد أزرارٌ لنقلاته، والإلغاء يمرّ على المال لا حوله.

جرد التكافؤ، القسم (ب): «`AUCTION_MOVES` تُعرِّف **ثماني نقلات للمزاد** — لا
واحدة منها لها زرّ، بينما نقلات المركبة التسع عشرة كلها لها زرّ في
`console:vehicle-state`، محسوبةً من الآلة نفسها». و`cancel_auction` **بلا
مستدعٍ واحد في الإنتاج**، وهي التي تفكّ كل حجز وتُبطل كل ترسية.

**والمصيدة التي يحرسها هذا الملفّ** أخطر من غياب الزرّ. الشاشة الساذجة تستدعي
`auctions.services.cancel` لكل إلغاء — وهي دالّةٌ صحيحة تماماً، تنقل الحالة
وتنتهي. فيصير المزاد «ملغى» على الشاشة **والودائع ما زالت محجوزة**، والفواتير
غير المدفوعة ما زالت مستحقّة. لا خطأ يظهر، ولا اختبار يسقط: مالٌ محبوس لأحدٍ
لم يعد عليه شيء.

فالإلغاء **بعد الانتهاء** يمرّ على `settlement.cancel_auction`؛ والإلغاء وهو
مسودّة أو مجدول يمرّ على `services.cancel` — لأن لا مال تحرّك بعد، ونصّ
`cancel_auction` نفسه يقول ذلك.

والمصيدة الثانية من الشكل ذاته: التسوية اليدوية تمرّ على
`settlement.close_auction` الذي **يرفض** ما دامت مركبةٌ لم تُحسم، لا على
`services.settle` الذي يعلن التسوية وفيها معلّق.
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
from apps.money import services as money
from apps.money.models import Hold, HoldState

pytestmark = pytest.mark.django_db

DEPOSIT = Decimal("10000.00")


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def operator(client):
    client.force_login(staff(Role.OPERATIONS, "966500000801"))
    return client


@pytest.fixture
def draft(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=7701,
        title="مزاد مسودّة",
        starts_at=now + timezone.timedelta(days=1),
        ends_at=now + timezone.timedelta(days=2),
        state=AuctionState.DRAFT,
        deposit_required=DEPOSIT,
    )


@pytest.fixture
def ended(db) -> Auction:
    """مزادٌ يُنشَأ منتهياً.

    ولا يُنقَل إليها بـ`.update(state=…)`: كتابةُ حالةٍ خارج
    `auctions.services` يمنعها `ops/checks/auction_state_single_writer.py`،
    وقد أمسك هذه التجهيزة بعينها في أول تشغيل. والإنشاء ليس نقلة.
    """
    now = timezone.now()
    return Auction.objects.create(
        number=7702,
        title="مزاد منتهٍ",
        starts_at=now - timezone.timedelta(days=2),
        ends_at=now - timezone.timedelta(hours=1),
        state=AuctionState.ENDED,
        deposit_required=DEPOSIT,
    )


def a_car(auction: Auction, lot: int, state: str = VehicleState.LISTED) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=state,
        reserve_price=Decimal("40000.00"),
    )


def test_the_detail_page_offers_the_moves_the_machine_allows(operator, draft):
    """محسوبةً من `AUCTION_MOVES` لا مكتوبةً في القالب — قائمةٌ ثانية تنحرف."""
    a_car(draft, 1)

    body = operator.get(
        reverse("console:auction-detail", args=[draft.pk])
    ).content.decode()

    assert 'name="target"' in body, "لا زرّ نقلةٍ واحد على الصفحة"
    assert AuctionState.SCHEDULED in body
    assert AuctionState.CANCELLED in body
    # مسودّةٌ لا تصير حيّةً مباشرة: النقلة غير موجودة في الآلة.
    assert f'value="{AuctionState.LIVE}"' not in body


def test_scheduling_moves_the_auction_and_records_why(operator, draft):
    a_car(draft, 1)

    operator.post(
        reverse("console:auction-state", args=[draft.pk]),
        {"target": AuctionState.SCHEDULED, "reason": "اكتمل الإعداد"},
    )

    draft.refresh_from_db()
    assert draft.state == AuctionState.SCHEDULED
    entry = AuditLog.objects.get(action="console.move_auction")
    assert entry.note == "اكتمل الإعداد"


def test_a_move_the_machine_refuses_says_so_and_changes_nothing(operator, draft):
    """جملة الآلة تُعرض كما هي: هي تفرّق بين «لا نقلة» و«ليست جاهزة بعد»."""
    response = operator.post(
        reverse("console:auction-state", args=[draft.pk]),
        {"target": AuctionState.LIVE, "reason": "نبدأ بدري"},
        follow=True,
    )

    draft.refresh_from_db()
    assert draft.state == AuctionState.DRAFT
    assert response.status_code == 200


def test_a_move_with_no_reason_is_refused(operator, draft):
    a_car(draft, 1)

    operator.post(
        reverse("console:auction-state", args=[draft.pk]),
        {"target": AuctionState.SCHEDULED, "reason": "  "},
    )

    draft.refresh_from_db()
    assert draft.state == AuctionState.DRAFT


# ---------------------------------------------------------------------------
# المصيدة: الإلغاء بعد الانتهاء يمرّ على المال
# ---------------------------------------------------------------------------


@pytest.fixture
def ended_with_a_held_deposit(ended) -> tuple[Auction, User]:
    """مزادٌ انتهى، ولمزايدٍ فيه وديعةٌ **محجوزة** عليه."""
    bidder = User.objects.create_user(phone="966581212121", full_name="مزايد")
    bidder.phone_verified_at = timezone.now()
    bidder.national_id = "1099887766"
    bidder.save(update_fields=["phone_verified_at", "national_id"])
    money.deposit_insurance(
        user=bidder, amount=DEPOSIT, source="cash", reference="moves/1"
    )
    money.hold_for_auction(user=bidder, auction=ended, amount=DEPOSIT)

    a_car(ended, 1, state=VehicleState.RELEASED)
    return ended, bidder


def test_cancelling_an_ended_auction_frees_the_deposits(
    operator, ended_with_a_held_deposit
):
    """**العطل الذي يحرسه هذا الملفّ كلّه.**

    `services.cancel` تنقل الحالة وتنتهي — فيصير المزاد «ملغى» والوديعة ما
    زالت محجوزة. لا استثناء يُرفع ولا اختبارٌ يسقط: مالٌ محبوسٌ لأحدٍ لم يعد
    عليه شيء، ولا شيء في النظام يقول ذلك.
    """
    auction, bidder = ended_with_a_held_deposit
    assert Hold.objects.filter(
        owner=bidder, auction=auction, state=HoldState.ACTIVE
    ).exists()

    operator.post(
        reverse("console:auction-state", args=[auction.pk]),
        {"target": AuctionState.CANCELLED, "reason": "الشريك سحب أسطوله"},
    )

    auction.refresh_from_db()
    assert auction.state == AuctionState.CANCELLED
    assert not Hold.objects.filter(
        owner=bidder, auction=auction, state=HoldState.ACTIVE
    ).exists(), "أُلغي المزاد والوديعة ما زالت محجوزة"


def test_cancelling_a_draft_needs_no_settlement(operator, draft):
    """ولا مالَ تحرّك بعدُ، فلا شيء يُفكّ — والمسار الآخر ليس خطأً هنا."""
    operator.post(
        reverse("console:auction-state", args=[draft.pk]),
        {"target": AuctionState.CANCELLED, "reason": "أُنشئ بالغلط"},
    )

    draft.refresh_from_db()
    assert draft.state == AuctionState.CANCELLED


def test_settling_by_hand_refuses_while_a_car_is_unresolved(operator, ended):
    """المصيدة الثانية: `services.settle` تعلن التسوية وفيها معلّق."""
    a_car(ended, 1, state=VehicleState.AWAITING_DECISION)

    operator.post(
        reverse("console:auction-state", args=[ended.pk]),
        {"target": AuctionState.SETTLED, "reason": "نقفلها"},
    )

    ended.refresh_from_db()
    assert ended.state == AuctionState.ENDED, "أُعلنت التسوية ومركبةٌ لم تُحسم"
