"""جسرُ المفاتيح: أيُّ صفٍّ في v1 صار أيَّ صفٍّ عندنا.

## لماذا وُجد هذا الجدول

القاعدة الثالثة في [`spec.md`](../../../specs/004-data-migration/spec.md):
«**مفتاح المصدر محفوظ.** كل صفٍّ مُرحَّل يحمل معرّفه القديم، فتبقى المقارنة
ممكنة للأبد». و`T306` يقولها صراحةً: «رحّل **مع حفظ `legacy_id`**».

**ولم تكن محفوظة.** `import_v1._people` يبني `made[row["id"]] = person` في
الذاكرة، ثم — بعد `bulk_create` الذي لا يُرجع المفاتيح — يعيد المطابقة
**بالجوّال** ويرمي القاموس عند انتهاء الأمر. فبعد الاستيراد لا يبقى في القاعدة
شيءٌ يقول إن هذا الحساب هو `userss.id = 15034`.

وذلك يمنع كلَّ ما بعده لا `T307` وحده: `customer_links.user_id` و
`invoices_odoo.user_id` و`insurance_deposits.user_id` كلُّها مفاتيحُ v1، ولا
سبيل إلى ترجمتها. والمطابقةُ بالجوّال ليست بديلاً — v1 يحوي جوّالاتٍ مكرَّرة
(ولذلك `ignore_conflicts` هناك)، فالمطابقةُ به تخلط حسابين.

## جدولٌ واحدٌ لا عمودٌ على كل نموذج

الشكلُ الآخر `User.legacy_id` و`Auction.legacy_id` و`Vehicle.legacy_id`… أي
عمودٌ في كل نموذجٍ من أربعة، في ثلاثة تطبيقات، لحاجةٍ **تنتهي يوم التحويل**.
وهنا صفٌّ واحدٌ يخدمها جميعاً، وله ثلاثُ فوائدَ عمليّة:

* **نموذجُ المجال يبقى نظيفاً** من عمودٍ لا معنى له إلا في الترحيل؛
* **و`T312` (المطابقة عميلاً عميلاً) و`T313` (تقرير الفروق) يقرآن جدولاً
  واحداً** بدل أربعة `JOIN` مختلفة الشكل؛
* **والحذفُ بعد التحويل حذفُ جدول**، لا أربعُ هجراتٍ على جداولَ حيّة.

وثمنُه مذكور: `JOIN` إضافيّ عند كل ترجمة، وهو ثمنٌ يُدفع في الترحيل وحده —
ولا شيء في مسار التشغيل اليوميّ يقرأ هذا الجدول.
"""

from __future__ import annotations

from django.db import models

__all__ = ["LegacyRef"]


class LegacyRef(models.Model):
    """صفٌّ في v1 ⟶ صفٌّ عندنا. يُكتب مرّةً، ولا يُعدَّل.

    ``model_label`` بصيغة ``app_label.modelname`` — نصٌّ لا `ContentType`:
    الجدولُ يُقرأ من أوامرَ تعمل على قاعدةٍ قد لا تحمل `django_content_type`
    مهيّأً بعد، والنصُّ يبقى مقروءاً بعد حذف النموذج نفسِه يومَ يُنظَّف
    الترحيل — ومعرّفُ `ContentType` لا يبقى.
    """

    model_label = models.CharField(max_length=64, db_index=True)

    #: مفتاحُ الصفّ في v1 كما هو. نصٌّ لأن مفاتيح v1 ليست كلُّها أعداداً
    #: (`invoices_odoo.invoice_id` نصٌّ يحمل `"/"` أحياناً)، وتحويلُها عدداً
    #: هنا يفقد ما لا يُحوَّل بلا أن يقول أحدٌ إنه فُقد.
    legacy_id = models.CharField(max_length=64)

    #: المفتاحُ عندنا. عددٌ صحيحٌ لا `ForeignKey`: الجدولُ يشير إلى أربعة
    #: نماذجَ في ثلاثة تطبيقات، ومفتاحٌ أجنبيٌّ واحدٌ لا يستطيع ذلك — و`GenericForeignKey`
    #: يجرّ `ContentType` الذي رُفض أعلاه.
    object_id = models.BigIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مفتاح مصدر"
        verbose_name_plural = "مفاتيح المصدر"
        constraints = [
            # صفُّ v1 الواحد لا يصير صفّين عندنا. وهو ما يجعل إعادةَ تشغيل
            # الاستيراد آمنةً (القاعدة ٢: «التشغيل مرّتين يعطي نفس الوجهة»):
            # الثانيةُ تصطدم بالقيد بدل أن تُضاعف الجسر.
            models.UniqueConstraint(
                fields=["model_label", "legacy_id"], name="one_row_per_legacy_key"
            ),
        ]
        indexes = [models.Index(fields=["model_label", "object_id"])]

    def __str__(self) -> str:
        return f"{self.model_label} {self.legacy_id} → {self.object_id}"

    # -- ترجمةٌ في الاتجاهين -------------------------------------------------

    @classmethod
    def remember(cls, model_label: str, pairs: dict) -> int:
        """اكتب جسراً لكلّ زوجٍ (مفتاحُ v1 ⟶ صفُّنا). يُرجع كم كُتب.

        ``ignore_conflicts`` لأن الاستيراد يُعاد تشغيله: الصفُّ القائم هو
        الصحيح، ورفعُ خطأٍ هنا يجعل إعادةَ التشغيل — وهي **مطلبٌ** في القاعدة
        الثانية — تسقط على أوّل صفٍّ سبق جسرُه.
        """
        rows = [
            cls(model_label=model_label, legacy_id=str(key), object_id=pk)
            for key, pk in pairs.items()
            if pk is not None
        ]
        cls.objects.bulk_create(rows, batch_size=1000, ignore_conflicts=True)
        return len(rows)

    @classmethod
    def resolve(cls, model_label: str) -> dict[str, int]:
        """كلُّ جسور هذا النموذج قاموساً: مفتاحُ v1 ⟶ مفتاحُنا.

        دفعةً واحدة لا صفّاً صفّاً: البانِي التالي يترجم عشرات الآلاف من
        المفاتيح، واستعلامٌ لكلٍّ منها هو الفرق بين دقيقةٍ وساعة.
        """
        return {
            row["legacy_id"]: row["object_id"]
            for row in cls.objects.filter(model_label=model_label).values(
                "legacy_id", "object_id"
            )
        }
