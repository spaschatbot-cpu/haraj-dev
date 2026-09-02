"""إعداد جلسة الاختبار — الحارس والـfixtures المشتركة.

هنا شيئان فقط:

1. الحارس الذي يمنع تشغيل الحزمة على أي قاعدة غير PostgreSQL (المادة ٤-٢).
2. الـfixtures التي يحتاجها أكثر من تطبيق واحد، حتى لا يُعاد تعريفها في كل
   ملف اختبار (المادة ٤-٥: لا تكرار لنقطة القرار).

الاستيرادات داخل الدوال لا في رأس الملف: هذا الـconftest يُحمَّل قبل أن ينتهي
pytest-django من تهيئة Django في بعض المسارات، واستيراد نموذج هنا يفجّر
``AppRegistryNotReady`` بدل الرسالة المفهومة التي نريدها.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

REQUIRED_VENDOR = "postgresql"

_WHY = """اختبارات هذا المشروع لا تعمل إلا على PostgreSQL.

القواعد المضبوطة الآن على محرّك آخر:
{offenders}

السبب (الدستور، المادة ٤-٢): محرّك الفلوس يقف على ‏SELECT ... FOR UPDATE‏
وعلى قيود CHECK وفهارس فريدة جزئية. SQLite لا يقدّم أياً منها، فاختبار يمرّ
عليه يقيس نظاماً آخر غير الذي سيعمل في الإنتاج — وهذا بالضبط ما جعل منطق فلوس
في v1 يمرّ محلياً ويفشل على الخادم.

الحل: وجّه الاختبارات إلى PostgreSQL قبل التشغيل، مثلاً:

    export DATABASE_URL=postgres://haraj:haraj@127.0.0.1:5432/haraj2
"""


def pytest_configure(config: pytest.Config) -> None:
    """أوقف الجلسة قبل جمع أي اختبار لو القاعدة ليست PostgreSQL.

    ``vendor`` سمة على صنف الـbackend نفسه، فقراءتها لا تفتح اتصالاً — الحارس
    يعمل حتى لو كانت القاعدة مطفأة، وهذا مقصود: الرسالة عن الاختيار الخاطئ لا
    عن تعذّر الاتصال.
    """
    from django.conf import settings
    from django.db import connections

    offenders = {
        alias: connections[alias].vendor
        for alias in settings.DATABASES
        if connections[alias].vendor != REQUIRED_VENDOR
    }
    if not offenders:
        return

    listing = "\n".join(
        f"  - {alias}: {vendor} ({settings.DATABASES[alias].get('ENGINE')})"
        for alias, vendor in offenders.items()
    )
    raise pytest.UsageError(_WHY.format(offenders=listing))


@pytest.fixture
def customer(db, django_user_model):
    """عميل عادي — المزايد النموذجي في كل اختبار."""
    return django_user_model.objects.create_user(
        phone="966500000001", full_name="عميل اختبار", password="x"
    )


@pytest.fixture
def staff(db, django_user_model):
    """موظف. ليس superuser: الصلاحية الواسعة تخفي أخطاء التصريح."""
    return django_user_model.objects.create_user(
        phone="966500000099", full_name="موظف اختبار", password="x", is_staff=True
    )


@pytest.fixture
def auction(db):
    """مزاد جارٍ الآن — الحالة الوحيدة التي تقبل مزايدة."""
    from django.utils import timezone

    from apps.auctions.models import Auction, AuctionState

    now = timezone.now()
    return Auction.objects.create(
        number=1,
        title="مزاد الاختبار",
        starts_at=now,
        ends_at=now + timedelta(hours=2),
        state=AuctionState.LIVE,
    )
