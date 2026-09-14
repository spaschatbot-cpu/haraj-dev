"""فلاتر جدول مركبات المزاد — T868.

فوق الجدول في v1 أربعةُ صفوفٍ تعمل معاً: بحثٌ في كل عمود، وتبويباتُ حالةٍ
بعدّاداتها، وتبويباتُ تغطيةِ صور، وتبويباتُ تسويق. وهنا نظيرُها على الخادم.

**والفرق عن v1 يغيّر التنفيذ كلَّه.** v1 يحمّل كلَّ صفوف المزاد بلا LIMIT
ويرقّم في المتصفّح، ففلترُه جافاسكربت على DOM. وهنا الترقيمُ على الخادم —
خمسةٌ وعشرون صفّاً — ففلترٌ على الصفحة المعروضة وحدها يقول «٣ بلا صور»
والحقيقةُ ٤٠. وذلك الرقمُ أسوأ من غيابه: يُقرأ إثباتاً على أن العمل تمّ.
فكلُّ فلترٍ هنا مُعامِلُ استعلامٍ على QuerySet **قبل الترقيم**، والعدّادات
`.count()` على القاعدة لا على الصفحة، وتُحسب على الصفوف قبل الترشيح.

القواعد هنا لا في القالب ولا في الـview (المادة ٤-٤): القالب يرسم ما يُعطى،
والـview يستدعي `apply` ثم `state` ولا يقرّر شيئاً.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django.db.models import Count, Q
from django.urls import reverse

from apps.auctions import engine
from apps.auctions.models import VehicleColour
from apps.auctions.states import VehicleState
from apps.core.arabic import fold, search_q
from apps.core.arabic import matches as _folded_in

#: تبويبة الصور: بلا صور تعني `image_count == 0`، ولها صور ما فوقه. والعددُ من
#: `image_count` المعلَّق أصلاً في `engine.vehicle_rows` — لا يُحسب ثانيةً.
PHOTOS_WITH = "with"
PHOTOS_WITHOUT = "without"

#: تبويبة التسويق على `is_marketing`: «تسويق» للدعاية لا للبيع في هذه الدورة،
#: و«بيع» لما هو معروضٌ للبيع فعلاً.
MKT_ON = "1"
MKT_OFF = "0"

#: حقولُ بحث الأعمدة الثمانية: (مُعامِل الاستعلام، التسمية العربية).
SEARCH_FIELDS: tuple[tuple[str, str], ...] = (
    ("q_lot", "اللوت"),
    ("q_make", "الماركة / الموديل"),
    ("q_year", "السنة"),
    ("q_vin", "الشاصي"),
    ("q_claim", "رقم المطالبة"),
    ("q_plate", "اللوحة"),
    ("q_colour", "اللون"),
    ("q_insurance", "شركة التأمين"),
)


def _get(params, key: str) -> str:
    """قيمةُ مُعامِلٍ واحد كنصّ — يقبل QueryDict والقاموس معاً (للاختبارات)."""
    try:
        value = params.get(key, "")
    except AttributeError:  # pragma: no cover - دفاعٌ عن عقدٍ بسيط
        return ""
    return "" if value is None else str(value)


#: التطبيعُ **لم يعد يعيش هنا** — انتقل إلى `apps.core.arabic` يوم صار لأكثر
#: من شاشة (T897). وكان مكتوباً في `console/bids.py` أنها تطبّع وهي لا تطبّع،
#: لأن الدالّة كانت حبيسةَ هذا الملفّ. وقاعدةٌ واحدةٌ تعيش في موضعين قاعدتان
#: تتفارقان (المادة ٤-٥)، فالاسمُ هنا مجرّدُ اسمٍ قديمٍ للدالّة المشتركة.
normalize = fold


def apply(rows, params):
    """رشِّح صفوف المزاد بما اختاره الموظّف — وأعِد QuerySet لا قائمة.

    `rows` هو `engine.vehicle_rows(auction)` — حاملاً `image_count` — والترشيحُ
    كلُّه قبل الترقيم، فالصفحةُ تُبنى على المُرشَّح لا العكس. والفلاتر الأربعة
    تتراكب (AND): «بلا صور» + «مسودة» + بحثٌ في اللوحة في طلبٍ واحد.
    """
    state = _get(params, "state").strip()
    if state in VehicleState.values:
        rows = rows.filter(state=state)

    photos = _get(params, "photos").strip()
    if photos == PHOTOS_WITH:
        rows = rows.filter(image_count__gt=0)
    elif photos == PHOTOS_WITHOUT:
        rows = rows.filter(image_count=0)

    marketing = _get(params, "marketing").strip()
    if marketing == MKT_ON:
        rows = rows.filter(is_marketing=True)
    elif marketing == MKT_OFF:
        rows = rows.filter(is_marketing=False)

    # بحثٌ موحّد لشاشة الكروت (أسلوب v1: لوحة/شاصي/اسم في خانةٍ واحدة) — ويطبّع
    # العربية كبقيّة اللوحة (T897)، لا `icontains` أعمى: لوحاتُ القاعدة
    # المُرحَّلة مكتوبةٌ «د ط ق 1265» بمسافات، ومن ينسخها من ورقةٍ يكتبها ملتصقة.
    q = _get(params, "q").strip()
    if q:
        match = search_q(q, "make", "model", "plate_number", "vin")
        # `q.isdigit()` كانت تقول «نعم» لـ`²` و`⑤` ثم يرفع `int` عليهما
        # `ValueError` — أي **٥٠٠** على الشاشة لا نتيجةً فارغة (قِيس نظيرُه
        # على `?q=²` في الكتالوج والبحث، ١٤ سبتمبر ٢٠٢٦). و`fold` تحسمها:
        # تطوي `٠-٩` و`۰-۹` كما يفعل `foldArabicDigits` في v1، و`NFKC` تردّ
        # `²` إلى `2`. فما بقي رقماً لاتينياً بعدها فهو رقم.
        folded_q = fold(q)
        if folded_q.isascii() and folded_q.isdigit():
            match |= Q(lot_number=int(folded_q))
        rows = rows.filter(match)

    return _apply_text(rows, params)


#: «مُعامِلُ الفلتر ← أعمدتُه» للحقول النصّية. الماركةُ خانةٌ واحدة على
#: عمودين كما في v1 (`vehColFilter` على خليّة «الماركة / الموديل»).
_TEXT_COLUMNS: dict[str, tuple[str, ...]] = {
    "q_make": ("make", "model"),
    "q_vin": ("vin",),
    "q_claim": ("claim_number",),
    "q_plate": ("plate_number",),
    "q_insurance": ("insurance_company",),
}

#: وعمودان عدديّان (`PositiveIntegerField`): لا همزةَ فيهما ولا تشكيل، فطيُّ
#: **المُدخَل** وحده يكفي — «١٢٦٥» تصير «1265» ثم `icontains` على النصّ.
#: ولا يُبنى لهما تعبيرٌ نمطيّ: `~*` لا يقبل عموداً عدديّاً بلا `Cast`، وثمنُ
#: الصبّ بلا فائدةٍ هنا.
_NUMBER_COLUMNS = {"q_lot": "lot_number", "q_year": "year"}


def _apply_text(rows, params):
    """بحثُ الأعمدة الثمانية — مطابقةٌ عربية كاملة **في القاعدة**.

    العمودُ مخزَّنٌ خاماً («الماركة») والمُدخَلُ قد يُكتب بصورةٍ أخرى
    («الماركه»)، و`icontains` على المُدخَل المطبَّع وحده **لا يجده أبداً**.
    فالمُدخَلُ يُطوى ثم يُوسَّع إلى تعبيرٍ نمطيّ يقبل كلَّ صور الحرف في العمود
    (`apps.core.arabic`)، والمطابقةُ تبقى في SQL.

    **وكان هذا يُقرأ صفّاً صفّاً في بايثون** — `values_list` على صفوف المزاد
    كلِّها ثم `pk__in` بقائمةٍ من مئات المعرّفات. صحيحٌ على مزادٍ صغير، وثمنُه
    قراءةُ الجدول كاملاً في كل ضغطة، ورابطُه بالبحث في بقيّة اللوحة مستحيل.
    فصار الترشيحُ `Q` واحدةً تتراكب (AND) كفلاتر v1 تماماً.

    واللونُ وحده يبقى في بايثون: العمودُ يخزّن رمزاً (`white`) والموظّفُ يكتب
    «أبيض»، والتسميةُ في `choices` لا في القاعدة. فتُطوى التسمياتُ هنا ويُرشَّح
    بـ`colour__in` — ومعها الرمزُ نفسُه لمن يكتبه.
    """
    for key, columns in _TEXT_COLUMNS.items():
        clause = search_q(_get(params, key), *columns)
        if clause:
            rows = rows.filter(clause)

    for key, column in _NUMBER_COLUMNS.items():
        folded = fold(_get(params, key))
        if folded:
            rows = rows.filter(**{f"{column}__icontains": folded})

    colour = _get(params, "q_colour").strip()
    if colour:
        codes = [
            value
            for value, label in VehicleColour.choices
            if _folded_in(label, colour) or _folded_in(value, colour)
        ]
        rows = rows.filter(colour__in=codes)

    return rows


def counts(rows):
    """عدّاداتُ التبويبات على الصفوف **قبل الترشيح**.

    تُحسب على القاعدة كلّها لا على الصفحة — وإلا صار كلُّ عدّادٍ صفراً بعد
    أوّل ضغطة. ثلاثُ قراءاتٍ مجمَّعة لا واحدةٌ لكل حالة.
    """
    by_state = {
        row["state"]: row["n"]
        for row in rows.values("state").annotate(n=Count("id")).order_by()
    }
    photos = rows.aggregate(
        with_n=Count("pk", filter=Q(image_count__gt=0)),
        without_n=Count("pk", filter=Q(image_count=0)),
    )
    marketing = rows.aggregate(
        on_n=Count("pk", filter=Q(is_marketing=True)),
        off_n=Count("pk", filter=Q(is_marketing=False)),
    )
    return {
        "state": by_state,
        "photos": {"with": photos["with_n"], "without": photos["without_n"]},
        "marketing": {"on": marketing["on_n"], "off": marketing["off_n"]},
    }


def _tab_url(params, auction, **overrides) -> str:
    """رابطُ تبويبةٍ يحمل الفلاتر الأخرى معها — يُبنى هنا لا في القالب.

    الضغطُ على تبويبةٍ لا يمسح بحثاً مكتوباً، ويسقط `page` عمداً: نتيجةٌ
    تغيّرت قد لا تملك سبعَ صفحات، والبقاءُ على السابعة شاشةٌ فارغة.
    """
    merged: dict[str, str] = {}
    try:
        items = params.items()
    except AttributeError:  # pragma: no cover - دفاعٌ عن عقدٍ بسيط
        items = []
    for key, value in items:
        if key == "page" or value in ("", None):
            continue
        merged[key] = value
    for key, value in overrides.items():
        if value in ("", None):
            merged.pop(key, None)
        else:
            merged[key] = value
    base = reverse("console:auction-detail", args=[auction.pk])
    query = urlencode(merged)
    return f"{base}?{query}" if query else base


def keep(params) -> str:
    """الفلاتر القائمة مسلسلةً، بلا `page` — تُلحَق بأيّ رابطٍ يغادر الصفحة.

    **الترقيمُ والتصديرُ كانا يُسقطانها.** وذلك أسوأ من غياب الفلتر أصلاً:
    من يرشّح إلى «بلا صور» ثم يضغط «التالي» يعود إلى الجدول كلِّه وهو يظنّ
    نفسه داخل نتيجته؛ ومن يضغط «تصدير إكسل» يأخذ ثلاثمئة صفٍّ بينما الشاشة
    أمامه تقول سبعة — ملفٌّ لا يطابق ما رآه، ولا شيء يقول له ذلك.

    و`page` تُسقط: الفلتر يُلحَق بالرابط وينشئ الرابطُ صفحتَه بنفسه.
    """
    try:
        items = params.items()
    except AttributeError:  # pragma: no cover - دفاعٌ عن عقدٍ بسيط
        return ""
    kept = {
        key: value
        for key, value in items
        if key not in ("page", "export") and value not in ("", None)
    }
    return urlencode(kept)


def state(params, auction) -> dict:
    """حالُ الفلاتر للقالب: القيمُ والتبويباتُ بعدّاداتها وروابطُها.

    العدّاداتُ من `counts` على المزاد كلّه قبل أيّ ترشيح — فتبقى بقيّةُ
    الأرقام مقروءةً بعد الضغط على فلتر. وتبويباتُ الحالة هي الموجودُ فعلاً
    في هذا المزاد من `VehicleState` (المرجع)، لا حالات v1 الستّ.
    """
    base = engine.vehicle_rows(auction)
    tallies = counts(base)
    total = sum(tallies["state"].values())

    current_state = _get(params, "state").strip()
    if current_state not in VehicleState.values:
        current_state = ""
    current_photos = _get(params, "photos").strip()
    if current_photos not in (PHOTOS_WITH, PHOTOS_WITHOUT):
        current_photos = ""
    current_marketing = _get(params, "marketing").strip()
    if current_marketing not in (MKT_ON, MKT_OFF):
        current_marketing = ""

    state_tabs = [
        {
            "value": "",
            "label": "الكل",
            "count": total,
            "url": _tab_url(params, auction, state=""),
            "active": not current_state,
        }
    ]
    for value, label in VehicleState.choices:
        if value not in tallies["state"]:
            continue
        state_tabs.append(
            {
                "value": value,
                "label": label,
                "count": tallies["state"][value],
                "url": _tab_url(params, auction, state=value),
                "active": current_state == value,
            }
        )

    photo_tabs = [
        {
            "value": "",
            "label": "الكل",
            "count": total,
            "url": _tab_url(params, auction, photos=""),
            "active": not current_photos,
        },
        {
            "value": PHOTOS_WITHOUT,
            "label": "بلا صور",
            "count": tallies["photos"]["without"],
            "url": _tab_url(params, auction, photos=PHOTOS_WITHOUT),
            "active": current_photos == PHOTOS_WITHOUT,
        },
        {
            "value": PHOTOS_WITH,
            "label": "لها صور",
            "count": tallies["photos"]["with"],
            "url": _tab_url(params, auction, photos=PHOTOS_WITH),
            "active": current_photos == PHOTOS_WITH,
        },
    ]
    mkt_tabs = [
        {
            "value": "",
            "label": "الكل",
            "count": total,
            "url": _tab_url(params, auction, marketing=""),
            "active": not current_marketing,
        },
        {
            "value": MKT_ON,
            "label": "تسويق",
            "count": tallies["marketing"]["on"],
            "url": _tab_url(params, auction, marketing=MKT_ON),
            "active": current_marketing == MKT_ON,
        },
        {
            "value": MKT_OFF,
            "label": "بيع",
            "count": tallies["marketing"]["off"],
            "url": _tab_url(params, auction, marketing=MKT_OFF),
            "active": current_marketing == MKT_OFF,
        },
    ]

    search = [
        {"name": key, "label": label, "value": _get(params, key)}
        for key, label in SEARCH_FIELDS
    ]
    # خريطةُ «عمودُ الجدول ← فلترُه»، ليوضع كلُّ مُدخَلٍ **تحت عموده** في رأس
    # الجدول كما في v1 (`vehColFilter data-col`)، لا في صندوقٍ منفصل فوقه.
    # المفتاحُ هو `data-col` في القالب.
    search_by_col = {
        "lot": search[0],
        "car": search[1],
        "year": search[2],
        "vin": search[3],
        "claim": search[4],
        "plate": search[5],
        "colour": search[6],
        "insurance": search[7],
    }
    has_active = (
        any(item["value"].strip() for item in search)
        or bool(current_state)
        or bool(current_photos)
        or bool(current_marketing)
    )
    # سلسلةُ الفلاتر بلا `q` — لرابط «مسح البحث»: يمسح النصَّ ويُبقي التبويبات.
    from urllib.parse import urlencode as _urlencode

    keep_no_q = _urlencode(
        [
            (k, v)
            for k, v in (params.items() if hasattr(params, "items") else [])
            if k not in ("page", "q") and str(v).strip()
        ]
    )

    return {
        "search": search,
        "search_by_col": search_by_col,
        "q": _get(params, "q"),
        "keep_no_q": keep_no_q,
        "state": current_state,
        "photos": current_photos,
        "marketing": current_marketing,
        "state_tabs": state_tabs,
        "photo_tabs": photo_tabs,
        "mkt_tabs": mkt_tabs,
        "has_active": has_active,
        "clear_url": _tab_url({}, auction),
        # يقرؤه الترقيمُ وزرُّ التصدير — لا يبنيان الرابط بأنفسهما.
        "keep": keep(params),
    }
