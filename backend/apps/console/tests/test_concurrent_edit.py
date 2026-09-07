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
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.console.forms import AuctionForm
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


# ---------------------------------------------------------------------------
# HR-13ب — الختم لا يُحسب على لا شيء
# ---------------------------------------------------------------------------


def declared_like(**meta) -> type[AuctionForm]:
    """استمارةُ مزادٍ بـ`Meta` أخرى — تُبنى هنا لا تُكتب، فالمقصود شكل الإعلان."""
    return type(
        "Declared", (AuctionForm,), {"Meta": type("Meta", (AuctionForm.Meta,), meta)}
    )


def another_auction() -> Auction:
    """صفٌّ يختلف عن تجهيزة `auction` في كل عمودٍ تكتبه الاستمارة."""
    now = timezone.now()
    return Auction.objects.create(
        number=991,
        title="مزاد آخر تماماً",
        starts_at=now - timezone.timedelta(days=3),
        ends_at=now + timezone.timedelta(days=3),
        state=AuctionState.DRAFT,
        deposit_required=Decimal("25000.00"),
    )


@pytest.mark.parametrize(
    "meta",
    [
        pytest.param({"fields": None, "exclude": ("number",)}, id="exclude"),
        pytest.param({"fields": "__all__"}, id="all-fields"),
    ],
)
def test_a_form_that_does_not_list_its_fields_still_stamps_its_row(auction, meta):
    """صفّان مختلفان، ختمان مختلفان — مهما كُتبت `Meta`.

    ‏`Meta.fields` ليست دائماً قائمة أسماء: استمارةٌ تكتب `"__all__"`، أو تترك
    `fields` وتكتب `exclude` بدلها، يجعلها Django `None` في الحالتين. وكان
    الختم يُقرأ منها مباشرةً، فيُحسب على النصّ الفارغ ويخرج **واحداً لكلّ
    الصفوف**: يقارن الفحصُ حينئذٍ ثابتاً بثابت فيمرّ دائماً، ويعود المحو
    الصامت — والحقل المخفيّ ما يزال يُرسم في الصفحة، فلا شيء يبدو معطوباً.

    مقيسٌ لا مُخمَّن: قبل الإصلاح أعطت الحالتان مزادين مختلفين البصمة نفسها،
    وهي `e3b0c442…` — بصمة النصّ الفارغ.
    """
    other = another_auction()
    form_class = declared_like(**meta)

    mine = form_class(instance=auction).initial["row_stamp"]
    theirs = form_class(instance=other).initial["row_stamp"]

    assert mine != theirs, "ختمٌ واحد لصفّين — الفحص يقارن ثابتاً بثابت"


def test_a_form_with_no_stampable_column_screams_instead_of_passing(auction):
    """الفحص الذي لا يجد ما يحرسه يصرخ ولا يمرّ (المادة ٤).

    استمارةُ تعديلٍ تستثني كلّ أعمدتها لا يحرسها هذا الحارس. أن ترفع خطأً عند
    الرسم عطلٌ يُرى في الحال؛ وأن تُخرج بصمة النصّ الفارغ عطلٌ لا يُرى حتى
    يُمحى عملُ أحدهم.
    """
    every_column = tuple(
        field.name
        for field in Auction._meta.fields
        if field.editable and not field.auto_created
    )

    with pytest.raises(ImproperlyConfigured, match="HR-13"):
        declared_like(fields=None, exclude=every_column)(instance=auction)
