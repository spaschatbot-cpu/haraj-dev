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

import re
import unicodedata
from urllib.parse import urlencode

from django.db.models import Count, Q
from django.urls import reverse

from apps.auctions import engine
from apps.auctions.models import VehicleColour
from apps.auctions.states import VehicleState

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


def normalize(text) -> str:
    """طيُّ النصّ قبل المطابقة — دالةٌ واحدة للمُدخَل ولقيمة العمود معاً.

    كما في v1 (`initColumnFilters`): الأرقامُ العربية-الهندية ٠-٩ والفارسية
    ۰-۹ إلى ASCII — فلوحةُ المفاتيح العربية تُخرج «٣١٠» حيث الخليّة «310».
    وفوق v1: أ إ آ←ا · ى←ي · ة←ه، وحذفُ التشكيل والتطويل — فـ«الماركه» تجد
    «الماركة». ثم lower وحذفُ المسافات و- _ . /.
    """
    chars = str(text or "")
    chars = chars.translate(_ARABIC_DIGITS).translate(_PERSIAN_DIGITS)
    chars = re.sub("[أإآ]", "ا", chars)
    chars = chars.replace("ى", "ي").replace("ة", "ه")
    chars = chars.replace("ـ", "")
    chars = re.sub("[ً-ْ]", "", chars)
    chars = unicodedata.normalize("NFKC", chars)
    return re.sub(r"[\s\-_./]", "", chars.lower())


_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


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

    # بحثٌ موحّد لشاشة الكروت (أسلوب v1: لوحة/شاصي/اسم في خانةٍ واحدة). مطابقةٌ
    # مباشرة `icontains` كبحث v1 نفسِه — للّوحة والشاصي والرقم تكفي، والاسمُ
    # يُطابَق كما كُتب. ورقمٌ صِرفٌ يُقارَن باللوت أيضاً.
    q = _get(params, "q").strip()
    if q:
        from django.db.models import Q as _Q

        match = (
            _Q(make__icontains=q)
            | _Q(model__icontains=q)
            | _Q(plate_number__icontains=q)
            | _Q(vin__icontains=q)
        )
        if q.isdigit():
            match |= _Q(lot_number=int(q))
        rows = rows.filter(match)

    return _apply_text(rows, params)


def _apply_text(rows, params):
    """بحثُ الأعمدة الثمانية — مطابقةٌ عربية كاملة، لا `icontains` أعمى.

    العمودُ مخزَّنٌ خاماً («الماركة») والمُدخَلُ قد يُكتب بصورةٍ أخرى
    («الماركه»)، ولا توجد دالةُ SQL واحدة تطبّق `normalize` على الطرفين —
    فـ`icontains` على المُدخَل المطبَّع وحده **لا يجدها أبداً**: «الماركه» ليست
    جزءاً من «الماركة».

    فالمرشَّحاتُ هنا تُقرأ من القاعدة على مستوى المزاد كلّه (مئاتُ الصفوف لا
    الصفحة)، وتُطابَق في بايثون بالدالة الواحدة على الطرفين، ثم تعود
    `pk__in` — فتبقى QuerySet قبل الترقيم، وتبقى العدّادات على القاعدة.
    واللونُ مخزَّنٌ رمزاً (`white`) فيُطابَق على تسميته العربية لا على الرمز.
    """
    wanted: dict[str, str] = {}
    for key, _label in SEARCH_FIELDS:
        query = normalize(_get(params, key))
        if query:
            wanted[key] = query
    if not wanted:
        return rows

    colour_labels = dict(VehicleColour.choices)
    columns = (
        "lot_number",
        "make",
        "model",
        "year",
        "vin",
        "claim_number",
        "plate_number",
        "colour",
        "insurance_company",
    )
    hits: list[int] = []
    for values in rows.values_list("pk", *columns):
        record = dict(zip(("pk", *columns), values, strict=True))
        if _matches(record, wanted, colour_labels):
            hits.append(record["pk"])
    return rows.filter(pk__in=hits)


def _matches(record: dict, wanted: dict[str, str], colour_labels: dict) -> bool:
    """كلُّ حقلٍ مكتوبٍ يجب أن يتحقّق (AND) — كفلاتر v1 تماماً."""
    for key, query in wanted.items():
        if key == "q_lot":
            if query not in normalize(record["lot_number"]):
                return False
        elif key == "q_make":
            if query not in normalize(record["make"]) and query not in normalize(
                record["model"]
            ):
                return False
        elif key == "q_year":
            if query not in normalize(record["year"]):
                return False
        elif key == "q_vin":
            if query not in normalize(record["vin"]):
                return False
        elif key == "q_claim":
            if query not in normalize(record["claim_number"]):
                return False
        elif key == "q_plate":
            if query not in normalize(record["plate_number"]):
                return False
        elif key == "q_colour":
            label = colour_labels.get(record["colour"], "")
            if query not in normalize(label) and query not in str(
                record["colour"] or ""
            ).lower():
                return False
        elif key == "q_insurance":
            if query not in normalize(record["insurance_company"]):
                return False
    return True


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
