"""منصّةُ الملّاك — اختيارُ العروض في المزاد المنتهي الأخير. T965

طلبُ المالك (٢١ سبتمبر ٢٠٢٦) بالحرف: «استبدل صفحة منصّة الملّاك بالصفحة دي»،
ومعه رابطُ `admin2/bills/index.php`.

## ولماذا كان الاستبدالُ هو الصواب

الشاشةُ التي كانت هنا أربعَ عشرةَ بطاقةً معظمُها **روابطُ شاشاتٍ في الشريط
الجانبيّ أصلاً**، وسبعةُ أرقامٍ تُقرأ في لمحةٍ ثم لا يُفعَل بها شيء. وكان
مكتوباً في رأسها هي نفسِها أن أوّلَ رابطٍ في نسخة v1 «يخرج إلى
`admin2/bills/index.php` — أي أن الصفحة الموحّدة تُحيل إلى نظامٍ ثالث». فما
كان المالكُ يفتح «منصّة الملّاك» ليقرأ عدّادات؛ كان يفتحها **ليمرّ منها** إلى
الشاشة التي يعمل فيها فعلاً. فصارت هي هي.

## وما تفعله الشاشة

بعد أن يُقفل مزاد، يجلس المالكُ أمام صفٍّ لكلّ مركبةٍ فيه ومعه **أعلى عرضٍ
قائم**: يقبل، أو يرفض، أو يفتح قائمةَ المزايدين ليأخذ الثاني. ثمّ يُصدر
الفواتير دفعةً واحدة، ويُبلغ الفائزين.

## وثمانيةُ فروقٍ عن v1، كلٌّ منها من عطلٍ في ملفّه

**١ — الضريبةُ لا تُضرَب هنا.** v1 يقرأ `auctions.vat_type` ويضربه في هذا
الملفّ (``$vat = $vat/100; … $amount + $amount*$vat``) وفي ثلاثة مواضعَ أخرى.
وهنا `money.services.tax_added_to` هي الموضعُ الوحيدُ الذي يضرب في النسبة في
المستودع كلِّه.

**٢ — والرسمُ الإداريُّ داخلٌ في «شامل الضريبة».** عمودُ v1 يجمع المزايدةَ
وضريبتَها ويتوقّف، والفاتورةُ التي تصدر بعده تحمل **رسمَ المزاد أيضاً وضريبتَه**
(`money.services.issue_invoice`). فالمالكُ يقرأ رقماً على الشاشة ويرى رقماً
أكبرَ في الفاتورة ولا يعرف من أين جاء الفرق. والعمودُ هنا يُبنى بالمعادلة التي
تبني الفاتورةَ نفسَها: ``tax_added_to(العرض + رسم المزاد)``.

**٣ — المرشّحاتُ على الخادم لا في المتصفّح.** فلاترُ v1 جافاسكربت تُخفي صفوفاً
مرسومة، **والتصديرُ يتجاهلها** — مكتوبٌ في `index.php` بصراحة: «يصدّر الجدول
كاملاً… الفلاتر تعمل في المتصفّح فلا تصل إلى الخادم». فمن رشّح «مرفوض» وضغط
«تصدير» أخذ الورقةَ كاملةً وهو يظنّها نتيجتَه. وهنا المرشِّحُ في `WHERE`،
والورقةُ **هي** ما على الشاشة بحكم البناء.

**٤ — صفٌّ واحدٌ لكلّ مركبة، والتعادلُ عمودٌ لا صفٌّ مكرَّر.** v1 يعرض المركبةَ
المتعادَلَ عليها **مرّتين** ويلوّن الصفّين. وهنا الصفُّ مركبةٌ، وعددُ
المتعادلين رقمٌ في خليّته — فالعدُّ على الشاشة يبقى عددَ المركبات.

**٥ — ولا «تعديل سعر مزايدة».** زرُّ v1 يكتب فوق `bids.amount`. والمزايدةُ
عرضٌ قانونيٌّ وقع، فلا يُكتب فوقه في هذا المستودع أبداً: يُسحَب ويُستبدَل بقيدٍ
يقول من ولماذا (`bidding.settlement`). ومكانُه «قائمةُ المزايدين» — وهي الطريقُ
الصحيحُ إلى الحالة التي كان الزرُّ يُستعمل لها فعلاً: «خُذ الثاني».

**٦ — والقبولُ والرفضُ ليسا هنا.** يذهبان إلى `console:partner-award-top` و
`console:partner-reject` — النقطتين اللتين تكتبان السجلَّ وتغلقان المزاد
وتحرّران تأمينات الخاسرين. بابٌ جديدٌ إلى منطقٍ قائمٍ، لا نسخةٌ ثانيةٌ منه.

**٧ — والمفوتَرةُ لا تختفي.** v1 يُخرج المركبةَ من الشاشة بمجرّد أن تُفوتَر
(`$invoicedExclude`)، فالمالكُ لا يستطيع أن يرى ما قرّره قبل قليل. وهنا تبقى
بحالتها ورقم فاتورتها، ومن أراد المتبقّي وحدَه رشّح «قيد القرار».

**٨ — والمبلغُ والجوّالُ خلف حارسَيهما** (`sensitive.py`) على الشاشة **وفي
الورقة معاً**. وv1 لا يحجب شيئاً: من فتح الصفحة رأى كلَّ جوّالٍ وكلَّ مبلغ.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.shortcuts import render
from django.utils.http import urlencode

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import VehicleState
from apps.auctions.visibility import PHASE_AUCTION_STATES, Phase, latest_ended_auction
from apps.bidding.models import Bid
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

from .exports import export_table, wants_export
from .icons import path_of
from .paging import paged, pager
from .sensitive import AWARDED_STATES, CUSTOMER, MONEY, columns_for, shown_to
from .tones import with_tones
from .views import console_page

#: قرارُ المالك على المركبة، مقروءاً من حالتها. ثلاثةٌ كما في v1
#: (`pending`/`accepted`/`rejected`) — والحالاتُ عندنا تسعٌ، فتُطوى إلى السؤال
#: الذي تجيبه هذه الشاشة وحدَه: **أحُسم أمرُها؟**
#:
#: و«مقبول» يشمل المفوترةَ والمسدَّدةَ والخارجة: كلُّها مركباتٌ رستْ، والفرقُ
#: بينها موضعُها في طريق المال لا في قرار المالك.
DECISIONS = (
    ("", "كلُّ القرارات"),
    ("pending", "قيد القرار"),
    ("accepted", "مقبول"),
    ("rejected", "مرفوض"),
)

#: الحالاتُ التي يقابلها كلُّ قرار — تعريفٌ واحدٌ يقرؤه المرشِّحُ والعرضُ معاً،
#: فلا يُرشَّح على معنىً ويُلوَّن على آخر.
DECISION_STATES = {
    "accepted": tuple(AWARDED_STATES),
    "rejected": (VehicleState.REJECTED,),
    "pending": (
        VehicleState.DRAFT,
        VehicleState.LISTED,
        VehicleState.BIDDING,
        VehicleState.AWAITING_DECISION,
    ),
}

MARKETING = (("", "تسويقيّة وغيرها"), ("1", "التسويقيّة فقط"), ("0", "غير التسويقيّة"))

#: طولُ قائمة المزادات في المرشّح. سبعةٌ وستّون مزاداً في القاعدة اليوم،
#: وقائمةٌ بها كلِّها لا تُقرأ — والمُراجَعُ منها آخرُ بضعة.
ENDED_CHOICES = 30


def decision_of(vehicle) -> str:
    """قرارُ المالك على هذه المركبة — الدالّةُ التي يُبنى منها المرشّحُ والحبّة."""
    if vehicle.state in AWARDED_STATES:
        return "accepted"
    if vehicle.state == VehicleState.REJECTED:
        return "rejected"
    return "pending"


def _amount(raw: str) -> Decimal | None:
    """رقمٌ من خانةِ مبلغٍ، أو ``None`` لما ليس رقماً.

    و``None`` لا صفر: «من ٠» مرشِّحٌ يمرّ كلَّ شيء، و«من (فراغ)» يجب أن يعني
    «لا حدَّ أدنى» — وهما مختلفان لمن يكتب حرفاً خطأً في الخانة.
    """
    raw = (raw or "").strip().replace(",", "")
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def latest_ended() -> Auction | None:
    """المزادُ المنتهي الأحدث — بالتعريف الذي يقرؤه التطبيقُ نفسُه.

    `visibility.latest_ended_auction` هي التي ترسم تبويبَ «المنتهي» في تطبيق
    العميل، ومكتوبٌ فوقها لماذا `ends_at__lte=now` شرطٌ زائدٌ عن v1 ولازم.
    فالشاشتان تقولان «آخرُ مزادٍ منتهٍ» وتعنيان المزادَ نفسَه — ولو كتبتُ هنا
    استعلاماً ثانياً لافترقا أوّلَ ما يُصلَح أحدُهما.
    """
    return Auction.objects.filter(pk__in=latest_ended_auction()).first()


def ended_choices():
    """المزاداتُ المنتهيةُ لمرشّح الشاشة — الأحدثُ إقفالاً أوّلاً.

    **وهذا ما لا يملكه v1 إطلاقاً.** `admin2/bills/index.php` يثبّت المزادَ
    الأخيرَ في الاستعلام نفسِه (``AND b.auction_id = (SELECT … LIMIT 1)``)،
    فمن أراد أن يراجع قرارَ المزاد الذي قبله لا سبيلَ له من الشاشة أصلاً —
    ولو أُقفل بعده مزادٌ تجريبيٌّ بسيّارةٍ واحدةٍ صارت الشاشةُ سيّارةً واحدة
    والعملُ الحقيقيُّ لا يُرى (وقع هذا على قاعدة التطوير حرفيّاً).

    والافتراضيُّ يبقى الأخيرَ: هو ما يُفتح لأجله في تسعٍ من عشر.

    وما لا مركبةَ فيه يُعرَض كذلك — بعدده صفراً: مزادٌ أُقفل فارغاً خطأٌ
    يستحقّ أن يُرى، وإخفاؤه يجعل «أين مزادي؟» سؤالاً بلا جواب.
    """
    return (
        Auction.objects.filter(state__in=sorted(PHASE_AUCTION_STATES[Phase.ENDED]))
        .annotate(cars=Count("vehicles"))
        .order_by("-ends_at", "-pk")
        .values("pk", "number", "title", "cars")[:ENDED_CHOICES]
    )


def offer_rows(
    auction: Auction,
    *,
    text: str = "",
    price_from: Decimal | None = None,
    price_to: Decimal | None = None,
    decision: str = "",
    marketing: str = "",
):
    """مركباتُ هذا المزاد ومعها أعلى عرضٍ قائمٍ على كلٍّ منها.

    **والترتيبُ برقم الموقف** كما في v1 (`ORDER BY lot_number`): المالكُ يمرّ
    في الحوش بالترتيب، والشاشةُ تُقرأ بجانب السيّارات. وعمودُنا عدديٌّ فلا
    تقع فيه فوضى الترتيب النصّيّ التي في v1 (١٤ ثمّ ١٤٩ ثمّ ٣٤ ثمّ ٨).

    و`top_bid` بالتعريف الوحيد للمزايدة القائمة (`Bid.objects.live()` مكتوباً
    شرطاً هنا لأنه داخل `Max`): المسحوبةُ فعلُ صاحبها والمتجاوَزةُ أثرُ فعله،
    وكلتاهما لم تعد عرضاً يُقبَل.
    """
    live = Q(bids__is_withdrawn=False, bids__is_superseded=False)
    rows = (
        Vehicle.objects.filter(auction=auction)
        .select_related("auction", "awarded_to")
        .annotate(
            top_bid=Max("bids__amount", filter=live),
            bidders=Count("bids__bidder", filter=live, distinct=True),
            image_count=Count("images", distinct=True),
        )
        .order_by("lot_number", "pk")
    )

    text = (text or "").strip()
    if text:
        # ما يُتذكَّر من سيّارةٍ في الحوش: لوحتُها، أو شاصيها، أو رقمُ مطالبتها،
        # أو اسمُها — أو اسمُ من زايد عليها. ولا يُعرف أيُّها في يد السائل.
        matches = search_q(
            text,
            "plate_number",
            "vin",
            "claim_number",
            "make",
            "model",
            "bids__bidder__full_name",
            "bids__bidder__phone",
        )
        if text.isdigit():
            matches |= Q(lot_number=int(text))
        # `distinct` لأن المطابقة على `bids__…` تصل من الوصل بصفٍّ لكلّ مزايدة:
        # سيّارةٌ زايد عليها اسمٌ مطابقٌ ثلاثَ مرّاتٍ كانت ستظهر ثلاثاً.
        rows = rows.filter(matches).distinct()

    if price_from is not None:
        rows = rows.filter(top_bid__gte=price_from)
    if price_to is not None:
        rows = rows.filter(top_bid__lte=price_to)
    if decision in DECISION_STATES:
        rows = rows.filter(state__in=DECISION_STATES[decision])
    if marketing in ("0", "1"):
        rows = rows.filter(is_marketing=(marketing == "1"))
    return rows


def top_offers(vehicles) -> tuple[dict, dict]:
    """أعلى عرضٍ قائمٍ لكلّ مركبةٍ في الصفحة، وعددُ المتعادلين عليه.

    **استعلامٌ واحدٌ يردّ صفّاً لكلّ مركبةٍ تقريباً، لا كلَّ مزايداتها.**
    الطريقُ الساذج — جلبُ مزايدات الصفحة كلِّها وأخذُ الأعلى في بايثون — يردّ
    على صفحةٍ من مئةِ مركبةٍ بثلاثةِ آلاف صفٍّ ومعها عميلُ كلٍّ منها. فالشرطُ
    في القاعدة: مزايدةٌ **مبلغُها هو الأعلى على مركبتها**.

    والتعادلُ يسقط من الاستعلام نفسِه: أكثرُ من صفٍّ لمركبةٍ واحدةٍ يعني
    مزايدَين كتبا المبلغَ نفسَه، وهي الحالةُ التي يلوّنها v1 بصفٍّ مكرَّر.
    """
    ids = [vehicle.pk for vehicle in vehicles]
    if not ids:
        return {}, {}

    highest = (
        Bid.objects.live()
        .filter(vehicle=OuterRef("vehicle"))
        .order_by("-amount")
        .values("amount")[:1]
    )
    best: dict[int, Bid] = {}
    tied: dict[int, int] = {}
    for bid in (
        Bid.objects.live()
        .filter(vehicle_id__in=ids, amount=Subquery(highest))
        .select_related("bidder")
        .order_by("vehicle_id", "placed_at")
    ):
        tied[bid.vehicle_id] = tied.get(bid.vehicle_id, 0) + 1
        best.setdefault(bid.vehicle_id, bid)
    return best, tied


def live_invoices(vehicles) -> dict:
    """فاتورةُ كلّ مركبةٍ في الصفحة إن كانت لها فاتورةٌ حيّة — استعلامٌ واحد.

    والملغاةُ مستثناةٌ لأن قيدَ القاعدة نفسَه يستثنيها
    (`one_live_invoice_per_vehicle`): فاتورةٌ ملغاةٌ لا تمنع فاتورةً ثانية،
    فعرضُها «مفوترة» يقول للمالك إنّ عملاً تمَّ وهو لم يتمّ.
    """
    ids = [vehicle.pk for vehicle in vehicles]
    if not ids:
        return {}
    rows = Invoice.objects.filter(vehicle_id__in=ids).exclude(
        state=InvoiceState.CANCELLED
    )
    return {invoice.vehicle_id: invoice for invoice in rows}


def dress(vehicles, *, auction: Auction, seen) -> None:
    """اكتبْ على كلّ صفٍّ ما يُعرَض منه فعلاً — والمحجوبُ يُمحى هنا.

    النمطُ نفسُه الذي في `sensitive.prepare`، ولا يُستدعى هو لأن شخصَ هذا
    الصفّ **أعلى مزايدٍ لا فائزاً**: `prepare` تقرأ `awarded_to`، وهو `NULL`
    في كلّ مركبةٍ لم يُحسم أمرُها — أي في كلّ صفٍّ تعنيه هذه الشاشة.

    و«شامل الضريبة» يُحسب هنا بالمعادلة التي تبني الفاتورةَ نفسَها، ولا يُحسب
    لمن لا يرى المبلغَ أصلاً: رقمٌ مشتقٌّ من محجوبٍ يكشفه بالقسمة.
    """
    best, tied = top_offers(vehicles)
    invoices = live_invoices(vehicles)
    fee = auction.admin_fee or Decimal("0")

    for vehicle in vehicles:
        bid = best.get(vehicle.pk)
        vehicle.top = bid
        vehicle.tied = tied.get(vehicle.pk, 0)
        vehicle.decision = decision_of(vehicle)
        vehicle.invoice = invoices.get(vehicle.pk)

        who = bid.bidder if (bid and seen.customer) else None
        vehicle.buyer_name = who.full_name if who else ""
        vehicle.buyer_phone = who.phone if who else ""

        # المبلغُ المعروض: ما رستْ به إن رستْ، وإلّا أعلى عرضٍ قائم. وv1 يعيد
        # حساب الأعلى في كلّ عرض، فمركبةٌ رستْ على الثاني تعرض رقمَ الأوّل —
        # **والرقمُ يدخل حديثَ الفاتورة**.
        offer = vehicle.awarded_price if vehicle.awarded_price else vehicle.top_bid
        vehicle.offer = offer if seen.money else None
        vehicle.with_tax = (
            money.tax_added_to(offer + fee).total if (seen.money and offer) else None
        )


def totals(rows) -> dict:
    """عدّاداتُ رأس الشاشة — استعلامٌ واحدٌ بأربعة أعداد.

    وهي الرقمُ الذي يفتح المالكُ الشاشةَ لأجله: «كم بقي عليّ؟». وv1 لا يقوله
    إطلاقاً — يُعَدُّ بالعين في جدولٍ من ثلاثمئة صفّ.
    """
    return rows.aggregate(
        all_rows=Count("pk", distinct=True),
        pending=Count(
            "pk", filter=Q(state__in=DECISION_STATES["pending"]), distinct=True
        ),
        accepted=Count(
            "pk", filter=Q(state__in=DECISION_STATES["accepted"]), distinct=True
        ),
        rejected=Count(
            "pk", filter=Q(state__in=DECISION_STATES["rejected"]), distinct=True
        ),
        # **ما ينتظر فاتورة** — والحالةُ وحدَها تقوله: الفوترةُ تنقل المركبةَ
        # من `awarded` إلى `invoiced` في المعاملة نفسِها (`mark_invoiced`).
        # وهو بعينه ما ترشّحه `decisions.accepted_invoice_all`، فالعددُ على
        # الزرّ هو عددُ ما سيُفوتَر لا تقديرٌ له.
        to_invoice=Count("pk", filter=Q(state=VehicleState.AWARDED), distinct=True),
    )


@console_page("console:owners-console")
def owners_console(request):
    """منصّةُ الملّاك: اختيارُ العروض في المزاد المنتهي الأخير."""
    # المزادُ المطلوبُ إن سُمِّي وكان منتهياً، وإلّا فالأخير. ومن كتب رقماً
    # لمزادٍ جارٍ أو ملغىً يُردُّ إلى الأخير لا إلى شاشةٍ فارغة: الشاشةُ
    # تعرض ما انتهى، ورقمٌ خطأٌ في الرابط لا يجوز أن يقرأ «لا مركبات».
    chosen = (request.GET.get("auction") or "").strip()
    auction = None
    if chosen.isdigit():
        auction = Auction.objects.filter(
            pk=int(chosen), state__in=sorted(PHASE_AUCTION_STATES[Phase.ENDED])
        ).first()
    auction = auction or latest_ended()
    seen = shown_to(request.user)

    if auction is None:
        return render(
            request,
            "console/owners_console.html",
            {
                "auction": None,
                "decisions": DECISIONS,
                "marketing_choices": MARKETING,
                "auctions": [],
            },
        )

    text = request.GET.get("q", "")
    decision = request.GET.get("decision", "")
    marketing = request.GET.get("marketing", "")
    price_from = _amount(request.GET.get("from", ""))
    price_to = _amount(request.GET.get("to", ""))

    rows = offer_rows(
        auction,
        text=text,
        price_from=price_from,
        price_to=price_to,
        decision=decision,
        marketing=marketing,
    )

    if wants_export(request):
        # الورقةُ **هي** ما على الشاشة: المرشّحُ نفسُه، والترتيبُ نفسُه،
        # والحارسُ نفسُه — وذلك بحكم البناء لا بوعدٍ في تعليق، فالصفوفُ من
        # `rows` عينِها.
        listed = list(rows)
        dress(listed, auction=auction, seen=seen)
        return export_table(
            listed,
            name=f"اختيار-العروض-مزاد-{auction.number}",
            columns=columns_for(
                [
                    ("الموقف", lambda v: v.lot_number, None),
                    ("المركبة", lambda v: v.display_title, None),
                    ("سنة الصنع", lambda v: v.year, None),
                    ("رقم اللوحة", lambda v: v.plate_number, None),
                    ("رقم المطالبة", lambda v: v.claim_number, None),
                    ("تسويقيّة", lambda v: v.is_marketing, None),
                    ("أعلى عرض", lambda v: v.offer, MONEY),
                    ("شامل الضريبة والرسم", lambda v: v.with_tax, MONEY),
                    ("أعلى مزايد", lambda v: v.buyer_name, CUSTOMER),
                    ("رقم الجوال", lambda v: v.buyer_phone, CUSTOMER),
                    ("المزايدون", lambda v: v.bidders, None),
                    ("متعادلون", lambda v: v.tied if v.tied > 1 else "", None),
                    ("القرار", lambda v: dict(DECISIONS).get(v.decision, ""), None),
                    ("الحالة", lambda v: v.get_state_display(), None),
                    ("الفاتورة", lambda v: v.invoice.number if v.invoice else "", None),
                ],
                seen,
            ),
        )

    page = paged(request, rows)
    dress(page.object_list, auction=auction, seen=seen)
    with_tones(page.object_list)

    counts = totals(rows)
    return render(
        request,
        "console/owners_console.html",
        {
            "auction": auction,
            "page": page,
            "pager": pager(request, page, "مركبة"),
            "counts": counts,
            "q": text,
            "auctions": ended_choices(),
            "chosen": str(auction.pk),
            "decision": decision,
            "marketing": marketing,
            "price_from": request.GET.get("from", ""),
            "price_to": request.GET.get("to", ""),
            "decisions": DECISIONS,
            "marketing_choices": MARKETING,
            # المرشّحاتُ كما هي، ليعود إليها بعد كلّ حكم: المالكُ يحكم على
            # أربعين مركبةً في مزادٍ واحد، وعودةٌ إلى الصفحة عاريةً تعني بحثاً
            # جديداً بعد كلّ واحدة.
            "filters": urlencode(
                {
                    "auction": auction.pk,
                    "q": text,
                    "decision": decision,
                    "marketing": marketing,
                    "from": request.GET.get("from", ""),
                    "to": request.GET.get("to", ""),
                    "page": request.GET.get("page", ""),
                }
            ),
            "show_money": seen.money,
            "show_customer": seen.customer,
            "can_invoice": can(request.user, Capability.MONEY_ACT),
            "can_notify": can(request.user, Capability.NOTIFICATIONS_SEND),
            "icon_yes": path_of("check"),
            "icon_no": path_of("ban"),
            "icon_offers": path_of("eye"),
            "icon_camera": path_of("camera"),
        },
    )
