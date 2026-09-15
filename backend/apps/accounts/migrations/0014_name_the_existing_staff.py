"""أسماءُ دخولٍ للموظّفين القائمين — وإلّا أُقفلت اللوحةُ على الجميع. T918

‏`0013` يضيف `username` **فارغاً**، و`StaffUsernameBackend` يردّ الاسمَ الفارغ
قبل أيّ استعلام (وهو حارسٌ لازم: `username=""` يطابق ٤٦ ألفَ عميلٍ في
`haraj2_t307`). أي أن الهجرةَ الساذجة — عمودٌ يُضاف ويُترك — تُنتج قاعدةً
**لا يدخل اللوحةَ فيها أحد**، ولا شاشةَ تصلحها لأن شاشةَ الإصلاح خلف الدخول.

فالأسماءُ تُسنَد هنا، و**تُطبَع في مخرَج `migrate`**: من يُشغّل الهجرة هو من
يحتاج أن يعرف بأيّ اسمٍ يدخل بعدها، وقراءةُ الجدول بعد ذلك تستلزم دخولاً هو
ما نحاول إنقاذه بعينه.

## لماذا `staff<id>` ولا شيء أجمل

الأسماءُ الكاملةُ عربيّةٌ («المالك»، «مراجع اللوحة»)، واسمُ الدخول لاتينيّ —
فلا اشتقاقَ منها إلا بنقحرةٍ تُخمَّن وتُقرأ خطأً. و`id` ثابتٌ لا يتغيّر، ومطبوعٌ
في جدول المشرفين إلى جانب الاسم أصلاً (`#4`)، فالرابطُ بين السطرِ المطبوع
والصفِّ على الشاشة مباشر. والاسمُ **مؤقّتٌ بطبعه**: تُغيّره شاشةُ «تعديل مشرف»
بقيدٍ في `AuditLog` متى شاء المالك.

والتصادمُ مستحيلٌ نظرياً (العمودُ جديدٌ وكلُّه فارغ) — ومع ذلك يُعالَج: هجرةٌ
تُعاد على قاعدةٍ أُسنِدت فيها أسماءٌ باليد بين الخطوتين تلقى اسماً مأخوذاً،
و`IntegrityError` وسط هجرةِ بياناتٍ يوقف الترحيلَ كلَّه عند نصفه.
"""

from __future__ import annotations

from django.db import migrations


def name_the_staff(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    taken = set(
        User.objects.exclude(username="").values_list("username", flat=True)
    )
    named: list[str] = []

    # ‏`is_staff` وحدها: العميلُ يبقى بلا اسمٍ عمداً — `""` ليست هويّة، وقيدُ
    # التفرّد جزئيٌّ لذلك بالضبط.
    for person in User.objects.filter(is_staff=True, username="").order_by("id"):
        candidate = f"staff{person.id}"
        suffix = 2
        while candidate in taken:
            candidate = f"staff{person.id}-{suffix}"
            suffix += 1
        taken.add(candidate)

        # ‏`update` لا `save`: نموذجُ الهجرة نموذجٌ تاريخيّ بلا `save` المطويّة
        # للحروف الصغيرة، والقيمةُ هنا مصغَّرةٌ بالبناء فلا فرق — ولا يُستدعى
        # `full_clean` في هجرة، فالتصغيرُ يجب أن يكون صحيحاً عند الكتابة.
        User.objects.filter(pk=person.pk).update(username=candidate)
        named.append(f"  · #{person.id} «{person.full_name}» ← {candidate}")

    if named:
        print("\n  أسماءُ دخولِ المشرفين بعد هذه الهجرة (تُغيَّر من «تعديل مشرف»):")
        print("\n".join(named))
    else:
        print("\n  لا مشرفَ بلا اسم دخول — لم يُسنَد شيء.")


def unname_the_staff(apps, schema_editor):
    """الرجوع: تُمحى الأسماءُ المولَّدة وحدها، لا كلُّ اسم.

    من غيّر اسمَه بعد الهجرة يخسره لو مسحنا العمود كلَّه — والرجوعُ لا يجوز
    أن يُتلف ما كُتب بعده. فالممحوُّ ما يطابق النمطَ المولَّد فقط.
    """
    import re

    User = apps.get_model("accounts", "User")
    pattern = re.compile(r"^staff\d+(-\d+)?$")
    for person in User.objects.filter(is_staff=True).exclude(username=""):
        if pattern.match(person.username):
            User.objects.filter(pk=person.pk).update(username="")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_staff_username")]

    operations = [migrations.RunPython(name_the_staff, unname_the_staff)]
