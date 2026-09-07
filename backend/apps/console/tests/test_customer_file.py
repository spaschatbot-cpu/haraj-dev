"""ملفّ العميل الكامل — الثلاثة التي تُصلَح في نظيره عند v1. T849.

**١. التسريب.** هناك يُقرأ رقم العميل في أودو، وإن كان فارغاً صار `0` — فتُعرض
مالياتُ وصورُ آيبان **كل** عميلٍ يحمل صفراً على أنها ماليةُ هذا العميل. وهو
تسريبٌ لا يظهر في فحص: الصفحة تعمل، والأرقام تُقرأ، وهي لشخصٍ آخر.

**٢. «الحرّ» ليس حرّاً.** والحساب هنا من البوّابة نفسها التي سترفض المزايدة،
فلا يقول الملفُّ شيئاً ويقول الرفضُ غيرَه.

**٣. وقائمةُ ما يُخفى مبنيّةٌ من النموذج** لا مكتوبةً باليد — والاختبار الأخير
هنا هو ما يجعل ذلك صحيحاً غداً لا اليوم فقط.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.console.customer_file import SECRET_FIELDS, full_record
from apps.core.permissions import Capability, Role
from apps.money import services
from apps.odoo.models import CustomerLink

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    person = User.objects.create_user(phone=phone, full_name="موظّف", password="x")
    person.is_staff = True
    person.console_role = role
    person.save(update_fields=["is_staff", "console_role"])
    return person


@pytest.fixture
def owner(client) -> User:
    person = staff(Role.OWNER, "966500000801")
    client.force_login(person)
    return person


@pytest.fixture
def customer() -> User:
    return User.objects.create_user(
        phone="966555550801", full_name="صاحب الملفّ", password="x"
    )


# ---------------------------------------------------------------------------
# ١ — التسريب: غيابُ الربط غيابُ صفٍّ لا قيمةٌ فارغة
# ---------------------------------------------------------------------------


def test_an_unlinked_customer_shows_nobody_elses_odoo_id(client, owner, customer):
    """صفرُ v1 هنا لا وجود له: القائمة تُقرأ من علاقة المستخدم نفسه.

    ولذلك عميلٌ آخرُ مربوطٌ فعلاً لا يظهر رقمُه على صفحة من ليس مربوطاً — وهي
    الصورةُ المصغَّرة للتسريب الذي يقع هناك.
    """
    other = User.objects.create_user(
        phone="966555550802", full_name="عميل آخر", password="x"
    )
    CustomerLink.objects.create(user=other, odoo_customer_id="7788", is_primary=True)

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "7788" not in body, "رقمُ عميلٍ آخر ظهر على صفحة من ليس مربوطاً"
    assert "غير مربوطٍ بأودو" in body


def test_a_linked_customer_shows_its_own_link(client, owner, customer):
    """والغيابُ يُقال صراحةً، والوجودُ يُعرض — كلاهما جوابٌ لا فراغ."""
    CustomerLink.objects.create(user=customer, odoo_customer_id="9911", is_primary=True)

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "9911" in body


# ---------------------------------------------------------------------------
# ٢ — «الحرّ» ليس حرّاً، والرقم من البوّابة
# ---------------------------------------------------------------------------


def test_the_page_warns_that_free_insurance_will_not_be_spent(client, owner, customer):
    """أذكى ما في شاشة v1 منقولٌ هنا: وديعةٌ تبدو متاحة والبوّابة سترفض.

    ولا يُعاد الحساب هنا — `money_snapshot` هي التي تجيب، وهي التي يقرؤها
    الرفضُ لحظةَ المزايدة. فما تقوله الصفحة هو ما سيقوله الرفض حرفياً.
    """
    from django.utils import timezone

    from apps.money.models import Invoice, InvoiceSource, InvoiceState

    services.deposit_insurance(
        user=customer, amount=Decimal("5000.00"), source="cash", reference="file/1"
    )
    Invoice.objects.create(
        customer=customer,
        number="V-FILE-1",
        amount=Decimal("12000.00"),
        source=InvoiceSource.LOCAL,
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
    )

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "عليه مستحقات" in body
    assert "12000.00" in body


def test_a_customer_with_no_dues_gets_no_warning(client, owner, customer):
    """تحذيرٌ يظهر دائماً لا يُقرأ — فالصامتُ هنا معلومةٌ أيضاً."""
    services.deposit_insurance(
        user=customer, amount=Decimal("5000.00"), source="cash", reference="file/2"
    )

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "عليه مستحقات" not in body


# ---------------------------------------------------------------------------
# ٣ — البيانات الكاملة: مبنيّةٌ من النموذج، والسرُّ مطروحٌ باسمه
# ---------------------------------------------------------------------------


def test_every_column_is_either_shown_or_named_a_secret(customer):
    """الحارس الذي يجعل «كل عمود إلا السرّ» صحيحاً **غداً** لا اليوم فقط.

    v1 يكتب قائمتين بأربعة عشر اسماً لما يُخفى، فحقلٌ يُضاف بعدها يظهر على
    الشاشة بلا قرار — وقد يكون سرّاً. وهذا الاختبار يُسقط أي حقلٍ جديد حتى
    يُقرَّر فيه: يُعرض، أو يُسمّى سرّاً هنا.
    """
    shown = {label for label, _ in full_record(customer)}
    every = {
        str(field.verbose_name or field.name)
        for field in User._meta.fields
        if field.name not in SECRET_FIELDS
    }

    assert shown == every, f"حقولٌ لم تُعرض ولم تُسمَّ سرّاً: {sorted(every - shown)}"


def test_the_password_never_reaches_the_page(client, owner, customer):
    """السرُّ مطروحٌ فعلاً لا في القائمة وحدها — يُقاس على الصفحة المرسومة."""
    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert customer.password not in body
    assert "pbkdf2" not in body


def test_a_boolean_reads_as_a_word_not_as_python(client, owner, customer):
    """«superuser status: False» تُقرأ رسالةَ عطلٍ لا معلومة."""
    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()
    record = body.split("البيانات الكاملة")[1].split("</table>")[0]

    assert "False" not in record
    assert "True" not in record


# ---------------------------------------------------------------------------
# ٤ — قوائم النشاط: كلٌّ خلف قدرتها، وv1 يعرض الستّ للجميع
# ---------------------------------------------------------------------------


def test_the_ledger_card_is_not_shown_to_somebody_without_money_view(client, customer):
    """المستودع يقسم المال ثلاثاً منذ T801 — والملفُّ لا يلتفّ على ذلك."""
    from apps.accounts.models import StaffGrant
    from apps.core.permissions import can

    viewer = staff(Role.SUPPORT, "966500000802")
    StaffGrant.objects.create(
        user=viewer,
        capability=Capability.MONEY_VIEW,
        granted=False,
        reason="لا يحتاج الدفتر",
    )
    assert not can(viewer, Capability.MONEY_VIEW)

    client.force_login(viewer)
    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "دفتر المحفظة" not in body
    # ويبقى ما يخصّه: من هو العميل.
    assert "صاحب الملفّ" in body


def test_the_owner_sees_every_card(client, owner, customer):
    """والستّ تُعرض لمن يملكها كلَّها — فالتقسيم قسمةٌ لا حجب."""
    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    for title in (
        "المزايدات",
        "الفواتير",
        "محاولات الدفع",
        "طلبات الاسترداد",
        "دفتر المحفظة",
        "الحجوزات القائمة",
    ):
        assert title in body, title


# ---------------------------------------------------------------------------
# ٥ — T850: العنوان الوطني، محاولات الدخول، الآيبان، والتحقّق بالعربية
# ---------------------------------------------------------------------------


def test_national_address_card_is_rendered(client, owner, customer):
    """العنوان الوطني يظهر في بطاقته بجدول ممرر، ولا حقول مكررة على User."""
    from apps.accounts.models import NationalAddress

    NationalAddress.objects.create(
        user=customer,
        city="الرياض",
        district="الملقا",
        street="طريق أنس بن مالك",
        building_number="1234",
        postal_code="12345",
        additional_number="5678",
        plot_number="9988",
    )

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "العنوان الوطني" in body
    assert "الرياض" in body
    assert "الملقا" in body
    assert "1234" in body
    assert "12345" in body
    assert "5678" in body


def test_login_attempts_card_is_rendered(client, owner, customer):
    """محاولات الدخول تُقرأ من PhoneVerification وتُعرض في جدول ممرّر."""
    from django.utils import timezone

    from apps.accounts.models import PhoneVerification

    PhoneVerification.objects.create(
        phone=customer.phone,
        purpose="login",
        code_hash="dummy",
        expires_at=timezone.now() + timezone.timedelta(minutes=5),
        attempts=2,
    )

    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "محاولات الدخول ورموز التحقق" in body
    assert "دخول أو تسجيل" in body


def test_iban_is_hidden_without_money_view_and_shown_with_it(client, customer):
    """الآيبان سرٌّ ماليّ: لا يراه من يملك users.view إلا إذا ملك money.view (T850)."""
    from apps.accounts.models import StaffGrant
    from apps.core.permissions import can

    customer.iban = "SA1234567890123456789012"
    customer.save(update_fields=["iban"])

    viewer = staff(Role.SUPPORT, "966500000803")
    StaffGrant.objects.create(
        user=viewer,
        capability=Capability.MONEY_VIEW,
        granted=False,
        reason="لا يرى الحسابات البنكية",
    )
    assert not can(viewer, Capability.MONEY_VIEW)

    client.force_login(viewer)
    body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    # الآيبان لا يظهر في البيانات الكاملة ولا في بطاقة بنكية لموظف الدعم
    assert customer.iban not in body

    # يظهر للمالك الذي يملك MONEY_VIEW
    owner_user = staff(Role.OWNER, "966500000804")
    client.force_login(owner_user)
    owner_body = client.get(
        reverse("console:customer-detail", args=[customer.pk])
    ).content.decode()

    assert "البيانات البنكية" in owner_body
    assert customer.iban in owner_body


def test_no_address_columns_on_user_or_company_models():
    """العنوان الوطني نموذج واحد — لا city على User ولا على Company بعد الهجرة."""
    from apps.accounts.models import Company, User

    user_fields = {f.name for f in User._meta.fields}
    company_fields = {f.name for f in Company._meta.fields}

    assert "city" not in user_fields
    assert "district" not in user_fields
    assert "postal_code" not in user_fields

    assert "city" not in company_fields
    assert "district" not in company_fields
    assert "street" not in company_fields
    assert "building_number" not in company_fields
    assert "postal_code" not in company_fields


def test_national_address_validation_rejects_bad_formats_in_arabic(customer):
    """المعيار ٦: التحقق يرفض الصيغ الخاطئة برسائل عربية صريحة."""
    from django.core.exceptions import ValidationError

    from apps.accounts.models import NationalAddress

    # رمز بريدي من 4 أرقام
    bad_postal = NationalAddress(user=customer, postal_code="1234")
    with pytest.raises(ValidationError) as exc:
        bad_postal.clean()
    assert (
        "الرمز البريدي يجب أن يتكون من 5 أرقام" in exc.value.message_dict["postal_code"]
    )

    # رقم مبنى من 3 أرقام
    bad_building = NationalAddress(user=customer, building_number="123")
    with pytest.raises(ValidationError) as exc:
        bad_building.clean()
    assert (
        "رقم المبنى يجب أن يتكون من 4 أرقام" in exc.value.message_dict["building_number"]
    )

    # رقم إضافي من 3 أرقام
    bad_additional = NationalAddress(user=customer, additional_number="123")
    with pytest.raises(ValidationError) as exc:
        bad_additional.clean()
    assert (
        "الرقم الإضافي يجب أن يتكون من 4 أرقام"
        in exc.value.message_dict["additional_number"]
    )

    # صيغة صحيحة تمر بسلام
    valid = NationalAddress(
        user=customer,
        postal_code="12345",
        building_number="1234",
        additional_number="5678",
    )
    valid.clean()  # لا يرمي أي استثناء
