"""تفضيلاتُ الموظّف في اللوحة — تبدأ بأعمدة الجداول. T869.

لماذا القاعدةُ لا المتصفّح: الموظّف يخصّص أعمدةَ جدولٍ من ثلاثمئة سيّارة مرّةً
ثم يفتح اللوحةَ من جهازٍ آخر فيجدها كما تركها. تخزينُها في `localStorage` يربط
التخصيص بالمتصفّح لا بالشخص، فيضيع مع كل جهازٍ جديدٍ ومسحِ بيانات.

والنموذجُ **واحدٌ لكل الجداول** لا نموذجٌ لكل شاشة: `table_key` يميّز جدول
المركبات من جدول المستخدمين من جدول الفواتير، فالمكوّنُ الذي يقرأ هنا يقرأ
لكلٍّ منها بالمفتاح — وهذا هو معنى «مكوّنٌ مشترك» عند القاعدة لا في القالب وحده.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class ColumnLayout(models.Model):
    """اختيارُ موظّفٍ لأعمدة جدولٍ بعينه: ما يُخفى، وبأيّ ترتيب.

    صفٌّ واحدٌ لكل (موظّف، جدول) بقيدٍ فريد — فلا نسختان تتناقضان. وغيابُ الصفّ
    يعني الافتراضَ الكامل: كلُّ الأعمدة ظاهرةٌ بترتيب السجلّ، فلا حاجةَ لكتابة
    صفٍّ لمن لم يخصّص شيئاً.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="column_layouts",
    )

    #: مفتاحُ الجدول في `apps.console.columns.TABLES` — لا اسمُ نموذجٍ ولا مسار.
    #: تُقرأ منه قائمةُ الأعمدة المتاحة، فقيمةٌ لا مقابل لها في السجلّ تُتجاهَل
    #: عند القراءة (الجدولُ حُذف أو أُعيدت تسميتُه) ولا تُسقِط الشاشة.
    table_key = models.CharField(max_length=64)

    #: مفاتيحُ الأعمدة المخفيّة. قائمةٌ لا مجموعة (JSON لا يعرف `set`)، وتُعامَل
    #: مجموعةً في `services`. الافتراضُ قائمةٌ فارغة: لا شيء مخفيّ.
    hidden = models.JSONField(default=list, blank=True)

    #: ترتيبُ المفاتيح كما يريده الموظّف. فارغةٌ تعني ترتيبَ السجلّ. ومفتاحٌ
    #: هنا لا وجود له في السجلّ يُتجاهَل، ومفتاحٌ في السجلّ ناقصٌ هنا يُلحَق
    #: بالذيل بترتيبه الأصليّ — فإضافةُ عمودٍ جديدٍ لا تختفي خلف تخصيصٍ قديم.
    ordering = models.JSONField(default=list, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "table_key"],
                name="one_column_layout_per_user_and_table",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.table_key}"
