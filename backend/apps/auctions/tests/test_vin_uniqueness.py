"""HR-11 — السيارة الواحدة لا تدخل المزاد الواحد مرتين.

في v1 كانت السيارة تُدخَل بلوتين مختلفين في المزاد نفسه، فتُعرض مرتين ويزايد
عليها مزايدان مختلفان، ولا يُكتشف ذلك إلا عند الترسية — حين يكون لسيارةٍ واحدة
فائزان.

**والقيد جزئي، وذلك جوهر التاسك لا تفصيلٌ فيه.** الشاصي `blank=True`، وقيدٌ
كامل يقول إن مركبتين مجهولتَي الشاصي نسخةٌ من بعضهما — وهو ادّعاء. المجهول
ليس قيمةً تتكرّر، ومنعُ الثانية يمنع إدخال أسطولٍ لم تصل أوراقه بعد.

**والكتابة بـSQL خام عمداً**، كما في `test_lot_number.py` نظيره: `full_clean()`
يثبت أن كودنا يفحص، ولا يقول شيئاً عن الاستيراد الجماعي ولا عن جلسة `shell`
في الثانية صباحاً. المادة ٣-٣: القاعدة التي تعيش في المخطط تُثبَت بالالتفاف
حول كل سطر بايثون قد يكون هو من يفعلها.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, connection, transaction

from apps.auctions.models import Vehicle
from apps.auctions.tests.conftest import insert_raw

pytestmark = pytest.mark.django_db

VIN = "JTDBE32K123456789"


def _insert_raw(auction_id: int, lot_number: int, vin: str) -> None:
    """Straight to SQL, so the partial index answers and not `full_clean`."""
    insert_raw(
        Vehicle,
        auction_id=auction_id,
        lot_number=lot_number,
        vin=vin,
        make="تويوتا",
        model="كامري",
        year=2022,
    )


def test_the_same_vin_twice_in_one_auction_fails(make_auction, make_vehicle):
    """العطل نفسه: سيارةٌ واحدة بلوتين، فمزايدان على شيءٍ واحد."""
    auction = make_auction()
    make_vehicle(auction, lot_number=1, vin=VIN)

    with pytest.raises(IntegrityError, match="one_vin_per_auction"):
        with transaction.atomic():
            _insert_raw(auction.pk, 2, VIN)

    assert Vehicle.objects.filter(auction=auction, vin=VIN).count() == 1


def test_two_vehicles_without_a_vin_are_not_duplicates(make_auction, make_vehicle):
    """المجهول ليس قيمةً تتكرّر — وهذا ما يجعل القيد جزئياً.

    أسطولٌ لم تصل أوراقه بعد يدخل المزاد، ولا يقول له النظام إن السيارة
    الثانية نسخةٌ من الأولى لأن كلتيهما بلا شاصي معروف.
    """
    auction = make_auction()
    make_vehicle(auction, lot_number=1, vin="")

    with transaction.atomic():
        _insert_raw(auction.pk, 2, "")

    assert Vehicle.objects.filter(auction=auction, vin="").count() == 2


def test_the_same_vin_in_another_auction_is_the_point(make_auction, make_vehicle):
    """سيارةٌ لم تُبع تُعاد في مزادٍ تالٍ — وذلك هو العمل، لا خطأ فيه."""
    first = make_auction()
    second = make_auction()
    make_vehicle(first, lot_number=1, vin=VIN)

    with transaction.atomic():
        _insert_raw(second.pk, 1, VIN)

    assert Vehicle.objects.filter(vin=VIN).count() == 2


def test_the_constraint_exists_under_the_name_the_code_expects(make_auction):
    """الاسم يزحف حين تُحرَّر هجرةٌ بيد، ورسالةُ الخطأ التي يقرؤها المشغّل هي هو.

    ويُسأل عنه في `pg_indexes` لا في `pg_constraint`: القيد **الجزئي** لا يوجد
    في PostgreSQL بوصفه `CONSTRAINT` أصلاً — يُنشئه Django فهرساً فريداً
    بشرط `WHERE`. وهو الفرق بين اختبارٍ يفحص ما بُني وآخر يفحص ما تصوّرناه
    أنه بُني.
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT indexdef FROM pg_indexes
            WHERE tablename = 'auctions_vehicle'
              AND indexname = 'one_vin_per_auction'
            """
        )
        row = cursor.fetchone()

    assert row is not None, "القيد غير موجود في القاعدة بالاسم المتوقَّع"
    #: والشرط نفسه جزءٌ من التوكيد: فهرسٌ فريد بلا `WHERE` يمنع المجهولين معاً.
    assert "WHERE" in row[0].upper(), f"الفهرس ليس جزئياً: {row[0]}"
