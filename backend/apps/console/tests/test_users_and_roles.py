"""إدارة المستخدمين وأدوارها — الرصيد من الدفتر، والحذف يُرفض، والدور صفّ. T838.

ثلاث دعاوى، كلٌّ منها عطلٌ مقيسٌ في v1:

**١. عمود الرصيد.** في إنتاج v1 هذا العمود `0 SAR` في **كل** صفٍّ من أربعةٍ
وأربعين ألفاً — عمودٌ مشتقٌّ مخزَّنٌ لا يحدّثه شيء (جرد T302). فالاختبار هنا
يودع مبلغاً في الدفتر ثم يقرأ الشاشة: رقمٌ لا صفر.

**٢. زرّ الحذف.** في v1 بجوار زرّ التعديل وبالثقة نفسها. وهنا قدرةٌ وحدها،
ويُرفض على حسابٍ له أثر — ويقول **كلَّ** ما يمنع لا أوّلَه.

**٣. الأدوار.** أحدَ عشرَ دوراً في قائمة v1، أربعةٌ منها تكرارُ أربعةٍ بأسماءٍ
مختلفة، ولا أحد يحذف القديم لأنه لا يعرف من يحمله. فالدورُ هنا صفٌّ يقول من
يحمله، ويُحذف حين لا يحمله أحد — ولا يُحذف حين يحمله واحد.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import ConsoleRole, User
from apps.core.permissions import Capability, Role, bundle_for, can
from apps.money import services

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str = "966500000700") -> User:
    person = User.objects.create_user(phone=phone, full_name="موظّف", password="x")
    person.is_staff = True
    person.console_role = role
    person.save(update_fields=["is_staff", "console_role"])
    return person


@pytest.fixture
def owner(client) -> User:
    person = staff(Role.OWNER, "966500000701")
    client.force_login(person)
    return person


@pytest.fixture
def customer() -> User:
    return User.objects.create_user(
        phone="966555550001", full_name="عميل الشاشة", password="x"
    )


# ---------------------------------------------------------------------------
# ١ — الرصيد رقمٌ من الدفتر، لا صفرٌ من عمودٍ مهمَل
# ---------------------------------------------------------------------------


def test_the_balance_column_carries_the_ledger_not_a_stored_zero(client, owner, customer):
    """v1 يعرض `0 SAR` في كل صفّ. هذا الاختبار هو الفرق."""
    services.deposit_insurance(
        user=customer,
        amount=Decimal("2500.00"),
        source="cash",
        reference="users-screen-1",
    )

    body = client.get(reverse("console:customers")).content.decode()

    assert "2500.00" in body, "الرصيد لم يصل الشاشة من الدفتر"


def test_a_customer_with_no_ledger_row_reads_zero_not_blank(client, owner, customer):
    """الصفرُ محسوبٌ لا غائب: عميلٌ بلا حسابٍ في الدفتر رصيدُه صفرٌ حقيقة."""
    body = client.get(reverse("console:customers")).content.decode()

    assert "0.00" in body


# ---------------------------------------------------------------------------
# ٢ — البحث والمرشّحات بأسماء v1 نفسها
# ---------------------------------------------------------------------------


def test_the_filters_answer_to_the_v1_parameter_names(client, owner, customer):
    """رابطٌ محفوظٌ عند موظّف من v1 يفتح هنا على النتيجة نفسها.

    `account_type` و`per_page` لا `type` و`rows`: اسمٌ مختلف يعني أن المرشّح
    يُهمَل بصمت والصفحة تُقرأ كأنها بلا مرشّح.
    """
    company = User.objects.create_user(
        phone="966555550002", full_name="شركة الشاشة", password="x"
    )
    company.account_type = "company"
    company.save(update_fields=["account_type"])

    body = client.get(
        reverse("console:customers"), {"account_type": "company", "per_page": "50"}
    ).content.decode()

    assert "شركة الشاشة" in body
    assert "عميل الشاشة" not in body


def test_stopping_a_customer_is_a_filter_not_a_hunt(client, owner, customer):
    """«من الموقوفون؟» سؤالٌ له مرشّح — وv1 يعرض «نشط» بلا أن يُرشَّح به."""
    customer.is_active = False
    customer.save(update_fields=["is_active"])

    shown = client.get(reverse("console:customers"), {"status": "stopped"})
    hidden = client.get(reverse("console:customers"), {"status": "active"})

    assert "عميل الشاشة" in shown.content.decode()
    assert "عميل الشاشة" not in hidden.content.decode()


# ---------------------------------------------------------------------------
# ٣ — الحذف: قدرةٌ وحدها، ويُرفض على حسابٍ له أثر
# ---------------------------------------------------------------------------


def test_deleting_is_not_the_same_trust_as_editing(client, customer):
    """من يملك `users.manage` لا يحذف: v1 يضع الزرّين بالثقة نفسها."""
    editor = staff(Role.SUPPORT, "966500000702")
    assert can(editor, Capability.USERS_VIEW)
    assert not can(editor, Capability.USERS_DELETE)

    client.force_login(editor)
    assert (
        client.get(reverse("console:customer-delete", args=[customer.pk])).status_code
        == 403
    )


def test_an_account_with_a_ledger_row_is_not_deleted(client, owner, customer):
    """والرفضُ يقول ما يمنع بالاسم والعدد — لا «تعذّر الحذف»."""
    services.deposit_insurance(
        user=customer,
        amount=Decimal("100.00"),
        source="cash",
        reference="users-screen-2",
    )

    body = client.get(
        reverse("console:customer-delete", args=[customer.pk])
    ).content.decode()
    assert "قيود في الدفتر" in body

    client.post(
        reverse("console:customer-delete", args=[customer.pk]), {"reason": "تجربة"}
    )
    assert User.objects.filter(pk=customer.pk).exists(), "حُذف حسابٌ له أثر في الدفتر"


def test_an_account_with_no_trace_is_deleted_and_leaves_its_phone_behind(
    client, owner, customer
):
    """الحذف الوحيد المسموح — والقيدُ يحمل الجوّال بعد أن لا يبقى صفّ."""
    from apps.core.models import AuditLog

    response = client.post(
        reverse("console:customer-delete", args=[customer.pk]),
        {"reason": "حساب فُتح بالخطأ ولم يُستعمل"},
    )

    assert response.status_code == 302
    assert not User.objects.filter(pk=customer.pk).exists()

    entry = AuditLog.objects.filter(action="console.delete_customer").latest("id")
    assert entry.before["phone"] == "966555550001"
    assert "فُتح بالخطأ" in entry.note


def test_you_do_not_delete_your_own_account(client, owner):
    """من يحذف حسابه يخرج من اللوحة في منتصف الفعل، ولا يبقى من يعكسه."""
    client.post(reverse("console:customer-delete", args=[owner.pk]), {"reason": "لا"})

    assert User.objects.filter(pk=owner.pk).exists()


# ---------------------------------------------------------------------------
# ٤ — الأدوار: تُضاف وتُحذف، والمكتوبُ في الشيفرة يبقى
# ---------------------------------------------------------------------------


def test_a_new_role_reaches_the_gate_that_admits_people(client, owner):
    """دورٌ يُضاف من شاشة **يُقرأ** — وإلّا فهو صفٌّ يزيّن قائمة.

    وهذا هو الاختبار الذي يجعل الشاشة تعني شيئاً: `bundle_for` هي التي تجيب
    البوّابة، فلو لم تقرأ الجدول لكان الدورُ الجديد بلا أثر.
    """
    client.post(
        reverse("console:roles"),
        {
            "label": "خدمات ما بعد البيع (اطلاع)",
            "slug": "aftersales",
            "capabilities": [Capability.CONSOLE_ACCESS, Capability.AUCTIONS_VIEW],
            "reason": "فريق ما بعد البيع يقرأ ولا يكتب",
        },
    )

    assert ConsoleRole.objects.filter(slug="aftersales").exists()
    assert bundle_for("aftersales") == frozenset(
        {Capability.CONSOLE_ACCESS, Capability.AUCTIONS_VIEW}
    )

    holder = staff("aftersales", "966500000703")
    assert can(holder, Capability.AUCTIONS_VIEW)
    assert not can(holder, Capability.MONEY_VIEW)


def test_a_role_that_names_a_built_in_one_is_refused(client, owner):
    """`bundle_for` تقرأ المكتوب أولاً، فصفٌّ اسمُه `owner` لا يُقرأ أبداً.

    وصفٌّ لا أثر له وهو معروضٌ في شاشةٍ أسوأ من رفضٍ صريح: من أنشأه يظنّ أنه
    غيّر شيئاً.
    """
    client.post(
        reverse("console:roles"),
        {
            "label": "مالكٌ ثانٍ",
            "slug": "owner",
            "capabilities": [Capability.CONSOLE_ACCESS],
            "reason": "محاولة",
        },
    )

    assert not ConsoleRole.objects.filter(slug="owner").exists()
    assert bundle_for("owner") == frozenset(Capability.values)


def test_a_role_somebody_holds_is_not_deleted(client, owner):
    """حذفُ دورٍ يحمله سبعةٌ يُخرج سبعةً من اللوحة بلا أن يقول لهم أحدٌ لماذا."""
    ConsoleRole.objects.create(
        slug="datentry", label="إدخال بيانات", capabilities=[], reason="تجربة"
    )
    staff("datentry", "966500000704")

    client.post(reverse("console:role-delete", args=["datentry"]), {"reason": "تنظيف"})

    assert ConsoleRole.objects.filter(slug="datentry").exists()


def test_a_role_nobody_holds_is_deleted(client, owner):
    """وهذا ما يجعل القائمة تُنظَّف بدل أن تطول أبداً."""
    ConsoleRole.objects.create(
        slug="unused", label="دورٌ قديم", capabilities=[], reason="لم يعد له عمل"
    )

    client.post(reverse("console:role-delete", args=["unused"]), {"reason": "لا حامل له"})

    assert not ConsoleRole.objects.filter(slug="unused").exists()


def test_a_capability_that_does_not_exist_is_refused_at_the_row(client, owner):
    """قدرةٌ مكتوبةٌ خطأً تبدو صحيحةً في الشاشة ولا تمنح شيئاً — فتُرفض عند الحفظ."""
    from django.core.exceptions import ValidationError

    role = ConsoleRole(
        slug="typo", label="خطأ مطبعيّ", capabilities=["users.delet"], reason="تجربة"
    )

    with pytest.raises(ValidationError):
        role.full_clean()


# ---------------------------------------------------------------------------
# ٥ — الدمج: «التحكم في صفحات المستخدمين» تُفتح من صفِّ المشرف لا من الشريط
# ---------------------------------------------------------------------------


def test_the_overrides_screen_is_reached_from_the_admin_row(client, owner):
    """كانتا شاشتين في الشريط تعرضان القائمة نفسها بعمودٍ مختلف.

    فيفتح الموظّف إحداهما، ثم يكتشف أن ما يريده في الأخرى بالاسم نفسه تقريباً.
    والمدخلُ الآن واحد: صفُّ المشرف.
    """
    body = client.get(reverse("console:admins")).content.decode()

    assert reverse("console:page-control") in body
    assert reverse("console:roles") in body


def test_the_overrides_screen_still_renders_on_its_own(client, owner):
    """خرجت من الشريط ولم تُحذف — والرندرة تُقاس، لا تُفترض من كونها مسجَّلة."""
    response = client.get(reverse("console:page-control"))

    assert response.status_code == 200
    assert "تجاوزٌ فرديٌّ فوق الدور" in response.content.decode()


def test_the_overrides_screen_is_not_in_the_sidebar_any_more(client, owner):
    """مدخلان إلى القائمة الواحدة أحدُهما زائد — والزائد يُقاس بغيابه."""
    from apps.console.navigation import PAGES

    sidebar = {page.url_name for page in PAGES}

    assert "console:page-control" not in sidebar
    assert "console:roles" in sidebar
