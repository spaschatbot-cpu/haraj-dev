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


def test_snapshot_answers_the_whole_screen(make_auction, make_vehicle):
    now = timezone.now()
    auction = make_auction(
        AuctionState.LIVE,
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=1),
    )
    make_vehicle(auction, VehicleState.LISTED, lot_number=1)

    view = engine.snapshot(auction, now=now)

    assert view.phase == engine.Phase.OPEN
    assert view.is_open is True
    assert view.is_late is False
    assert view.cars.total == 1
    assert [op.target for op in view.operations] == ["ended"]


# ---------------------------------------------------------------------------
# ملخّصُ الصفّ — أعمدة شاشة v1، وما تُصلحه (T844)
# ---------------------------------------------------------------------------


def test_the_summary_counts_cars_makes_and_prices(make_auction, make_vehicle):
    auction = make_auction(AuctionState.LIVE)
    make_vehicle(
        auction, VehicleState.LISTED, lot_number=1, make="تويوتا",
        reserve_price=Decimal("30000.00"),
    )
    make_vehicle(
        auction, VehicleState.LISTED, lot_number=2, make="تويوتا",
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


def test_the_summary_is_a_fixed_number_of_queries(
    make_auction, make_vehicle, django_assert_num_queries
):
    """الشاشةُ تعرض عشرة أعمدة عن خمسة وعشرين مزاداً في أربعة استعلامات.

    وعمودٌ واحدٌ محسوبٌ في حلقةٍ يعني خمسةً وعشرين ذهاباً إلى القاعدة لكل
    عمود — وهو ما كان يفعله v1.
    """
    auctions = [make_auction(AuctionState.LIVE) for _ in range(3)]
    for auction in auctions:
        make_vehicle(auction, VehicleState.LISTED, lot_number=1)

    with django_assert_num_queries(6):
        engine.summarise(auctions)


def test_an_auction_with_nothing_in_it_summarises_to_zeroes(make_auction):
    """صفٌّ فارغ لا `KeyError`: مزادٌ بلا سيارات يُعرض، ولا يُسقط الصفحة."""
    auction = make_auction(AuctionState.DRAFT)

    row = engine.summarise([auction])[auction.pk]

    assert (row.cars, row.images, row.bids, row.top_makes) == (0, 0, 0, ())
