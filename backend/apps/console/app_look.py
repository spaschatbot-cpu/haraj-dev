"""«مظهر التطبيق» — اللونُ والإضاءةُ اللذان يراهما عملاءُ تطبيق الجوّال.

طلبُ المالك (١٣ أكتوبر ٢٠٢٦): صار في «حسابي» بالتطبيق قسمُ «المظهر» على مثال
درج «المظهر» هنا، فسأل «ومين يقدر يتحكّم فيها؟» — فالإدارةُ تحدّد ما يراه من لم
يختر، وتقرّر هل يغيّره العميلُ أصلاً.

**خلف «إدارة المحتوى»** كشريط الأخبار لا «منح الصلاحيات»: كتابةٌ تخرج إلى كلّ
عميل، لا مالٌ ولا صلاحيات. وكلُّ حفظٍ قيدُ تدقيقٍ بالقيم قبل وبعد ومن غيّر.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core import audit
from apps.storefront.models import AppAppearance, app_appearance

from .views import console_page

#: ألوانُ العيّنات — قيمُ `.themer__swatch` في app.css، فالعيّنةُ هنا لونُ العيّنة
#: في درج المظهر وفي التطبيق (`HarajAccent`).
SWATCHES = {
    "azure": "#1e3a5f",
    "sea": "#1f97c4",
    "gold": "#a88118",
    "violet": "#8b5cf6",
    "teal": "#159e95",
    "emerald": "#109d5f",
    "amber": "#bc7a0d",
    "rose": "#ef4463",
}


class AppLookForm(forms.Form):
    accent = forms.ChoiceField(
        label="اللون الأساسي",
        choices=AppAppearance.Accent.choices,
        widget=forms.RadioSelect,
    )
    mode = forms.ChoiceField(
        label="الإضاءة",
        choices=AppAppearance.Mode.choices,
        widget=forms.RadioSelect,
    )
    customers_choose = forms.BooleanField(
        label="العميل يغيّر المظهر من حسابه",
        required=False,
        help_text="إن أُطفئ غاب قسمُ «المظهر» من التطبيق، ورأى الجميعُ ما يُختار هنا.",
    )
    reason = forms.CharField(
        label="السبب",
        max_length=500,
        help_text="يدخل سجلَّ التدقيق — لونُ التطبيق يراه كلُّ عميل.",
    )


@console_page("console:app-look")
def app_look(request):
    current = app_appearance()
    form = AppLookForm(request.POST or None, initial=current)
    if request.method == "POST" and form.is_valid():
        data = {k: form.cleaned_data[k] for k in ("accent", "mode", "customers_choose")}
        row = AppAppearance.objects.first() or AppAppearance()
        for key, value in data.items():
            setattr(row, key, value)
        row.updated_by = request.user
        row.save()
        audit.record(
            action="console.app_look",
            entity=row,
            actor=request.user,
            before=current,
            after=data,
            note=form.cleaned_data["reason"],
        )
        messages.success(request, "حُفظ مظهرُ التطبيق — ويراه العملاءُ في أوّل فتحٍ بعده.")
        return redirect("console:app-look")

    choices = [
        {"value": value, "label": label, "swatch": SWATCHES[value]}
        for value, label in AppAppearance.Accent.choices
    ]
    return render(
        request,
        "console/app_look.html",
        {
            "form": form,
            "current": current,
            "accents": choices,
            "modes": AppAppearance.Mode.choices,
            "current_label": dict(AppAppearance.Accent.choices)[current["accent"]],
            "mode_label": dict(AppAppearance.Mode.choices)[current["mode"]],
        },
    )
