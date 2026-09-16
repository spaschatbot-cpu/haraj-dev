"""قرارات المزايدات: ما رسا، وملخّصُه. T830أ.

الشاشتان من قائمة v1 (`/bills/accepted` و`/auctions/bids/accepted-summary`)،
وهما قراءةٌ محضة: لا ترسية تُطلَق من هنا ولا فاتورةٌ تُصدَر. الترسية في
`apps.auctions.services` وحدها، والفاتورة في `apps.money.services` — وشاشةٌ
تعرض ما وقع لا يجوز أن تكون بابَ تغييرٍ فيه.

ثلاثة فروقٍ عن v1، كلٌّ منها من عطلٍ مقيسٍ في الإنتاج
=====================================================

**١ — «مقبولة» تعني صفّاً واحداً لكل مركبة.** شاشة v1 تعرض ٤٬٣٧٨ صفّاً،
وعشرةٌ منها المتتالية لمركبةٍ واحدة (`معرف 1017`، اللوحة `6996 ر أ و`) بعشرة
مزايدين ومبالغ من `6,777` إلى `315,000`، **وكلُّها بحالة «مقبول»**. ومن قرأها
ظنَّ عشرة فائزين على سيارة. والمبالغ تكشف السبب: `مسافه التوصيل` وحده ثلاثة
صفوف (`6,777` ثم `10,777` ثم `20,777`) — أي مزايداتٌ متتالية لشخصٍ واحد،
والمستبدَلةُ منها تُعرض «مقبولة».

فهذه الشاشة تُبنى على **المركبة** لا على المزايدة: `Vehicle.awarded_to`
واحدٌ بقيدٍ في القاعدة (`an_awarded_vehicle_names_its_winner`)، فصفٌّ واحدٌ
لكلّ مركبةٍ رست — لا يُمكن غيرُه.

**٢ — الضريبة لا تُحسب هنا.** v1 يكتب `15%` عموداً نصّياً ويضرب فيه. وفي هذا
المستودع `money.services.tax_of` هي **الموضع الوحيد** الذي يضرب في النسبة،
و`ops/checks/one_tax_rule.py` يُسقط البناء على ثانٍ — لأن الفاتورة التي نصدرها
نحن تحمل مبلغاً **قبل** الضريبة، والتي تصل من أودو تحمله **شاملاً**؛ ومعادلةٌ
واحدة عليهما تُحمّل العميل ١٥٪ على رقمٍ فيه ١٥٪ أصلاً.

ولذلك: **الضريبة تُقرأ من الفاتورة، لا من سعر الترسية.** المركبة التي رست ولم
تُفوتَر بعدُ تعرض `—` في عمودَي الضريبة والإجمالي، وتقول «بلا فاتورة». وذلك
ليس نقصاً في الشاشة — هو الحقيقة: لا ضريبةَ على مبلغٍ لم يُفوتَر، والرقم الذي
كان سيُعرَض هناك تخمينٌ.

**٣ — الملخّص يعدّ ما تعدّه القائمة.** في v1 تقول «المزايدات المقبولة»
٤٬٣٧٨ صفّاً و«ملخّص المقبولة» بجوارها `0.00` و`0.00` و`0` — لأن فلترَ الأولى
«مقبول» وفلترَ الثانية «نشطة/مقبولة»، فالشاشتان تعدّان شيئين مختلفين تحت اسمٍ
واحد. وهنا الملخّص يستدعي `awarded()` نفسها التي تبنيها القائمة، بالمرشّحات
نفسها — فرقمُه **هو** عدد صفوفها بحكم البناء، ويثبت ذلك اختبارٌ يقارنهما.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import render
from django.utils.timezone import localtime

from apps.auctions.models import Vehicle
from apps.core.arabic import search_q
from apps.money import services as money
from apps.money.models import Invoice

from .exports import export_table, wants_export
from .sensitive import AWARDED_STATES, CUSTOMER, MONEY, columns_for, prepare, shown_to
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")

PAGE_SIZE = 50

#: المركبة التي رست. تُقرأ من الحالة لا من وجود `awarded_to`: الحالتان
#: متلازمتان بقيدٍ في القاعدة، والقراءة من الحالة تُفهرَس.
#:
#: واسمٌ آخرُ لـ:data:`~apps.console.sensitive.AWARDED_STATES` لا نسخةٌ ثانية:
#: حارسُ المبلغ يسأل «أرَست؟» وهذه الشاشة تُبنى على الجواب نفسِه، وتعريفان
#: للكلمة الواحدة يُصلَح أحدُهما ويُنسى الآخر. والاسمُ هنا يبقى لأن
#: `analytics.py` يستورده باسمه.
AWARDED = AWARDED_STATES


def awarded(*, text: str = "", first: str = "", last: str = ""):
    """المركبات التي رست، الأحدث ترسيةً أولاً — صفٌّ واحدٌ لكلٍّ منها.

    مفصولةٌ عن العرض ليسألها الاختبار والملخّصُ **الاستعلام نفسه**: ادّعاءُ أن
    الرقمين يعدّان الشيء ذاته يجب أن يكون خاصيّةَ بناءٍ لا وعداً في تعليق.

    `select_related` على الثلاثة لأن كل صفٍّ يعرض اسم الفائز وجوّاله ورقم
    المزاد: بدونها صفحةٌ من ٥٠ صفّاً تساوي ١٥١ استعلاماً.
    """
    rows = (
        Vehicle.objects.filter(state__in=AWARDED, awarded_to__isnull=False)
        .select_related("auction", "awarded_to", "owner_company")
        .order_by("-awarded_at", "-id")
    )

    text = (text or "").strip()
    if text:
        # ما يُتذكَّر من مركبةٍ رست: لوحتها، أو شاصيها، أو اسم من أخذها، أو
        # رقم مزادها. ولا يُعرف أيُّها في يد السائل، فتُطابَق الأربعة.
        matches = search_q(
            text,
            "plate_number",
            "vin",
            "awarded_to__full_name",
            "awarded_to__phone",
            "make",
            "model",
        )
        if text.isdigit():
            matches |= Q(auction__number=int(text)) | Q(lot_number=int(text))
        rows = rows.filter(matches)

    # مدى أرقام المزادات كما في v1 («من رقم مزاد» / «إلى رقم مزاد»). والقيمة
    # غيرُ الرقمية تُهمَل ولا تُسقِط الصفحة: خانةٌ يكتب فيها موظّفٌ حرفاً
    # فتُرمى 500 هي خانةٌ لا تُستعمل مرّةً ثانية.
    if (first or "").strip().isdigit():
        rows = rows.filter(auction__number__gte=int(first))
    if (last or "").strip().isdigit():
        rows = rows.filter(auction__number__lte=int(last))

    return rows


def money_of(vehicle: Vehicle) -> dict:
    """ما تحمله هذه الترسية من مالٍ — **من فاتورتها إن وُجدت**.

    ولا يُحسب هنا شيء: `tax_of` هي القارئ الوحيد للنسبة في المستودع، وتنظر في
    `Invoice.source` قبل أن تضرب. والمركبة بلا فاتورةٍ تُرجع `None` في
    الثلاثة — لا أصفاراً: الصفر رقمٌ يُجمَع، و«لا يوجد» ليس صفراً.
    """
    invoice = (
        Invoice.objects.filter(vehicle=vehicle).order_by("-issued_at", "-id").first()
    )
    if invoice is None:
        return {"invoice": None, "base": None, "tax": None, "total": None}

    split = money.tax_of(invoice)
    return {
        "invoice": invoice,
        "base": split.base,
        "tax": split.tax,
        "total": split.total,
    }


@console_page("console:accepted-bids")
def accepted_bids(request):
    """المزايدات المقبولة: صفٌّ لكل مركبةٍ رست، ومالُها من فاتورتها."""
    rows = awarded(
        text=request.GET.get("q", ""),
        first=request.GET.get("from", ""),
        last=request.GET.get("to", ""),
    )

    # الشاشةُ `auctions.view`، والفائزُ وجوّالُه ومبالغُه ليسوا منها. وكانت
    # الصفحةُ تضع في **مصدرها** ثمانيةَ جوّالاتٍ واثنين وعشرين مبلغاً لمن يملك
    # `auctions.view` وحدَها، والملفُّ أربعةَ عشرَ عموداً فيها «الفائز»
    # و«الجوال» و«سعر الترسية» و«الضريبة». والقاعدةُ في `sensitive.py`.
    seen = shown_to(request.user)

    if wants_export(request):
        return export_table(
            rows,
            name="المزايدات-المقبولة",
            columns=columns_for(
                [
                    ("المزاد", lambda row: row.auction.number, None),
                    ("اللوت", lambda row: row.lot_number, None),
                    ("المركبة", lambda row: f"{row.make} {row.model}", None),
                    ("السنة", lambda row: row.year, None),
                    ("اللوحة", lambda row: row.plate_number, None),
                    ("اللون", lambda row: row.get_colour_display(), None),
                    ("رقم الهيكل", lambda row: row.vin, None),
                    ("الفائز", lambda row: row.awarded_to.full_name, CUSTOMER),
                    ("الجوال", lambda row: row.awarded_to.phone, CUSTOMER),
                    ("سعر الترسية", lambda row: row.awarded_price or ZERO, MONEY),
                    (
                        "تاريخ الانتهاء",
                        lambda row: localtime(row.auction.ends_at).strftime("%Y-%m-%d")
                        if row.auction.ends_at
                        else "",
                        None,
                    ),
                    ("الحالة", lambda row: row.get_state_display(), None),
                    # رقمُ الفاتورة يبقى بـ`auctions.view`: «أفُوتِرت هذه
                    # المركبة؟» سؤالُ تشغيلٍ لا سؤالُ مال — الحكمُ نفسُه الذي
                    # في `sensitive.py` وفي كتالوج السيارات.
                    ("رقم الفاتورة", lambda row: _cell(row, "number"), None),
                    ("قبل الضريبة", lambda row: _cell(row, "base"), MONEY),
                    ("الضريبة", lambda row: _cell(row, "tax"), MONEY),
                    ("الإجمالي", lambda row: _cell(row, "total"), MONEY),
                ],
                seen,
            ),
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    # الفاتورة تُقرأ لصفحةٍ واحدة لا للاستعلام كلّه: `money_of` استعلامٌ لكل
    # صفّ، وخمسون منها مقبولةٌ في صفحة، وأربعةُ آلافٍ في تصدير ليست كذلك —
    # ولذلك التصدير يمرّ بـ`_cell` التي تقرأ الفاتورة مرّةً لكلّ صفّ وتحفظها
    # عليه، فأربعةُ أعمدةٍ ماليّةٍ لا تعني أربعةَ استعلامات.
    for vehicle in page.object_list:
        vehicle.money = money_of(vehicle)
        # الثلاثةُ تُمحى من الصفّ قبل أن يصل القالبَ، لا تُخفى فيه: «قبل
        # الضريبة» و«الضريبة» و«الإجمالي» مبالغُ فاتورةٍ بعينها. ورقمُ
        # الفاتورة ورابطُها يبقيان، وهما ما يبقى في v1 نفسِه.
        if not seen.money:
            vehicle.money |= {"base": None, "tax": None, "total": None}

    # اسمُ الفائز وجوّالُه إلى `buyer_name`/`buyer_phone`، وسعرُ الترسية إلى
    # `award_price` — بالدالّة نفسها التي تحرس الكتالوج وكارت الأرشيف.
    prepare(page.object_list, seen)

    return render(
        request,
        "console/accepted_bids.html",
        {
            "page": page,
            "show_money": seen.money,
            "show_customer": seen.customer,
            "q": request.GET.get("q", ""),
            "first": request.GET.get("from", ""),
            "last": request.GET.get("to", ""),
        },
    )


def _cell(vehicle: Vehicle, key: str):
    """خليّةٌ من فاتورة المركبة في التصدير — **والفاتورة تُقرأ مرّةً للصفّ**.

    أربعةُ أعمدةٍ ماليّةٍ تسأل `money_of` أربعَ مرّاتٍ تعني أربعةَ استعلاماتٍ
    لكلّ صفٍّ في ملفٍّ يبلغ خمسةَ آلاف صفّ. فالجوابُ يُحفظ على الصفّ نفسِه —
    وهو كائنٌ يُبنى مرّةً في حلقة `export_table` ثم يُرمى، فلا ذاكرةَ تتراكم.
    """
    split = getattr(vehicle, "_money", None)
    if split is None:
        split = vehicle._money = money_of(vehicle)
    if split["invoice"] is None:
        return ""
    return split["invoice"].number if key == "number" else split[key]


def summary(*, text: str = "", first: str = "", last: str = "") -> dict:
    """أرقام الملخّص — من `awarded()` نفسها التي تبني القائمة.

    و«قبل الضريبة» هنا هو **مجموع أسعار الترسية**، و«بعد الضريبة» مجموعُ
    إجماليّات الفواتير الصادرة عليها. والاثنان لا يتساويان بالضرورة ولا يُراد
    لهما ذلك: الفرق هو ما رسا ولم يُفوتَر بعد، وهو رقمٌ يُقرأ — لا فجوةٌ
    تُخبَّأ بضربِ الأول في النسبة.
    """
    rows = awarded(text=text, first=first, last=last)

    awarded_total = rows.aggregate(t=Sum("awarded_price"))["t"] or ZERO

    invoiced = Invoice.objects.filter(vehicle__in=rows)
    invoiced_total = ZERO
    invoiced_tax = ZERO
    for invoice in invoiced.iterator():
        split = money.tax_of(invoice)
        invoiced_total += split.total
        invoiced_tax += split.tax

    count = rows.count()
    return {
        "count": count,
        "awarded_total": awarded_total,
        "invoiced_count": invoiced.count(),
        "invoiced_total": invoiced_total,
        "invoiced_tax": invoiced_tax,
        "uninvoiced_count": count - invoiced.count(),
    }


@console_page("console:accepted-summary")
def accepted_summary(request):
    """ملخّص المقبولة: ثلاثةُ أرقامٍ، وكلٌّ منها بابٌ إلى صفوفه."""
    text = request.GET.get("q", "")
    first = request.GET.get("from", "")
    last = request.GET.get("to", "")

    # ثلاثةُ أرقامٍ من الستّة مبالغُ مجموعة، **ومبلغٌ مجموعٌ على آلاف الصفوف
    # ليس أقلَّ حساسيّةً من مبلغِ فاتورةٍ واحدة بل أكثر** — الحجّةُ نفسُها
    # التي حجبت بطاقات أرشيف المزادات. والأعدادُ الثلاثةُ تبقى: «كم مركبةً
    # رست وكم منها فُوتِرت» سؤالُ تشغيلٍ يجيبه عدّ، وهو سببُ فتح الشاشة.
    seen = shown_to(request.user)

    return render(
        request,
        "console/accepted_summary.html",
        {
            "totals": summary(text=text, first=first, last=last),
            "show_money": seen.money,
            "q": text,
            "first": first,
            "last": last,
        },
    )
