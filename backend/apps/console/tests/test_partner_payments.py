"""اعتماد مدفوعات الشريك: ملفٌّ يُقيَّد، لا جدولٌ موازٍ. T830-ي.

ثلاث جملٍ مكتوبةٍ على شاشة v1 صارت هنا بناءً، ولكلٍّ منها اختبارٌ:

* «تجنّب رفع الملف نفسه مرتين حتى لا تُسجَّل الدفعة مرتين» ← بصمةٌ فريدة.
* «الصفوف تُضاف ولا يُحذف شيء» + زرُّ حذف ← لا حذفَ، والتصحيح عكسُ قيد.
* «المبلغ فارغ = أعلى عرض» ← لا تخمين؛ الصفُّ بلا مبلغٍ يُتخطّى ويُذكر.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.console.partner_payments import read_rows
from apps.core.permissions import Role
from apps.core.sheets import Sheet, SheetError
from apps.money.models import Invoice, InvoiceSource, InvoiceState, PaymentSheet

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")
URL = "console:partner-payments-approve"


@pytest.fixture
def viewer(client) -> User:
    user = User.objects.create_user(phone="966500000601", full_name="مالية", password="x")
    user.is_staff = True
    user.console_role = Role.OWNER
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def sold(db):
    """مركبةُ شريكٍ رست وفُوتِرت — الصفُّ الذي يقبل دفعة."""
    now = timezone.now()
    seller = User.objects.create_user(
        phone="966555560601", full_name="شريك الدفعات", password="x"
    )
    Company.objects.create(user=seller, name="شركة الدفعات")
    buyer = User.objects.create_user(
        phone="966555560602", full_name="مشتري الدفعات", password="x"
    )

    auction = Auction.objects.create(
        number=860,
        title="مزاد الدفعات",
        starts_at=now - timezone.timedelta(days=2),
        ends_at=now - timezone.timedelta(days=1),
        state=AuctionState.ENDED,
        deposit_required=TEN_K,
    )
    car = Vehicle.objects.create(
        auction=auction,
        lot_number=7,
        make="تويوتا",
        model="لاندكروزر",
        year=2024,
        vin="SHEET0000000001",
        plate_number="ر ر ب 1655",
        reserve_price=Decimal("50000.00"),
        state=VehicleState.AWARDED,
        awarded_to=buyer,
        awarded_price=Decimal("60000.00"),
        awarded_at=now,
        owner_company=seller.company,
    )
    Invoice.objects.create(
        customer=buyer,
        vehicle=car,
        number="INV/860/1",
        amount=Decimal("60000.00"),
        state=InvoiceState.OPEN,
        issued_at=now,
        source=InvoiceSource.LOCAL,
    )
    return car


def _csv(body: str) -> SimpleUploadedFile:
    return SimpleUploadedFile(
        "payments.csv", body.encode("utf-8"), content_type="text/csv"
    )


# ---------------------------------------------------------------------------
# ١ — البصمة: الملفُّ نفسه لا يُرفع مرّتين
# ---------------------------------------------------------------------------


def test_the_same_file_twice_is_refused_before_a_row_is_read(client, viewer, sold):
    """«تجنّب رفع الملف نفسه مرتين» تذكيرٌ في v1 — ومفتاحٌ هنا.

    ورافعُ الملفّ مرّتين ليس مهملاً غالباً: هو من انقطع اتصالُه فأعاد، أو لم
    يجد رسالة نجاحٍ فضغط. والتحذير لا يمنع أيّاً من الاثنين.
    """
    body = "الشاصي,المبلغ\nSHEET0000000001,60000\n"

    client.post(reverse(URL), {"sheet": _csv(body)})
    assert PaymentSheet.objects.count() == 1
    assert PaymentSheet.objects.first().rows_posted == 1

    response = client.post(reverse(URL), {"sheet": _csv(body)}, follow=True)

    # لا صفَّ ثانٍ، ولا قيدَ ثانٍ.
    assert PaymentSheet.objects.count() == 1
    sold.refresh_from_db()
    assert Invoice.objects.get(vehicle=sold).amount_paid == Decimal("60000.00")
    assert "مرفوعٌ من قبل" in response.content.decode()


def test_a_posted_row_moves_the_invoice_not_a_side_table(client, viewer, sold):
    """الفرق كلُّه: الدفعة تصل الفاتورة، فيراها المحاسب والشريك معاً."""
    client.post(
        reverse(URL),
        {"sheet": _csv("الشاصي,المبلغ\nSHEET0000000001,60000\n")},
    )

    invoice = Invoice.objects.get(vehicle=sold)
    assert invoice.amount_paid == Decimal("60000.00")
    assert invoice.state == InvoiceState.PAID


# ---------------------------------------------------------------------------
# ٢ — لا تخمينَ لمبلغ
# ---------------------------------------------------------------------------


def test_a_row_with_no_amount_is_skipped_not_guessed():
    """v1: «اتركه فارغاً = أعلى عرض» — فتُقيَّد دفعةٌ على رقمٍ لم يكتبه أحد."""
    sheet = Sheet(headers=["الشاصي", "المبلغ"], rows=[["SHEET0000000001", ""]])
    good, skipped = read_rows(sheet)

    assert good == []
    assert skipped[0]["why"] == "المبلغ ليس رقماً موجباً"


@pytest.mark.parametrize("bad", ["0", "-5", "كلام", "1,2,3.4.5"])
def test_an_amount_that_is_not_a_positive_number_is_skipped(bad):
    """صفرٌ وسالبٌ وحرفٌ — والثلاثة تُذكر لا تُبتلع."""
    sheet = Sheet(headers=["الشاصي", "المبلغ"], rows=[["SHEET0000000001", bad]])
    good, skipped = read_rows(sheet)

    assert good == []
    assert len(skipped) == 1


def test_a_file_without_the_needed_columns_is_refused_whole():
    """ملفٌّ بلا عمود مفتاحٍ أو مبلغ لا يُقيَّد منه صفٌّ واحد."""
    sheet = Sheet(headers=["الاسم", "الملاحظات"], rows=[["أحمد", "شيء"]])
    with pytest.raises(SheetError):
        read_rows(sheet)


# ---------------------------------------------------------------------------
# ٣ — الصفُّ الذي لا يطابق يُذكر بسببه
# ---------------------------------------------------------------------------


def test_a_row_that_matches_no_vehicle_is_named(client, viewer, sold):
    """v1 يقول «يُتخطّى ويُذكر لك» — والزيادة هنا أن السبب مكتوب."""
    response = client.post(
        reverse(URL),
        {"sheet": _csv("الشاصي,المبلغ\nLAYOUJADSHASI,900\n")},
        follow=True,
    )
    body = response.content.decode()

    assert "لا مركبةً مرساةً واحدةً بهذا المفتاح" in body
    assert PaymentSheet.objects.first().rows_posted == 0
    assert PaymentSheet.objects.first().rows_skipped == 1


def test_a_vehicle_that_was_not_sold_is_not_settled(client, viewer, sold):
    """`فورد ميلان #12276` في إنتاج v1: صفر مزايدات، ومعها زرُّ اعتماد سداد."""
    unsold = Vehicle.objects.create(
        auction=sold.auction,
        lot_number=8,
        make="فورد",
        model="ميلان",
        year=2010,
        vin="SHEET0000000002",
        reserve_price=Decimal("20000.00"),
        state=VehicleState.LISTED,
        owner_company=sold.owner_company,
    )
    client.post(
        reverse(URL),
        {"sheet": _csv("الشاصي,المبلغ\nSHEET0000000002,900\n")},
    )

    unsold.refresh_from_db()
    assert unsold.state == VehicleState.LISTED
    assert PaymentSheet.objects.first().rows_posted == 0


# ---------------------------------------------------------------------------
# ٤ — لا حذف
# ---------------------------------------------------------------------------


def test_the_screen_offers_no_delete(client, viewer, sold):
    """حذفُ صفِّ دفعةٍ من الدفتر محوُ تدقيق — والتصحيح عكسُ قيد.

    ويُقرأ من `<main>`: الفقرةُ التي تشرح ذلك تذكر الكلمة، فالبحث في الصفحة
    كلّها كان سيسقط على شرحها هي — ولذلك يُقرأ الجدول وحده.
    """
    client.post(reverse(URL), {"sheet": _csv("الشاصي,المبلغ\nSHEET0000000001,60000\n")})
    body = client.get(reverse(URL)).content.decode()
    rows = body.split("<tbody>")[-1].split("</tbody>")[0]

    assert "حذف" not in rows
    assert "delete" not in rows.lower()


def test_the_upload_is_recorded_with_who_and_when(client, viewer, sold):
    """«هذه الدفعة من أين؟» سؤالٌ يُسأل بعد شهر، ولا يُجاب بمبلغٍ وتاريخ."""
    client.post(reverse(URL), {"sheet": _csv("الشاصي,المبلغ\nSHEET0000000001,60000\n")})

    sheet = PaymentSheet.objects.get()
    assert sheet.uploaded_by == viewer
    assert sheet.filename == "payments.csv"
    assert sheet.total == Decimal("60000.00")
    assert len(sheet.digest) == 64


def test_an_empty_file_is_refused_with_a_sentence(client, viewer):
    """رسالةٌ بالعربية لا أثرُ استثناء: من يرفع ملفاً فارغاً يريد أن يعرف."""
    empty = SimpleUploadedFile("x.csv", b"", content_type="text/csv")
    response = client.post(reverse(URL), {"sheet": empty}, follow=True)

    assert PaymentSheet.objects.count() == 0
    assert "الملف فارغ" in response.content.decode()


def test_reading_a_workbook_needs_no_database(tmp_path):
    """`read_rows` تُسأل عن ملفٍّ سيّئ بلا قاعدة — ولذلك فُصلت عن الكتابة."""
    del tmp_path
    sheet = Sheet(
        headers=["اللوحة", "المبلغ", "ملاحظات"],
        rows=[["ر ر ب 1655", "1,500.50", "تحويل"], ["", "900", ""]],
    )
    good, skipped = read_rows(sheet)

    assert good[0]["amount"] == Decimal("1500.50")
    assert good[0]["note"] == "تحويل"
    assert skipped[0]["why"] == "لا مفتاح في الصفّ"
