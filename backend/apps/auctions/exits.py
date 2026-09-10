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
    UNDER_TRANSFER = "under_transfer", "قيد متابعة النقل"
    ARCHIVED = "archived", "منقولة (أرشيف)"


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

    #: سببُ الخروج — نصٌّ حرٌّ كـ v1 (مثل «خروج بدون نقل — حظر»). لم تُقرأ
    #: مفرداتُه المغلقة من الإنتاج بعد، فيبقى نصّاً لا تعداداً يرفض قيمةَ الأمس.
    exit_reason = models.CharField(max_length=200, blank=True)

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


# ---------------------------------------------------------------------------
# الخدمات — الكاتبُ الوحيد لمراحل الخروج.
# ---------------------------------------------------------------------------


def create_exit(
    vehicle,
    *,
    actor=None,
    exit_reason: str = "",
    recipient_name: str = "",
    recipient_id: str = "",
    recipient_phone: str = "",
    recipient_id_image=None,
) -> VehicleExit:
    """أنشئ أمرَ خروجٍ لمركبةٍ بيعت وسُدِّدت — أو أعِد القائمَ إن وُجد.

    بياناتُ المستلِم تُكتَب عند الإنشاء (نافذةُ v1): اسمُه وهويّتُه وجوّالُه وصورةُ
    هويّته. ولا يُنشأ لمركبةٍ لم تُسدَّد: الخروجُ تسليمٌ، والتسليمُ بعد المال.
    """
    from .states import VehicleState

    existing = VehicleExit.objects.filter(vehicle=vehicle).first()
    if existing is not None:
        return existing

    if vehicle.state not in (VehicleState.PAID, VehicleState.RELEASED):
        raise ValueError("لا يُنشأ أمرُ خروجٍ لمركبةٍ لم تُسدَّد فاتورتُها.")

    return VehicleExit.objects.create(
        vehicle=vehicle,
        exit_reason=exit_reason,
        recipient_name=recipient_name,
        recipient_id=recipient_id,
        recipient_phone=recipient_phone,
        recipient_id_image=recipient_id_image or "",
        created_by=actor,
    )


def confirm_gate(order: VehicleExit) -> VehicleExit:
    """تأكيدُ الخروج من البوابة: يُختَم الخروجُ من الساحة ويصير «قيد النقل».

    يُكتَب `warehouse_exit_at` هنا وحده، فلا صفٌّ في متابعة النقل بلا تاريخ خروج.
    """
    if order.stage == ExitStage.ARCHIVED:
        return order
    order.stage = ExitStage.UNDER_TRANSFER
    if order.warehouse_exit_at is None:
        order.warehouse_exit_at = timezone.now()
    order.save(update_fields=["stage", "warehouse_exit_at", "updated_at"])
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
