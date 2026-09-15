"""الباقات — مبلغُ التأمين الذي يفتح المزايدة، وحصّةُ المزادات. T921.

مقابلُها `packages` في v1: **صفٌّ واحدٌ حيٌّ و`AUTO_INCREMENT = 15`**، أي
أن أربعةَ عشرَ صفّاً جُرّب ثم زال. فالشاشةُ قليلةُ الاستعمال — وذلك يُبسّط
شكلَها ولا يُلغيها: الصفُّ الواحدُ الباقي هو الذي يقرّر **من يزايد أصلاً**
(`bids_submit.php:173` يرفض من كان رصيدُ تأمينه دون `price`).

**والسعرُ مالٌ يقع على عميل، فتغييرُه يلزمه سببٌ مكتوب.** وليس لأنه
«يُعرَض» فحسب — بل لأنه **يُنفَّذ**: رفعُه يقلب مشتركاً قائماً إلى ممنوعٍ
من المزايدة في اللحظة التالية بلا إشعارٍ ولا فاتورة. فحقلُ السبب إلزاميٌّ
على تغيير السعر وحدَه؛ وعلى الإنشاء لا يُطلَب — لا «قبل» يُفسَّر، والقيدُ
يحمل القيمةَ الأولى كاملة.

**ولا حذف.** v1 يحذف حذفاً حقيقيّاً (`PackageController.php:142`) بلا فحصٍ
لـ`userss.id_package`، وأثرُ ذلك في شيفرته: الوصلةُ تسقط فيقرأ **مشترِكٌ
دافعٌ** أن عليه إيداع تأمين. والإيقافُ هنا يُبقي الصفَّ ويمنع إسنادَه.

وبنيةُ الشاشة كـ«شريط الأخبار»: مسارٌ واحد، و`op` يميّز الفعل — والسببُ
مكتوبٌ في رأس `news.py`.
"""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core import audit
from apps.storefront.models import Package

from .forms import ReasonMixin
from .views import atomic_write, console_page, row_for_write

#: ما يُرصد في `AuditLog`. السعرُ أوّلُ ما يُسأل عنه، ولذلك يُرصد معه كلُّ
#: ما يُقرأ بجانبه في الشاشة — قيدٌ يقول «تغيّر السعر» ولا يقول من أيّ باقة
#: يُقرأ مرّتين.
PACKAGE_FIELDS = ["name", "price", "description", "period", "auction_quota", "is_active"]


class PackageForm(ReasonMixin, forms.ModelForm):
    """باقةٌ جديدة أو تعديلُ قائمة. والتفعيلُ ليس حقلاً — زرُّ الصفّ يملكه."""

    class Meta:
        model = Package
        fields = ("name", "price", "description", "period", "auction_quota")
        widgets = {
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "auction_quota": forms.NumberInput(attrs={"min": "0"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        # المعنى في **العنوان** لا في `help_texts`: `console/_form.html` لا
        # يرسم `help_text` إطلاقاً، فشرحٌ يُكتب هناك شرحٌ لا يراه أحد —
        # وإعدادٌ لا يُقرأ أسوأُ من غيابه، لأنه يبدو مكتوباً. رُئي على الشاشة.
        labels = {
            "price": "مبلغ التأمين المطلوب لفتح المزايدة",
            "auction_quota": "حصّة المزادات (٠ تعني: لا مزايدة)",
        }

    def clean_price(self):
        price = self.cleaned_data["price"]
        # `DecimalField` يلتقط النصَّ وما زاد عن الخانات؛ والسالبُ يمرّ منه
        # ويسقط على قيد القاعدة بـ`IntegrityError` — أي صفحةَ ٥٠٠ على رقمٍ
        # كتبه موظّف. فيُردّ هنا بجملةٍ تُقرأ.
        if price is not None and price < Decimal("0"):
            raise forms.ValidationError(
                "سعرٌ سالب يعني عتبةً يجتازها كلُّ رصيد — بما فيه الصفر."
            )
        return price

    def clean(self):
        cleaned = super().clean()

        # السببُ إلزاميٌّ على **تغيير السعر** وحده. ولا يُطلب على الإنشاء:
        # لا قيمةَ سابقةً تُفسَّر، والقيدُ يحمل الأولى كاملةً في `after`.
        if self.instance.pk and "price" in cleaned:
            before = Package.objects.filter(pk=self.instance.pk).values_list(
                "price", flat=True
            )[0]
            if cleaned["price"] != before and not (cleaned.get("reason") or "").strip():
                self.add_error(
                    "reason",
                    f"تغييرُ السعر من {before} إلى {cleaned['price']} يمنع مشتركين "
                    "من المزايدة أو يسمح لآخرين — اكتب سببه.",
                )
        return cleaned


@console_page("console:packages")
@atomic_write
def packages(request):
    """قائمةُ الباقات، وإضافتُها وتعديلُها وإيقافُها — في صفحةٍ واحدة."""
    create_form = PackageForm()
    bound_pk = None
    bound_edit = None
    opens = ""

    if request.method == "POST":
        op = request.POST.get("op", "")

        if op == "create":
            create_form = PackageForm(request.POST)
            if create_form.is_valid():
                row = create_form.save()
                audit.record(
                    action="console.create_package",
                    entity=row,
                    actor=request.user,
                    after=audit.snapshot(row, PACKAGE_FIELDS),
                    note=create_form.cleaned_data["reason"],
                )
                messages.success(request, f"أُضيفت الباقة «{row.name}».")
                return redirect("console:packages")
            opens = "packageNew"

        elif op == "edit":
            row = row_for_write(
                request, Package.objects.all(), pk=request.POST.get("pk")
            )
            before = audit.snapshot(row, PACKAGE_FIELDS)
            bound_edit = PackageForm(request.POST, instance=row)
            if bound_edit.is_valid():
                saved = bound_edit.save()
                audit.record(
                    action="console.edit_package",
                    entity=saved,
                    actor=request.user,
                    before=before,
                    after=audit.snapshot(saved, PACKAGE_FIELDS),
                    note=bound_edit.cleaned_data["reason"],
                )
                messages.success(request, f"حُفظت الباقة «{saved.name}».")
                return redirect("console:packages")
            bound_pk = row.pk
            opens = f"packageEdit{row.pk}"

        elif op == "toggle":
            row = row_for_write(
                request, Package.objects.all(), pk=request.POST.get("pk")
            )
            before = audit.snapshot(row, PACKAGE_FIELDS)
            row.is_active = not row.is_active
            # ما تغيّر وحده يُكتب: حفظٌ كامل يدهس سعراً عدّله غيرُنا بين
            # قراءةِ هذا الطلب وكتابته.
            row.save(update_fields=["is_active", "updated_at"])
            audit.record(
                action="console.toggle_package",
                entity=row,
                actor=request.user,
                before=before,
                after=audit.snapshot(row, PACKAGE_FIELDS),
                note=request.POST.get("reason", "").strip(),
            )
            messages.success(
                request,
                f"فُعّلت الباقة «{row.name}»."
                if row.is_active
                else f"أُوقفت الباقة «{row.name}» — لا تُعرَض ولا تُسنَد من جديد.",
            )
            return redirect("console:packages")

        else:
            messages.error(request, "طلبٌ لا يقول ماذا يريد.")
            return redirect("console:packages")

    rows = list(Package.objects.all())
    pairs = [
        (
            row,
            bound_edit
            if bound_edit is not None and row.pk == bound_pk
            else PackageForm(instance=row),
        )
        for row in rows
    ]
    return render(
        request,
        "console/packages.html",
        {
            "pairs": pairs,
            "form": create_form,
            "offered": sum(1 for row in rows if row.is_active),
            "stopped": sum(1 for row in rows if not row.is_active),
            "opens": opens,
        },
    )


__all__ = ["PackageForm", "packages"]
