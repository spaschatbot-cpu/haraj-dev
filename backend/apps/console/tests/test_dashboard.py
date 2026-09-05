"""لوحة التحليلات — رندرةٌ على صفوفٍ حقيقية، وأرقامٌ لكلٍّ منها باب.

`console:home` صفحة تنقّل عمداً: «لوحة أرقامٍ لا يستطيع أحد التصرّف فيها هي ما
كانت عليه رئيسية v1». هذه الصفحة لا تنقض ذلك — تجيب عليه، **وأول اختبار هنا هو
تلك الإجابة**: كل بطاقة تحمل رقماً تحمل معه وجهةً يُفعل فيها شيء.

والثاني هو المادة ١-٦: **الأرقام المالية مشتقّة من الحسابات لا من عمودٍ
مخزَّن.** جرد T302 وجد في `userss` ثلاثة أعمدة رصيدٍ مشتقّة، أحدها محذَّرٌ منه
واثنان مثله بلا تحذير — ولوحةٌ تقرأ عموداً كهذا تعرض رقماً لا يعرف أحدٌ من أين
جاء.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.core.permissions import Capability, Role
from apps.money import services
from apps.money.models import Invoice, InvoiceSource, InvoiceState

pytestmark = pytest.mark.django_db

URL = "console:dashboard"
TEN_K = Decimal("10000.00")


@pytest.fixture
def owner(django_user_model):
    user = django_user_model.objects.create_user(
        phone="966500000009", full_name="مالك", password="x"
    )
    user.is_staff = True
    user.console_role = Role.OWNER
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def operations(django_user_model):
    user = django_user_model.objects.create_user(
        phone="966500000008", full_name="تشغيل", password="x"
    )
    user.is_staff = True
    user.console_role = Role.OPERATIONS
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def a_platform(django_user_model):
    """صفوفٌ حقيقية: عميلٌ بوديعة، ومزادٌ جارٍ، ومركبة، وفاتورة معلّقة."""
    customer = django_user_model.objects.create_user(
        phone="966501111111", full_name="عميل", national_id="1234567890"
    )
    services.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="SEED/DASH"
    )
    now = timezone.now()
    auction = Auction.objects.create(
        number=940,
        title="مزاد اللوحة",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )
    Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.AWAITING_DECISION,
        reserve_price=Decimal("40000.00"),
    )
    Invoice.objects.create(
        customer=customer,
        number="V-DASH-1",
        amount=Decimal("70000.00"),
        state=InvoiceState.OPEN,
        source=InvoiceSource.LOCAL,
        issued_at=now,
    )
    return customer


def body(client, user) -> str:
    client.force_login(user)
    response = client.get(reverse(URL))
    assert response.status_code == 200
    return response.content.decode()


# ---------------------------------------------------------------------------
# الإجابة على اعتراض `home`
# ---------------------------------------------------------------------------


def test_every_number_that_can_be_acted_on_carries_its_door(client, owner, a_platform):
    """الفرق كله عن لوحة v1: رقمٌ يُقرأ ورقمٌ يُفتح."""
    page = body(client, owner)

    for destination in (
        reverse("console:money-ledger"),
        reverse("console:invoices"),
        reverse("console:auctions"),
        reverse("console:partner-decisions"),
        reverse("console:customers"),
    ):
        assert destination in page, f"رقمٌ بلا باب: {destination}"


def test_the_stats_are_links_not_decorated_boxes(client, owner, a_platform):
    page = body(client, owner)
    section = re.search(r'<section class="board-stats".*?</section>', page, re.S)

    assert section, "لا قسم أرقام على الصفحة"
    assert section.group(0).count("<a ") >= 4


# ---------------------------------------------------------------------------
# المادة ١-٦ — الرقم المالي من الدفتر لا من عمود
# ---------------------------------------------------------------------------


def test_the_insurance_total_is_derived_from_the_accounts(
    client, owner, a_platform, django_user_model
):
    """عميلٌ ثانٍ يودع، فيتحرّك الإجمالي — لأنه مجموع الحسابات لا عمودٌ محفوظ."""
    before = body(client, owner)
    assert "10,000.00" in before

    second = django_user_model.objects.create_user(
        phone="966502222222", full_name="ثانٍ", national_id="9876543210"
    )
    services.deposit_insurance(
        user=second, amount=TEN_K, source="cash", reference="SEED/DASH2"
    )

    assert "20,000.00" in body(client, owner)


def test_the_buckets_are_named_apart_not_added_into_one_number(client, owner, a_platform):
    """«متاح ومحجوز ومرهون» ثلاثة أشياء، ومجموعها وحده رقمٌ مبهم (spec 007 §5)."""
    page = body(client, owner)

    assert "متاح" in page
    assert "محجوز" in page
    assert "مرهون" in page


def test_it_reads_no_stored_balance_column():
    """جرد T302: ثلاثة أعمدة رصيدٍ في `userss` كان اثنان منها بلا تحذير.

    فحصٌ نصّي لأن العطل هنا لا يُرى في نتيجة: عمودٌ مجمَّع يعرض رقماً يبدو
    صحيحاً ولا يعرف أحدٌ من أين جاء.
    """
    import ast
    from pathlib import Path

    source = Path(__file__).resolve().parents[1] / "dashboard.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))

    # الشيفرة وحدها. الأسماء مذكورةٌ في تعليق الوحدة عمداً — لتقول لماذا لا
    # تُقرأ — وفحصٌ نصّي يخلط الشرح بالفعل يُبلّغ عن كل وثيقةٍ تشرح نفسها.
    names = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)} | {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }

    for forbidden in ("total_insurance_paid", "purchases_balance", "wallet"):
        assert forbidden not in names, f"اللوحة تقرأ عموداً مشتقّاً: {forbidden}"
        assert forbidden not in literals, f"اللوحة تسمّي عموداً مشتقّاً: {forbidden}"


# ---------------------------------------------------------------------------
# الصحّة أولاً
# ---------------------------------------------------------------------------


def test_a_clean_ledger_says_so_once_and_briefly(client, owner, a_platform):
    page = body(client, owner)

    assert "الدفتر متّزن" in page


def test_unattributed_money_is_raised_above_the_totals(client, owner, a_platform):
    """رقمٌ كبير فوق مالٍ بلا صاحب ليس معلومة."""
    services.receive_unattributed(
        amount=Decimal("3000.00"), source="cash", reference="SUS/DASH"
    )

    page = body(client, owner)
    alarms = re.search(r'<section class="board-alarms".*?</section>', page, re.S)

    assert alarms, "لا قسم تنبيهات رغم وجود معلّق"
    assert "معلّق بلا صاحب" in alarms.group(0)
    assert "3,000.00" in alarms.group(0)
    assert "الدفتر متّزن" not in page


# ---------------------------------------------------------------------------
# ما لا يُسمح لك برؤيته لا يُعرض
# ---------------------------------------------------------------------------


def test_operations_does_not_see_the_money(client, operations, a_platform):
    """بالبوابة الواحدة نفسها (T801)، لا ببوابة ثانية للّوحة."""
    from apps.core.permissions import can

    assert not can(operations, Capability.MONEY_VIEW)

    page = body(client, operations)

    assert "إجمالي التأمين" not in page
    assert "المزادات" in page, "التشغيل يرى المزادات"


def test_a_customer_cannot_open_it_at_all(client, django_user_model):
    customer = django_user_model.objects.create_user(
        phone="966509999999", full_name="عميل", password="x"
    )
    client.force_login(customer)

    assert client.get(reverse(URL)).status_code == 403


def test_it_is_a_row_in_the_registry_like_every_other_screen():
    """صفحةٌ غير مسجَّلة يبلغها رابطٌ هي بالضبط شكل التسريب غير المقصود."""
    from apps.console.navigation import PAGES

    assert URL in {page.url_name for page in PAGES}


# ---------------------------------------------------------------------------
# الرسوم — أرقامٌ مكتوبة، لا رسمٌ يُقرأ منه رقم
# ---------------------------------------------------------------------------


def test_the_wheel_carries_its_own_numbers(client, owner, a_platform):
    """الرسم يقول «أيّها أكبر»، والمفتاح بجواره يقول «كم» — ولا رقمَ يُقرأ منه."""
    page = body(client, owner)

    assert "حالات المزادات" in page
    assert "جارٍ" in page
    assert 'class="wheel__count"' in page
    assert 'class="wheel__share"' in page
    # والمركز يحمل الإجمالي، فالنسب تُقرأ «من كم».
    assert 'class="wheel__hole"' in page


def test_the_trend_shows_seven_days(client, owner, a_platform):
    page = body(client, owner)
    section = re.search(r'<ol class="spark">.*?</ol>', page, re.S)

    assert section
    assert section.group(0).count('class="spark__day"') == 7


def test_the_percentages_are_computed_in_python_not_in_the_template():
    """قالبٌ يقسّم أرقاماً مكانٌ ثانٍ للقاعدة، ولا يُختبَر (المادة ٤-٤)."""
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[3] / "templates" / "console" / "dashboard.html"
    )
    text = template.read_text(encoding="utf-8")

    assert "widthratio" not in text
    assert "|divisibleby" not in text


# ---------------------------------------------------------------------------
# تشريح البطاقة — الدلتا والفعل
# ---------------------------------------------------------------------------


def test_a_delta_is_a_comparison_not_a_decoration(
    client, owner, a_platform, django_user_model
):
    """«١٢٠ ألف مزايدة» لا تقول شيئاً وحدها؛ «أعلى بـ٪ عن الأسبوع الماضي» تقول."""
    from apps.auctions.models import Vehicle
    from apps.bidding.models import Bid

    car = Vehicle.objects.first()
    now = timezone.now()
    # مزايدٌ لكل مزايدة: القيد `one_live_bid_per_bidder_per_vehicle` يمنع
    # اثنتين حيّتين لشخصٍ واحد على مركبة — وهو محقّ.
    plan = [(10, 1), (2, 3)]  # الأسبوع السابق واحدة، وهذا ثلاث
    n = 0
    for offset, count in plan:
        for _ in range(count):
            n += 1
            bidder = django_user_model.objects.create_user(
                phone=f"96650777{n:04d}", full_name=f"مزايد {n}"
            )
            bid = Bid.objects.create(
                vehicle=car, bidder=bidder, amount=Decimal("50000.00")
            )
            Bid.objects.filter(pk=bid.pk).update(
                placed_at=now - timezone.timedelta(days=offset)
            )

    page = body(client, owner)

    assert "200%" in page, "لم تُحسب المقارنة"
    assert "عن الأسبوع الماضي" in page


def test_no_previous_week_means_no_delta_rather_than_a_made_up_one(
    client, owner, a_platform
):
    """نسبةٌ من صفرٍ ليست «زيادة لا نهائية» — هي لا مقارنة، وعرضها ادّعاء."""
    page = body(client, owner)

    assert "عن الأسبوع الماضي" not in page


def test_the_direction_is_written_not_only_coloured(client, owner, a_platform):
    """من لا يميّز الأخضر من الأحمر يقرأ الجملة نفسها."""
    from apps.migration import extract  # noqa: F401  (يثبت أن الاستيراد سليم)

    page = body(client, owner)

    assert 'class="stat__action"' in page, "بطاقةٌ بلا تذييلٍ يقول إلى أين"


def test_the_icon_is_hidden_from_screen_readers(client, owner, a_platform):
    """تزيينيٌّ صراحةً: رمزٌ يُقرأ بصوتٍ عالٍ ضجيج، ولا يحمل معلومة."""
    page = body(client, owner)
    icons = re.findall(r'<span class="stat__icon"([^>]*)>', page)

    assert icons, "لا رموز على البطاقات"
    assert all('aria-hidden="true"' in attrs for attrs in icons)


# ---------------------------------------------------------------------------
# الخطّ المصغَّر والدائرة
# ---------------------------------------------------------------------------


def test_the_direction_word_is_not_a_yesno_filter():
    """`yesno` كان الحلّ الواضح وهو خطأ صامت: كلاهما نصٌّ غيرُ فارغ فيُقرأ صحيحاً."""
    from apps.console.dashboard import Delta

    assert Delta(5, "up", "").word == "أعلى"
    assert Delta(5, "down", "").word == "أقل"
    assert Delta(0, "flat", "").word == "مستقر"


def test_the_template_does_not_decide_the_direction():
    from pathlib import Path

    template = (
        Path(__file__).resolve().parents[3] / "templates" / "console" / "_stat.html"
    )
    assert "yesno" not in template.read_text(encoding="utf-8")


def test_the_sparkline_points_are_computed_in_python():
    """قالبٌ يحسب إحداثيات مكانٌ ثانٍ للقاعدة ولا يُختبَر (المادة ٤-٤)."""
    from apps.console.dashboard import Stat

    stat = Stat("س", "1", spark=(0, 50, 100))
    points = stat.spark_points.split()

    assert len(points) == 3
    xs = [float(p.split(",")[0]) for p in points]
    ys = [float(p.split(",")[1]) for p in points]
    assert xs == [0.0, 50.0, 100.0]
    # المحور الرأسي مقلوب: أعلى قيمةٍ أدنى إحداثي.
    assert ys[0] > ys[-1]


def test_a_single_point_draws_no_line():
    """نقطةٌ واحدة ليست اتجاهاً، وخطٌّ من نقطةٍ ادّعاء."""
    from apps.console.dashboard import Stat

    assert Stat("س", "1", spark=(50,)).spark_points == ""
    assert Stat("س", "1").spark_points == ""


def test_the_wheel_slices_add_up_to_the_whole(client, owner, a_platform):
    from apps.console.dashboard import _wheel

    css = _wheel([("أ", 3, 50), ("ب", 3, 50)])

    assert css.startswith("conic-gradient(")
    assert "0.0% 50.0%" in css
    assert "50.0% 100.0%" in css


def test_an_incomplete_wheel_is_filled_not_left_transparent():
    """قطاعٌ ناقص يترك فجوةً تُقرأ كصفرٍ — والباقي يُملأ بلونٍ محايد."""
    from apps.console.dashboard import _wheel

    assert "var(--line-soft)" in _wheel([("أ", 1, 40)])


def test_the_key_colours_match_the_wheel_colours():
    """قائمتان تتطابقان بالترتيب — وقائمةٌ ثانية تكفّ عن المطابقة بلا حارس."""
    from pathlib import Path

    from apps.console.dashboard import WHEEL

    css = (
        Path(__file__).resolve().parents[1] / "static" / "console" / "app.css"
    ).read_text(encoding="utf-8")

    for index, colour in enumerate(WHEEL):
        rule = f'.wheel__dot[data-slice="{index}"] {{ background: {colour}; }}'
        assert rule in css, f"لون القطاع {index} في بايثون لا يطابق CSS: {colour}"
