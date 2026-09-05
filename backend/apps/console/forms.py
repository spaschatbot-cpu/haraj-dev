"""The console's edit forms. T805.

Two rules shape every form here, and both come from v1 incidents:

**The state is never a form field.** An auction's or a car's state moves through
`apps.auctions.services` and its state machine, never by somebody typing into a
dropdown — `ops/checks/auction_state_single_writer.py` fails the build if a
screen writes the column. A form offering `state` would be a second way to move
a car, and a second way is how a car ended up `awarded` with no winner in v1.

**Validation happens before the save, field by field.** Under
`STRICT_TRANS_TABLES` v1 aborted the *entire* update when one value did not fit
its column, so an operator correcting six fields lost all six because the
seventh had a stray character — and the error named the statement, not the
field. Django's forms give per-field messages by construction; what this file
adds is making sure nothing reaches the database without passing through one.
"""

from __future__ import annotations

import hashlib
from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.core.time import from_display, to_display


class DisplayDateTimeField(forms.DateTimeField):
    """A datetime typed as a Riyadh wall clock, stored as UTC.

    Django parses a naive form value in ``TIME_ZONE``, which is UTC here — so by
    the time an ordinary `DateTimeField` hands over its result, "10:00" has
    already become 10:00 UTC and the operator's intent is gone. Converting after
    that point cannot recover it: the value no longer says it was a wall clock.

    So the parse itself happens under the display zone, and `apps.core.time`
    does the one conversion (Article 3-1). Both directions are here, because a
    field that stored correctly and rendered in UTC would show an operator a
    time they never typed — which is the same bug wearing the other face.
    """

    def to_python(self, value):
        with timezone.override(ZoneInfo(settings.DISPLAY_TIME_ZONE)):
            parsed = super().to_python(value)
        return from_display(parsed) if parsed else parsed

    def prepare_value(self, value):
        if hasattr(value, "tzinfo") and value is not None and value.tzinfo:
            return to_display(value)
        return value


class ReasonMixin(forms.Form):
    """Every console write carries a written reason.

    Spec 009 asks it of financial actions; it is asked here of edits too, for
    the same reason support gives: a row that changed and nobody can say why is
    a row nobody can explain to the partner who owns it.
    """

    reason = forms.CharField(
        label="سبب التعديل",
        max_length=500,
        widget=forms.TextInput(attrs={"placeholder": "لماذا هذا التغيير؟"}),
        error_messages={"required": "سبب التعديل مطلوب."},
    )

    #: HR-13 — ختمُ حالة الصفّ ساعةَ رُسمت الاستمارة.
    #
    # مخفيّ، ويعود مع الإرسال. فإن اختلف عمّا في القاعدة ساعةَ الحفظ، فبين
    # اللحظتين كتب أحدٌ آخر — وهذا هو كلّ ما يعرفه الخادم، وهو يكفي للرفض.
    row_stamp = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # الختم على **حقول هذه الاستمارة** لا على `updated_at`، لسببين:
        # `User` و`Company` بلا `updated_at` أصلاً فكان سيلزم عمودان وهجرة؛
        # والأهمّ أن `updated_at` يتحرّك لحفظٍ لم يغيّر شيئاً، فيرفض تعديلاً
        # لا يدهس أحداً. والحقول هي بالضبط ما يستطيع هذا النموذج أن يكتبه —
        # لا أوسع فيزعج، ولا أضيق فيفوته ما يحرسه.
        if not self.is_bound:
            self.initial["row_stamp"] = self._row_stamp()

    def _row_stamp(self) -> str:
        """بصمةُ ما تكتبه هذه الاستمارة الآن، أو `""` لصفٍّ لم يوجد بعد."""
        instance = getattr(self, "instance", None)
        if instance is None or instance.pk is None:
            return ""

        # من `self.instance` مباشرةً، وقد جُرّبت إعادةُ قراءةٍ من القاعدة هنا
        # فلم يُسقطها اختبار: الشاشات الأربع كلّها تُحمّل الصفّ بـ`get_object_
        # _or_404` عند الطلب نفسه، فالكائن **هو** ما في القاعدة. وسطرٌ دفاعيّ
        # لا تُسقطه مخالفةٌ مصنوعة سطرٌ لا يُميَّز عن سطرٍ لا يعمل.
        names = list(getattr(getattr(self, "_meta", None), "fields", None) or [])
        payload = "|".join(f"{name}={getattr(instance, name, '')!r}" for name in names)
        return hashlib.sha256(payload.encode()).hexdigest()[:32]

    def clean_reason(self) -> str:
        reason = (self.cleaned_data.get("reason") or "").strip()
        if not reason:
            raise forms.ValidationError("سبب التعديل مطلوب.")
        return reason

    def clean(self):
        cleaned = super().clean()

        # الفحص في `clean` لا في العرض: `_post_clean` يكون قد كتب قيم الإرسال
        # على `self.instance` بحلول ذلك الوقت، فبصمةٌ تُحسب بعده تبصم ما أراده
        # المرسِل لا ما في القاعدة — وتتطابق دائماً.
        expected = self._row_stamp()
        if expected and cleaned.get("row_stamp") != expected:
            raise forms.ValidationError(
                "عُدِّل هذا الصفّ من مكانٍ آخر بعد أن فتحتَ الصفحة. "
                "افتحها من جديد لترى ما صار إليه، ثم أعِد تعديلك — "
                "الحفظ الآن يمحو عمل غيرك بلا أن يعلم."
            )
        return cleaned


class AuctionForm(ReasonMixin, forms.ModelForm):
    """Create or edit an auction — everything except where it stands.

    The times are entered as Riyadh wall clocks and converted once on the way
    in by `apps.core.time.from_display`, which is the only place in the project
    that converts (Article 3-1). An operator typing "منتصف الليل" means midnight
    in Riyadh, and no view here does arithmetic to work that out.
    """

    class Meta:
        model = Auction
        fields = ("number", "title", "starts_at", "ends_at", "deposit_required")
        labels = {
            "number": "رقم المزاد",
            "title": "العنوان",
            "starts_at": "يبدأ",
            "ends_at": "ينتهي",
            "deposit_required": "التأمين المطلوب",
        }
        error_messages = {
            "number": {"unique": "رقم المزاد مستعمل في مزاد آخر."},
        }
        field_classes = {
            "starts_at": DisplayDateTimeField,
            "ends_at": DisplayDateTimeField,
        }
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }

    def clean(self):
        cleaned = super().clean()
        starts, ends = cleaned.get("starts_at"), cleaned.get("ends_at")
        if starts and ends and ends <= starts:
            # Named on the field rather than as a form-wide error: an operator
            # fixing a date wants to know which box is wrong.
            self.add_error("ends_at", "وقت الانتهاء لازم يكون بعد وقت البدء.")
        return cleaned


class VehicleForm(ReasonMixin, forms.ModelForm):
    """Create or edit a car. Its state and its award are not fields.

    `awarded_to`, `awarded_price` and `awarded_at` are settlement's output, not
    an operator's input: an award typed by hand is an award with no bid behind
    it and no money moved for it. Correcting one is `replace_winner`, which
    moves the invoice and the deposit with it.
    """

    class Meta:
        model = Vehicle
        fields = (
            "auction",
            "lot_number",
            "make",
            "model",
            "year",
            "vin",
            "plate_number",
            "plate_type",
            "odometer_km",
            "transmission",
            "fuel_type",
            "condition",
            "owner_company",
            "reserve_price",
        )
        labels = {
            "auction": "المزاد",
            "lot_number": "رقم اللوت",
            "make": "الماركة",
            "model": "الموديل",
            "year": "السنة",
            "vin": "رقم الهيكل",
            "plate_number": "رقم اللوحة",
            "plate_type": "نوع اللوحة",
            "odometer_km": "الممشى (كم)",
            "transmission": "ناقل الحركة",
            "fuel_type": "الوقود",
            "condition": "الحالة الفنية",
            "owner_company": "الشريك المالك",
            "reserve_price": "سعر الوقوف",
        }

    def clean(self):
        cleaned = super().clean()
        auction = cleaned.get("auction")
        lot = cleaned.get("lot_number")

        if auction and lot:
            # The database has a unique constraint on this pair (T405). Checking
            # here as well is not redundancy for its own sake: an IntegrityError
            # reaches the operator as a 500, and "رقم اللوت مستعمل" reaches them
            # as a sentence next to the box they typed it in.
            clash = Vehicle.objects.filter(auction=auction, lot_number=lot)
            if self.instance.pk:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                self.add_error("lot_number", "رقم اللوت مستعمل في هذا المزاد.")

        return cleaned
