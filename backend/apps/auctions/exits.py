"""أوامرُ الخروج ونقل الملكية — نظيرُ جدول `vehicle_exits` في v1.

دورةُ حياةٍ لمركبةٍ بيعت وسُدِّدت حتى تخرج من الساحة وتُنقَل ملكيّتها:

    إنشاء (created) → البوابة (under_transfer) → نقل الملكية (archived)

**لماذا موديلٌ منفصل لا حالةٌ على المركبة؟** لأن الخروج **حدثٌ له بياناتُه**:
باركودٌ يُمسَح، ومستلِمٌ باسمه وجوّاله، وتاريخُ خروجٍ وتاريخُ نقل، وملفَّا إقرارٍ
وإثبات. حشرُها في `Vehicle` يجعله جدولَ كلِّ شيء؛ وفصلُها يجعل «أين وصل خروجُ
هذه السيارة؟» سؤالاً لصفٍّ واحد. والمركبةُ تبقى `RELEASED` حالةً، والتفاصيلُ هنا.

والخدماتُ **الكاتبُ الوحيد**: كلُّ انتقالٍ يمرّ بدالّةٍ هنا تتحقّق من الحالة
الحاليّة وتكتب الطابعَ الزمنيّ في المعاملة نفسها — فلا صفٌّ «قيد النقل» بلا
تاريخِ خروج، ولا «أرشيف» بلا تاريخِ نقل.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core import uploads


class ExitStage(models.TextChoices):
    CREATED = "created", "تم إنشاء الخروج"
    #: أوراقُه اكتملت (نوعٌ وسببٌ وإقرارٌ موقّع) وينتظر مسحَ الباركود على البوابة.
    #: مرحلةٌ في v1 (`sent_to_gate`) سقطت من النسخة الأولى هنا، فكان الصفُّ يبقى
    #: «تم إنشاء الخروج» بعد رفع أوراقه — فلا يُعرف من الشاشة ما جهّزَ للبوّابة.
    SENT_TO_GATE = "sent_to_gate", "بانتظار البوابة"
    UNDER_TRANSFER = "under_transfer", "قيد متابعة النقل"
    ARCHIVED = "archived", "منقولة (أرشيف)"


class ExitType(models.TextChoices):
    """نوعُ الخروج — وهو **ما يوجّه المركبةَ عند البوابة**.

    مفرداتُ v1 حرفيّاً (`AfterSalesController::vehicleExitUpload`): الثلاثةُ
    مقبولةٌ هناك وما عداها يُردّ بـ422. و`after_transfer` وحدَه ينتهي بالأرشيف
    مباشرةً، والآخران يدخلان متابعةَ النقل.
    """

    AFTER_TRANSFER = "after_transfer", "خروج بعد النقل (تمّ نقل الملكية)"
    WITHOUT_TRANSFER = "without_transfer", "خروج بدون نقل (بانتظار النقل)"
    REPAIR_INSPECTION = "repair_inspection", "خروج للإصلاح والفحص"


class ExitReason(models.TextChoices):
    """سببُ الخروج — يُطلَب لكلّ نوعٍ **إلا** `after_transfer`.

    ولهذه المفردات أثرٌ على الشاشة لا على التخزين وحده: `no_plates_ban` تعني
    مركبةً محظورة، ولا تُعامَل معاملةَ «بانتظار نقل الملكية» في لسان المتابعة —
    الموظّفُ يتابع رفعَ الحظر أولاً (`ban_lifted_at`)، ثم تعود إلى المتابعة
    العاديّة.
    """

    NO_PROBLEM = "no_problem", "خروج بدون مشكلة"
    NO_PLATES_NO_INSPECTION = "no_plates_no_inspection", "بدون لوحات / لا يوجد فحص"
    NO_PLATES_BAN = "no_plates_ban", "بدون لوحات / حظر"


def _new_barcode() -> str:
    """رمزٌ فريدٌ يُطبَع باركوداً ويُمسَح عند البوابة — قصيرٌ وقابلٌ للكتابة يدوياً
    إن تعذّر المسح. بادئةُ `HRJ-` كـ v1. `secrets` لا `random`: يُطبَع على ورقةٍ
    تُسلَّم بها سيارة."""
    return "HRJ-" + secrets.token_hex(5).upper()


class VehicleExit(models.Model):
    """أمرُ خروجٍ واحدٍ لمركبةٍ واحدة."""

    vehicle = models.OneToOneField(
        "auctions.Vehicle", on_delete=models.PROTECT, related_name="exit_order"
    )
    stage = models.CharField(
        max_length=20, choices=ExitStage.choices, default=ExitStage.CREATED
    )

    #: باركودُ الإقرار — فريدٌ، يُمسَح عند البوابة. مفهرَسٌ لأن البوابة تبحث به.
    barcode = models.CharField(max_length=24, unique=True, default=_new_barcode)

    #: نوعُ الخروج وسببُه — يُملآن في خطوة «رفع الموقّع» لا عند الإنشاء، كـ v1:
    #: الموظّفُ لا يعرف عند طباعة الإقرار أستُنقَل الملكيّةُ قبل الخروج أم بعده.
    exit_type = models.CharField(
        max_length=24, choices=ExitType.choices, blank=True, db_index=True
    )
    #: كان نصّاً حرّاً بحجّة أن «مفرداتِه المغلقة لم تُقرأ من الإنتاج بعد» —
    #: وقد قُرئت: `vehicleExitUpload` في v1 يقبل ثلاثاً ويردّ ما عداها بـ422.
    #: و`max_length` يبقى ٢٠٠ لا ٢٤: تضييقُه يقطع صفّاً قديماً لو حُقنت قاعدةٌ
    #: من v1 بنصٍّ حرّ، والقيدُ الحقيقيّ هو `choices` لا طولُ العمود.
    exit_reason = models.CharField(
        max_length=200, choices=ExitReason.choices, blank=True
    )

    #: المستلِمُ الفعليّ — قد لا يكون المشتري (وكيلٌ أو ناقل). باسمه وهويّته وجوّاله.
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_id = models.CharField(max_length=40, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    #: تاريخُ الإقرار — يُملأ في نافذة التعديل (يُطبَع على السند). اختياريّ.
    declaration_date = models.DateField(null=True, blank=True)

    #: صورةُ هوية المستلِم — تُرفَع عند إنشاء الأمر (نافذةُ v1). مرفقٌ لا يُطبَع
    #: على الإقرار بل يُحفَظ سنداً لمن استلم.
    recipient_id_image = models.FileField(
        upload_to=uploads.exit_declaration_path, blank=True
    )
    declaration_file = models.FileField(
        upload_to=uploads.exit_declaration_path, blank=True
    )
    transfer_proof_file = models.FileField(
        upload_to=uploads.exit_proof_path, blank=True
    )

    #: طوابعُ المراحل — كلٌّ يُكتب في خدمةٍ واحدة، فلا يُملأ إلا في محلّه.
    warehouse_exit_at = models.DateTimeField(null=True, blank=True)
    transfer_at = models.DateTimeField(null=True, blank=True)
    ban_lifted_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["stage"])]

    def __str__(self) -> str:
        return f"خروج {self.barcode} — لوت {self.vehicle_id}"

    @property
    def days_out(self) -> int | None:
        """كم يوماً مضى على الخروج من الساحة دون نقلٍ — عمودُ «المؤقّت» في v1."""
        if self.warehouse_exit_at is None:
            return None
        return (timezone.now() - self.warehouse_exit_at).days

    @property
    def is_banned(self) -> bool:
        """مركبةٌ خرجت بلا لوحاتٍ وعليها حظرٌ لم يُرفَع بعد."""
        return (
            self.exit_reason == ExitReason.NO_PLATES_BAN
            and self.ban_lifted_at is None
        )

    @property
    def purpose(self) -> tuple[str, str]:
        """عمودُ «الغرض / الحالة»: ماذا يتابع الموظّفُ في هذا الصفّ بالضبط.

        خمسُ حالاتٍ كـ v1، وأهمُّها الأولى: **المحظورةُ ليست «بانتظار نقل
        الملكية»**. لو عُرضت كذلك لطالب الموظّفُ العميلَ بنقلٍ لا يستطيعه
        نظاماً، والمتابعةُ الصحيحةُ رفعُ الحظر أولاً.
        """
        if self.is_banned:
            return "خروج بدون نقل — حظر (متابعة رفع الحظر)", "bad"
        if self.exit_reason == ExitReason.NO_PLATES_BAN:
            return "رُفع الحظر — متابعة نقل الملكية", "ok"
        if self.exit_type == ExitType.REPAIR_INSPECTION:
            return "خروج للإصلاح والفحص", "info"
        if self.exit_reason == ExitReason.NO_PLATES_NO_INSPECTION:
            return "خروج بدون لوحات / لا فحص", "warn"
        return "بانتظار نقل الملكية", "warn"

    @property
    def timer(self) -> tuple[str, str, int]:
        """عمودُ «المؤقّت»: نصٌّ ونبرةٌ ودرجةُ تأخّر (٠–٣) — عتباتُ v1 نفسُها.

        ١٥ يوماً مهلةٌ، ثم متأخر، وعند ٢٥ تنبيهُ مديرٍ وعند ٣٠ تنبيهُ المالك.
        والدرجةُ تُلوّن الصفَّ كلَّه لا الخليّةَ وحدها: جدولٌ من ستّين صفّاً
        لا يُقرأ بشارةٍ صغيرةٍ في عمودٍ واحد.

        وهي عتباتُ `cron_vehicle_exit_alerts.php` في v1 حرفيّاً — التنبيهُ نفسُه
        لم يُبنَ هنا بعد، فالشارةُ هي الإشارةُ الوحيدة المرئيّة اليوم.
        """
        days = self.days_out
        if days is None:
            return "—", "plain", 0
        if days < 15:
            return f"ضمن المهلة ({days} يوم)", "ok", 0
        if days < 25:
            return f"متأخر ({days} يوم)", "bad", 1
        if days < 30:
            return f"تنبيه مدير ({days} يوم)", "bad", 2
        return f"تنبيه المالك ({days} يوم)", "critical", 3


# ---------------------------------------------------------------------------
# الخدمات — الكاتبُ الوحيد لمراحل الخروج.
# ---------------------------------------------------------------------------


def create_exit(
    vehicle,
    *,
    actor=None,
    recipient_name: str = "",
    recipient_id: str = "",
    recipient_phone: str = "",
    recipient_id_image=None,
) -> VehicleExit:
    """أنشئ أمرَ خروجٍ لمركبةٍ بيعت وسُدِّدت — أو أعِد القائمَ إن وُجد.

    بياناتُ المستلِم تُكتَب عند الإنشاء (نافذةُ v1): اسمُه وهويّتُه وجوّالُه وصورةُ
    هويّته. ولا يُنشأ لمركبةٍ لم تُسدَّد: الخروجُ تسليمٌ، والتسليمُ بعد المال.

    ولا نوعَ هنا ولا سبب: كانا وسيطين في هذه الدالّة لا يمرّرهما أحد (لا خانةَ
    لهما في أيّ استمارة)، فيبقى العمودان فارغين أبداً والبوّابةُ توجّه كلَّ
    مركبةٍ إلى المتابعة. محلُّهما `set_papers` كـ v1.
    """
    from .states import VehicleState

    existing = VehicleExit.objects.filter(vehicle=vehicle).first()
    if existing is not None:
        return existing

    if vehicle.state not in (VehicleState.PAID, VehicleState.RELEASED):
        raise ValueError("لا يُنشأ أمرُ خروجٍ لمركبةٍ لم تُسدَّد فاتورتُها.")

    return VehicleExit.objects.create(
        vehicle=vehicle,
        recipient_name=recipient_name,
        recipient_id=recipient_id,
        recipient_phone=recipient_phone,
        recipient_id_image=recipient_id_image or "",
        created_by=actor,
    )


def set_papers(
    order: VehicleExit,
    *,
    exit_type: str,
    exit_reason: str = "",
    signed=None,
    proof=None,
) -> VehicleExit:
    """أوراقُ الخروج: نوعُه وسببُه وإقرارُه الموقّع — ثم يُرسَل إلى البوابة.

    الخطوةُ التي كانت غائبةً بكاملها: `exit_upload` كانت تحفظ الملفَّ وحده،
    فلا يُكتب نوعُ خروجٍ قطّ، **فتوجيهُ البوابة يستحيل** (انظر `confirm_gate`).

    والشروطُ شروطُ v1 حرفاً بحرف، ولكلٍّ سببُه:

    * **النوع مطلوب** — وهو المُوجِّه، وبدونه تذهب المركبةُ إلى المتابعة بحكم
      الصمت لا بحكم قرار.
    * **السبب مطلوبٌ لغير `after_transfer`** — ومنه وحده يُعرف المحظورُ الذي
      يُتابَع رفعُ حظره لا نقلُ ملكيّته.
    * **الإقرار الموقّع مطلوبٌ دائماً** — هو السند الذي تُسلَّم به السيارة.
    * **وإثباتُ النقل مطلوبٌ مع `after_transfer` وحده** — لأن هذا النوعَ يُؤرشِف
      الصفَّ عند البوابة مباشرةً، فلو مرّ بلا إثباتٍ لَما بقي بعده لسانٌ يُطالَب
      فيه أحدٌ به.
    """
    if exit_type not in ExitType.values:
        raise ValueError("نوعُ الخروج مطلوب.")

    after = exit_type == ExitType.AFTER_TRANSFER
    if after:
        # منقولةٌ سلفاً فلا سببَ لخروجها — ويُمحى ما كُتب قبلُ إن غُيّر النوع.
        exit_reason = ""
    elif exit_reason not in ExitReason.values:
        raise ValueError("سببُ الخروج مطلوب.")

    if signed is None and not order.declaration_file:
        raise ValueError("صورةُ الإقرار الموقّع مطلوبة.")
    if after and proof is None and not order.transfer_proof_file:
        raise ValueError("صورةُ إثبات نقل الملكية مطلوبةٌ لهذا النوع.")

    order.exit_type = exit_type
    order.exit_reason = exit_reason
    order.stage = ExitStage.SENT_TO_GATE
    fields = ["exit_type", "exit_reason", "stage", "updated_at"]
    if signed is not None:
        order.declaration_file = signed
        fields.append("declaration_file")
    if proof is not None:
        order.transfer_proof_file = proof
        fields.append("transfer_proof_file")
    order.save(update_fields=fields)
    return order


def confirm_gate(order: VehicleExit) -> VehicleExit:
    """تأكيدُ الخروج من البوابة: يُختَم الخروجُ من الساحة، ويُوجَّه بحسب النوع.

    يُكتَب `warehouse_exit_at` هنا وحده، فلا صفٌّ في متابعة النقل بلا تاريخ خروج.

    والتوجيهُ توجيهُ v1 (`vehicleExitGateConfirm`): `after_transfer` مركبةٌ
    نُقلت ملكيّتُها قبل أن تخرج، فمتابعةُ نقلِ ملكيّتها بعد خروجها لا معنى لها —
    تُؤرشَف في اللحظة نفسها بتاريخ نقلٍ هو تاريخُ خروجها. وما عداه يدخل المتابعة.

    وأمرٌ بلا نوعٍ (لم تُرفَع أوراقُه) يدخل المتابعة كما في v1 — لا يُردّ عند
    البوّابة: السيارةُ واقفةٌ هناك وسائقُها ينتظر، والمتابعةُ بابُ إصلاحٍ مفتوح
    بينما الردُّ بابٌ مغلقٌ على رصيف.
    """
    if order.stage == ExitStage.ARCHIVED:
        return order

    now = timezone.now()
    if order.warehouse_exit_at is None:
        order.warehouse_exit_at = now
    fields = ["stage", "warehouse_exit_at", "updated_at"]

    if order.exit_type == ExitType.AFTER_TRANSFER:
        order.stage = ExitStage.ARCHIVED
        order.transfer_at = order.warehouse_exit_at
        fields.append("transfer_at")
    else:
        order.stage = ExitStage.UNDER_TRANSFER

    order.save(update_fields=fields)
    return order


def mark_transferred(order: VehicleExit, *, proof=None) -> VehicleExit:
    """نقلُ الملكية تمّ: يُؤرشَف الأمرُ ويُكتَب تاريخُ النقل (وإثباتُه إن رُفع)."""
    order.stage = ExitStage.ARCHIVED
    order.transfer_at = timezone.now()
    fields = ["stage", "transfer_at", "updated_at"]
    if proof is not None:
        order.transfer_proof_file = proof
        fields.append("transfer_proof_file")
    order.save(update_fields=fields)
    return order


def lift_ban(order: VehicleExit) -> VehicleExit:
    """رفعُ الحظر (خروجٌ بلا لوحات) — يُؤرَّخ فيُتابَع النقلُ بعده."""
    if order.ban_lifted_at is None:
        order.ban_lifted_at = timezone.now()
        order.save(update_fields=["ban_lifted_at", "updated_at"])
    return order
