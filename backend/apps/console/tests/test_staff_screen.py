"""إدارة المشرفين وتقرير مزايدات المستخدم. T830-ج.

الشاشتان من قسم «إدارة الأعضاء» في v1، ولكلٍّ منهما عطلٌ مقيسٌ لا يُنقَل:

* `/admins` تعرض زرَّ حذفٍ في كل صفّ، وتستثني اثنين بنصّ. والاستثناءان صحيحان
  والزرُّ نفسه هو الخطأ — وهنا لا زرَّ أصلاً.
* وعمود حالتها يقول «نشط الآن» في سبعةٍ وثلاثين من سبعةٍ وثلاثين.
* و`/users/bids-report` تحسن واحدة يجب أن تُنقَل بنصّها: لا تفتح على أصفار.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Company, StaffGrant, User
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding.models import Bid
from apps.console.analytics import report_for
from apps.console.staff import staff_rows
from apps.core.permissions import Capability, Role

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def viewer(client) -> User:
    user = User.objects.create_user(
        phone="966500000501", full_name="مالك اللوحة", password="x"
    )
    user.is_staff = True
    user.console_role = Role.OWNER
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def crew(db, viewer):
    """موظّفان غير القارئ: أحدهما معطَّل، والآخر بلا دورٍ مكتوب."""
    off = User.objects.create_user(
        phone="966500000502", full_name="موظّف معطَّل", password="x"
    )
    off.is_staff = True
    off.is_active = False
    off.console_role = Role.SUPPORT
    off.save(update_fields=["is_staff", "is_active", "console_role"])

    bare = User.objects.create_user(
        phone="966500000503", full_name="موظّف بلا دور", password="x"
    )
    bare.is_staff = True
    bare.save(update_fields=["is_staff"])

    StaffGrant.objects.create(
        user=off,
        capability=Capability.MONEY_VIEW,
        granted=False,
        reason="أثناء المراجعة",
        granted_by=viewer,
    )
    return off, bare


# ---------------------------------------------------------------------------
# ١ — إدارة المشرفين
# ---------------------------------------------------------------------------


def test_a_staff_member_with_no_written_role_still_appears(crew):
    """`is_staff` هي التعريف لا `console_role`.

    موظّفٌ بلا دورٍ مكتوب **يفتح اللوحة** بأدنى قدرة، وإخفاؤه كان سيجعل
    الشاشة تقول اثنين والقاعدة تعرف ثلاثة. والصفُّ الذي لا يظهر لا يُراجَع.
    """
    names = {person.full_name for person in staff_rows()}
    assert "موظّف بلا دور" in names


def test_a_role_that_is_not_in_the_enum_is_shown_not_hidden():
    """دورٌ في القاعدة لا وجود له في `Role` يُعرض كما هو — لا يُبتلع.

    و`role_label` تعيش في `apps.core.permissions` لا في الشاشة:
    `ops/checks/one_permission_gate.py` يمنع قراءة `console_role` خارج
    البوابة، وقد أسقط أوّل نسخةٍ من هذه الشاشة فعلاً. والحارس محقّ — العطل
    الذي وُضع لأجله نشأ من **وجود** سؤال الدور لا من موضعه.
    """
    from apps.core.permissions import role_label

    assert "motrek" in role_label(User(console_role="motrek"))
    assert role_label(User(console_role="")).startswith("بلا دور")


def test_the_role_filter_ignores_a_value_that_is_not_a_role(crew):
    """خانةٌ في رابطٍ يكتبها أحدٌ بيده تُقرأ «لا مرشّح» لا «لا نتائج»."""
    assert staff_rows(role="لا-دور-كهذا").count() == staff_rows().count()


def test_the_state_column_carries_two_values_not_one(client, viewer, crew):
    """«نشط الآن» في ٣٧ من ٣٧ عمودٌ لا يحمل إلا قيمةً واحدة — وليس عموداً."""
    body = client.get(reverse("console:admins")).content.decode()
    assert "مفعّل" in body
    assert "معطّل" in body

    assert staff_rows(state="off").count() == 1
    assert staff_rows(state="active").count() == 2


def test_no_row_offers_to_delete_anybody(client, viewer, crew):
    """الزرُّ نفسه هو الخطأ، لا استثناؤه: حسابُ الموظّف طرفٌ في كل قيدٍ كتبه.

    ويُقرأ من **صفوف الجدول** لا من الصفحة: الفقرةُ تحت الجدول تشرح لماذا لا
    حذف، فبحثٌ عن الكلمة في الصفحة كلها كان سيسقط على شرحها هي.
    """
    body = client.get(reverse("console:admins")).content.decode()
    rows = body.split("<tbody>")[1].split("</tbody>")[0]

    assert "حذف" not in rows
    assert "delete" not in rows.lower()
    assert 'method="post"' not in rows.lower()

    # ولا في الإطار كلّه: النموذج الوحيد في الصفحة هو البحث () والخروج.
    main = body.split("<main>")[1].split("</main>")[0]
    assert 'method="post"' not in main.lower()


def test_the_exceptions_column_separates_a_grant_from_a_revoke(client, viewer, crew):
    """«٤٦ صفحة مخفية» في v1 رقمٌ واحد لا يقول أمُنحت أم سُحبت.

    والفرق هو كلُّ شيء: `+` قدرةٌ فوق الدور، `−` قدرةٌ سُحبت منه.
    """
    off, _ = crew
    row = next(person for person in staff_rows() if person.pk == off.pk)
    assert row.revoked == 1
    assert row.granted == 0


# ---------------------------------------------------------------------------
# ٢ — تقرير مزايدات مستخدم
# ---------------------------------------------------------------------------


@pytest.fixture
def bidder(db):
    """مزايدٌ له أربع مزايدات، وفاز بواحدة."""
    now = timezone.now()
    seller = User.objects.create_user(
        phone="966555559501", full_name="مالك التقرير", password="x"
    )
    Company.objects.create(user=seller, name="شركة التقرير")
    person = User.objects.create_user(
        phone="966555559502", full_name="مزايد التقرير", password="x"
    )

    auction = Auction.objects.create(
        number=850,
        title="مزاد التقرير",
        starts_at=now - timezone.timedelta(days=2),
        ends_at=now - timezone.timedelta(days=1),
        state=AuctionState.ENDED,
        deposit_required=TEN_K,
    )
    won = Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="لكزس",
        model="ES 350",
        year=2024,
        reserve_price=Decimal("80000.00"),
        state=VehicleState.AWARDED,
        awarded_to=person,
        awarded_price=Decimal("95000.00"),
        awarded_at=now,
        owner_company=seller.company,
    )
    Bid.objects.create(vehicle=won, bidder=person, amount=Decimal("95000.00"))
    Bid.objects.create(
        vehicle=won, bidder=person, amount=Decimal("90000.00"), is_superseded=True
    )
    return person


def test_it_does_not_open_on_zeros(client, viewer):
    """v1 يحسن هذه، وتُنقل بنصّها: «ابحث برقم الجوال أو الاسم».

    وشاشةٌ تفتح على «إجمالي ٠» قبل أن تُسأل تقول للقارئ إن المستخدم بلا
    مزايدات وهي لم تُسأل عن أحد.
    """
    assert report_for() is None

    body = client.get(reverse("console:user-bids")).content.decode()
    assert "ابحث برقم الجوال أو الاسم" in body
    assert "إجمالي المزايدات" not in body


def test_two_matches_ask_to_narrow_rather_than_pick_the_first(db, bidder):
    """تقريرٌ لشخصٍ آخر يحمل اسماً مشابهاً أسوأ من لا تقرير: يُقرأ صحيحاً."""
    User.objects.create_user(
        phone="966555559503", full_name="مزايد التقرير الثاني", password="x"
    )
    report = report_for(name="مزايد التقرير")

    assert report["person"] is None
    assert report["ambiguous"] is True
    assert report["count"] == 2


def test_the_report_counts_the_way_the_platform_counts(bidder):
    """قسمةُ الحالات هي قسمةُ `bid_shape` نفسها.

    فلا يقول تقريرُ الشخص «مزايدتان قائمتان» ويقول تحليلُ المنصّة «واحدة».
    """
    report = report_for(phone=bidder.phone)

    assert report["count"] == 2
    assert report["standing"] == 1
    assert report["superseded"] == 1
    assert report["withdrawn"] == 0
    assert (
        report["standing"] + report["superseded"] + report["withdrawn"] == report["count"]
    )


def test_what_he_won_is_read_from_the_same_place_the_decisions_screen_reads(bidder):
    """«أعلى مزايداته الفائزة» في v1 — وهنا `decisions.awarded()` نفسها.

    فرقمُ ما فاز به هنا **هو** صفوفُه في «المزايدات المقبولة»، ولا يمكن أن
    يختلفا.
    """
    from apps.console.decisions import awarded

    report = report_for(phone=bidder.phone)

    assert report["won_count"] == awarded().filter(awarded_to=bidder).count() == 1
    assert report["won_value"] == Decimal("95000.00")
