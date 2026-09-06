"""T826 — طابور عجز الاسترداد له شاشة، والرقم في اللوحة له باب.

جرد التكافؤ، القسم (ب): «أرى طلبات الاسترداد وأعتمدها أو أرفضها» — و`HR-09`
أُغلق ببناء `odoo.RefundShortfall` ومُسجَّلٌ في `tasks.md` أن **«لا شاشة
للطابور بعد»**.

فما يقع اليوم: أودو يطلب سحب وديعةٍ مرهونة، فيُفتح صفٌّ يقول كم طُلب وكم كان
متاحاً وكم العجز — **ولا يبلغه موظّف**. والعميل يسأل «أين استردادي؟» وجوابه
مكتوبٌ عندنا في جدولٍ لا شاشة له.

**وللوحة التحليلات وعدٌ يُتمّه هذا الملفّ.** رسالتها: «كل رقمٍ فيها باب»،
وكل تنبيهٍ فيها يحمل `reverse(...)` إلا واحداً: «عجز استرداد مفتوح» يحمل `""`
— لأن الباب لم يكن مبنيّاً.

**والقراءة والإغلاق صلاحيتان لا واحدة.** المستودع يقسم المال ثلاثاً — قراءة
الدفتر، والفعل فيه، ومنح استثناء — لأن v1 جمعها في علمٍ واحد «فمن يقرأ رصيداً
كان يستطيع مصادرته. فالطابور يُقرأ بـ`money.view` ويُغلق بـ`money.act`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.core.permissions import Role
from apps.odoo.models import InboundMessage, InboundState, RefundShortfall

pytestmark = pytest.mark.django_db


def staff(role: str, phone: str) -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def finance(client) -> User:
    user = staff(Role.FINANCE, "966500000601")
    client.force_login(user)
    return user


@pytest.fixture
def bidder(db) -> User:
    return User.objects.create_user(phone="966582020202", full_name="مزايد")


def a_case(bidder: User, ref: str, shortfall: str = "4000.00") -> RefundShortfall:
    message = InboundMessage.objects.create(
        source="odoo",
        event="refund",
        delivery_id=f"D-{ref}",
        payload={"refund_id": ref},
        state=InboundState.RECEIVED,
    )
    return RefundShortfall.objects.create(
        message=message,
        user=bidder,
        refund_ref=f"odoo:{ref}",
        requested=Decimal("10000.00"),
        free=Decimal("6000.00"),
        held=Decimal("0.00"),
        locked=Decimal("4000.00"),
        shortfall=Decimal(shortfall),
        note="طلب أودو استرداد 10000 والمتاح 6000.",
    )


def test_the_queue_shows_an_open_case(client, finance, bidder):
    a_case(bidder, "R-1")

    body = client.get(reverse("console:refund-queue")).content.decode()

    assert "odoo:R-1" in body
    assert bidder.full_name in body


def test_the_oldest_wait_is_first(client, finance, bidder):
    """ترتيبٌ بالانتظار لا بالمعرّف: من ينتظر استرداده أطول هو السؤال."""
    old = a_case(bidder, "R-OLD")
    a_case(bidder, "R-NEW")
    RefundShortfall.objects.filter(pk=old.pk).update(
        opened_at=timezone.now() - timezone.timedelta(days=3)
    )

    body = client.get(reverse("console:refund-queue")).content.decode()

    assert body.index("odoo:R-OLD") < body.index("odoo:R-NEW")


def test_a_closed_case_is_no_longer_offered_for_closing(client, finance, bidder):
    """المُغلق يبقى معروضاً — «آخر ما أُغلق» هو نصف الجواب عن «ماذا حدث؟».

    فالمقيس ليس غيابه عن الصفحة، بل غيابُ **زرّه**: قضيةٌ مغلقة تُعرض ولا
    تُغلَق مرّتين، لأن الإغلاق الثاني يمحو اسم من أغلق أولاً وقراره.
    """
    case = a_case(bidder, "R-DONE")
    RefundShortfall.objects.filter(pk=case.pk).update(
        resolved_at=timezone.now(), resolution="سُلّمت السيارة", resolved_by=finance
    )

    body = client.get(reverse("console:refund-queue")).content.decode()

    assert "odoo:R-DONE" in body, "المُغلق اختفى، فلا أحد يعرف ماذا حدث"
    assert reverse("console:refund-resolve", args=[case.pk]) not in body


def test_closing_names_its_decision_and_who_made_it(client, finance, bidder):
    """القيد في القاعدة يشترطهما؛ وهذا يثبت أن الشاشة تحترمه لا تبلغه فتنهار."""
    case = a_case(bidder, "R-2")

    client.post(
        reverse("console:refund-resolve", args=[case.pk]),
        {"resolution": "السيارة سُلّمت والوديعة تحقّقت — لا استرداد"},
    )

    case.refresh_from_db()
    assert case.resolved_at is not None
    assert case.resolved_by_id == finance.pk
    assert case.resolution.startswith("السيارة سُلّمت")


def test_closing_leaves_a_row_in_the_audit_log(client, finance, bidder):
    case = a_case(bidder, "R-3")

    client.post(
        reverse("console:refund-resolve", args=[case.pk]),
        {"resolution": "أُعيد للعميل نقداً بموافقة المالك"},
    )

    entry = AuditLog.objects.get(action="console.resolve_refund_shortfall")
    assert entry.actor_id == finance.pk
    assert entry.note.startswith("أُعيد للعميل")


def test_closing_with_no_decision_is_refused(client, finance, bidder):
    """`a_closed_shortfall_names_its_decision` قيدٌ في القاعدة — وبلوغه من
    شاشةٍ صفحةُ خطأ لا جملةٌ بجانب الخانة."""
    case = a_case(bidder, "R-4")

    response = client.post(
        reverse("console:refund-resolve", args=[case.pk]), {"resolution": "   "}
    )

    case.refresh_from_db()
    assert case.resolved_at is None
    assert response.status_code in (200, 302)


def test_a_case_is_not_closed_twice(client, finance, bidder):
    """إغلاقٌ ثانٍ يمحو اسم من أغلق أولاً وقراره."""
    case = a_case(bidder, "R-5")
    url = reverse("console:refund-resolve", args=[case.pk])
    client.post(url, {"resolution": "القرار الأول"})

    client.post(url, {"resolution": "القرار الثاني"})

    case.refresh_from_db()
    assert case.resolution == "القرار الأول"


def test_reading_the_queue_does_not_admit_you_to_closing(client, bidder):
    """المال مقسومٌ ثلاثاً: من يقرأ الدفتر لا يفعل فيه (درس v1)."""
    case = a_case(bidder, "R-6")
    client.force_login(staff(Role.SUPPORT, "966500000602"))

    assert client.get(reverse("console:refund-queue")).status_code == 200
    assert (
        client.post(
            reverse("console:refund-resolve", args=[case.pk]), {"resolution": "لا"}
        ).status_code
        == 403
    )


def test_the_dashboard_alarm_now_has_a_door(client, finance, bidder):
    """وعدُ لوحة التحليلات: «كل رقمٍ فيها باب». هذا كان الوحيد بلا رابط."""
    a_case(bidder, "R-7")

    body = client.get(reverse("console:dashboard")).content.decode()

    assert reverse("console:refund-queue") in body
