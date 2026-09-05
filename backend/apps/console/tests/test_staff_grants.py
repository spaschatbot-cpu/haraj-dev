"""T822 — منح صلاحيةٍ يقع بشاشةٍ ويترك صفّاً، لا بيدٍ على قاعدة البيانات.

جرد التكافؤ، القسم (ب): «`StaffGrant` نموذجٌ **بلا شاشة**، فمنح صلاحية اليوم
لا يقع إلا بيدٍ على قاعدة البيانات».

و T803 بنى الآلية وأثبتها: منحٌ ثم سحبٌ يغيّر الوصول فوراً. لكن **لا أحد
يكتب في الجدول**: لا خدمة، ولا شاشة، ولا تسجيلٌ في لوحة Django —
`capabilities_of` تقرؤه وحدها. فالآلية موجودة والباب غير موجود.

**ولماذا هذا أخطر من شاشةٍ ناقصة عادية.** منحُ صلاحيةٍ هو الفعل الذي يوسّع ما
يستطيعه إنسانٌ في اللوحة كلّها؛ ووقوعه على قاعدة البيانات مباشرةً يعني: بلا
سبب مقروء، وبلا اسم مانحٍ، وبلا صفٍّ في سجلّ التدقيق. أي أن أخطر تغييرٍ في
النظام هو **الوحيد الذي لا أثر له**.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import StaffGrant, User
from apps.core.models import AuditLog
from apps.core.permissions import Capability, Role, can

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def owner(client) -> User:
    user = staff(Role.OWNER, "966500000901")
    client.force_login(user)
    return user


@pytest.fixture
def clerk() -> User:
    return staff(Role.SUPPORT, "966500000902")


def test_the_owner_can_give_a_capability_and_it_takes_effect(client, owner, clerk):
    """معيار T803 بنصّه، لكن **من الشاشة**: منحٌ يغيّر الوصول فوراً."""
    assert not can(clerk, Capability.MONEY_ACT)

    client.post(
        reverse("console:staff-grants", args=[clerk.pk]),
        {
            "capability": Capability.MONEY_ACT,
            "granted": "on",
            "reason": "يغطّي إجازة زميله أسبوعين",
        },
    )

    clerk.refresh_from_db()
    assert can(clerk, Capability.MONEY_ACT)


def test_the_grant_names_its_reason_and_who_gave_it(client, owner, clerk):
    """صفٌّ بلا سبب ولا مانحٍ هو ما لا يستطيع أحدٌ شرحه بعد ستة أشهر."""
    client.post(
        reverse("console:staff-grants", args=[clerk.pk]),
        {
            "capability": Capability.MONEY_ACT,
            "granted": "on",
            "reason": "يغطّي إجازة زميله أسبوعين",
        },
    )

    row = StaffGrant.objects.get(user=clerk, capability=Capability.MONEY_ACT)
    assert row.granted is True
    assert row.reason == "يغطّي إجازة زميله أسبوعين"
    assert row.granted_by_id == owner.pk


def test_the_grant_leaves_a_row_in_the_audit_log(client, owner, clerk):
    """تغييرُ وصولٍ بلا قيدٍ في السجلّ هو أوّل ما تسأل عنه المراجعة."""
    client.post(
        reverse("console:staff-grants", args=[clerk.pk]),
        {
            "capability": Capability.MONEY_ACT,
            "granted": "on",
            "reason": "يغطّي إجازة زميله",
        },
    )

    entry = AuditLog.objects.get(action="console.set_capability")
    assert entry.actor_id == owner.pk
    assert entry.note == "يغطّي إجازة زميله"
    assert entry.after["granted"] is True


def test_revoking_replaces_the_row_rather_than_contradicting_it(client, owner, clerk):
    """`one_grant_per_user_capability` قيدٌ في القاعدة؛ وهذا يثبت أن الشاشة
    تحترمه بدل أن تبلغه فتنهار."""
    url = reverse("console:staff-grants", args=[clerk.pk])
    client.post(
        url,
        {"capability": Capability.MONEY_ACT, "granted": "on", "reason": "تغطية"},
    )
    client.post(url, {"capability": Capability.MONEY_ACT, "reason": "انتهت التغطية"})

    rows = StaffGrant.objects.filter(user=clerk, capability=Capability.MONEY_ACT)
    assert rows.count() == 1
    assert rows.get().granted is False
    assert not can(clerk, Capability.MONEY_ACT)


def test_a_revoke_beats_the_role(client, owner):
    """السحب يسبق الدور — وهو سبب وجود الجدول: إيقاف وصولٍ **اليوم** بلا تعديل
    دورٍ يشترك فيه اثنا عشر."""
    finance = staff(Role.FINANCE, "966500000903")
    assert can(finance, Capability.MONEY_ACT)

    client.post(
        reverse("console:staff-grants", args=[finance.pk]),
        {"capability": Capability.MONEY_ACT, "reason": "تحت المراجعة"},
    )

    finance.refresh_from_db()
    assert not can(finance, Capability.MONEY_ACT)


def test_a_grant_with_no_reason_is_refused(client, owner, clerk):
    """القاعدة تمنعه بـCHECK؛ وبلوغُ القيد من شاشةٍ صفحةُ خطأ لا جملةٌ بجانب
    الخانة."""
    response = client.post(
        reverse("console:staff-grants", args=[clerk.pk]),
        {"capability": Capability.MONEY_ACT, "granted": "on", "reason": "   "},
    )

    assert response.status_code == 200
    assert not StaffGrant.objects.exists()


def test_nobody_below_the_owner_may_open_the_screen(client, clerk):
    """منحُ الصلاحيات ثقةٌ وحدها: من يملكها يستطيع أن يمنح نفسه كل شيء."""
    for role, phone in (
        (Role.OPERATIONS, "966500000904"),
        (Role.FINANCE, "966500000905"),
        (Role.SUPPORT, "966500000906"),
    ):
        client.force_login(staff(role, phone))
        response = client.get(reverse("console:staff-grants", args=[clerk.pk]))
        assert response.status_code == 403, f"{role} فتح شاشة المنح"
