"""محرّك المزاد: المرحلة، والمُجمَّع، والعمليّات — T843.

ما يُثبَت هنا هو ما كان مكسوراً قبله، لا ما هو بديهيّ:

* **الفجوة بين العمود والساعة لها اسم.** مزادٌ حالتُه ``live`` وانتهى وقتُه
  كان يُقرأ «جارياً» في اللوحة و«منتهياً» في البوّابة و«مضى» عند العميل. هنا
  مرحلةٌ واحدة اسمها ``OVERDUE_END`` تقولها الثلاثةُ معاً.
* **التأمين واحدٌ لكل مزاد.** المالك بالحرف: «المزاد الواحد مطلوب عشان
  المشاركة فيه تأمين واحد للمزايدة فيه حتى لو هيزايد على كل السيارات اللي
  فيه». القاعدة تمنع الثاني بقيد، وهذا يثبت أن الشاشة تقرأ الواحد.
* **الفاتورة تصل إلى تأمينها بالسلسلة.** فاتورة → مركبة → مزاد → حجز، بلا
  عمودٍ ثانٍ يحمل الجواب نفسه.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions import engine
from apps.auctions.states import AuctionState, VehicleState
from apps.money import services as money

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# المرحلة
# ---------------------------------------------------------------------------


def test_live_auction_inside_its_window_is_open(make_auction):
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )

    assert engine.phase(auction, now=now) == engine.Phase.OPEN
    assert engine.is_open_for_bidding(auction, now=now)
    assert not engine.is_late(auction, now=now)


def test_live_auction_past_its_end_is_named_not_guessed(make_auction):
    """العطلُ الذي وُجد المحرّك لأجله.

    مزادٌ في الحالة ``live`` ونهايتُه مضت: العمودُ يقول جارٍ، والساعة تقول
    انتهى. قبل هذا كانت اللوحة تعدّه ضمن «الجارية» بينما البوّابةُ ترفض كل
    مزايدةٍ فيه — رُئي في قاعدة التطوير بفارق تسع ساعات.
    """
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )

    assert auction.state == AuctionState.LIVE  # العمود لم يتغيّر
    assert engine.phase(auction, now=now) == engine.Phase.OVERDUE_END
    assert not engine.is_open_for_bidding(auction, now=now)
    assert engine.is_late(auction, now=now)


def test_scheduled_auction_whose_moment_arrived_is_late_not_scheduled(make_auction):
    now = timezone.now()
    auction = make_auction(
        AuctionState.SCHEDULED,
        starts_at=now - timedelta(minutes=10),
        ends_at=now + timedelta(hours=2),
    )

    assert engine.phase(auction, now=now) == engine.Phase.OVERDUE_START
    assert engine.is_late(auction, now=now)
    assert not engine.is_open_for_bidding(auction, now=now)


def test_live_auction_whose_start_was_pushed_forward_is_not_open(make_auction):
    """شاشةُ التعديل تستطيع تحريك البداية إلى المستقبل على مزادٍ جارٍ.

    ولو قُرئ «مفتوحاً» لقُبلت مزايدةٌ قبل الموعد المعلن للمزاد.
    """
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
    )

    assert engine.phase(auction, now=now) == engine.Phase.SCHEDULED
    assert not engine.is_open_for_bidding(auction, now=now)


@pytest.mark.parametrize(
    "state",
    [
        AuctionState.DRAFT,
        AuctionState.ENDED,
        AuctionState.SETTLED,
        AuctionState.CANCELLED,
    ],
)
def test_states_the_clock_does_not_touch_pass_through(make_auction, state):
    auction = make_auction(state)
    assert engine.phase(auction).value == state.value


def test_the_model_property_and_the_engine_cannot_disagree(make_auction):
    """``Auction.is_open_for_bidding`` كان يحسب الساعة بنفسه؛ الآن يفوّض."""
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )

    assert auction.is_open_for_bidding is engine.is_open_for_bidding(auction)


def test_open_now_excludes_the_auction_the_state_column_still_calls_live(make_auction):
    """ما كانت اللوحة تعدّه: ``filter(state=LIVE)`` بلا ساعة."""
    now = timezone.now()
    running = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    overdue = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )

    open_pks = set(engine.open_now(now=now).values_list("pk", flat=True))
    late_pks = set(engine.late_now(now=now).values_list("pk", flat=True))

    assert open_pks == {running.pk}
    assert late_pks == {overdue.pk}


def test_late_now_catches_both_directions(make_auction):
    now = timezone.now()
    not_started = make_auction(
        AuctionState.SCHEDULED,
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(hours=2),
    )
    not_closed = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )
    fine = make_auction(
        AuctionState.SCHEDULED,
        starts_at=now + timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
    )

    late = set(engine.late_now(now=now).values_list("pk", flat=True))
    assert late == {not_started.pk, not_closed.pk}
    assert fine.pk not in late


def test_phase_value_does_not_collide_with_an_invoice_state():
    """``open`` تعني «مستحقّة» في الفاتورة، فلا تكون قيمةَ مرحلةٍ مفتوحة.

    خريطةُ النغمات في اللوحة مفتاحُها القيمةُ المجرّدة، فقيمتان بمعنيين
    متضادّين تحت مفتاحٍ واحد تجعل المزادَ المفتوح يُرسم بلون الدَّين.
    """
    from apps.money.models import InvoiceState

    stored = set(InvoiceState.values) | set(VehicleState.values)
    only_phases = set(engine.Phase.values) - set(AuctionState.values)
    assert not (only_phases & stored)


# ---------------------------------------------------------------------------
# المُجمَّع: تأمينٌ واحد للمزاد مهما بلغ عدد السيارات
# ---------------------------------------------------------------------------


@pytest.fixture
def bidder(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000771", full_name="مزايد المُجمَّع", password="x"
    )


def _hold_for(bidder, auction, amount="10000.00"):
    """حجزٌ عبر خدمة المال، لا صفٌّ مكتوبٌ بيد.

    `money_single_writer` يرسب على `Transaction.objects.create` هنا — والمادة
    ١-٢ ليست تشدّداً على الاختبارات: حجزٌ بلا قيدٍ يوازنه يجعل الدفتر يكذب،
    و`verify_ledger` يُقارن مجموعَ المحجوز بمجموع الحجوز القائمة. فاختبارٌ
    يبني حجزاً بيده يبني حالةً لا تُنتَج في الإنتاج، ثم يُثبت عليها سلوكاً.
    """
    money.deposit_insurance(
        user=bidder,
        amount=Decimal(amount),
        source="cash",
        reference=f"engine-test/{auction.pk}/{bidder.pk}",
    )
    return money.hold_for_auction(user=bidder, auction=auction, amount=Decimal(amount))


def test_one_deposit_covers_every_car_the_bidder_wins(make_auction, make_vehicle, bidder):
    """المالك بالحرف: «تأمين واحد… حتى لو هيزايد على كل السيارات اللي فيه»."""
    auction = make_auction(AuctionState.ENDED)
    hold = _hold_for(auction=auction, bidder=bidder)

    cars = [
        make_vehicle(auction, VehicleState.AWARDED, lot_number=n, awarded_to=bidder)
        for n in (1, 2, 3)
    ]

    rows = engine.participants(auction)
    assert len(rows) == 1
    row = rows[0]
    assert row.customer == bidder
    assert row.hold == hold
    assert row.held_amount == Decimal("10000.00")
    assert {v.pk for v in row.won} == {v.pk for v in cars}
    # ثلاثُ سياراتٍ وتأمينٌ واحد، لا ثلاثة.
    assert engine.money_held_in(auction) == Decimal("10000.00")


def test_asking_for_a_second_deposit_returns_the_first_one(make_auction, bidder):
    """«تأمين واحد للمزاد» على مستوى الخدمة: النداءُ الثاني لا يحجز ثانيةً.

    ولا يرمي: عميلٌ يزايد عشرين مرّةً في المزاد نفسه يمرّ من هنا عشرين مرّة،
    ورميُ استثناءٍ في التاسعة عشرة يعني رفضَ مزايدةٍ صحيحة. فالخدمة تُرجع
    الحجزَ القائم، والقاعدةُ تمنع الثاني لو تسلّل نداءٌ متزامن —
    و`money/tests/test_schema_refusals.py` هو ما يثبت القيدَ نفسه.
    """
    auction = make_auction(AuctionState.LIVE)
    first = _hold_for(auction=auction, bidder=bidder)
    second = _hold_for(auction=auction, bidder=bidder)

    assert first.pk == second.pk
    assert engine.deposit_of(bidder, auction) == first
    assert engine.money_held_in(auction) == Decimal("10000.00")


def test_participants_keeps_the_buyer_whose_hold_was_already_released(
    make_auction, make_vehicle, bidder
):
    """من سدّد فُكّ حجزُه — وحصرُ القائمة على أصحاب الحجوز يُخفيه."""
    auction = make_auction(AuctionState.SETTLED)
    make_vehicle(auction, VehicleState.PAID, lot_number=1, awarded_to=bidder)

    rows = engine.participants(auction)
    assert len(rows) == 1
    assert rows[0].hold is None
    assert rows[0].has_deposit is False


def test_the_invoice_reaches_its_deposit_through_the_chain(
    make_auction, make_vehicle, bidder
):
    """فاتورة → مركبة → مزاد → حجز. بلا عمودٍ ثانٍ يحمل الجواب نفسه."""
    from apps.money.models import Invoice, InvoiceSource

    auction = make_auction(AuctionState.ENDED)
    hold = _hold_for(auction=auction, bidder=bidder)
    vehicle = make_vehicle(
        auction, VehicleState.INVOICED, lot_number=1, awarded_to=bidder
    )
    invoice = Invoice.objects.create(
        customer=bidder,
        number="INV-ENGINE-1",
        amount=Decimal("55000.00"),
        source=InvoiceSource.LOCAL,
        vehicle=vehicle,
        issued_at=timezone.now(),
    )

    assert engine.deposit_behind(invoice) == hold
    assert engine.deposit_of(bidder, auction) == hold


def test_a_dues_invoice_with_no_vehicle_has_no_auction_deposit(make_auction, bidder):
    from apps.money.models import Invoice, InvoiceSource

    invoice = Invoice.objects.create(
        customer=bidder,
        number="INV-ENGINE-2",
        amount=Decimal("300.00"),
        source=InvoiceSource.LOCAL,
        issued_at=timezone.now(),
    )
    assert engine.deposit_behind(invoice) is None


def test_every_invoice_in_one_auction_stands_behind_the_same_deposit(
    make_auction, make_vehicle, bidder
):
    """المالك بالحرف: «فواتير المزاد الواحد تتربط برده بنفس التأمين بتاعه»."""
    from apps.money.models import Invoice, InvoiceSource

    auction = make_auction(AuctionState.ENDED)
    hold = _hold_for(auction=auction, bidder=bidder)

    invoices = []
    for lot in (1, 2, 3):
        vehicle = make_vehicle(
            auction, VehicleState.INVOICED, lot_number=lot, awarded_to=bidder
        )
        invoices.append(
            Invoice.objects.create(
                customer=bidder,
                number=f"INV-ENGINE-SAME-{lot}",
                amount=Decimal("10000.00"),
                source=InvoiceSource.LOCAL,
                vehicle=vehicle,
                issued_at=timezone.now(),
            )
        )

    assert {engine.deposit_behind(i).pk for i in invoices} == {hold.pk}

    row = engine.participants(auction)[0]
    assert row.invoiced_total == Decimal("30000.00")
    assert row.unpaid == Decimal("30000.00")


# ---------------------------------------------------------------------------
# العدّ والعمليّات
# ---------------------------------------------------------------------------


def test_tally_counts_every_state_in_one_query(
    make_auction, make_vehicle, django_assert_num_queries
):
    auction = make_auction(AuctionState.LIVE)
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)
    make_vehicle(auction, VehicleState.LISTED, lot_number=2)
    make_vehicle(auction, VehicleState.AWAITING_DECISION, lot_number=3)

    with django_assert_num_queries(1):
        counted = engine.tally(auction)

    assert counted.total == 3
    assert counted.of(VehicleState.LISTED) == 2
    assert counted.awaiting_decision == 1
    assert counted.sold == 0


def test_operations_say_why_a_move_is_not_available_yet(make_auction, make_vehicle):
    """زرٌّ مطفأ بلا سبب يُنتج تذكرةَ دعم؛ وزرٌّ يعمل ثم يرفض يُنتج اثنتين."""
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)

    ending = next(
        op for op in engine.operations(auction, now=now) if op.target == "ended"
    )
    assert ending.allowed is False
    assert ending.blocked_by == "المزاد لم ينته بعد"


def test_operations_open_up_once_the_moment_arrives(make_auction, make_vehicle):
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=5),
        ends_at=now - timedelta(hours=1),
    )
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)

    ending = next(
        op for op in engine.operations(auction, now=now) if op.target == "ended"
    )
    assert ending.allowed is True
    assert ending.blocked_by == ""


def test_snapshot_answers_the_whole_screen(make_auction, make_vehicle, bidder):
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)
    _hold_for(auction=auction, bidder=bidder)

    view = engine.snapshot(auction, now=now)

    assert view.phase == engine.Phase.OPEN
    assert view.is_open is True
    assert view.is_late is False
    assert view.cars.total == 1
    assert view.held == Decimal("10000.00")
    assert [op.target for op in view.operations] == ["ended"]


# ---------------------------------------------------------------------------
# ملخّصُ الصفّ — أعمدة شاشة v1، وما تُصلحه (T844)
# ---------------------------------------------------------------------------


def test_the_summary_counts_cars_makes_and_prices(make_auction, make_vehicle):
    auction = make_auction(AuctionState.LIVE)
    make_vehicle(
        auction,
        VehicleState.LISTED,
        lot_number=1,
        make="تويوتا",
        reserve_price=Decimal("30000.00"),
    )
    make_vehicle(
        auction,
        VehicleState.LISTED,
        lot_number=2,
        make="تويوتا",
        reserve_price=Decimal("50000.00"),
    )
    # `reserve_price=None` صريحةً: البذرةُ تعطي سعراً افتراضياً، وسيارةٌ بلا
    # سعرٍ مسجَّل هي بالضبط ما يعدّه هذا العمود ناقصاً.
    make_vehicle(
        auction, VehicleState.DRAFT, lot_number=3, make="نيسان", reserve_price=None
    )

    row = engine.summarise([auction])[auction.pk]

    assert row.cars == 3
    assert row.makes == 2
    assert row.top_makes == ("تويوتا", "نيسان")
    assert row.with_reserve == 2
    assert row.reserve_low == Decimal("30000.00")
    assert row.reserve_high == Decimal("50000.00")


def test_offered_is_derived_from_the_state_not_a_second_column(
    make_auction, make_vehicle
):
    """في v1 كان «التفعيل» عموداً نصّياً بجانب حالة السيارة، فيختلفان.

    سيارةٌ `activation_status='active'` وقد رست على مشترٍ منذ أسبوع كانت
    تُعدّ «متاحة». هنا لا عمودَ ثانٍ يُخالف.
    """
    auction = make_auction(AuctionState.LIVE)
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)
    make_vehicle(auction, VehicleState.BIDDING, lot_number=2)
    make_vehicle(auction, VehicleState.AWARDED, lot_number=3)
    make_vehicle(auction, VehicleState.DRAFT, lot_number=4)

    row = engine.summarise([auction])[auction.pk]

    assert row.cars == 4
    assert row.offered == 2


def test_a_withdrawn_bid_is_not_activity(make_auction, make_vehicle, bidder):
    """v1 يعدّ الصفوف كلَّها فيقول «٦٥١٨ مزايدة» وفيها مسحوبةٌ ومتجاوَزة.

    والرقم يُقرأ نشاطاً، و«أعلى» يُعلن رقماً لا يشتري به أحد.
    """
    from apps.bidding.models import Bid

    auction = make_auction(AuctionState.LIVE)
    car = make_vehicle(auction, VehicleState.BIDDING, lot_number=1)

    Bid.objects.create(vehicle=car, bidder=bidder, amount=Decimal("40000.00"))
    # `withdrawn_at` ليس زينة: `a_withdrawn_bid_names_its_moment` قيدٌ في
    # القاعدة — مزايدةٌ مسحوبةٌ بلا لحظةِ سحبٍ لا يمكن الردّ على «متى سُحبت».
    Bid.objects.create(
        vehicle=car,
        bidder=bidder,
        amount=Decimal("99000.00"),
        is_withdrawn=True,
        withdrawn_at=timezone.now(),
    )

    row = engine.summarise([auction])[auction.pk]

    assert row.bids == 1
    assert row.bidders == 1
    assert row.top_bid == Decimal("40000.00")


def test_the_image_count_says_coverage_not_only_a_total(make_auction, make_vehicle):
    """«٣١٠ سيارة · ٣٦٧٠ صورة» تقول إن التغطية كاملة؛ الإجماليُّ وحده لا يقول.

    ومزادٌ نصفُ سياراته بلا صورة هو مزادٌ نصفُه لا يُشترى — والرقم الذي يكشفه
    هو `cars_with_images`، لا `images`.

    والصفوفُ تُنشأ هنا مباشرةً بلا رفعٍ حقيقيّ: المفحوصُ هو العدّ، ورفعُ
    صورتين حقيقيّتين يُشغّل توليدَ المصغّرات ويقيس شيئاً آخر يقيسه
    `test_images.py` بالفعل.
    """
    from apps.auctions.models import VehicleImage

    auction = make_auction(AuctionState.LIVE)
    with_photos = make_vehicle(auction, VehicleState.LISTED, lot_number=1)
    make_vehicle(auction, VehicleState.LISTED, lot_number=2)

    VehicleImage.objects.create(vehicle=with_photos, image="a.png", position=0)
    VehicleImage.objects.create(vehicle=with_photos, image="b.png", position=1)

    row = engine.summarise([auction])[auction.pk]

    assert row.cars == 2
    assert row.cars_with_images == 1
    assert row.images == 2
    assert row.images_missing == 1


def test_the_summary_costs_the_same_for_three_auctions_as_for_ten(
    make_auction, make_vehicle, django_assert_num_queries
):
    """العددُ **لا يتعلّق بعدد الصفوف** — وذلك هو ما يحرسه هذا الاختبار.

    وعمودٌ واحدٌ محسوبٌ في حلقةٍ يعني خمسةً وعشرين ذهاباً إلى القاعدة لكل
    عمود، وهو ما كان يفعله v1.

    وكان مكتوباً «أربعة استعلامات» رقماً ثابتاً، فلمّا أُضيف قسمُ العيّنة
    والمصغَّرة (استعلامان مجمَّعان) سقط الاختبار — **وهو سليم**: الرقم ستّة
    الآن. فصار يقيس ما يعنيه بدل أن يقيس رقماً: ثلاثةُ مزادات وعشرةٌ بالعدد
    نفسه. ورقمٌ يُحدَّث يدوياً كلَّما نما الكود هو رقمٌ يُحدَّث بلا قراءة.
    """
    few = [make_auction(AuctionState.LIVE) for _ in range(3)]
    many = [make_auction(AuctionState.LIVE) for _ in range(10)]
    for auction in few + many:
        make_vehicle(auction, VehicleState.LISTED, lot_number=1)

    with django_assert_num_queries(6):
        engine.summarise(few)

    with django_assert_num_queries(6):
        engine.summarise(many)


def test_an_auction_with_nothing_in_it_summarises_to_zeroes(make_auction):
    """صفٌّ فارغ لا `KeyError`: مزادٌ بلا سيارات يُعرض، ولا يُسقط الصفحة."""
    auction = make_auction(AuctionState.DRAFT)

    row = engine.summarise([auction])[auction.pk]

    assert (row.cars, row.images, row.bids, row.top_makes) == (0, 0, 0, ())
    assert row.reserve_low is None
