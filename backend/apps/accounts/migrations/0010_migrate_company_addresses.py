# Generated data migration for T850

from django.db import migrations


def copy_company_addresses(apps, schema_editor):
    Company = apps.get_model("accounts", "Company")
    NationalAddress = apps.get_model("accounts", "NationalAddress")

    for company in Company.objects.all():
        has_address = any(
            [
                company.city,
                company.district,
                company.street,
                company.building_number,
                company.postal_code,
            ]
        )
        if has_address:
            NationalAddress.objects.update_or_create(
                user_id=company.user_id,
                defaults={
                    "city": company.city or "",
                    "district": company.district or "",
                    "street": company.street or "",
                    "building_number": company.building_number or "",
                    "postal_code": company.postal_code or "",
                },
            )


def reverse_copy_company_addresses(apps, schema_editor):
    Company = apps.get_model("accounts", "Company")
    NationalAddress = apps.get_model("accounts", "NationalAddress")

    for addr in NationalAddress.objects.all():
        Company.objects.filter(user_id=addr.user_id).update(
            city=addr.city,
            district=addr.district,
            street=addr.street,
            building_number=addr.building_number,
            postal_code=addr.postal_code,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_add_user_fields_and_national_address"),
    ]

    operations = [
        migrations.RunPython(copy_company_addresses, reverse_copy_company_addresses),
    ]
