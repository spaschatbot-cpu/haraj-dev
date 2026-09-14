"""شريط الأخبار — الجملةُ التي يقرؤها كلُّ زائرٍ على واجهة العميل. T921.

مقابلُها في v1 جدولُ `news_ticker`: ثلاثةُ صفوفٍ حيّة و`AUTO_INCREMENT = 9`،
أي أن **ستّاً كُتبت وحُذفت**. فهذه شاشةُ عملٍ يوميّ لا إعدادٌ يُضبَط مرّة،
وتصميمُها من ذلك: القائمةُ والإضافةُ والتعديلُ في صفحةٍ واحدة، ولا رحلةَ
ذهابٍ وإيابٍ لجملةٍ من سطر.

**ولا حذفَ — إيقافٌ.** ما خرج إلى الناس يبقى صفّاً يُسأل عنه: «متى قلنا
هذا؟» سؤالٌ يُطرح بعد شهور، وقيدُ التدقيق يشير إلى الصفّ بمعرّفه فحذفُه
يترك في السجلّ إشارةً إلى لا شيء. وv1 نفسُه يحمل `is_active`، فالإيقافُ
منطقُه لا اختراعُنا.

**وكلُّ كتابةٍ لها قيدٌ بالنصّ قبل وبعد ومن كتبه.** هذه هي الشاشةُ الوحيدة
في نصيب هذا التاسك التي تكتب كلاماً **يخرج من الشركة إلى الناس**؛ ومن غيّر
جملةً على واجهة العميل فعل فعلاً خارجيّاً، والسؤالُ الذي يليه دائماً «من
كتب هذا؟».

**ومسارٌ واحدٌ لا أربعة.** الإضافةُ والتعديلُ والإيقاف ثلاثةُ `POST` على
عنوان الشاشة نفسِه يميّزها حقلُ `op`. والبديلُ — مسارٌ لكلّ فعل — كان يعني
ثلاثةَ صفوفٍ إضافيّةٍ في `navigation.DETAIL_PAGES` لصفحاتٍ **لا تُفتح
أبداً** (كلُّها تُعيد التوجيه)، أي حارساً يُصان لشيءٍ لا يُرسَم.
"""

from __future__ import annotations

from django import forms
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.core import audit
from apps.storefront.models import NewsTickerMessage

from .forms import DisplayDateTimeField, ReasonMixin
from .views import atomic_write, console_page, row_for_write

#: ما يُرصد في `AuditLog` — النصُّ والنافذةُ والعلم. لا `created_at`: لا
#: يتغيّر، وسطرُ «قبل/بعد» يحمله يقول ما لم يقع.
NEWS_FIELDS = ["text_ar", "text_en", "starts_at", "ends_at", "is_active"]

_DATETIME_WIDGET = {"type": "datetime-local"}


class NewsMessageForm(ReasonMixin, forms.ModelForm):
    """رسالةُ شريط: نصُّها ونافذتُها. والتفعيلُ ليس حقلاً هنا.

    `is_active` يملكه زرُّ «أوقف/فعّل» في الصفّ وحده. ولو كان حقلاً في هذه
    الاستمارة لصار للإيقاف بابان: أحدُهما يكتب قيداً باسم `toggle_news`
    والآخر يخبّئه داخل `edit_news` بين تغييراتٍ أخرى — فيصير سؤالُ «متى
    أُوقفت هذه الرسالة؟» بحثاً في نصوصِ القيود بدل ترشيحٍ على الفعل.
    """

    class Meta:
        model = NewsTickerMessage
        fields = ("text_ar", "text_en", "starts_at", "ends_at")
        field_classes = {
            "starts_at": DisplayDateTimeField,
            "ends_at": DisplayDateTimeField,
        }
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs=_DATETIME_WIDGET, format="%Y-%m-%dT%H:%M"
            ),
            "ends_at": forms.DateTimeInput(
                attrs=_DATETIME_WIDGET, format="%Y-%m-%dT%H:%M"
            ),
        }

    def clean(self):
        cleaned = super().clean()
        starts, ends = cleaned.get("starts_at"), cleaned.get("ends_at")

        # نفسُ شرط `news_window_ends_after_it_starts` في القاعدة، مكرّراً هنا
        # عمداً: القيدُ يحمي البيانات ويخرج `IntegrityError` — أي صفحةَ ٥٠٠
        # على خطأٍ كتبه موظّف. والرسالةُ تُقال بجانب الحقل، والقيدُ يبقى
        # للأبواب التي لا تمرّ بهذه الاستمارة.
        if starts and ends and ends < starts:
            self.add_error(
                "ends_at",
                "نهايةُ العرض قبل بدايته — الرسالةُ بهذه النافذة لا تظهر أبداً.",
            )

        # فراغاتٌ بيضاء ليست نصّاً. `CharField` يقلّمها أصلاً، لكنّ القيد في
        # القاعدة يقارن بـ`""` لا بـ«بعد التقليم» — فلولا هذا لمرّت مسافةٌ
        # واحدةٌ من `shell` ولم تمرّ من هنا، وهو تفاوتٌ لا يُقرأ لاحقاً.
        #
        # و`"text_ar" not in self.errors` شرطٌ لازم: بدونه يحمل حقلٌ رُفض
        # لطوله رسالتين متناقضتين — «أطولُ من ٢٥٥» و«بلا نصّ» معاً. قِيس.
        if "text_ar" not in self.errors and not (cleaned.get("text_ar") or "").strip():
            self.add_error("text_ar", "الرسالةُ بلا نصّ شريطٌ يمرّ بلا كلام.")
        return cleaned


def _forms_for(rows, *, bound_pk=None, bound=None):
    """صفٌّ ومعه استمارتُه — والمرفوضةُ تحلّ محلّ استمارةِ صاحبها.

    استمارةٌ لكلّ صفٍّ لا استمارةٌ واحدةٌ تُملأ بجافاسكربت (كما في شاشة
    الأدوار): هناك سبعةُ أدوارٍ × ثمانَ عشرةَ قدرةً = مئةٌ وستّةٌ وعشرون
    مربّعاً مخفيّاً، وهنا **أربعةُ حقولٍ في صفّ**. والثمنُ الذي يشتريه هذا:
    الرفضُ يعود بأخطائه **بجانب حقولها** وبما كتبه الموظّف لا فارغاً.
    """
    return [
        (
            row,
            bound
            if bound is not None and row.pk == bound_pk
            else NewsMessageForm(instance=row),
        )
        for row in rows
    ]


@console_page("console:news")
@atomic_write
def news(request):
    """قائمةُ رسائل الشريط، وإضافتُها وتعديلُها وإيقافُها — في صفحةٍ واحدة."""
    create_form = NewsMessageForm()
    bound_pk = None
    bound_edit = None
    opens = ""

    if request.method == "POST":
        op = request.POST.get("op", "")

        if op == "create":
            create_form = NewsMessageForm(request.POST)
            if create_form.is_valid():
                row = create_form.save()
                audit.record(
                    action="console.create_news",
                    entity=row,
                    actor=request.user,
                    after=audit.snapshot(row, NEWS_FIELDS),
                    note=create_form.cleaned_data["reason"],
                )
                messages.success(request, "أُضيفت رسالةٌ إلى الشريط.")
                return redirect("console:news")
            opens = "newsNew"

        elif op == "edit":
            row = row_for_write(
                request, NewsTickerMessage.objects.all(), pk=request.POST.get("pk")
            )
            before = audit.snapshot(row, NEWS_FIELDS)
            bound_edit = NewsMessageForm(request.POST, instance=row)
            if bound_edit.is_valid():
                saved = bound_edit.save()
                audit.record(
                    action="console.edit_news",
                    entity=saved,
                    actor=request.user,
                    before=before,
                    after=audit.snapshot(saved, NEWS_FIELDS),
                    note=bound_edit.cleaned_data["reason"],
                )
                messages.success(request, "حُفظ نصُّ الرسالة.")
                return redirect("console:news")
            bound_pk = row.pk
            opens = f"newsEdit{row.pk}"

        elif op == "toggle":
            row = row_for_write(
                request, NewsTickerMessage.objects.all(), pk=request.POST.get("pk")
            )
            before = audit.snapshot(row, NEWS_FIELDS)
            row.is_active = not row.is_active
            # `update_fields` لا حفظٌ كامل: الحفظُ الكامل يكتب النصَّ
            # والنافذةَ بما في الكائن، فيدهس تعديلاً وقع بينهما بقيمٍ قرأها
            # هذا الطلبُ قبل لحظة — وهو عينُ ما يحرس منه `row_stamp`.
            row.save(update_fields=["is_active", "updated_at"])
            audit.record(
                action="console.toggle_news",
                entity=row,
                actor=request.user,
                before=before,
                after=audit.snapshot(row, NEWS_FIELDS),
                note=request.POST.get("reason", "").strip(),
            )
            messages.success(
                request,
                "فُعّلت الرسالة." if row.is_active else "أُوقفت الرسالة.",
            )
            return redirect("console:news")

        else:
            messages.error(request, "طلبٌ لا يقول ماذا يريد.")
            return redirect("console:news")

    rows = list(NewsTickerMessage.objects.all())
    return render(
        request,
        "console/news.html",
        {
            "pairs": _forms_for(rows, bound_pk=bound_pk, bound=bound_edit),
            "form": create_form,
            "showing": sum(1 for row in rows if row.is_showing),
            "stopped": sum(1 for row in rows if not row.is_active),
            "opens": opens,
        },
    )


__all__ = ["NewsMessageForm", "news"]
