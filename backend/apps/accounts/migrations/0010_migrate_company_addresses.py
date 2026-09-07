# Generated data migration for T850

from django.db import migrations


#: أعمدةٌ ضاقت في النموذج الجديد: `Company.building_number` كان `varchar(8)`
#: و`postal_code` كان `varchar(8)`، وصارا ٤ و٥ (صيغةُ العنوان الوطنيّ
#: السعوديّ). فقيمةٌ أطول تجعل بوستجرس يرمي
#: `value too long for type character varying(4)` — **وتنهار الهجرة كلُّها**،
#: أي يتوقّف النشر. ولا يظهر ذلك على قاعدة تطوير فيها صفّان قصيران.
NARROWED = {"building_number": 4, "postal_code": 5}


def copy_company_addresses(apps, schema_editor):
    """انقل عناوين الشركات، وسمِّ ما لم يتّسع بدل أن تنهار عليه.

    والقاعدة هي قاعدة T808: **القيمةُ الخطأ تُذكر ولا تُسقط الجدول.** والأشدُّ
    هنا أن السقوط لا يُفقد صفّاً واحداً — يُجهض الهجرة، فلا يُنشَر شيء.

    والقيمةُ التي لا تتّسع **تُترك فارغة ويُطبَع صاحبُها**: قصُّها إلى أربعة
    أرقام يخترع رقمَ مبنى لم يقله أحد، ويُقرأ بعد سنةٍ على أنه الرقم الصحيح.
    والفراغُ يقول «لم يُنقَل» ويُصلَح بعينه.
    """
    Company = apps.get_model("accounts", "Company")
    NationalAddress = apps.get_model("accounts", "NationalAddress")

    dropped = []
    for company in Company.objects.all().iterator(chunk_size=500):
        values = {
            "city": company.city or "",
            "district": company.district or "",
            "street": company.street or "",
            "building_number": company.building_number or "",
            "postal_code": company.postal_code or "",
        }
        for column, limit in NARROWED.items():
            if len(values[column]) > limit:
                dropped.append((company.user_id, column, values[column]))
                values[column] = ""

        if any(values.values()):
            NationalAddress.objects.update_or_create(
                user_id=company.user_id, defaults=values
            )

    for user_id, column, value in dropped:
        print(
            f"  [T850] لم يُنقَل {column}=«{value}» للمستخدم {user_id}: "
            f"أطولُ من {NARROWED[column]} — يُصحَّح من شاشة الشركة."
        )
    if dropped:
        print(f"  [T850] {len(dropped)} قيمةً لم تتّسع، والباقي نُقل.")


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
