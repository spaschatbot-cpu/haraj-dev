"""التحليلات: الحالات قسمةٌ تجمع، والمركز يقول ما تقوله شاشاته. T830-ب.

الرقمان اللذان بُنيت الشاشتان لأجلهما، وكلاهما مقيسٌ في إنتاج v1:

* «تحليل المزايدات» يعرض `6,503 + 70,146 + 81,475 = 158,124` بجوار إجماليٍّ
  معروضٍ `125,006` — فائضٌ ٣٣٬١١٨ لا تفسّره الشاشة.
* و«لوحة التقارير» تقول «المزايدات المقبولة 6,503» وتقول شاشتُها `4,378`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.console.analytics import bid_shape, report_totals, top_bidders
from apps.console.decisions import awarded
from apps.core.permissions import Role

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def viewer(client) -> User:
    user = User.objects.create_user(phone="966500000401", full_name="محلّل", password="x")
    user.is_staff = True
    user.console_role = Role.OWNER
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def bids(db):
    """أربع مزايداتٍ بالحالات الثلاث — ومنها **واحدةٌ مسحوبةٌ ومستبدَلةٌ معاً**.

    وتلك هي الصفُّ الذي يكشف العطل: من يعدّ «المسحوبة» و«المستبدَلة» بشرطين
    مستقلّين يعدّها مرّتين، فيصير مجموعُه أكبر من الكلّ — وهو شكل الفائض في
    v1 حرفياً. فبلا هذا الصفّ يمرّ الاختبار على تنفيذٍ خاطئ.
    """
    now = timezone.now()
    seller = User.objects.create_user(
        phone="966555558401", full_name="مالك التحليل", password="x"
    )
    Company.objects.create(user=seller, name="شركة التحليل")
    one = User.objects.create_user(
        phone="966555558402", full_name="مزايد أول", password="x"
    )
    two = User.objects.create_user(
        phone="966555558403", full_name="مزايد ثانٍ", password="x"
    )

    auction = Auction.objects.create(
        number=840,
        title="مزاد التحليل",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=2),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )
    car = Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="مازدا",
        model="سي اكس 9",
        year=2023,
        reserve_price=Decimal("30000.00"),
        state=VehicleState.BIDDING,
        owner_company=seller.company,
    )

    Bid.objects.create(vehicle=car, bidder=one, amount=Decimal("31000.00"))
    Bid.objects.create(
        vehicle=car, bidder=one, amount=Decimal("32000.00"), is_superseded=True
    )
    Bid.objects.create(
        vehicle=car,
        bidder=two,
        amount=Decimal("33000.00"),
        is_withdrawn=True,
        withdrawn_at=now,
    )
    Bid.objects.create(
        vehicle=car,
        bidder=two,
        amount=Decimal("34000.00"),
        is_withdrawn=True,
        withdrawn_at=now,
        is_superseded=True,
    )
    return car


# ---------------------------------------------------------------------------
# ١ — الحالات الثلاث قسمةٌ يساوي مجموعُها الإجمالي
# ---------------------------------------------------------------------------


def test_the_three_states_add_up_to_the_total(bids):
    """العطل المقيس في v1: `158,124` بجوار `125,006`، بلا سطرٍ يفسّر الفرق."""
    shape = bid_shape()
    parts = shape["withdrawn"] + shape["superseded"] + shape["standing"]

    assert parts == shape["total"] == Bid.objects.count() == 4


def test_a_bid_that_is_both_withdrawn_and_superseded_is_counted_once(bids):
    """الصفُّ الذي يجعل الشرطين المستقلَّين يفيضان — يُعدّ مرّةً هنا.

    مكتوبٌ منفصلاً لا مدموجاً في الذي قبله: لو دُمج لمرّ اختبارٌ يعدّ ثلاثةً
    من أربعة بحجّة أن المجموع «قريب».
    """
    shape = bid_shape()

    assert shape["withdrawn"] == 2
    assert shape["superseded"] == 1  # المسحوبةُ المستبدَلة ليست هنا
    assert shape["standing"] == 1


def test_a_refusal_is_not_one_of_the_three(bids):
    """محاولةٌ منعتها البوابة لم تصر مزايدةً، فلا تدخل قسمةَ المزايدات.

    و`BidRefusal` صفوفُه صفرٌ هنا: التجهيزة لا تُنشئ رفضاً. والمقصود إثباتُ
    أن العدّاد **منفصل** لا أن قيمته صفر — فلو أُدخل في القسمة لاختلّ
    المجموع فور أول رفض.
    """
    shape = bid_shape()
    assert "refused" in shape
    assert shape["withdrawn"] + shape["superseded"] + shape["standing"] == shape["total"]


def test_the_page_draws_the_comparison_rather_than_hiding_it(client, viewer, bids):
    """السطر الذي تُفتح الشاشة لأجله مرسومٌ فيها: المجموع بجوار الإجمالي."""
    body = client.get(reverse("console:analytics-bids")).content.decode()
    assert "مجموع الثلاثة" in body
    assert "يساوي الإجمالي" in body


def test_the_average_is_two_places_not_eighteen(bids):
    """تُرجع  — مبلغٌ لا يُقرأ ولا يوجد بهذه الدقّة.

    والتقريب في بايثون لا في القالب، فيُختبَر هنا. و تبقى : «لا
    مزايدة بعد» ليس «متوسّطها صفر».
    """
    average = bid_shape()["average"]
    assert average == Decimal("32500.00")
    assert average.as_tuple().exponent == -2

    Bid.objects.all().delete()
    assert bid_shape()["average"] is None


# ---------------------------------------------------------------------------
# ٢ — أعلى المزايدين
# ---------------------------------------------------------------------------


def test_top_bidders_name_how_many_vehicles_not_only_how_many_bids(bids):
    """`5,636` مزايدة على ١٢ سيارة شيء، وعلى ٥٬٠٠٠ شيءٌ آخر — والرقم وحده لا يفرّق."""
    rows = list(top_bidders())
    assert rows
    assert all("vehicles" in row for row in rows)
    assert rows[0]["bids"] == 2
    assert rows[0]["vehicles"] == 1


# ---------------------------------------------------------------------------
# ٣ — المركز يقول ما تقوله شاشاته
# ---------------------------------------------------------------------------


def test_the_hub_number_equals_the_screen_it_links_to(bids):
    """`6,503` هنا و`4,378` هناك هو العطل — ولا يُصان بتذكُّر، بل بمصدرٍ واحد."""
    assert report_totals()["awarded"] == awarded().count()
    assert report_totals()["bids"] == bid_shape()["total"]


def test_the_hub_links_to_every_number_it_shows(client, viewer, bids):
    """رقمٌ بلا بابٍ يُقرأ ولا يُتصرَّف فيه — وهي رئيسية v1 بعينها."""
    body = client.get(reverse("console:analytics")).content.decode()
    for url_name in (
        "console:accepted-bids",
        "console:accepted-summary",
        "console:analytics-bids",
        "console:why-no-bid",
        "console:auctions",
        "console:vehicles",
    ):
        assert reverse(url_name) in body, url_name
