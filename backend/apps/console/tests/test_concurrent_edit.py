"""HR-13 — موظفان على صفٍّ واحد، ولا أحد يعلم أن تعديله مُحي.

**العطل في v1** (`PHASE_04` §3-1، و`TASK_03` §3-1 بنصّه): «موظفان يقومان
بتعديل نفس المزاد في نفس اللحظة فيمسح أحدهما تعديلات الآخر». وليس في ذلك
رسالةٌ ولا أثر: الثاني يحفظ استمارةً رُسمت قبل دقائق، فتُكتب قيمها فوق ما
كتبه الأول، ويمضي كلاهما وهو يظنّ أن تعديله قائم.

**ولماذا لا يكفي سجلّ التدقيق:** هو يقول ماذا صار الصفّ، لا أن أحداً دُهس.
`before` في قيد الثاني يحمل ما كتبه الأول فعلاً، فالسجلّ صحيحٌ تماماً وهو
يصف محواً لا يعرف أنه محو. من يقرؤه لاحقاً يرى تعديلين متتاليين مشروعين.

**والقياس هنا آخِرُ الكتابة لا آخِرُ القراءة.** الاستمارة تحمل ختماً لحالة
الصفّ ساعةَ رُسمت؛ فإن اختلف عمّا في القاعدة ساعةَ الحفظ، فبين اللحظتين كتب
أحدٌ آخر. والرفض حينئذٍ ليس تشدّداً — هو الجواب الوحيد الصادق، لأن دمج
النيّتين ليس شيئاً يملك الخادم أن يفعله نيابةً عن أحد.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
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
    client.force_login(staff(Role.OPERATIONS, "966500000021"))
    return client


@pytest.fixture
def owner(client):
    client.force_login(staff(Role.OWNER, "966500000022"))
    return client


@pytest.fixture
def auction(db) -> Auction:
    from django.utils import timezone

    now = timezone.now()
    return Auction.objects.create(
        number=901,
        title="مزاد الدمّام",
        starts_at=now,
        ends_at=now + timezone.timedelta(days=1),
        state=AuctionState.DRAFT,
        deposit_required=Decimal("10000.00"),
    )


@pytest.fixture
def car(auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal("50000.00"),
    )


def stamp_in(body: str) -> str:
    """الختم كما رسمته الصفحة — يُقرأ من الاستمارة لا يُبنى في الاختبار.

    اختبارٌ يحسب الختم بنفسه يختبر حسابه هو، ويمرّ ولو لم ترسم الصفحة الحقل
    أصلاً — وحينها لا ختم مع أي حفظٍ حقيقيّ.
    """
    marker = 'name="row_stamp"'
    assert marker in body, "الصفحة لم ترسم حقل الختم"
    tail = body[body.index(marker) :]
    value = tail[tail.index('value="') + len('value="') :]
    return value[: value.index('"')]


def test_the_second_save_of_a_stale_form_is_refused(operator, auction):
    """الحادثة بنصّها: اثنان على مزادٍ واحد، والثاني يحفظ استمارةً قديمة."""
    url = reverse("console:auction-edit", args=[auction.pk])
    stale = stamp_in(operator.get(url).content.decode())

    # الأول حفظ — من مكانٍ آخر، وهو ما لا تعرفه استمارة الثاني.
    Auction.objects.filter(pk=auction.pk).update(title="عنوان الأول")

    response = operator.post(
        url,
        {
            "number": "901",
            "title": "عنوان الثاني",
            "starts_at": "2026-01-01 10:00",
            "ends_at": "2026-01-02 10:00",
            "deposit_required": "10000.00",
            "reason": "تصحيح",
            "row_stamp": stale,
        },
    )

    assert response.status_code == 200, "الرفض انتهى إلى تحويلٍ لا إلى الاستمارة"
    auction.refresh_from_db()
    assert auction.title == "عنوان الأول", "مُحي تعديل الأول"
    assert "عُدِّل" in response.content.decode(), "رُفض بلا جملة تقول لماذا"


def test_a_fresh_form_still_saves(operator, auction):
    """الحارس الذي يمنع الحفظ السليم يُطفأ في أسبوع."""
    url = reverse("console:auction-edit", args=[auction.pk])
    fresh = stamp_in(operator.get(url).content.decode())

    operator.post(
        url,
        {
            "number": "901",
            "title": "عنوان مصحَّح",
            "starts_at": "2026-01-01 10:00",
            "ends_at": "2026-01-02 10:00",
            "deposit_required": "10000.00",
            "reason": "تصحيح",
            "row_stamp": fresh,
        },
    )

    auction.refresh_from_db()
    assert auction.title == "عنوان مصحَّح"


def test_the_vehicle_screen_is_stamped_too(operator, car):
    """أربع شاشات ترث `ReasonMixin`، والقاعدة تُكتب مرة."""
    url = reverse("console:vehicle-edit", args=[car.pk])
    stale = stamp_in(operator.get(url).content.decode())

    Vehicle.objects.filter(pk=car.pk).update(make="نيسان")

    operator.post(
        url,
        {
            "auction": car.auction_id,
            "lot_number": "1",
            "make": "هوندا",
            "model": "كامري",
            "year": "2020",
            "plate_type": "private",
            "transmission": "unknown",
            "fuel_type": "unknown",
            "condition": "unknown",
            "reserve_price": "50000.00",
            "reason": "تصحيح",
            "row_stamp": stale,
        },
    )

    car.refresh_from_db()
    assert car.make == "نيسان", "مُحي تعديل الأول على المركبة"


def test_the_customer_screen_is_stamped_too(owner, db):
    """`User` بلا `updated_at`، والختم على حقول الاستمارة فلا يحتاج عموداً."""
    customer = User.objects.create_user(
        phone="966501234567", full_name="اسم أول", password="x"
    )
    url = reverse("console:customer-edit", args=[customer.pk])
    stale = stamp_in(owner.get(url).content.decode())

    User.objects.filter(pk=customer.pk).update(full_name="اسم الأول")

    owner.post(
        url,
        {
            "full_name": "اسم الثاني",
            "email": "",
            "national_id": "",
            "account_type": "individual",
            "reason": "تصحيح",
            "row_stamp": stale,
        },
    )

    customer.refresh_from_db()
    assert customer.full_name == "اسم الأول", "مُحي تعديل الأول على العميل"


def test_a_new_row_needs_no_stamp(operator):
    """لا صفَّ بعد، فلا شيء يُدهَس. واشتراط ختمٍ هنا يمنع الإنشاء بلا سبب."""
    response = operator.post(
        reverse("console:auction-new"),
        {
            "number": "902",
            "title": "مزاد جديد",
            "starts_at": "2026-01-01 10:00",
            "ends_at": "2026-01-02 10:00",
            "deposit_required": "10000.00",
            "reason": "مزاد الأسبوع",
        },
        follow=True,
    )

    assert response.status_code == 200
    assert Auction.objects.filter(number=902).exists()
