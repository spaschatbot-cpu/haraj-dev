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
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from apps.auctions import services as auctions
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState
from apps.bidding.models import Bid
from apps.core import audit

#: المزادات التي انتهت. تُقرأ من `archive` لا تُكتب ثانيةً.
from .archive import ARCHIVED  # noqa: E402
from .views import console_page


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
    """أنهِ ما اختير — مزاداً مزاداً، بالخدمة، وبسببٍ مكتوب."""
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
        except Exception as refusal:
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
        matches = Q(title__icontains=text)
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


@console_page("console:auctions-quick-edit")
def quick_edit(request):
    """تعديل سريع للعدادات: جدولُ سياراتِ مزادٍ واحد، وما تغيّر وحده يُكتب."""
    number = request.GET.get("number", "") or request.POST.get("number", "")
    auction = None
    if (number or "").strip().isdigit():
        auction = Auction.objects.filter(number=int(number)).first()

    if request.method == "POST" and auction is not None:
        return _save_meters(request, auction)

    cars = (
        Vehicle.objects.filter(auction=auction).order_by("lot_number", "id")
        if auction
        else Vehicle.objects.none()
    )
    return render(
        request,
        "console/auctions_quick_edit.html",
        {
            "auction": auction,
            "cars": cars,
            "number": number,
            "auctions": quick_edit_targets()[:60],
        },
    )


def _save_meters(request, auction: Auction):
    """اكتب ما تغيّر وحده، وسمِّ ما لم يُقبَل."""
    changed, refused = 0, []

    for car in Vehicle.objects.filter(auction=auction):
        raw = (request.POST.get(f"meter-{car.pk}") or "").strip()
        if raw == "":
            was_blank = car.odometer_km is None
            if was_blank:
                continue
            new = None
        else:
            if not raw.isdigit():
                refused.append((car, "العدّاد يجب أن يكون رقماً صحيحاً"))
                continue
            new = int(raw)

        if new == car.odometer_km:
            continue

        before = car.odometer_km
        car.odometer_km = new
        car.save(update_fields=["odometer_km", "updated_at"])
        changed += 1
        audit.record(
            action="console.quick_edit_meter",
            entity=car,
            actor=request.user,
            note=f"العدّاد: {before if before is not None else '—'} ← "
            f"{new if new is not None else '—'}",
        )

    if changed:
        messages.success(request, f"حُفظ {changed} عدّاداً.")
    elif not refused:
        messages.success(request, "لا تغيير — لم يُكتب شيء.")
    for car, why in refused:
        messages.error(request, f"اللوت {car.lot_number}: {why}")

    return redirect(f"{request.path}?number={auction.number}")
