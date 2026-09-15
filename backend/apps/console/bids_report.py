"""تقرير المزايدات — **المزايدون مجمَّعين، لا المزايدات مصفوفة**. T832.

السؤال الذي تُفتح لأجله، ولا تجيبه واحدةٌ من الأربع
====================================================
في اللوحة أربعُ شاشاتٍ تعرض مزايدات، وكلُّها تجيب سؤالاً آخر:

* «تحليل المزايدات» (`analytics-bids`) — قسمةُ الحالات على المنصّة كلِّها،
  ومعها **عشرةُ** مزايدين ثابتون بلا ترشيحٍ ولا صفحاتٍ ولا تصدير. تجيب «كم».
* «مزايدات السيارات» و«مزايدات المزاد الجاري» (`bids.py`) — صفٌّ لكلّ
  **مزايدة**: ١٦٣ ألف صفّ. تجيب «ماذا حدث على هذه السيارة».
* «المزايدات المقبولة» و«ملخّص المقبولة» (`decisions.py`) — ما **رسا** وحدَه.
* «تقرير مزايدات مستخدم» (`analytics.user_bids`) — تقريرٌ عميقٌ لشخصٍ **تعرف
  اسمه أو جوّاله**، ولا تفتح قبل أن تُسأل عن أحد.

فالناقص هو «**مَن**»: لا تقريرٌ عن واحدٍ تعرفه، بل ترتيبُ الألفٍ وثمانمئةٍ
كلِّهم في جدولٍ يُقارَن — من زايد كثيراً، على كم مركبةً، في كم مزاداً، وكم رسا
له فعلاً. وهو السؤال الذي يُسأل **قبل منح حدّ ائتمان** وعند نزاع: «هذا العميل،
كم حجمُه عندنا؟» — ولا يُجاب اليوم إلا بفتح `user_bids` مرّةً لكلّ عميل.

ماذا يفعل v1، وما الذي لم يُنقَل منه
=====================================
شاشتا v1 (`admin3/user_bids_report.php` و`AnalyticsController::bidsReport`)
تفعلان هذا بالضبط في خطوتين: `loadBidUsers` تجمع `COUNT(b.id)` و`SUM(b.amount)`
على `GROUP BY u.id`، ثم يُنقَر صفٌّ فيُفتح تقريرُ الشخص. **والخطوة الثانية
مبنيّةٌ عندنا** (`user_bids`, T863)، والأولى هي هذه.

ولم يُنقَل منها ثلاثة، ولكلٍّ سببُه:

* **`ORDER BY u.arabic_name`** — ترتيبٌ أبجديٌّ يجيب «أين فلان» لا «من الأكبر».
  وهو هنا بلا معنىً أصلاً: **٤٤٬٠٣٥ من ٤٤٬٠٣٩ عميلاً اسمُهم فارغٌ في القاعدة
  المُرحَّلة** (قِيس على `haraj2_t307`)، فترتيبٌ بالاسم ترتيبٌ عشوائيّ. والترتيب
  هنا بالعدد، ويُختار.
* **بلا ترقيم صفحاتٍ ولا سقفِ تصدير** — v1 يُخرج كلَّ من زايد في صفحةٍ واحدة.
* **مبالغُ لكلّ من يفتح الشاشة** — الحجبُ هنا في `sensitive.py`.

الأداء: **التجميعُ بلا وصلة، والتفاصيلُ لصفحةٍ واحدة**
=======================================================
قِيس على `haraj2_t307` (١٦٣٬٢٨٩ مزايدة · ١٬٨٠٥ مزايدين) في ١٤ سبتمبر ٢٠٢٦:

    الشكل                                      صفحةُ ٥٠      العدّ
    ─────────────────────────────────────────────────────────────
    GROUP BY مع وصلتَي المستخدم والمركبة         ٩٣٢ms      ١٧٦ms
    مع وصلة المستخدم وحدها                       ٧٦٧ms      ١١٨ms
    **بلا وصلةٍ — على `bidder_id` وحده**         **٢٠٥ms**   **٣٤ms**

أي أن الاسمَ والجوّالَ وعدَّ المزادات — ثلاثةُ حقولٍ تحتاج وصلة — كانت تكلّف
**أربعةَ أخماس زمن الصفحة**. فالتجميعُ هنا على العمود المفهرس وحده، وما يحتاج
وصلةً يُسأل **بعد الترقيم لخمسين صفّاً**: المستخدمون ٢ms، والترسيات ١٧ms،
وعدُّ المزادات ١٠٠ms. الجملةُ **أربعةُ استعلاماتٍ ثابتة**، ولا استعلامَ في حلقة.

**ولا وصلةَ إلى `awarded_to` في التجميع أبداً** — وهذا هو الدرسُ الغالي: وصلةٌ
من `Bid` إلى مركبات الفائز تضرب كلَّ مزايدةٍ في كلّ مركبةٍ رست له، فوق تجميعٍ
قائم. وضربٌ ديكارتيٌّ من هذا الشكل عَلِق في هذه اللوحة **عشرَ دقائقَ وإحدى
وأربعين ثانية** وأسقط عمليّةَ الخادم على كلّ من كان يعمل عليها. فالترسياتُ
استعلامٌ ثانٍ بمفاتيحِ الصفحة، لا `annotate` فوق `annotate`.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, Vehicle
from apps.bidding.models import Bid
from apps.core.arabic import search_q

from .exports import export_table, oversize, refuse, wants_export
from .sensitive import (
    AWARDED_STATES,
    CUSTOMER,
    MONEY,
    Shown,
    aggregate_money,
    columns_for,
    scrub,
    shown_to,
)
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50

#: مفاتيحُ الترتيب المسموحة → عمودُ الترتيب. قاموسٌ لا `request.GET` مباشرةً:
#: تمريرُ نصٍّ من الطلب إلى `order_by` يفتح أعمدةً لم يُقصَد فتحُها
#: (`bidder__password` تُرتَّب ولا تُعرض، والترتيبُ وحدَه يُفشي).
SORTS = {
    "bids": "-bids",
    "vehicles": "-vehicles",
    "value": "-value",
    "highest": "-highest",
    "last": "-last",
    "withdrawn": "-withdrawn",
}

#: مفاتيحُ الترتيب التي **هي ترتيبٌ بالمال**. من لا يرى المبالغ لا يرتّب بها:
#: جدولٌ مرتَّبٌ تنازلياً بإجمالي القيمة يقول «هذا أكبرُ من ذاك» بلا رقمٍ واحد
#: في الصفحة — وهو نصفُ الجواب يُسرَّب بالترتيب بعد أن حُجبت الأرقام.
MONEY_SORTS = ("value", "highest")

#: ما يُحذف من صفّ التقرير حين لا يحقّ لقارئه رؤيتُه — يقرؤه :func:`scrub`.
MONEY_KEYS = ("value", "highest", "won_value")
CUSTOMER_KEYS = ("name", "phone")


def _filtered(*, search: str = "", auction: str = "", first: str = "", last: str = ""):
    """المزايداتُ التي يشملها التقرير — **مصدرُ المرشّحات الوحيد**.

    مفصولةٌ عن التجميع ليقرأها الجدولُ والأرقامُ فوقه معاً. ورقمٌ في ترويسةٍ
    لا يتبع مرشّحَ جدوله هو بعينه كيف صار مركزُ تقارير v1 يقول «المزايدات
    المقبولة ٦٬٥٠٣» وتقول شاشتُها `4,378` — ثلاثةُ أرقامٍ لشيءٍ واحد، ولا
    واحدةٌ تقول أيَّ مرشّحٍ تطبّق.

    والمرشّحاتُ كلُّها تُحَلّ على الجداول الصغيرة ثمّ تُربَط بالمفتاح المفهرس،
    كما في `bids._searched` وللسبب نفسه: شرطٌ على عمودٍ خلف وصلةٍ يُقيَّم
    ١٦٣ ألف مرّة، وشرطٌ على الجدول الصغير يُقيَّم مرّةً لكلّ صفٍّ فيه ثم يمرّ
    الباقي بالمفتاح.
    """
    rows = Bid.objects.all()

    # **رقمُ المزاد معرّفٌ آليّ، فلا يمرّ بالتطبيع العربيّ.** `search_q` تطوي
    # الهمزةَ والتاءَ المربوطة وتقبل مسافةً بين كلّ حرفين — وهو ما يُراد لاسمٍ
    # يُكتب بإملاءين، ونقيضُ ما يُراد لرقمٍ يُقصَد به الدقّة: «٣٨» تصير تعبيراً
    # يطابق «3 8» و«٣-٨». فالمقارنةُ هنا مساواةٌ على `int` بعد `isdigit`.
    if auction.isdigit():
        picked = Vehicle.objects.filter(auction__number=int(auction))
        rows = rows.filter(vehicle__in=picked)

    # المدى **بأرقام المزادات لا بالتواريخ** — وهو ما تفعله «تحليل المزايدات»
    # المجاورة، فيُقارَن التقريران. ولا مرشّحَ تاريخٍ عمداً: `Bid.placed_at`
    # هو `auto_now_add`، و**٤٣٬٣٦٢ من ١٦٣٬٢٨٩ مزايدةً في `haraj2_t307` تحمل
    # لحظةَ الاستيراد نفسَها** (٢٠٢٦-٠٩-١٣) — فمرشّحُ تاريخٍ يقسم البياناتِ
    # على «متى استُوردت» ويُقرأ «متى زايد». والمزادُ رقمُه يتقدّم مع الزمن.
    if first.isdigit():
        rows = rows.filter(vehicle__auction__number__gte=int(first))
    if last.isdigit():
        rows = rows.filter(vehicle__auction__number__lte=int(last))

    text = (search or "").strip()
    if text:
        people = User.objects.filter(search_q(text, "full_name", "phone")).values("pk")
        rows = rows.filter(bidder__in=people)

    return rows


def _bidders(**filters):
    """صفوفُ التقرير: مزايدٌ واحدٌ في كلّ صفّ — **تجميعٌ بلا وصلة**.

    `values("bidder_id")` وحدَه: ضمُّ الاسم أو الجوّال أو المزاد إليه يجرّ
    وصلةً داخل `GROUP BY` ويرفع صفحةَ الخمسين من ٢٠٥ms إلى ٧٦٧ms ثم ٩٣٢ms.
    انظر رأسَ الملفّ.
    """
    return _filtered(**filters).values("bidder_id").annotate(
        bids=Count("id"),
        vehicles=Count("vehicle_id", distinct=True),
        # القسمةُ الثلاثيّة نفسُها التي في «تحليل المزايدات»، بالترتيب نفسه:
        # المسحوبةُ أوّلاً، فالمستبدَلةُ **من غير المسحوب**، فالباقي. وبلا هذا
        # الترتيب تُعدّ المسحوبةُ المستبدَلةُ مرّتين فيزيد مجموعُ الثلاثة عن
        # `bids` — وهو بعينه فائضُ v1 الذي بُنيت تلك الشاشة لأجل ألّا يتكرّر.
        withdrawn=Count("id", filter=Q(is_withdrawn=True)),
        superseded=Count("id", filter=Q(is_withdrawn=False, is_superseded=True)),
        standing=Count("id", filter=Q(is_withdrawn=False, is_superseded=False)),
        value=Sum("amount"),
        highest=Max("amount"),
        last=Max("placed_at"),
    )


def _people_of(ids) -> dict[int, User]:
    """اسمُ كلّ مزايدٍ في الصفحة وجوّالُه — استعلامٌ واحدٌ لخمسين، لا خمسون.

    خارجَ التجميع عمداً: ضمُّ `bidder__full_name` إلى `values()` يجرّ وصلةً إلى
    `accounts_user` داخل `GROUP BY`، وقياسُها ٢٠٥ms ← ٧٦٧ms على صفحةٍ واحدة.
    وهي هنا ٢ms لأن المفاتيح خمسون وهي المفتاحُ الأساسيّ.
    """
    return {row.pk: row for row in User.objects.filter(pk__in=ids)}


def _wins_of(ids) -> dict[int, dict]:
    """ما رسا لكلّ مزايدٍ في الصفحة: عدداً وقيمة — **استعلامٌ ثانٍ لا وصلة**.

    التعريفُ هو `decisions.awarded` نفسُه (`AWARDED_STATES` ومالكٌ غيرُ فارغ)،
    مقروءاً من `sensitive` حيث يعيش الحكمُ مرّةً واحدة — تعريفان لكلمة «رست»
    في لوحةٍ واحدة يجعلان شاشتين تعدّان شيئين.

    ولماذا ليست `annotate` على التجميع فوق: انظر رأسَ الملفّ. الوصلةُ من
    المزايدات إلى مركبات الفائز ضربٌ ديكارتيٌّ فوق تجميعٍ قائم، وهو الشكلُ
    الذي علِق عشرَ دقائقَ وأسقط الخادم.
    """
    rows = (
        Vehicle.objects.filter(state__in=AWARDED_STATES, awarded_to_id__in=ids)
        .values("awarded_to_id")
        .annotate(won=Count("id"), won_value=Sum("awarded_price"))
    )
    return {row["awarded_to_id"]: row for row in rows}


def _auctions_of(ids) -> dict[int, int]:
    """كم **مزاداً مختلفاً** دخل كلُّ مزايدٍ في الصفحة.

    رقمٌ يفرّق ما لا يفرّقه عددُ المزايدات: أربعون مزايدةً في مزادٍ واحد عميلُ
    مزادٍ واحد، وأربعون في عشرين مزاداً عميلٌ دائم — والحدُّ الائتمانيُّ يُقرّر
    على الثاني لا الأوّل. (والحجّةُ نفسُها في `analytics.report_for`، T863.)

    وهو الحقلُ الوحيد الذي يحتاج وصلةً إلى `auctions_vehicle`، فأُخرِج من
    التجميع إلى هنا: ٢٠٥ms ← ٧٦٧ms داخله، و١٠٠ms خارجه لخمسين مفتاحاً.
    """
    rows = (
        Bid.objects.filter(bidder_id__in=ids)
        .values("bidder_id")
        .annotate(count=Count("vehicle__auction_id", distinct=True))
    )
    return {row["bidder_id"]: row["count"] for row in rows}


def _shown(rows, seen: Shown) -> list[dict]:
    """صفوفُ الصفحة كاملةً — منقوصةً ما لا يحقُّ لقارئها رؤيتُه.

    والمفاتيحُ المحجوبة **تُحذف** لا تُصفَّر (:func:`~.sensitive.scrub`): مفتاحٌ
    يبقى ويُخفى في القالب يبقى في **مصدر الصفحة**.

    والاسمُ الفارغ يبقى فارغاً لمن يملك الصلاحية
    ============================================
    `name` يخرج `""` لعميلٍ اسمُه فارغٌ في القاعدة، ويقرؤه القالبُ «—». وكتابةُ
    «محجوب» مكانَه لمن يملك `users.view` عطلٌ وقع في جولةٍ سابقةٍ وأُصلح —
    و**٤٤٬٠٣٥ من ٤٤٬٠٣٩ عميلاً في القاعدة المُرحَّلة اسمُهم فارغ**، فالعطلُ
    كان سيصيب كلَّ صفٍّ في الشاشة لا صفّاً نادراً.
    """
    ids = [row["bidder_id"] for row in rows]
    people = _people_of(ids)
    wins = _wins_of(ids)
    spread = _auctions_of(ids)

    out = []
    for row in rows:
        who = people.get(row["bidder_id"])
        win = wins.get(row["bidder_id"], {})
        out.append(
            scrub(
                {
                    **row,
                    "name": who.full_name if who else "",
                    "phone": who.phone if who else "",
                    "auctions": spread.get(row["bidder_id"], 0),
                    "won": win.get("won", 0),
                    "won_value": win.get("won_value") or ZERO,
                },
                seen,
                money=MONEY_KEYS,
                customer=CUSTOMER_KEYS,
            )
        )
    return out


def _moment(value):
    """لحظةٌ بتوقيت العرض وبالدقيقة — أو فراغ. تقرؤها خليّةُ الملفّ وحدها.

    `console_page` يفعّل منطقة الرياض للطلب، فالقالبُ يرسم الوقتَ محوَّلاً
    تلقائياً. والملفُّ لا يمرّ بقالب: `str(datetime)` يكتب UTC بميكروثانية.
    """
    return timezone.localtime(value).strftime("%Y-%m-%d %H:%M") if value else ""


def _export_columns(seen: Shown):
    """أعمدةُ الملفّ = أعمدةُ الشاشة، عموداً بعمود — **والملفُّ يرث حارسَها**.

    عمودٌ يخرج في ملفٍّ ولا يظهر على شاشةٍ هو بابُ التسريب الذي بُني
    `sensitive.py` لإغلاقه: من يفتح الشاشة يضغط «تصدير» فيأخذ في ملفٍّ واحدٍ
    ما حُجب عنه في الصفحة.

    **وهنا العمودُ يسقط كلُّه** لا خليّةً خليّة، خلافاً لملفّ المزايدات
    (`bids._export_columns`) الذي يحجب «المبلغ» صفّاً صفّاً. والفرقُ أن الصفَّ
    هناك مزايدةٌ على **مركبةٍ بعينها** يُسأل عن حالتها، والصفَّ هنا مجموعٌ فوق
    مركباتٍ من الحالتين — فلا شرطَ صفٍّ يفصل. انظر
    :func:`~.sensitive.aggregate_money`.
    """
    return columns_for(
        [
            ("المزايد", lambda row: row["name"], CUSTOMER),
            ("الجوال", lambda row: row["phone"], CUSTOMER),
            ("عدد المزايدات", lambda row: row["bids"], None),
            ("مركبات", lambda row: row["vehicles"], None),
            ("مزادات", lambda row: row["auctions"], None),
            ("قائمة", lambda row: row["standing"], None),
            ("مستبدَلة", lambda row: row["superseded"], None),
            ("مسحوبة", lambda row: row["withdrawn"], None),
            ("رسا له", lambda row: row["won"], None),
            ("إجمالي المزايدات", lambda row: row["value"], MONEY),
            ("أعلى مزايدة", lambda row: row["highest"], MONEY),
            ("قيمة ما رسا له", lambda row: row["won_value"], MONEY),
            # **بتوقيت الرياض وبالدقيقة، كما على الشاشة.** القيمةُ الخام
            # `datetime` بـUTC وبميكروثانية، فـ`str()` عليها يكتب في الملفّ
            # `2026-09-13 14:39:22.672359+00:00` بينما الصفُّ نفسُه على الشاشة
            # يقول `17:39` — ثلاثُ ساعاتٍ فرقاً بين ملفٍّ وشاشةٍ يقرؤهما
            # الموظّفُ نفسُه، وهو عطلُ T846 بعينه عائداً من باب التصدير.
            ("آخر مزايدة", lambda row: _moment(row["last"]), None),
        ],
        seen,
    )


@console_page("console:bids-report")
def bids_report(request):
    """تقرير المزايدات: صفٌّ لكلّ مزايد، مرتّبين — ومن رسا له كم."""
    search = request.GET.get("q", "")
    auction = (request.GET.get("auction") or "").strip()
    first = (request.GET.get("from") or "").strip()
    last = (request.GET.get("to") or "").strip()
    sort = request.GET.get("sort", "bids")
    filters = {"search": search, "auction": auction, "first": first, "last": last}

    seen = shown_to(request.user)

    # الترتيبُ بالمال يسقط إلى الافتراضيّ لمن لا يرى المال — لا يُرفَض الطلبُ
    # ولا تُعرض صفحةُ خطأ: من يكتب `?sort=value` في شريط العنوان لم يفعل شيئاً
    # ممنوعاً، إنّما طلب ترتيباً لا معنى له في صفحته. والشاشةُ تقول أيَّ ترتيبٍ
    # تعرضه فعلاً (`sort` يعود إلى القالب) فلا يُقرأ جدولٌ على أنه مرتَّبٌ بغير
    # ترتيبه.
    if sort in MONEY_SORTS and not seen.money:
        sort = "bids"
    order = SORTS.get(sort, SORTS["bids"])

    rows = _bidders(**filters).order_by(order, "bidder_id")

    if wants_export(request):
        count = oversize(rows)
        if count:
            return refuse(request, count)
        # `_shown` على كلّ الصفوف لا على صفحةٍ منها — والاستعلاماتُ تبقى أربعة:
        # `IN` بألفٍ وثمانمئة مفتاحٍ استعلامٌ واحد كما هو بخمسين.
        return export_table(
            _shown(list(rows), seen),
            name="تقرير-المزايدات",
            columns=_export_columns(seen),
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    # الأرقامُ فوق الجدول من `_filtered` نفسِها — لا من `Bid.objects.count()`
    # ولا بجمع أعمدة الصفحة: الأولى تتجاهل المرشّح، والثانية تعدّ خمسين صفّاً
    # وتكتب الرقم كأنّه الكلّ. واستعلامُ تجميعٍ واحدٌ رخيص (قِيس: ٣٤ms).
    totals = _filtered(**filters).aggregate(bids=Count("id"), value=Sum("amount"))

    keep = "".join(
        f"{key}={value}&"
        for key, value in (
            ("q", search),
            ("auction", auction),
            ("from", first),
            ("to", last),
            ("sort", sort),
        )
        if value
    )

    return render(
        request,
        "console/bids_report.html",
        {
            "rows": _shown(page.object_list, seen),
            "page": page,
            "q": search,
            "auction": auction,
            "first": first,
            "last": last,
            "sort": sort,
            "keep": keep,
            # بفواصلِ آلافٍ **هنا لا في القالب**، كما تفعل بطاقاتُ اللوحة
            # و`exports.refuse`: «4097273263.00» تُقرأ بعدّ الأرقام على الشاشة،
            # و«4,097,273,263.00» تُقرأ لمحةً. وخلايا الجدول تبقى بلا فواصل —
            # هي أعمدةٌ تُقارَن رأسيّاً وتُنسَخ إلى ورقةِ حساب.
            "bidders": f"{page.paginator.count:,}",
            "bids": f"{totals['bids'] or 0:,}",
            # مجموعُ مزايداتِ الجميع مبلغٌ مجمَّع — يظهر كلُّه أو يُحجَب كلُّه.
            "value": aggregate_money(f"{totals['value'] or ZERO:,}", seen),
            "show_money": seen.money,
            "show_customer": seen.customer,
            "auctions": Auction.objects.order_by("-starts_at").values(
                "number", "title"
            )[:200],
        },
    )
