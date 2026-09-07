"""T825 — إيقافُ عميلٍ يقع بشاشةٍ ويترك أثراً، ويُغلق البابين لا واحداً.

جرد التكافؤ، القسم (ب): «`User.is_active` حقلٌ قائم، **وليس من حقول
`CustomerForm`** ولا لأي شاشة طريق إليه. إيقاف مزايد اليوم يقع على قاعدة
البيانات».

**والقراءة كشفت أن العطل أعمق من غياب الشاشة.** `is_active` يُفحَص في
`tokens.verify` و`tokens.rotate` وحدهما — أي أنه يقطع الرمز **القائم**. أما
`sign_in_with_code` فلا يسأل عنه: فالموقوف يطلب رمزاً جديداً بجوّاله، يدخل،
ويأخذ زوج رموزٍ جديداً. الإيقاف يصمد حتى أوّل رسالةٍ نصّية.

فهذا الملفّ يحرس بابين:

1. **الشاشة** — إيقافٌ بسببٍ مكتوب وقيدٍ في سجلّ التدقيق، لا يدٌ على قاعدة
   البيانات. وإيقافُ الوصول تغييرٌ تسأل عنه المراجعة أوّلاً، فكان الوحيد بلا
   اسم فاعلٍ ولا سبب.
2. **الباب الثاني** — الدخول برمزٍ جديد يُرفض للموقوف. وبدونه، الشاشة تعطي
   إحساساً بالمنع لا منعاً.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts import services as accounts
from apps.accounts.errors import AccountStopped
from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.core.permissions import Role

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def manager(client) -> User:
    user = staff(Role.OWNER, "966500000701")
    client.force_login(user)
    return user


@pytest.fixture
def customer(db) -> User:
    return User.objects.create_user(phone="966581010101", full_name="مزايد")


def test_staff_can_stop_a_customer_from_a_screen(client, manager, customer):
    client.post(
        reverse("console:customer-access", args=[customer.pk]),
        {"is_active": "", "reason": "شكوى احتيال قيد النظر"},
    )

    customer.refresh_from_db()
    assert customer.is_active is False


def test_stopping_names_its_reason_and_who_did_it(client, manager, customer):
    """إيقافُ وصولٍ بلا سببٍ ولا فاعلٍ هو أوّل ما تسأل عنه المراجعة."""
    client.post(
        reverse("console:customer-access", args=[customer.pk]),
        {"is_active": "", "reason": "شكوى احتيال قيد النظر"},
    )

    entry = AuditLog.objects.get(action="console.set_customer_access")
    assert entry.actor_id == manager.pk
    assert entry.note == "شكوى احتيال قيد النظر"
    assert entry.before["is_active"] is True
    assert entry.after["is_active"] is False


def test_stopping_with_no_reason_is_refused(client, manager, customer):
    response = client.post(
        reverse("console:customer-access", args=[customer.pk]),
        {"is_active": "", "reason": "   "},
    )

    customer.refresh_from_db()
    assert customer.is_active is True
    assert response.status_code in (200, 302)


def test_a_stopped_customer_can_be_let_back_in(client, manager, customer):
    """حارسٌ يمنع العودة يجعل الإيقاف عقوبةً نهائية بيد موظّف."""
    customer.is_active = False
    customer.save(update_fields=["is_active"])

    client.post(
        reverse("console:customer-access", args=[customer.pk]),
        {"is_active": "on", "reason": "الشكوى أُغلقت"},
    )

    customer.refresh_from_db()
    assert customer.is_active is True


# ---------------------------------------------------------------------------
# الباب الثاني — وهو الذي كان مفتوحاً
# ---------------------------------------------------------------------------


def test_a_stopped_customer_cannot_sign_in_with_a_fresh_code(customer, sent):
    """`is_active` يُفحَص في `tokens.verify` و`rotate` وحدهما — أي أنه يقطع
    الرمز **القائم**. والموقوف يطلب رمزاً جديداً بجوّاله فيدخل ويأخذ زوجاً
    جديداً: الإيقاف يصمد حتى أوّل رسالةٍ نصّية.
    """
    customer.is_active = False
    customer.save(update_fields=["is_active"])

    accounts.send_verification_code(phone=customer.phone)

    with pytest.raises(AccountStopped):
        accounts.sign_in_with_code(phone=customer.phone, code=code_from(sent[0]["body"]))


def test_an_active_customer_still_signs_in(customer, sent):
    """الحارس الذي يمنع الدخول السليم يُطفَأ في أسبوع."""
    accounts.send_verification_code(phone=customer.phone)

    user, created = accounts.sign_in_with_code(
        phone=customer.phone, code=code_from(sent[0]["body"])
    )

    assert user.pk == customer.pk
    assert created is False


@pytest.fixture
def sent(monkeypatch) -> list[dict]:
    """التقاطُ ما سُلِّم إلى وصلة الرسائل، بدل قراءته من سجلّ.

    نظير التجهيزة في `apps/accounts/tests/test_auth_otp.py` — ولا تُستورَد
    منها: تجهيزةٌ مشتركة بين حزمتي اختبارٍ تربط ملفَّين لا علاقة بينهما،
    فيكسر تعديلُ أحدهما الآخر.
    """
    box: list[dict] = []

    def backend(*, phone: str, body: str) -> None:
        box.append({"phone": phone, "body": body})

    monkeypatch.setattr("apps.accounts.sms.import_string", lambda path: backend)
    return box


def code_from(message: str) -> str:
    """الأرقام كما يقرأها العميل من شاشته."""
    return "".join(ch for ch in message.split(chr(10))[0] if ch.isdigit())
