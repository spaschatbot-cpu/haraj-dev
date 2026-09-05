"""HR-14 — عزل الشريك: منعُ وصول، لا ترتيبَ قوائم.

**العطل في v1، بحادثتيه:** حساب الشريك كان يكتب رابط فاتورةٍ أو رقم جوال عميلٍ
في المتصفح فيصل إليه؛ ويرسل قبولاً على سيارةٍ ليست له بـ`POST` مباشر. الرابط
كان مخفيّاً من قائمته، وإخفاءُ الرابط ليس حماية.

**وحالُ v2 أن الشريك لا حساب لوحةٍ له أصلاً:** هو مستخدمٌ عادي له `Company`،
والأدوار أربعة (مالك · تشغيل · مالية · دعم) وليس فيها شريك. و`capabilities_of`
تُعيد المجموعة الفارغة لمن ليس `is_staff`. فالعزل قائمٌ **بالبناء**.

**فلماذا هذا الملفّ إذن؟** لأن ما كان يحرس ذلك اختبارٌ واحد
(`test_a_customer_cannot_reach_the_console_at_all`) يفتح **صفحةً واحدة مختارة
باليد** هي `console:home`. وقائمةٌ مكتوبةٌ باليد هي قائمةٌ يَنسى أحدهم أن
يمدّها، والصفحةُ المنسيّة هي التي أُضيفت على عجل — وهي بعينها التي تخطّت
الحارس. هذا هو الدرس المكتوب في رأس `tests/test_idor.py`، وهذا الملفّ نظيره
داخل اللوحة.

فالمسارات **تُكتشَف من محلّل Django** لا تُكتب: صفحةٌ جديدة تنضمّ إلى هذا
الاختبار بمجرّد وجودها.

**والقراءة والكتابة كلتاهما،** لأن حادثة v1 الثانية كانت `POST` لا `GET`:
صفحةٌ تُخفي زرّها عن الشريك وتقبل `POST` منه ليست معزولة، هي مُرتَّبة.
"""

from __future__ import annotations

import pytest
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from apps.accounts.models import Company, User

pytestmark = pytest.mark.django_db


def console_routes() -> list[str]:
    """أسماء كلّ مسارات اللوحة، مكتشفةً من المحلّل.

    بالاسم لا بالمسار (المادة: `ops/checks/console_urls_are_named.py`): مسارٌ
    مكتوبٌ نصّاً هنا يبطل يوم يتحرّك `APP_BASE`، وقد تحرّك في v1 ثلاث مرات.
    """
    names: list[str] = []

    def walk(resolver, namespace: str) -> None:
        for entry in resolver.url_patterns:
            if isinstance(entry, URLResolver):
                walk(entry, entry.namespace or namespace)
            elif isinstance(entry, URLPattern) and namespace == "console" and entry.name:
                names.append(f"console:{entry.name}")

    walk(get_resolver(), "")
    return sorted(set(names))


def test_the_sweep_actually_found_the_console():
    """مسحٌ لا يجد ما يمسحه يمرّ دائماً — وحارسٌ كهذا يُصدَّق ولا يعمل.

    والرقم أرضيّةٌ لا عدداً مضبوطاً: الصفحات تُضاف، واختبارٌ يُعدَّل مع كل
    إضافة هو اختبارٌ يُعدَّل بلا قراءة.
    """
    assert len(console_routes()) >= 20


@pytest.fixture
def partner_client(client) -> object:
    """شريكٌ مسجَّلُ الدخول: مستخدمٌ له شركةٌ تملك مركبات، وليس `is_staff`."""
    user = User.objects.create_user(
        phone="966500000777", full_name="ممثل الشريك", password="x"
    )
    Company.objects.create(
        user=user, name="شركة الشريك", representative_name="ممثل الشريك"
    )
    client.force_login(user)
    return client


@pytest.mark.parametrize("name", console_routes())
def test_no_console_page_answers_a_partner(partner_client, name):
    """ولا صفحةً واحدة — قراءةً أو كتابة.

    ‏`404` مقبولةٌ لمسارٍ يطلب صفّاً غير موجود، لكنّ `200` ليست مقبولةً أبداً:
    هي بالتعريف صفحةٌ رُسمت لمن لا يملكها. وكذلك `302` إلى غير صفحة الدخول —
    تحويلٌ إلى صفحةٍ داخلية يعني أن الحارس أذن ثم أعاد التوجيه.
    """
    try:
        url = reverse(name)
    except Exception:
        url = reverse(name, args=[1])

    for method in ("get", "post"):
        response = getattr(partner_client, method)(url)
        assert response.status_code != 200, (
            f"{name} أجاب الشريك بصفحة عبر {method.upper()}"
        )
        if response.status_code in (301, 302):
            assert "login" in response["Location"], (
                f"{name} حوّل الشريك إلى {response['Location']} لا إلى الدخول"
            )
