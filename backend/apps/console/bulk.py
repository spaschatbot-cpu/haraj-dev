"""عمليات مجمعة — والرقم الذي بُنيت الشاشة لتمنعه. T830م.

شاشة v1 المقابلة تعرض أربعة أرقام، واثنان منها لا يجتمعان:

    مزادات نشطة        0
    مزايدات نشطة  81,475

**والمزايدة النشطة مزايدةٌ على مزادٍ نشط.** فإمّا أن حالة المزايدة لا تُغلق
حين يُغلق مزادُها، أو أن «نشط» في الجدولين تعني شيئين. والأول هو الأرجح —
لأن الزرَّ الثاني في تلك الشاشة موجودٌ أصلاً:

    «إيقاف جميع المزايدات النشطة — سيتم تحويل حالة كل المزايدات (81,475)
     من active إلى not_active. ⚠ عملية لا يمكن التراجع عنها بسهولة.»

أي أن **الفعل الجماعي وُجد ليُصلح يدوياً ما كان يجب أن يُغلق تلقائياً**. وهو
ليس أداةً — هو عرَض.

ما تفعله هذه الشاشة بدلاً منه
=============================
**١. لا زرَّ «أوقف كل المزايدات».** إنهاءُ المزاد في v2 نقلةٌ في
`auctions.services.end`، وهي تُغلق مزايداته في المعاملة نفسها. وزرٌّ يغلق
المزايدات وحدها يعني أن هناك حالتين للشيء الواحد.

**٢. وعدّادٌ يقول إن ذلك لا يقع.** «مزايدات قائمة على مزادات منتهية» رقمٌ
**يجب أن يكون صفراً دائماً**، وهو معروضٌ في الرأس. وغيرُ الصفر هنا ليس عملاً
جماعياً يُطلَق — هو عطلٌ يُفتَح له تاسك.

**٣. والإنهاء الجماعي يمرّ بالخدمة، مزاداً مزاداً، بسببٍ واحدٍ مكتوب.**
`move_auction` هي الوحيدة التي تكتب حالة مزاد (`ops/checks/
auction_state_single_writer.py`)، وهي التي ترفض النقلة المستحيلة. فالجماعيُّ
هنا حلقةٌ على الفرديِّ لا مسارٌ ثانٍ — وما يُرفض منها يُذكر باسمه.

وv1 يقول «⚠ عملية لا يمكن التراجع عنها بسهولة» ثم ينفّذها بضغطة. وهنا تُطلب
**قائمةٌ مختارة** وسببٌ مكتوب: «أوقف الكلّ» ليس اختياراً، هو غيابُه.
"""

from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.auctions import services as auctions
from apps.auctions.models import (
    Auction,
    FuelType,
    PlateType,
    Vehicle,
    VehicleCondition,
)
from apps.auctions.states import AuctionError, AuctionState
from apps.bidding.models import Bid
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.core.uploads import UploadRejected

#: المزادات التي انتهت. تُقرأ من `archive` لا تُكتب ثانيةً.
from .archive import ARCHIVED  # noqa: E402
from .forms import row_stamp_of
from .icons import path_of
from .views import atomic_write, console_page, row_for_write


def dangling_bids():
    """مزايداتٌ قائمة على مزاداتٍ منتهية — **ويجب أن تكون صفراً**.

    وهي بعينها ما يعدّه v1 «مزايدات نشطة 81,475» بجوار «مزادات نشطة 0».
    فمعروضةٌ هنا عدّاداً: صفرٌ يعني أن الإغلاق يعمل، وغيرُ الصفر عطلٌ في
    `auctions.services.end` لا عملٌ جماعيٌّ يُطلَق.
    """
    return Bid.objects.filter(
        vehicle__auction__state__in=ARCHIVED,
        is_withdrawn=False,
        is_superseded=False,
    )


def movable():
    """المزادات التي يمكن إنهاؤها الآن — الجارية وحدها."""
    return (
        Auction.objects.filter(state=AuctionState.LIVE)
        .annotate(
            cars=Count("vehicles", distinct=True),
            bids=Count("vehicles__bids", distinct=True),
        )
        .order_by("-starts_at", "-number")
    )


@console_page("console:auctions-bulk")
def bulk(request):
    """عمليات مجمعة: إنهاءُ مزاداتٍ مختارة، وعدّادٌ يقول إن الإغلاق يعمل."""
    if request.method == "POST":
        return _end_selected(request)

    stale = dangling_bids()
    return render(
        request,
        "console/auctions_bulk.html",
        {
            "live": movable(),
            "auctions": Auction.objects.count(),
            "bids": Bid.objects.count(),
            "dangling": stale.count(),
            # أوّلُ خمسةٍ منها إن وُجدت: عدّادٌ بلا صفوفٍ لا يُتصرَّف فيه.
            "dangling_rows": stale.select_related("vehicle", "vehicle__auction")[:5],
        },
    )


def _end_selected(request):
    """أنهِ ما اختير — مزاداً مزاداً، بالخدمة، وبسببٍ مكتوب.

    **وما يُلتقَط هو رفضُ الآلة وحده.** كان `except Exception` يبتلع كلَّ شيء:
    رفضَ آلة الحالات (وهو المقصود — «لا يمكن نقل المزاد من… إلى…») وخطأَ
    البرمجة معه. فاسمٌ مكتوبٌ خطأً أو حقلٌ حُذف يخرج للموظّف سطراً أحمرَ
    بجوار رقم مزاد، ويقرؤه رفضَ عملٍ فيمضي — ولا شيء في السجلّ يقول إن
    الشيفرة انكسرت.

    و:class:`~apps.auctions.states.AuctionError` هو **أبو الرفضين معاً**
    (`InvalidTransition` و`TransitionNotReady`)، وكلاهما يحمل جملةً عربيّةً
    كُتبت لتُقرأ. وما عداهما يصعد إلى معالج جانغو: صفحةُ خطأٍ ٥٠٠ وسطرٌ في
    السجلّ خيرٌ من عطلٍ يلبس ثوبَ قرارِ عمل.
    """
    chosen = request.POST.getlist("auction")
    reason = (request.POST.get("reason") or "").strip()

    if not chosen:
        messages.error(request, "لم يُختَر مزاد. «أوقف الكلّ» ليس اختياراً.")
        return redirect("console:auctions-bulk")

    ended, refused = [], []
    for auction in Auction.objects.filter(pk__in=chosen):
        try:
            # الخدمةُ وحدها تكتب الحالة، وهي التي تُغلق المزايدات في
            # المعاملة نفسها — فلا زرَّ ثانياً يفعل نصفَ ذلك.
            auctions.end(auction)
        except AuctionError as refusal:
            refused.append((auction, str(refusal)))
            continue

        ended.append(auction)
        audit.record(
            action="console.auction_end_bulk",
            entity=auction,
            actor=request.user,
            note=reason,
        )

    if ended:
        numbers = "، ".join(str(auction.number) for auction in ended)
        messages.success(request, f"أُنهي {len(ended)} مزاداً: {numbers}.")
    for auction, why in refused:
        messages.error(request, f"المزاد {auction.number}: {why}")

    return redirect("console:auctions-bulk")


def quick_edit_targets(text: str = ""):
    """المزادات التي يُفتح منها التعديل السريع — بعدد سياراتها.

    شاشة v1 «⚡ اختر مزاد — تعديل سريع» بطاقاتٌ لكل مزاد، ومنها ما فيه
    **صفرُ سيارات** (`#1005 المطبخ · 0 سيارة`). وبطاقةٌ تُفتح على لا شيء ليست
    اختصاراً؛ فالصفرُ يُعرض هنا في عموده ويُقرأ قبل الضغط.
    """
    rows = Auction.objects.annotate(cars=Count("vehicles", distinct=True)).order_by(
        "-starts_at", "-number"
    )
    text = (text or "").strip()
    if text:
        matches = search_q(text, "title")
        if text.isdigit():
            matches |= Q(number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:auctions-manage")
def manage(request):
    """إدارة مزاد + سياراته: اختر مزاداً لتفتح صفحته وسياراته.

    v1 يفصل «إدارة مزاد + سياراته» عن «تعديل سريع للعدادات» عن «قائمة
    المزادات» — ثلاثةُ مداخل إلى الاختيار نفسه. وهي هنا مدخلٌ واحد يقول ما
    يمكن فعله بكل مزاد، لأن ما يليه (صفحة المزاد) هو نفسه في الثلاثة.
    """
    rows = quick_edit_targets(request.GET.get("q", ""))
    return render(
        request,
        "console/auctions_manage.html",
        {"rows": rows[:100], "q": request.GET.get("q", ""), "total": rows.count()},
    )


# ---------------------------------------------------------------------------
# تعديل سريع للعدادات — صفٌّ واحد لكل سيارة، وقيدٌ لكل تغيير. T830م
# ---------------------------------------------------------------------------
#
# شاشة v1: اختر مزاداً، ثم عدِّل عدّادات سياراته في جدولٍ واحد. والفكرة صحيحة
# — الساحةُ تقيس العدّادات دفعةً واحدة، وفتحُ صفحةِ تعديلٍ لكل سيارةٍ من ثلاثمئة
# عملٌ لا يُنجَز.
#
# وثلاثة أشياء تُضاف هنا:
#
# **١. ما تغيّر وحده يُكتب.** الحلقةُ تقارن القيمة الجديدة بالقديمة وتتخطّى
# المتساوية، فحفظُ الجدول بلا تعديلٍ لا يكتب ثلاثمئة صفّ ولا ثلاثمئة قيد.
#
# **٢. وكلُّ تغييرٍ قيدٌ في `AuditLog` بقيمته قبلُ وبعد.** «كم كان العدّاد؟»
# سؤالٌ يُسأل حين يشكو مشترٍ، ولا يُجاب بالقيمة الحالية.
#
# **٣. والقيمةُ غيرُ الرقمية تُذكر ولا تُسقِط الجدول.** تحت
# `STRICT_TRANS_TABLES` كان v1 يُجهض التحديث كلَّه لقيمةٍ واحدة لا تناسب
# عمودها، فيخسر الموظّفُ ما أدخله كلَّه (T808). وهنا الصفُّ الخطأ يُذكر باسمه
# والباقي يُحفظ.


#: القيمُ المعروضة كشرائح في «حالة المحرك» و«المفتاح» — نصٌّ حرٌّ في v2
#: (`varchar`)، فالشريحةُ اختصارٌ للقيمة الشائعة و«أخرى» تفتح كتابةً حرّة،
#: تماماً كما في v1 (`$optField`).
RUNS_PRESETS = ["تعمل", "لا تعمل"]
KEY_PRESETS = ["يوجد", "لا يوجد"]


#: أعمدةُ ختم HR-13 في التعديل السريع — **ما يكتبه هذا المسار بالضبط**.
#:
#: الصورةُ ليست منها: هي إضافةٌ إلى المعرض لا كتابةٌ فوق قيمة، فلا تدهس أحداً
#: ولا يحرسها ختم.
QUICK_EDIT_STAMPED = (
    "lot_number",
    "odometer_km",
    "plate_type",
    "fuel_type",
    "condition",
    "runs_status",
    "key_status",
)

#: لصائقُ الحقول بالعربية — تُستعمل في رسائل الرفض وفي وصف ما تغيّر.
#:
#: كانت القيمةُ غيرُ الصالحة في التعدادات **تُبتلَع صامتةً** فتخرج ٤٢٢ «لا
#: تغيير»، بينما العدّادُ واللوت يُرفضان برسالةٍ تسمّي الحقل: ثلاثةُ حقولٍ
#: بقاعدتين. والاسمُ هنا هو ما يجعل الرفضَ يقول أيَّ خانةٍ يُصلحها الموظّف.
#: وهي ألفاظُ الشاشة نفسِها (`auctions_quick_edit.html`) لا ألفاظُ النموذج،
#: كي يقرأ الموظّفُ اسمَ الخانة التي أمامه.
FIELD_LABELS = {
    "lot_number": "رقم الموقف",
    "odometer_km": "عداد المسافة",
    "plate_type": "نوع اللوحة",
    "fuel_type": "الوقود",
    "condition": "حالة المركبة",
    "runs_status": "حالة المحرك",
    "key_status": "المفتاح",
}


def _qe_record(car: Vehicle) -> dict:
    """سجلٌّ مضغوطٌ لكل سيارة — تُبنى منه الكروتُ كسولاً بالجافاسكربت.

    v1 يشحن كل سيارةٍ HTMLاً جاهزاً (٨٧ ألف عقدة DOM لـ٨٩٤ سيارة فتتجمّد
    الصفحة)، ثم صار يشحن سجلّاتٍ مضغوطة ويبني دفعةً كلَّ تمرير. المثلُ هنا.

    ويحمل `stamp` — ختمُ HR-13 **لهذا الكارت وحده**. والختمُ للكارت لا
    للصفحة لأن الشاشة تحفظ كارتاً كارتاً بـ`fetch`: ختمٌ واحدٌ للصفحة كان
    سيبطل عند أوّل حفظٍ ناجح، فيُرفض كلُّ ما بعده في الجدول نفسِه.
    """
    return {
        "id": car.pk,
        "stamp": row_stamp_of(car, QUICK_EDIT_STAMPED),
        "lot": car.lot_number,
        "name": f"{car.make} {car.model} {car.year}".strip(),
        "plate": car.plate_number or "",
        "vin": car.vin or "",
        "claim": car.claim_number or "",
        "odo": car.odometer_km if car.odometer_km is not None else "",
        "pt": car.plate_type or "",
        "ft": car.fuel_type or "",
        "cond": car.condition or "",
        "runs": car.runs_status or "",
        "key": car.key_status or "",
        # حقلُ بحثٍ واحدٌ يجمع ما يُبحث به — لوحة/شاصي/مطالبة/اسم/موقف.
        "s": " ".join(
            [
                car.plate_number or "",
                car.vin or "",
                car.claim_number or "",
                car.make,
                car.model,
                str(car.lot_number),
            ]
        ).lower(),
    }


@console_page("console:auctions-quick-edit")
def quick_edit(request):
    """تعديل سريع للعدادات — نظيرُ شاشتَي v1 (`quickEditChooser` ثم
    `quickEditVehicles`): بلا مزادٍ مختار كروتُ اختيار، ومعه كروتُ سياراتٍ
    يُحرَّر كلٌّ منها في مكانه ويحفظ وحده.

    الترتيبُ والحقولُ كما في v1: رقم الموقف، العدّاد وصورتُه، نوع اللوحة،
    الوقود، حالة المركبة، حالة المحرك، المفتاح. والشاصي للقراءة فقط. وما
    تغيّر وحده يُكتب، ولكل تغييرٍ قيدٌ في التدقيق (`vehicle_quick_update`).
    """
    number = request.GET.get("number", "").strip()
    auction = None
    if number.isdigit():
        auction = Auction.objects.filter(number=int(number)).first()

    # وضعُ الاختيار: كروتُ المزادات — نظيرُ `renderAuctionChooser`.
    if auction is None:
        rows = quick_edit_targets(request.GET.get("q", ""))
        return render(
            request,
            "console/quick_edit_pick.html",
            {
                "rows": rows[:100],
                "q": request.GET.get("q", ""),
                "total": rows.count(),
            },
        )

    # وضعُ التحرير: سجلّاتٌ مضغوطة + قوائمُ الخيارات بلصائقها من النموذج.
    cars = Vehicle.objects.filter(auction=auction).order_by("lot_number", "id")
    records = [_qe_record(c) for c in cars]
    return render(
        request,
        "console/auctions_quick_edit.html",
        {
            "auction": auction,
            "records": records,
            "count": len(records),
            # **لافتةٌ لا منع.** حكمُ المالك: لا يُمنع تعديلُ عدّادٍ في مزادٍ
            # منتهٍ — «منعُه يمنع تصحيحَ قراءةٍ اكتُشف خطؤها متأخّراً»، وليس
            # في v1 منع. لكنّ التعديلَ في مزادٍ منتهٍ ومُفوتَر فعلٌ يستحقّ أن
            # يُرى: شاشةُ الاختيار تعرض **كلَّ** المزادات (٥٤ منتهياً من ٥٦)،
            # فالموظّفُ يدخل مزاداً مُرحَّلاً وهو يحسبه جارياً. واللافتةُ
            # تقول له أين هو قبل أن يكتب، والقيدُ يقولها بعد أن كتب.
            "auction_is_closed": auction.state in ARCHIVED,
            "auction_state_label": auction.get_state_display(),
            "plate_choices": PlateType.choices,
            "fuel_choices": FuelType.choices,
            "condition_choices": VehicleCondition.choices,
            "runs_presets": RUNS_PRESETS,
            "key_presets": KEY_PRESETS,
            # الرسوم التي يحتاجها الجافاسكربت — تُشحن مع الصفحة كبقيّة
            # السجلّات (`qeData`، `qeChoices`) لا تُكتب بحرفها في السلسلة.
            #
            # والشاشةُ كانت **أثقلَ ما بقي من إيموجي**: تسعةَ عشرَ محرفاً،
            # أكثرُها داخل سلاسلِ جافاسكربت لرسائل التوست وعلامة الحفظ. ونسخُ
            # وسم `<svg>` في تلك السلاسل كان سيضاعف السطر ويُخفي المعنى؛
            # والمصدرُ الواحد هنا يجعل `toast()` و`setMark()` تبنيان الرسمَ
            # من اسمٍ واحد. ذيلُ T837.
            "qe_icons": {
                "save": path_of("save"),
                "camera": path_of("camera"),
                "ok": path_of("check"),
                "warn": path_of("warn"),
                "err": path_of("x-circle"),
                "search": path_of("search"),
                "car": path_of("car"),
            },
        },
    )


#: سقفُ العدّاد. `odometer_km` عمودُ `PositiveIntegerField` أي `integer` في
#: بوستجرس، وسقفُه ٢٬١٤٧٬٤٨٣٬٦٤٧ — وما فوقه **`DataError` غيرُ ملتقَط**: قِيس
#: بإرسال `99999999999999` فخرج **٥٠٠** وصفحةُ خطأٍ من HTML، والجافاسكربت
#: يحاول `r.json()` عليها فيسقط في `catch` ويقول «تعذّر الاتصال» — وهي كذبة،
#: فالاتصالُ سليمٌ والخادمُ هو الذي انكسر.
#:
#: والرقمُ المكتوب هنا **ليس سقفَ العمود** بل سقفٌ يعنيه الواقع: عشرةُ ملايين
#: كيلومتر أكثرُ مما تمشيه سيّارةٌ بمراحل، وما فوقه خطأُ إدخالٍ لا قياس. ورفضُه
#: برسالةٍ يُقرأ، وقبولُه ثم الانهيارُ عند سقف العمود لا يُقرأ.
ODOMETER_MAX = 10_000_000

#: طولُ `runs_status` و`key_status` في النموذج (`max_length=100`). الحقلان نصٌّ
#: حرّ، ولا شيء كان يقصّهما قبل `save` — فـ٢٠٠ حرفٍ في «أخرى» يخرج **٥٠٠**
#: و`DataError`، وقد قِيس. والرفضُ هنا لا القصُّ: قصُّ ما كتبه الموظّف صامتاً
#: يكتب في القاعدة غيرَ ما رآه على الشاشة.
FREE_TEXT_MAX = 100

#: ما يُقال لمن وصل ثانياً إلى الكارت نفسِه — وبعده تُذكر القيمُ التي تغيّرت.
#:
#: «تعارضٌ في النسخة» تشخيصٌ تقنيّ يُنتج تذكرةَ دعم. وهذه تقول ما جرى وما
#: يُفعَل، والجافاسكربت يُلحق بها **ما صار إليه الحقل** من `fresh` — فيرى
#: الموظّفُ الرقمَ الجديد في الكارت نفسِه بلا أن يُعاد تحميلُ الجدول كلِّه.
STALE_CARD = "عُدِّل هذا الكارت من نافذةٍ أخرى بعد أن فتحتَ الصفحة."


@atomic_write
def vehicle_quick_update(request, pk: int):
    """حفظُ سيارةٍ واحدة من كارت التعديل السريع — نظيرُ `quickUpdateVehicle` في v1.

    يُستدعى بـAJAX (حفظٌ تلقائيٌّ لكل كارت). يكتب ما أُرسل فقط، ويتخطّى
    الفارغَ كي لا يمحو قيمةً قائمة — كقاعدة v1 نفسِها. وكلُّ تغييرٍ قيدٌ يحمل
    القيمة قبلُ وبعد. وصورةُ العدّاد تدخل معرضَ السيارة عبر الخدمة المُعقَّمة.

    والمركبةُ تُقيَّد بمزادها المفتوح
    ================================
    v1 يأخذ المزادَ والمركبةَ معاً في المسار
    (`/auctions/{aid}/vehicles/{vid}/quick-update`) ويرفض ٤٠٤ إن لم يكونا
    زوجاً (`AuctionController.php:4913` → `findAuctionVehicle`). وهذا المسارُ
    أسقط المزادَ من العنوان فأسقط معه الشرط: `pk` وحدَه كان يفتح **أيَّ مركبةٍ
    في القاعدة** — قِيس في ١٤ سبتمبر ٢٠٢٦ بإرسال قيمةٍ مساويةٍ إلى المركبة
    ١٢٨٠٥ (مزاد ١٠١٧ **المنتهي**) فردَّ «لا تغيير» ٤٢٢ لا ٤٠٤، أي أنه وجدها
    وقارن. وتغييرُ رقمٍ في الطلب كان يكفي لتعديل عدّادِ سيّارةٍ في مزادٍ آخر،
    والعدّادُ يغيّر سعرَها.

    فالمزادُ يُرسَل في الجسد (`auction`، برقمه كما في الشاشة) ويُطابَق. وهو
    شرطُ v1 نفسُه، مكتوباً حيث يقدر هذا المسارُ أن يكتبه.

    والصفُّ يُقفَل ويُختَم — HR-13 على كارت
    =====================================
    هذه **أجمعُ شاشات اللوحة**: الساحةُ تقيس العدّادات بأجهزةٍ عدّة في وقتٍ
    واحد. وكانت بلا قفلٍ ولا ختم: موظّفان على السيّارة نفسِها، وآخرُ
    القادمين يكتب فوق الأوّل بلا أثر، والقيدُ الثاني يسجّل `before` قديمةً
    فيروي تاريخاً خاطئاً. وv1 مثلُه — وذلك ليس حجّة.

    والحارسان معاً لا أحدُهما:

    * **الختم** (`row_stamp` لكل كارت) يغلق النافذةَ الواسعة: دقائقُ بين
      رسمِ الجدول والحفظ.
    * **القفل** (`select_for_update` عند الكتابة، عبر :func:`row_for_write`)
      يغلق الضيّقة: طلبان في العشرات نفسِها من الميلي‑ثانية يقرآن الصفَّ
      فيتطابق ختماهما معاً ويكتب الثاني فوق الأوّل.

    والقفلُ على **صفّ المركبة وحده**: `select_related("auction")` مع
    `select_for_update` كان سيقفل صفَّ المزاد أيضاً، فيصير حفظُ كارتٍ واحدٍ
    يحجب كلَّ كروت المزاد الأخرى. فالمزادُ يُقرأ بعدها بلا قفل — استعلامٌ
    ثانٍ ثمنُه أرخصُ من طابورٍ على الجدول كلِّه.
    """
    if not request.user.is_authenticated or not can(
        request.user, Capability.AUCTIONS_MANAGE
    ):
        return JsonResponse({"ok": False, "message": "لا صلاحية."}, status=403)
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "POST فقط."}, status=405)

    car = row_for_write(request, Vehicle.objects.all(), pk=pk)

    # الزوجُ (مزاد، مركبة) كما يتحقّق منه v1. والرقمُ هو ما تحمله الشاشةُ في
    # `data-auction`، فلا يُطلب من الجافاسكربت أن يعرف `pk` لا يراه.
    wanted = (request.POST.get("auction") or "").strip()
    if not wanted.isdigit() or int(wanted) != car.auction.number:
        return JsonResponse(
            {"ok": False, "message": "هذه المركبة ليست في المزاد المفتوح."},
            status=404,
        )

    # ختمُ HR-13 — والصفُّ مقفولٌ ومقروءٌ من القاعدة في هذه اللحظة، فما يُحسب
    # هنا هو ما في القاعدة لا ما أراده المرسِل.
    #
    # **والكارتُ وحده يُعلَّم، ولا تُهدَر بقيّةُ الجدول**: الردُّ ٤٠٩ يحمل
    # `fresh` — سجلَّ الصفّ كما هو الآن بختمه الجديد — فيقارنه الجافاسكربت
    # بما بُني منه الكارتُ ويسمّي ما تغيّر. ولا إعادةَ تحميلٍ للصفحة، ولا
    # كارتٌ آخرُ يفقد ما فيه.
    #
    # والختمُ الفارغ يمرّ، كعقد `ReasonMixin` نفسِه: صفحةٌ رُسمت قبل النشر لا
    # تحمله. ثمنٌ يُدفع مرّةً واحدة.
    sent_stamp = (request.POST.get("row_stamp") or "").strip()
    if sent_stamp and sent_stamp != row_stamp_of(car, QUICK_EDIT_STAMPED):
        return JsonResponse(
            {
                "ok": False,
                "code": "stale",
                "message": STALE_CARD,
                "fresh": _qe_record(car),
            },
            status=409,
        )

    changes: dict[str, tuple] = {}
    #: علاماتٌ تُلحَق بنصّ القيد — ما لا يُقرأ من `before`/`after` وحدهما.
    notes: dict[str, str] = {}

    # العدّاد — رقمٌ صحيحٌ غير سالب ودون السقف. والفارغُ **يُترك** كما في v1
    # (`if ($mileage !== '')`, `AuctionController.php:4929`): كان الفراغُ يمحو
    # القيمةَ القائمة، والحفظُ تلقائيٌّ بعد ٩٠٠ مللي من آخر ضغطةِ مفتاح — فمسحُ
    # الخانة لإعادة كتابتها كان يكفي لمحو قياسٍ من الساحة بلا سؤال، وقيدُ
    # التدقيق يشهد: `odometer_km: 5 ← None`. ومَن أراد محوَ قراءةٍ خاطئة
    # فبابُه صفحةُ المركبة، لا خانةٌ تُفرَّغ سهواً.
    if "odometer_km" in request.POST:
        raw = request.POST.get("odometer_km", "").strip()
        if raw != "":
            if not raw.isdecimal():
                return JsonResponse(
                    {"ok": False, "message": "العدّاد يجب أن يكون رقماً صحيحاً."},
                    status=422,
                )
            new_odo = int(raw)
            if new_odo > ODOMETER_MAX:
                return JsonResponse(
                    {
                        "ok": False,
                        "message": f"العدّاد أكبر من المعقول (السقف {ODOMETER_MAX:,}).",
                    },
                    status=422,
                )
            # **النقصانُ يمرّ بتأكيد، ولا يُمنع.** حكمُ المالك: «الرقمُ ينقص
            # مشروعاً حين يُصحَّح خطأُ إدخالٍ سابق»، فالمنعُ يمنع التصحيح.
            # وv1 لا يمنع أيضاً — قِيس: ١٢٠٬٠٠٠ ← ٥ قُبل بلا كلمة.
            #
            # والعلمُ **في الطلب** لا في المتصفّح وحده: تأكيدٌ في الجافاسكربت
            # يُلتفّ عليه بطلبٍ مباشر، وهذا المسارُ يُنادى بـ`fetch` فالطلبُ
            # المباشر إليه ليس افتراضاً بعيداً. فبلا العلم ٤٢٢ تقول القيمتين،
            # ومعه يمرّ **ويُكتب في القيد أنه نقصانٌ مؤكَّد** — فمن يقرأ
            # السجلّ بعد شهور يفرّق بين تصحيحٍ مقصودٍ وخطأِ لوحةِ مفاتيح.
            if new_odo != car.odometer_km:
                dropping = car.odometer_km is not None and new_odo < car.odometer_km
                if dropping and request.POST.get("odometer_down_ack") != "1":
                    return JsonResponse(
                        {
                            "ok": False,
                            "code": "odometer_down",
                            "message": (
                                f"العدّاد ينقص: {car.odometer_km:,} ← {new_odo:,}. "
                                "أكّد أنك تقصد ذلك."
                            ),
                        },
                        status=422,
                    )
                changes["odometer_km"] = (car.odometer_km, new_odo)
                if dropping:
                    notes["odometer_km"] = "نقصانٌ مؤكَّد من الموظّف"
                car.odometer_km = new_odo

    # رقم الموقف — لوتٌ موجب. الفارغُ يُترك، فلا يُمحى موقفٌ قائم.
    if "lot_number" in request.POST:
        raw = request.POST.get("lot_number", "").strip()
        if raw != "":
            if not raw.isdigit() or int(raw) <= 0:
                return JsonResponse(
                    {"ok": False, "message": "رقم الموقف يجب أن يكون رقماً موجباً."},
                    status=422,
                )
            new_lot = int(raw)
            if new_lot != car.lot_number:
                changes["lot_number"] = (car.lot_number, new_lot)
                car.lot_number = new_lot

    # الحقولُ ذاتُ التعداد المغلق — والقيمةُ غيرُ الصالحة **تُرفض باسم حقلها**.
    #
    # كانت تُهمَل صامتةً: `plate_type=NOT_A_CHOICE` يخرج ٤٢٢ «لا تغيير» —
    # الرسالةُ نفسُها التي يقرأها من لم يعدّل شيئاً. فثلاثةُ حقولٍ بقاعدتين:
    # العدّادُ واللوت يُرفضان برسالةٍ تسمّي الحقل، والتعداداتُ تُبتلَع. وأسوأُ
    # ما في الابتلاع أنه **يبدو نجاحاً لما لم يُفهَم**: من أرسل قيمةً لا يعرفها
    # الخادم يُقال له «لا تغيير»، فيظنّ أن اختياره كان هو القائم أصلاً.
    #
    # و«لا تغيير» تبقى لما لم يتغيّر فعلاً، لا لما لم يُفهَم.
    enum_fields = {
        "plate_type": {v for v, _ in PlateType.choices},
        "fuel_type": {v for v, _ in FuelType.choices},
        "condition": {v for v, _ in VehicleCondition.choices},
    }
    for field, valid in enum_fields.items():
        if field in request.POST:
            val = request.POST.get(field, "").strip()
            # الفراغُ يُترك كبقيّة الحقول — القاعدةُ واحدةٌ في السبعة.
            if val == "":
                continue
            if val not in valid:
                return JsonResponse(
                    {
                        "ok": False,
                        "message": (
                            f"قيمةٌ غير مقبولة في «{FIELD_LABELS[field]}»: {val}"
                        ),
                    },
                    status=422,
                )
            if val != getattr(car, field):
                changes[field] = (getattr(car, field), val)
                setattr(car, field, val)

    # حالة المحرك والمفتاح — نصٌّ حرٌّ في v2؛ الفارغُ لا يمحو، والطويلُ يُردّ
    # برسالةٍ لا بـ`DataError` من القاعدة.
    for field in ("runs_status", "key_status"):
        if field in request.POST:
            val = request.POST.get(field, "").strip()
            if len(val) > FREE_TEXT_MAX:
                return JsonResponse(
                    {
                        "ok": False,
                        "message": (
                            f"«{FIELD_LABELS[field]}»: النصّ أطولُ من "
                            f"{FREE_TEXT_MAX} حرفاً."
                        ),
                    },
                    status=422,
                )
            if val and val != getattr(car, field):
                changes[field] = (getattr(car, field), val)
                setattr(car, field, val)

    # صورةُ العدّاد — تدخل المعرضَ صورةً عادية (لا غلافاً)، عبر الخدمة الوحيدة.
    image_id = 0
    image_error = None
    photo = request.FILES.get("meter_image")
    if photo is not None:
        try:
            image_id = auctions.add_image(car, photo, cover=False).pk
        except UploadRejected as refusal:
            image_error = str(refusal)

    if not changes and image_id == 0 and image_error is None:
        return JsonResponse({"ok": False, "message": "لا تغيير."}, status=422)

    # **مزادٌ منتهٍ لا يمنع التعديل، لكنّه يُكتب في القيد.** حكمُ المالك: منعُه
    # يمنع تصحيحَ قراءةٍ اكتُشف خطؤها متأخّراً، وv1 لا يمنع. لكنّ تعديلَ عدّادِ
    # سيّارةٍ في مزادٍ مُفوتَر فعلٌ يستحقّ أن يُرى — والشاشةُ تُظهر لافتةً،
    # والسجلُّ يحمل الحالة، فمن يسأل بعد شهور يعرف أن التعديل وقع بعد الإنهاء.
    ended_note = (
        f" · مزادٌ {car.auction.get_state_display()} ({car.auction.number})"
        if car.auction.state in ARCHIVED
        else ""
    )

    if changes:
        try:
            # نقطةُ حفظٍ داخل معاملة الطلب: `IntegrityError` تُسمّم المعاملةَ
            # التي تقع فيها، فالتقاطُها بلا `atomic` داخليّة كان سيجعل الردّ
            # ٤٠٩ ينفجر عند الإيداع بـ`TransactionManagementError`.
            with transaction.atomic():
                car.save(update_fields=[*changes.keys(), "updated_at"])
        except IntegrityError:
            return JsonResponse(
                {"ok": False, "message": "رقم الموقف مستعمَل في هذا المزاد."},
                status=409,
            )
        for field, (before, after) in changes.items():
            mark = f" · {notes[field]}" if field in notes else ""
            audit.record(
                action="console.quick_edit_field",
                entity=car,
                actor=request.user,
                before={field: before},
                after={field: after},
                note=f"{field}: {before} ← {after}{mark}{ended_note}",
            )
    if image_id:
        audit.record(
            action="console.quick_edit_meter_photo",
            entity=car,
            actor=request.user,
            after={"image": image_id},
            note=f"صورةُ عدّاد من التعديل السريع{ended_note}",
        )

    # والختمُ الجديد يعود مع الردّ: الشاشةُ تحفظ الكارتَ نفسَه مرّاتٍ متتالية
    # (حفظٌ تلقائيٌّ بعد كل سكون)، وختمٌ لا يتجدّد كان سيجعل الحفظ الثاني
    # يُرفض بحجّة أن الأوّل — وهو حفظُ الموظّف نفسِه — دهسه.
    resp = {
        "ok": True,
        "image_id": image_id,
        "saved": list(changes.keys()),
        "row_stamp": row_stamp_of(car, QUICK_EDIT_STAMPED),
    }
    if image_error:
        resp["image_error"] = image_error
    return JsonResponse(resp)
