"""ترقيمُ الصفحات — أرقامٌ تُنقر، ومقاسٌ يُختار. T930.

## العطل، بعدده

كلُّ شاشةٍ في اللوحة تطبع في ذيلها ``صفحة ١ من ١١٧`` **نصّاً لا يُنقر**. أي
أن الصفحة الثانية لا يصل إليها أحدٌ إلا بأن يكتب ``?page=2`` في شريط العنوان
بيده. وفي القاعدة اليوم ٥٬٨٣١ مركبةً مرساة و٤٤٬٠٣٤ عميلاً و١١٩٬٩٢١ مزايدة —
أي أن ٩٩٪ من الصفوف خلف رابطٍ لا وجود له.

## والنافذةُ لا القائمةُ كاملة

مئةٌ وسبعةَ عشرَ رقماً في سطرٍ واحدٍ لا تُقرأ ولا تُنقر. فالمعروضُ نافذةٌ حول
الصفحة الحالية ومعها الطرفان — ``١ … ٥ ٦ [٧] ٨ ٩ … ١١٧`` — وهو ما يحتاجه
من يتصفّح فعلاً: خطوةٌ إلى الجوار، وقفزةٌ إلى البداية أو النهاية.

## والمقاسُ من قائمةٍ مغلقة

``per_page`` يأتي من الرابط، أي من يدِ من يكتبه. و``?per_page=999999`` على
٤٤ ألف عميلٍ يعني صفحةً تبني أربعةً وأربعين ألفَ صفٍّ في الذاكرة ثم ترسلها —
فالمقبولُ خمسةُ أرقامٍ مكتوبة، وما عداها يسقط إلى الافتراضيّ صامتاً.

**والخمسمئةُ أعلاها بطلب المالك.** وهي ثقيلةٌ بقصد: من اختارها يريد أن يقرأ
دفعةً واحدة أو يصدّر، ويعرف أنه اختارها.
"""

from __future__ import annotations

from django.core.paginator import Page, Paginator

#: ما يُقبل في `per_page`. والقائمةُ مغلقةٌ — انظر رأس الملفّ.
ROW_CHOICES = (10, 20, 50, 100, 500)

#: الافتراضيّ حين لا يُطلب شيءٌ أو يُطلب ما ليس في القائمة.
DEFAULT_ROWS = 50

#: كم رقماً يُعرض على كلّ جانبٍ من الصفحة الحالية.
SPAN = 2


def page_size(raw: str | None) -> int:
    """مقاسُ الصفحة المطلوب، أو الافتراضيُّ لكل ما ليس في القائمة."""
    raw = (raw or "").strip()
    if raw.isdigit() and int(raw) in ROW_CHOICES:
        return int(raw)
    return DEFAULT_ROWS


def paged(request, rows, size: int | None = None) -> Page:
    """صفحةٌ من `rows` بمقاسٍ يقرؤه الرابط."""
    return Paginator(rows, size or page_size(request.GET.get("per_page"))).get_page(
        request.GET.get("page")
    )


def window(page: Page, span: int = SPAN) -> list[int | None]:
    """أرقامُ الصفحات المعروضة، و`None` مكان الفجوة.

    والطرفان دائماً: من هو في الصفحة السبعين يريد «الأولى» بنقرةٍ لا بسبعين.
    """
    last = page.paginator.num_pages
    here = page.number
    near = {1, last} | set(range(max(1, here - span), min(last, here + span) + 1))

    out: list[int | None] = []
    previous = 0
    for number in sorted(near):
        if previous and number > previous + 1:
            out.append(None)
        out.append(number)
        previous = number
    return out


def query_without(request, *drop: str) -> str:
    """مرشّحاتُ الرابط كما هي، بلا المفاتيح المذكورة — لبناء روابط الترقيم.

    والمرشّحاتُ تُحمل معها وإلّا كانت «الصفحة ٢» صفحةً ثانيةً من **نتيجةٍ
    أخرى**: من رشّح بمزادٍ ثم نقر ٢ يجد الجدولَ كلَّه.
    """
    kept = request.GET.copy()
    for key in ("page", *drop):
        kept.pop(key, None)
    encoded = kept.urlencode()
    return f"{encoded}&" if encoded else ""


def pager(request, page: Page, noun: str = "صفّاً") -> dict:
    """ما يحتاجه `console/_pager.html` — يُوضع في سياق الشاشة باسم `pager`."""
    return {
        "page": page,
        "noun": noun,
        "numbers": window(page),
        "size": page_size(request.GET.get("per_page")),
        "choices": ROW_CHOICES,
        # رابطان: أحدُهما يُبقي المقاسَ ويغيّر الصفحة، والآخرُ يغيّر المقاس
        # **ويعود إلى الأولى** — مقاسٌ جديدٌ يجعل «الصفحة ٩٠» صفحةً لا وجود
        # لها، و`get_page` يسقط إلى الأخيرة فيقرأ الموظّفُ ذيلَ الجدول بلا
        # أن يطلبه.
        "keep": query_without(request),
        "resize": query_without(request, "per_page"),
    }
