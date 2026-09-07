"""الشاشات الأربع الجديدة: الأرشيف، ومزايدات المزاد، والدفعات، والإشعارات. T826.

`test_navigation.py` يفتحها بالفعل بكل دور ويثبت أنها محروسة — فهذا الملف لا
يعيد ذلك. يسأل ما لا يسأله: **هل الرقم المعروض هو الرقم الصحيح، وهل الصفّ الذي
تُفتح الشاشة لأجله موجودٌ فيها؟**

وكلُّ ادّعاءٍ هنا مأخوذٌ من فرقٍ مقصودٍ عن v1 مكتوبٍ في رأس وحدته:

* الأرشيف يشتقّ «إجمالي المبيعات» ولا يقرؤه من عمود.
* شاشة المزايدات تعرض المسحوبة والمستبدَلة، لأن الصفَّ الساقط هو المطلوب.
* سجل الدفعات يعرض الفاشلة، ويصرخ على دفعةٍ نجحت بلا قيد.
* سجل الإشعارات يعرض سبب الفشل في الصفّ.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.console.archive import archived, bids_of
from apps.console.tests.conftest import screen_of
from apps.money.models import PaymentIntent, PaymentIntentState, PaymentPurpose
from apps.notifications.models import Channel, DeliveryState, Notification

pytestmark = pytest.mark.django_db


def _auction(**kwargs) -> Auction:
    """مزادٌ يُنشأ في حالته النهائية مباشرةً.

    `.update(state=…)` كتابةُ حالةٍ خارج `auctions.services` ويرفضها
    `ops/checks/auction_state_single_writer.py` — وهو محقّ. والإنشاء ليس نقلة.
    """
    moment = timezone.now() - timedelta(days=3)
    return Auction.objects.create(
        number=kwargs.pop("number", 900),
        title=kwargs.pop("title", "مزاد الأربعاء"),
        starts_at=moment - timedelta(days=1),
        ends_at=moment,
        state=kwargs.pop("state", AuctionState.SETTLED),
        deposit_required=Decimal("5000.00"),
        **kwargs,
    )


def _vehicle(
    auction: Auction, *, state: str, price=None, lot: int = 1, winner=None
) -> Vehicle:
    """مركبةٌ تُنشأ في حالتها.

    `winner` و`awarded_at` ليسا زينةً في التجهيزة: القاعدة نفسها فيها
    `an_awarded_vehicle_names_its_winner`، فمركبةٌ «مرساة» بلا فائزٍ لا تُكتب
    أصلاً. أوّل نسخةٍ من هذا الاختبار حاولت، فردّتها القاعدة — وهذا هو الفرق
    بين قاعدةٍ تحرس وقاعدةٍ تخزّن.
    """
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2020,
        vin=f"VIN{auction.number}{lot:04d}JKLMNPQRS",
        plate_number=f"ا ب ج {1000 + lot}",
        state=state,
        awarded_price=price,
        awarded_to=winner,
        awarded_at=timezone.now() if winner is not None else None,
        reserve_price=Decimal("30000.00"),
    )


# ---------------------------------------------------------------------------
# الأرشيف


def test_the_archive_holds_only_what_is_over() -> None:
    """المسودّة والمجدول والجاري عملٌ قائم لا تاريخ — ومكانها قائمة المزادات."""
    _auction(number=901, state=AuctionState.SETTLED)
    _auction(number=902, state=AuctionState.CANCELLED)
    _auction(number=903, state=AuctionState.DRAFT)
    _auction(number=904, state=AuctionState.SCHEDULED)

    numbers = {row.number for row in archived()}
    assert numbers == {901, 902}, "الأرشيف حمل مزاداً لم ينتهِ"


def test_the_total_is_derived_from_the_vehicles_not_a_stored_column(customer) -> None:
    """الادّعاء المكتوب في رأس `archive.py`، مسؤولاً عنه.

    ثلاث مركبات: مرساةٌ ومفوترةٌ ومرفوضة. الإجمالي مجموع الأوليين وحدهما،
    والمرفوضة لا تدخل — ولا عمودَ مخزَّناً في أي منهما.
    """
    auction = _auction(number=905)
    _vehicle(
        auction,
        state=VehicleState.AWARDED,
        price=Decimal("40000.00"),
        lot=1,
        winner=customer,
    )
    _vehicle(auction, state=VehicleState.INVOICED, price=Decimal("25000.50"), lot=2)
    _vehicle(auction, state=VehicleState.REJECTED, price=None, lot=3)

    row = archived().get(number=905)
    assert row.vehicle_count == 3
    assert row.sold_count == 2
    assert row.sold_total == Decimal("65000.50")


def test_an_auction_that_sold_nothing_reads_zero_not_none(client, staff) -> None:
    """خانةٌ فارغة تُقرأ «لم يُحسب»؛ وكلمة `None` أسوأ منهما.

    كُتب هذا الصفّ أوّلاً `{{ … |unlocalize|default:"0.00" }}` فطبع `None`:
    `unlocalize` يحوّل `None` إلى **السلسلة** «None» وهي غير فارغة، فلا يقع
    `default` بعدها. والترتيب المعكوس هو الصواب.

    وكان العطلُ نفسه قائماً في **خمس شاشاتٍ سابقة** (سعر الوقوف والممشى وسعر
    الرسو)، فصار له حارس: `ops/checks/default_runs_before_unlocalize.py`.
    """
    auction = _auction(number=906)
    _vehicle(auction, state=VehicleState.REJECTED, price=None)

    client.force_login(staff)
    body = screen_of(client.get(reverse("console:auction-archive")).content.decode())
    assert "0.00" in body
    assert "None" not in body, "طُبعت كلمة None في خانة مبلغ"


def test_the_archive_finds_an_auction_by_its_number(client, staff) -> None:
    """الرقم والاسم كلاهما ما يُتذكَّر من مزادٍ مضى."""
    _auction(number=907, title="مزاد الرياض")
    _auction(number=908, title="مزاد جدة")

    assert {row.number for row in archived(text="907")} == {907}
    assert {row.number for row in archived(text="جدة")} == {908}


# ---------------------------------------------------------------------------
# مزايدات المزاد


def test_a_withdrawn_bid_is_shown_and_said_so(client, staff, customer) -> None:
    """الصفّ الساقط هو ما تُفتح الشاشة لأجله — v1 يعرض القائمة وحدها."""
    auction = _auction(number=909)
    vehicle = _vehicle(
        auction, state=VehicleState.AWARDED, price=Decimal("40000.00"), winner=customer
    )
    Bid.objects.create(
        vehicle=vehicle,
        bidder=customer,
        amount=Decimal("31000.00"),
        is_withdrawn=True,
        withdrawn_at=timezone.now(),
    )
    Bid.objects.create(vehicle=vehicle, bidder=customer, amount=Decimal("40000.00"))

    assert bids_of(auction).count() == 2, "المزايدة المسحوبة سقطت من الاستعلام"

    client.force_login(staff)
    body = screen_of(
        client.get(reverse("console:auction-bids", args=[auction.pk])).content.decode()
    )
    assert "مسحوبة" in body
    assert "31000.00" in body


def test_the_bid_screen_writes_nothing(client, staff, customer) -> None:
    """شاشةٌ تعرض التاريخ لا تكون بابَ تغييرٍ فيه — والنقلات في `auction_moves`."""
    auction = _auction(number=910)
    vehicle = _vehicle(
        auction, state=VehicleState.AWARDED, price=Decimal("1.00"), winner=customer
    )
    Bid.objects.create(vehicle=vehicle, bidder=customer, amount=Decimal("1.00"))

    client.force_login(staff)
    screen = screen_of(
        client.get(reverse("console:auction-bids", args=[auction.pk])).content.decode()
    )
    assert "<form" not in screen.lower()


# ---------------------------------------------------------------------------
# الدفعات


def _intent(user, **kwargs) -> PaymentIntent:
    return PaymentIntent.objects.create(
        reference=kwargs.pop("reference", "PAY-1"),
        user=user,
        amount=kwargs.pop("amount", Decimal("5000.00")),
        state=kwargs.pop("state", PaymentIntentState.PENDING),
        purpose=kwargs.pop("purpose", PaymentPurpose.INSURANCE_DEPOSIT),
        **kwargs,
    )


def test_a_failed_payment_is_listed(client, staff, customer) -> None:
    """«دفعتُ ولم يصل» لا يُجاب من قائمةٍ تعرض الناجح وحده."""
    _intent(customer, reference="PAY-FAIL", state=PaymentIntentState.FAILED)

    client.force_login(staff)
    body = screen_of(client.get(reverse("console:payments")).content.decode())
    assert "PAY-FAIL" in body


def test_a_succeeded_payment_cannot_exist_without_its_entry(customer) -> None:
    """الشاشة لا تحتاج أن تصرخ على «دفعةٍ نجحت بلا قيد» — القاعدة تمنعها.

    كُتبت هنا أوّلاً خانةٌ تقول «نجحت بلا قيد»، ظنّاً أنها الحالة التي تُفتح
    الشاشة لأجلها. ثم ردّتها القاعدة: `a_succeeded_intent_names_its_transaction`
    قيدٌ حقيقي على الجدول، فالصفّ لا يُكتب أصلاً.

    فحُذفت الخانة، وبقي هذا الاختبار مكانها — لأن الادّعاء يجب أن يظلّ محروساً
    ولو انتقل الحارس من القالب إلى القاعدة. ويوم يُرفع القيد يسقط هذا الاختبار،
    وحينها تُعاد الخانة عن علم.
    """
    from django.db.utils import IntegrityError

    with pytest.raises(IntegrityError, match="a_succeeded_intent_names_its_transaction"):
        _intent(customer, reference="PAY-ORPHAN", state=PaymentIntentState.SUCCEEDED)


def test_payments_are_searchable_by_reference(client, staff, customer) -> None:
    """المرجع يُلصَق من إشعار البوابة، وهو المدخل الأول."""
    from apps.console.payments import search

    _intent(customer, reference="PAY-AAA")
    _intent(customer, reference="PAY-BBB")

    assert {row.reference for row in search(text="AAA")} == {"PAY-AAA"}


# ---------------------------------------------------------------------------
# الإشعارات


def test_a_failed_notification_shows_its_reason(client, staff, customer) -> None:
    """من يفتح السجلّ يفتحه بسبب فشل — فالسبب في الصفّ لا خلف نقرة."""
    Notification.objects.create(
        user=customer,
        channel=Channel.SMS,
        template="bid.outbid",
        body="تمّت المزايدة عليك",
        state=DeliveryState.FAILED,
        error="رقمٌ غير قابل للاستقبال",
    )

    client.force_login(staff)
    body = screen_of(client.get(reverse("console:notifications")).content.decode())
    assert "رقمٌ غير قابل للاستقبال" in body


def test_notifications_filter_by_state(customer) -> None:
    """الحالة التي لا تُرشَّح هي الحالة التي لا يجدها أحد."""
    from apps.console.alerts import search

    Notification.objects.create(
        user=customer,
        channel=Channel.SMS,
        template="t",
        body="أ",
        state=DeliveryState.FAILED,
    )
    Notification.objects.create(
        user=customer,
        channel=Channel.SMS,
        template="t",
        body="ب",
        state=DeliveryState.DELIVERED,
    )

    assert [row.body for row in search(state=DeliveryState.FAILED)] == ["أ"]
