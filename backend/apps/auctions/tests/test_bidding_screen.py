"""شاشة المزايدة كما يعرضها v1 — الرسوم والضريبة ومعرض الصور.

قِيست الشاشة من الإنتاج الحيّ في `specs/011-customer-web/v1-card-parity.md`،
وهذه الاختبارات تحرس الشقّ الذي يخصّ الخلفية منها:

* **رسمٌ إداريّ ورسمٌ مع الضريبة** يصلان **محسوبَين** مع الكرت. الويب ممنوع
  من ضرب مبلغٍ في نسبة (`ops/checks/web_money_is_never_computed.mjs`)، فإن لم
  يصل الرقم محسوباً لم يصل أصلاً؛
* **`POST /api/v1/bids/quote/`** الذي يجيب عن «السعر + الضريبة (15%)» بينما
  يكتب المزايد. وهو السطر الوحيد في تلك الشاشة الذي لا يمكن أن يُرسَل مسبقاً؛
* **`GET /api/v1/vehicles/{id}/images/`** — قناة طبقة المعاينة (HR-12ب)، التي
  كانت تُولَّد وتُخزَّن ولا يستطيع أي عميل طلبها.

وكلّها تُقاس على النسبة كما هي في الإعدادات لا على «٩٢٠» مكتوبةً بيد حيثما
أمكن: رقمٌ محفوظٌ في اختبارٍ هو نسخةٌ ثانية من المعادلة، وهي تُصدّق نفسها يوم
تتغيّر النسبة وتكذب على الشاشة.
"""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts import tokens as token_service
from apps.auctions import services
from apps.auctions.cards import card_queryset, vehicle_card
from apps.auctions.states import AuctionState, VehicleState
from apps.money import services as money

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def live_auction(make_auction):
    return make_auction(state=AuctionState.LIVE)


@pytest.fixture
def vehicle(live_auction, make_vehicle):
    return make_vehicle(live_auction, state=VehicleState.LISTED)


def a_photograph(name="car.png", size=(2400, 1600)) -> SimpleUploadedFile:
    buffer = BytesIO()
    Image.new("RGB", size, (120, 140, 160)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def bidder(customer):
    """عميلٌ ومعه عميلُ HTTP يحمل رمزه — النقطة تحتاج جلسةً كما تحتاجها المزايدة."""
    api = APIClient()
    api.credentials(
        HTTP_AUTHORIZATION=f"Bearer {token_service.issue_pair(customer)['access']}"
    )
    return api


def quote(api, written: str):
    return api.post(reverse("bidding_api:bid-quote"), {"amount": written}, format="json")


def a_card(vehicle):
    """البطاقة كما تصل العميل، مقروءةً عبر `card_queryset` كما تقرؤها الشاشة."""
    return vehicle_card(card_queryset().get(pk=vehicle.pk))


# ---------------------------------------------------------------------------
# الرسوم على الكرت
# ---------------------------------------------------------------------------


def test_the_card_carries_the_admin_fee_and_the_fee_with_tax(vehicle):
    card = a_card(vehicle)

    assert card["admin_fee"] == "800.00"
    assert card["admin_fee_with_vat"] == "920.00"


def test_the_fee_with_tax_follows_the_rate_and_is_not_a_stored_number(settings, vehicle):
    """النسبة تُغيَّر فيتغيّر الرقم — وإلا كان الرقم محفوظاً لا محسوباً.

    وهذه هي المخالفة المصنوعة لهذا الحقل: رقمٌ ثابتٌ في العمود أو في الكرت
    يمرّ الاختبارَ الأول ويسقط هنا.
    """
    settings.VAT_RATE = "0.05"

    assert a_card(vehicle)["admin_fee_with_vat"] == "840.00"


def test_the_fee_is_a_property_of_the_auction_not_the_car(make_auction, make_vehicle):
    """‏v1 يحمله في `auctions.fees`، فمزادان برسمين ومركباتُ كلٍّ تتبع مزادها."""
    cheap = make_auction(state=AuctionState.LIVE, admin_fee=Decimal("300.00"))
    dear = make_auction(state=AuctionState.LIVE, admin_fee=Decimal("1200.00"))

    first = make_vehicle(cheap, state=VehicleState.LISTED)
    second = make_vehicle(dear, state=VehicleState.LISTED)

    assert a_card(first)["admin_fee"] == "300.00"
    assert a_card(second)["admin_fee"] == "1200.00"


def test_the_fee_is_not_the_deposit(live_auction):
    """التأمين يُحجَز ويُردّ، والرسم يُدفَع ولا يُردّ — عمودان لا عمود.

    ودمجُهما هو العطل الذي يجعل ردَّ التأمين يردّ الرسم معه.
    """
    assert live_auction.admin_fee != live_auction.deposit_required


# ---------------------------------------------------------------------------
# قاعدة الضريبة الواحدة
# ---------------------------------------------------------------------------


def test_tax_added_to_is_the_same_rule_the_invoice_uses(customer):
    """فرعُ الفاتورة المحلية في `tax_of` هو `tax_added_to` نفسه، لا نسخةٌ منه.

    وهذا ما يجعل «الرسوم + الضريبة» على الشاشة و«المطلوب» على الفاتورة رقماً
    واحداً حين يكون المبلغ واحداً.
    """
    invoice = money.issue_invoice(customer=customer, amount=Decimal("800.00"))

    assert money.tax_of(invoice).total == money.tax_added_to(Decimal("800.00")).total


def test_tax_added_to_rounds_the_tax_and_keeps_the_total_equal_to_its_parts():
    """فاتورةٌ لا تساوي بنودُها مجموعَها فاتورةٌ لا يقبلها مراجع."""
    split = money.tax_added_to(Decimal("333.33"))

    assert split.total == split.base + split.tax
    assert split.tax == Decimal("50.00")


# ---------------------------------------------------------------------------
# نقطة «السعر + الضريبة»
# ---------------------------------------------------------------------------


def test_the_quote_endpoint_answers_with_strings(bidder):
    response = quote(bidder, "48500.75")

    assert response.status_code == 200
    assert response.json() == {
        "amount": "48500.75",
        "tax": "7275.11",
        "total": "55775.86",
    }


def test_the_quote_refuses_what_the_bid_would_refuse(bidder):
    """‏`1e5` مبلغٌ صحيحٌ في جافاسكربت ولا شيء في الريالات.

    والنمط هو نمط `PlaceBidSerializer` حرفاً بحرف: مبلغٌ يقبله العرضُ وترفضه
    المزايدة وعدٌ بخطأٍ بعد أن يقرأ العميل رقماً ويقرّر.
    """
    assert quote(bidder, "1e5").status_code == 400


def test_the_quote_needs_a_session(db):
    assert quote(APIClient(), "100.00").status_code == 401


def test_the_quote_writes_nothing(bidder):
    """لا قيد ولا مزايدة ولا صفّ — سؤالٌ لا حدث."""
    from apps.bidding.models import Bid
    from apps.money.models import Entry

    before = (Bid.objects.count(), Entry.objects.count())

    quote(bidder, "9000.00")

    assert (Bid.objects.count(), Entry.objects.count()) == before


# ---------------------------------------------------------------------------
# معرض الصور — HR-12ب
# ---------------------------------------------------------------------------


def test_the_gallery_hands_out_the_preview_tier(client, vehicle):
    """الطبقة التي كانت تُولَّد ولا يستطيع أحد طلبها — وهذه هي القناة."""
    services.add_image(vehicle, a_photograph(), cover=True)

    response = client.get(reverse("auctions_api:vehicle-images", args=[vehicle.pk]))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    shot = body["results"][0]
    assert shot["preview_url"] and "preview" in shot["preview_url"]
    assert shot["thumbnail_url"] and shot["thumbnail_url"] != shot["preview_url"]


def test_the_gallery_counts_every_image_and_puts_the_cover_first(client, vehicle):
    """عدّاد v1 يقول `1 / 9`، و«١» فيه هي الصورة التي رآها العميل على الكرت.

    فترتيبٌ آخر يعني أن الضغط على كرتٍ يفتح صورةً غير التي ضُغطت.
    """
    services.add_image(vehicle, a_photograph("a.png"))
    services.add_image(vehicle, a_photograph("b.png"))
    cover = services.add_image(vehicle, a_photograph("c.png"), cover=True)

    body = client.get(reverse("auctions_api:vehicle-images", args=[vehicle.pk])).json()

    assert body["total"] == 3
    assert body["results"][0]["id"] == cover.pk
    assert body["results"][0]["is_cover"] is True


def test_the_gallery_of_a_hidden_car_is_a_404_not_a_403(
    client, make_vehicle, live_auction
):
    """تأكيدُ وجود الصفّ وحده يكفي لعدّ مزادٍ قبل أن يُفتح."""
    hidden = make_vehicle(live_auction, state=VehicleState.DRAFT)

    response = client.get(reverse("auctions_api:vehicle-images", args=[hidden.pk]))

    assert response.status_code == 404


def test_the_gallery_urls_are_absolute_like_the_card(settings, client, vehicle):
    """المتصفّح ليس هو الخادم: مسارٌ نسبيّ يعني ٤٠٤ على أصل الويب.

    وهي الحادثة نفسها التي جعلت `_thumbnail_url` تقرأ `MEDIA_BASE_URL` —
    ولذلك يقرؤها المعرض من **الدالة نفسها**، لا من نسخةٍ ثانية.
    """
    settings.MEDIA_BASE_URL = "https://media.example.test"
    services.add_image(vehicle, a_photograph(), cover=True)

    shot = client.get(reverse("auctions_api:vehicle-images", args=[vehicle.pk])).json()[
        "results"
    ][0]

    assert shot["preview_url"].startswith("https://media.example.test/")
    assert shot["thumbnail_url"].startswith("https://media.example.test/")


def test_the_card_stays_the_size_it_was(vehicle):
    """المعرض نقطةٌ ثانية، فالكرت لا يكبر — T609 وقائمةُ الخمسين سيارة."""
    services.add_image(vehicle, a_photograph(), cover=True)

    card = a_card(vehicle)

    assert "images" not in card
    assert "preview_url" not in card
