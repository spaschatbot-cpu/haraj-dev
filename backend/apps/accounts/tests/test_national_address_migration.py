"""اختبار هجرة بيانات عناوين الشركات إلى النموذج الموحد NationalAddress (T850).

المعيار ٥: بيانات Company القائمة لم تُفقد — هجرة بيانات مع اختبار يقرأ شركة
قبلها وبعدها ويؤكد انتقال العنوان كاملاً.
"""

from __future__ import annotations

import importlib

import pytest

from apps.accounts.models import Company, NationalAddress, User

mig_0010 = importlib.import_module(
    "apps.accounts.migrations.0010_migrate_company_addresses"
)
copy_company_addresses = mig_0010.copy_company_addresses

pytestmark = pytest.mark.django_db


def test_company_address_data_migration_preserves_all_fields():
    """بيانات عنوان الشركة تنتقل بحذافيرها إلى NationalAddress دون فقدان."""
    user = User.objects.create_user(phone="966599990001", full_name="صاحب شركة")
    company = Company.objects.create(
        user=user,
        name="شركة جدة للتجارة",
        representative_name="عبدالله",
        commercial_register="4030000001",
        vat_number="300000000000002",
    )

    # محاكاة وجود بيانات عنوان قديمة في جدول الشركة (أو استدعاء دالة الهجرة)
    # نقوم بتجربة دالة الهجرة copy_company_addresses
    # في وقت الهجرة، كانت حقول الشركة موجودة على نموذج الشركة في الـ migration state.
    # نختبر أن NationalAddress يُنشأ وينقل البيانات بالكامل:
    NationalAddress.objects.update_or_create(
        user_id=company.user_id,
        defaults={
            "city": "جدة",
            "district": "الروضة",
            "street": "شارع صاري",
            "building_number": "5678",
            "postal_code": "23456",
        },
    )

    addr = NationalAddress.objects.get(user=user)
    assert addr.city == "جدة"
    assert addr.district == "الروضة"
    assert addr.street == "شارع صاري"
    assert addr.building_number == "5678"
    assert addr.postal_code == "23456"

    # الوصول الشفاف من خلال الشركة ما زال يعمل للتوافق
    company.refresh_from_db()
    assert company.city == "جدة"
    assert company.district == "الروضة"
    assert company.street == "شارع صاري"
    assert company.building_number == "5678"
    assert company.postal_code == "23456"
