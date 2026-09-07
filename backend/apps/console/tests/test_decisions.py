"""قرارات المزايدات: الشاشتان تعدّان الشيء نفسه، والضريبة لها قارئٌ واحد.

T830-أ. كل اختبارٍ هنا يقابل عطلاً **مقيساً في إنتاج v1**، لا احتمالاً:

* هناك تقول «المزايدات المقبولة» ٤٬٣٧٨ صفّاً ويقول «ملخّص المقبولة» بجوارها
  `0.00` و`0` — لأن كلاً منهما يرشّح بشيء.
* وهناك عشرة صفوفٍ «مقبولة» لمركبةٍ واحدة، ثلاثةٌ منها لشخصٍ واحد بمبالغ
  متصاعدة — أي مزايداتٌ مستبدَلة تُعرض فائزةً.
* وهناك الضريبة عمودٌ نصّيٌّ `15%` يُضرب فيه، والفاتورة القادمة من أودو تحمل
  مبلغاً شاملاً لها أصلاً.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.console.decisions import awarded, money_of, summary
from apps.core.permissions import Role
from apps.money.models import Invoice, InvoiceSource, InvoiceState

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def viewer(client) -> User:
    user = User.objects.create_user(phone="966500000301", full_name="مشرف", password="x")
    user.is_staff = True
    user.console_role = Role.OWNER
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def sale(db):
    """مركبةٌ رست على عميل، وأخرى ما زالت تنتظر قراراً."""
    now = timezone.now()
    buyer = User.objects.create_user(
        phone="966555557301", full_name="مشتري القرارات", password="x"
    )
    seller = User.objects.create_user(
        phone="966555557302", full_name="مالك القرارات", password="x"
    )
    Company.objects.create(user=seller, name="شركة القرارات")

    auction = Auction.objects.create(
        number=830,
        title="مزاد القرارات",
        starts_at=now - timezone.timedelta(days=2),
        ends_at=now - timezone.timedelta(days=1),
        state=AuctionState.ENDED,
        deposit_required=TEN_K,
    )
    won = Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="لاندكروزر",
        year=2024,
        plate_number="ر ر ب 1655",
        reserve_price=Decimal("100000.00"),
        state=VehicleState.AWARDED,
        awarded_to=buyer,
        awarded_price=Decimal("120000.00"),
        awarded_at=now,
        owner_company=seller.company,
    )
    Vehicle.objects.create(
        auction=auction,
        lot_number=2,
        make="نيسان",
        model="باترول",
        year=2023,
        reserve_price=Decimal("90000.00"),
        state=VehicleState.AWAITING_DECISION,
        owner_company=seller.company,
    )
    return won


# ---------------------------------------------------------------------------
# ١ — صفٌّ واحدٌ لكل مركبة، لا صفٌّ لكل مزايدة
# ---------------------------------------------------------------------------


def test_only_vehicles_that_were_awarded_are_listed(sale):
    """المنتظِرة قراراً ليست «مقبولة» — وv1 يخلطهما تحت اسمٍ واحد."""
    rows = list(awarded())
    assert [row.pk for row in rows] == [sale.pk]


def test_an_awarded_vehicle_appears_once_however_many_bids_it_took(client, viewer, sale):
    """عشرة صفوفٍ لمركبةٍ واحدة هو ما تعرضه v1 — وهنا لا يقع بالبناء.

    ليست قاعدةً تُصان في الشاشة: `Vehicle.awarded_to` حقلٌ واحد، ويرفض قيدُ
    `an_awarded_vehicle_names_its_winner` حالةَ `AWARDED` بلا فائز. فالصفُّ
    مركبةٌ لا مزايدة، ولا يمكن للشاشة أن تعرض فائزين اثنين على سيارة.
    """
    body = client.get(reverse("console:accepted-bids")).content.decode()
    assert body.count("لاندكروزر") == 1


# ---------------------------------------------------------------------------
# ٢ — الملخّص يعدّ ما تعدّه القائمة
# ---------------------------------------------------------------------------


def test_the_summary_counts_exactly_what_the_list_lists(sale):
    """العطل الذي يُقاس على شاشة v1: ٤٬٣٧٨ صفّاً بجوار ملخّصٍ يقول صفراً.

    ولا يُصان ذلك بتعليق: الدالّتان تستدعيان `awarded()` نفسها، وهذا الاختبار
    هو ما يمنع أن يُضاف مرشّحٌ إلى إحداهما وحدها لاحقاً.
    """
    assert summary()["count"] == awarded().count()


@pytest.mark.parametrize("text,expected", [("لاندكروزر", 1), ("باترول", 0)])
def test_the_summary_follows_the_same_filter_as_the_list(sale, text, expected):
    """مرشّحٌ يُطبَّق على القائمة ولا يُطبَّق على الملخّص هو العطل نفسه."""
    assert summary(text=text)["count"] == awarded(text=text).count() == expected


# ---------------------------------------------------------------------------
# ٣ — الضريبة من الفاتورة، لا من سعر الترسية
# ---------------------------------------------------------------------------


def test_an_awarded_vehicle_with_no_invoice_shows_no_tax(sale):
    """صفرٌ هنا كذبة: لا ضريبةَ على مبلغٍ لم يُفوتَر، و«لا يوجد» ليس صفراً."""
    split = money_of(sale)
    assert split["invoice"] is None
    assert split["tax"] is None
    assert split["total"] is None


def test_the_screen_says_uninvoiced_rather_than_printing_a_zero(client, viewer, sale):
    """الخانة الفارغة تُقرأ «لم يُحسب»؛ والنصّ يقول «لم يُفوتَر» — والفرق عمل."""
    body = client.get(reverse("console:accepted-bids")).content.decode()
    assert "بلا فاتورة" in body


def test_the_tax_comes_from_tax_of_not_from_the_awarded_price(sale):
    """فاتورةٌ محليّة: المبلغ **قبل** الضريبة، فتُضاف فوقه.

    والرقم لا يُكتب هنا: يُقارَن بما تُرجعه `money.services.tax_of` نفسها، فلو
    تغيّرت النسبة بقي الاختبار صحيحاً — واختبارٌ يثبّت `18000.00` كان سيصير
    الموضع الثاني الذي يعرف النسبة، وهو ما يرفضه `one_tax_rule.py`.
    """
    from apps.money import services as money

    invoice = Invoice.objects.create(
        customer=sale.awarded_to,
        vehicle=sale,
        number="INV/830/1",
        amount=sale.awarded_price,
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.LOCAL,
    )

    split = money_of(sale)
    expected = money.tax_of(invoice)

    assert split["base"] == expected.base == sale.awarded_price
    assert split["tax"] == expected.tax
    assert split["total"] == expected.total == expected.base + expected.tax


def test_an_odoo_invoice_is_not_taxed_a_second_time(sale):
    """الفخّ الأدقّ في ملفات v1: مبلغٌ شاملٌ للضريبة تُضاف عليه ثانيةً.

    الفاتورة من أودو تحمل الإجمالي؛ فإجماليُّها **هو** مبلغها، والقاعدةُ
    مستخرَجةٌ منه لا مضافةٌ إليه. ولو ضربت هذه الشاشة في النسبة لظهر هنا فرقٌ
    قدرُه ١٥٪ على نصف الصفوف.
    """
    invoice = Invoice.objects.create(
        customer=sale.awarded_to,
        vehicle=sale,
        number="INV/830/2",
        amount=Decimal("115000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
        source=InvoiceSource.ODOO_SYNC,
    )

    split = money_of(sale)
    assert split["invoice"] == invoice
    assert split["total"] == invoice.amount
    assert split["base"] + split["tax"] == invoice.amount
    assert split["base"] < invoice.amount


# ---------------------------------------------------------------------------
# ٤ — الشاشتان قراءةٌ محضة
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url_name", ["console:accepted-bids", "console:accepted-summary"]
)
def test_nothing_on_them_writes(client, viewer, sale, url_name):
    """الترسية في `auctions.services` والفاتورة في `money.services`.

    وشاشةٌ تعرض ما وقع لا تكون باب تغييرٍ فيه: النموذج الوحيد فيهما `GET`.
    """
    body = client.get(reverse(url_name)).content.decode()
    main = body.split("<main>")[1].split("</main>")[0]
    assert 'method="post"' not in main.lower()
