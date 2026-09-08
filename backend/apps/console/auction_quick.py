"""العمليّات السريعة على صفّ المزاد: اللافتة، والجدولة، والرسوم، والإنهاء. T846.

المالك طلب ثلاث نوافذَ منبثقة على الصفّ نفسه، وسببُ طلبه ظاهر: تغييرُ موعدٍ
اليوم يعني فتحَ الصفّ، ثم شاشة التعديل، ثم العودة إلى القائمة لتغيير الحالة.
ثلاثُ صفحاتٍ لفعلٍ واحد.

**ولماذا ملفٌّ خاصّ لا دوالُّ في `auctions.py`:** نطاق
`ops/checks/one_eligibility_gate.py` هو «كلُّ وحدةٍ تستورد من `apps.bidding`»،
وهذا الملفّ يستورد `Bid` ليمسح مزايدات ما لم يُبَع. و`auctions.py` يرسم
القوائم ولا يكلّم المزايدة — وهو الفصل نفسه الذي وُجد لأجله `auction_moves.py`.

ما لا يُنقَل عن v1، ولماذا
==========================
* **نسبة الضريبة عموداً على المزاد.** الطلب يذكر `vat_type` حقلاً يُحرَّر لكل
  مزاد، وv1 يخزّنه فعلاً — ووجدناه في النسخة مكتوباً بصيغتين مختلفتين في
  الصفوف القديمة والحديثة، وهما النسبة نفسها. ونسبةٌ لكلّ مزاد تعني أن
  فاتورتين في اليوم نفسه تُحسبان بنسبتين، وأن تصحيحَ نسبةٍ غداً يحتاج تعديل
  ستّةٍ وخمسين صفّاً — وأن `tax_of` تصير لها مصادر بعدد المزادات.

  فالنسبة تبقى قاعدةً واحدة في `apps.money`، ولا تُقرأ هنا أصلاً: حاولتُ
  عرضَها في النافذة للاطّلاع، فأرسبني `one_tax_rule` — ووصفُه يقول لماذا
  بحقّ: «للنسبة قارئٌ واحد، ومن أراد مبلغاً يسأل `tax_of`». وشاشةُ الرسوم
  لا تريد مبلغاً، فبقيت جملةٌ تقول إن النسبة قاعدةٌ واحدة، بلا رقم.
  وهذا قرارٌ يخصّ مالك مسار «أ»، ومكتوبٌ هنا ليُنقَض بعلمٍ لا بسهو.

* **حذف المزاد.** الطلب يريد زرَّ حذفٍ بفحصٍ أمنيّ يمنع الحذف إن كانت هناك
  فواتير. والحذفُ هنا **مستحيلٌ في القاعدة** لا ممنوعٌ في الشيفرة:
  `Vehicle.auction` و`Hold.auction` كلاهما `on_delete=PROTECT`، فمزادٌ تحته
  سيارةٌ أو تأمينٌ لا يُحذف ولو أذن الكود. والبديلُ الصحيح موجود: الإلغاء يفكّ
  الحجوز ويُبطل الفواتير غير المدفوعة **ثم** ينقل الحالة — وهو ما لا يفعله
  حذفُ صفّ، ولا يفعله فحصٌ يقول «لا يمكن الحذف» ثم يترك المال محجوزاً.
  فزرُّ الحذف هنا هو زرّ الإلغاء، ومكانُه صفحةُ المزاد حيث النقلات كلّها.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from apps.auctions import engine
from apps.auctions import services as auction_services
from apps.auctions.models import Auction, Showcase
from apps.auctions.states import AuctionState
from apps.core import audit

from .auction_moves import _mover
from .forms import DisplayDateTimeField
from .views import console_page

#: إلى أين يعود الموظّف بعد الحفظ. اسمُ مسارٍ من قائمةٍ مغلقة لا قيمةٌ من
#: الطلب: `redirect(request.POST["back"])` بابٌ مفتوح لإعادة توجيهٍ إلى أي
#: عنوان، ونافذةٌ منبثقة لا تستحقّ ثغرة.
RETURN_TO = {
    "list": "console:auctions",
    "detail": "console:auction-detail",
}


#: ما يُقال حين تنقص المزادَ نافذتُه الزمنية — ويدلّ على مالكها لا على نفسه.
_NEEDS_WINDOW = (
    "هذه الحالة تحتاج موعد بداية ونهاية، والمزاد بلا موعد. "
    "اضبطه أوّلاً من «إعادة الجدولة» ثم أعد المحاولة."
)

#: ونافذةٌ مقلوبة تُقال بالكلمات نفسها، وتُصلَّح في المكان نفسه.
_BAD_WINDOW = (
    "وقت النهاية يجب أن يكون بعد وقت البداية — صحّحه من «إعادة الجدولة»."
)


def _back(request, auction: Auction):
    where = RETURN_TO.get(request.POST.get("back", ""), "console:auctions")
    if where == "console:auction-detail":
        return redirect(where, pk=auction.pk)
    return redirect(where)


#: ساعةُ الرياض إلى UTC — **الحقلُ نفسه** الذي تستعمله استمارةُ تعديل المزاد.
#:
#: نسخةٌ ثانية من التحويل هنا كانت ستنتج مزاداً يبدأ متأخّراً ثلاث ساعات، وهو
#: عطلٌ لا يكشفه اختبار: من كتب التحويل الخاطئ يكتب الاختبار به فيقرأ ما كتب.
_CLOCK = DisplayDateTimeField()


def _moment(text: str):
    return _CLOCK.clean(text)


def _reason(request) -> str:
    return (request.POST.get("reason") or "").strip()


def _read_window(request, auction: Auction) -> str | None:
    """اقرأ الموعدين من الطلب إلى الكائن، أو أعِد سببَ الرفض نصّاً.

    التحويل من توقيت الرياض إلى UTC يمرّ بـ`apps.core.time` وحدها (المادة
    ٣-١). وكلُّ من كتب تحويلاً ثانياً بيده أنتج مزاداً يبدأ متأخّراً ثلاث
    ساعات عن موعده المعلن — وهو عطلٌ لا يظهر في اختبار، لأن الاختبار يكتب
    ويقرأ بالتحويل الخاطئ نفسه.
    """
    starts = (request.POST.get("starts_at") or "").strip()
    ends = (request.POST.get("ends_at") or "").strip()
    if not starts or not ends:
        return "هذه الحالة تحتاج وقت بداية ووقت نهاية."

    try:
        auction.starts_at = _moment(starts)
        auction.ends_at = _moment(ends)
    except ValidationError:
        return "صيغة التاريخ غير مفهومة."

    # السؤالُ يُوجَّه إلى المحرّك: القيد `auction_ends_after_it_starts` هو
    # الضمانة، وهذه قراءتُه قبل الحفظ ليقرأ الموظّف جملةً بدل صفحة خطأ ٥٠٠.
    if not engine.window_is_valid(auction):
        return "وقت النهاية يجب أن يكون بعد وقت البداية."
    return None


@console_page("console:auction-showcase")
def auction_showcase(request, pk: int):
    """غيّر لافتة المزاد أو حالته من القائمة — نافذةُ «تغيير الحالة».

    **واللافتة غيرُ الحالة**، وهذا الفرق هو ما يجعل النافذة آمنة: «لاحقاً»
    و«قادم» و«قريباً» ثلاثُ طرقِ عرضٍ لمزادٍ مجدولٍ واحد، فتغييرُها كتابةٌ في
    `showcase` لا نقلةٌ في آلة الحالات — ولا توقظ تسويةً ولا بوّابة. و«نشط»
    و«منتهٍ» **نقلتان**، فتمرّان بـ`_mover` — الكاتب نفسه الذي يستعمله زرّ
    صفحة المزاد، فلا يوجد بابان إلى الحالة.
    """
    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    badge = request.POST.get("badge", "")
    reason = _reason(request)
    if not reason:
        messages.error(request, "سبب التغيير مطلوب.")
        return _back(request, auction)

    fields = ["state", "showcase", "starts_at", "ends_at"]
    before = audit.snapshot(auction, fields)
    old_badge = engine.badge_of(auction)
    now = timezone.now()

    # **ولا موعدَ يُقرأ من الطلب.** كانت هذه النافذة تقبل `starts_at` و
    # `ends_at`، فصار للساعة كاتبان على الشاشة الواحدة — هذه و«إعادة
    # الجدولة» — بقاعدتين مختلفتين: تلك تتحقّق من النافذة وتمسح مزايدات ما
    # لم يُبَع إن طُلب، وهذه كانت تكتب التاريخ نفسه بلا شيء من ذلك.
    #
    # فالساعةُ تُقرأ هنا ولا تُكتب: ما تحتاجه الحالةُ من موعدٍ يجب أن يكون
    # مضبوطاً **قبل** فتح هذه النافذة، ومزادٌ ينقصه موعدٌ يُرَدُّ برسالةٍ
    # تدلّ على النافذة التي تملكه. T859
    #
    # ويبقى استثناءان، وكلاهما **اشتقاقٌ لا إدخال**: «نشط» بلا بدايةٍ يبدأ
    # الآن، و«منتهٍ» ينتهي الآن. لا يكتبهما الموظّف بيده، بل يلزمان من معنى
    # النقلة نفسها — ومزادٌ «نشط» بلا وقت بدءٍ ليس حالةً يمكن تمثيلها.
    if badge == "later":
        # لاحقاً: إخفاء المزاد عن العملاء
        pass
    elif badge == "upcoming":
        # قادم: يُعلَن بلا عدّاد، فلا يشترط موعداً.
        pass
    elif badge == "soon":
        if auction.starts_at is None or auction.ends_at is None:
            messages.error(request, _NEEDS_WINDOW)
            return _back(request, auction)
        if not engine.window_is_valid(auction):
            messages.error(request, _BAD_WINDOW)
            return _back(request, auction)
        # ساعةُ المزاد تُقرأ من المحرّك وحده (`one_auction_clock`): «قريباً»
        # تشترط أن يكون وقتُ البدء لم يحن بعد.
        if engine.has_started(auction, now=now):
            messages.error(
                request,
                'حالة "قريباً" تتطلب وقت بداية في المستقبل — '
                "غيّره من «إعادة الجدولة».",
            )
            return _back(request, auction)
    elif badge == "active":
        if auction.ends_at is None:
            messages.error(request, _NEEDS_WINDOW)
            return _back(request, auction)
        if auction.starts_at is None:
            auction.starts_at = now
        if not engine.window_is_valid(auction):
            messages.error(request, _BAD_WINDOW)
            return _back(request, auction)
    elif badge == "ended":
        # القراءةُ من المحرّك (`one_auction_clock`): «منتهٍ» يُثبِّت النهاية
        # على الآن إن غابت أو كانت ما زالت في المستقبل.
        if auction.ends_at is None or not engine.has_finished(auction, now=now):
            auction.ends_at = now

    try:
        with transaction.atomic():
            if badge in Showcase.values:
                auction.showcase = badge
                auction.save(update_fields=["showcase", "starts_at", "ends_at"])
                if auction.state == AuctionState.DRAFT:
                    auction_services.move_auction(auction, AuctionState.SCHEDULED)
                auction_services.cascade_auction_vehicles(auction, str(old_badge), badge)
            elif badge == "active":
                auction.save(update_fields=["starts_at", "ends_at"])
                if auction.state == AuctionState.DRAFT:
                    auction_services.move_auction(auction, AuctionState.SCHEDULED)
                _mover(auction, AuctionState.LIVE)(reason)
                auction_services.cascade_auction_vehicles(
                    auction, str(old_badge), "active"
                )
            elif badge == "ended":
                auction.save(update_fields=["ends_at"])
                _mover(auction, AuctionState.ENDED)(reason)
                auction_services.cascade_auction_vehicles(
                    auction, str(old_badge), "ended"
                )
            else:
                messages.error(request, "حالة غير معروفة.")
                return _back(request, auction)
    except IntegrityError:
        messages.error(request, "وقت النهاية يجب أن يكون بعد وقت البداية.")
        return _back(request, auction)
    except Exception as refusal:  # noqa: BLE001
        messages.error(request, str(refusal))
        return _back(request, auction)

    auction.refresh_from_db()
    audit.record(
        action="console.auction_showcase",
        entity=auction,
        actor=request.user,
        before=before,
        after=audit.snapshot(auction, fields),
        note=reason,
    )
    messages.success(request, f"مزاد {auction.number}: حُدِّثت حالته.")
    return _back(request, auction)


@console_page("console:auction-reschedule")
def auction_reschedule(request, pk: int):
    """موعدٌ جديد، وتذكيرٌ اختياري، وإعادةُ مزايدةِ ما لم يُبَع.

    **والمباعُ لا يُمَسّ.** المفتاح يمسح مزايدات المركبات التي لا فائز لها
    وحدها؛ ومركبةٌ رست على مشترٍ لها فاتورةٌ وتأمينٌ يشيران إلى مزايدةٍ بعينها،
    وحذفُ تلك المزايدة يترك الفاتورة تشير إلى رقمٍ لا أصل له.

    و«لم يُبَع» هو `awarded_to__isnull=True` لا حالةُ المركبة: مركبةٌ
    `rejected` لا فائز لها فتُمسح مزايداتُها بحقّ، ومركبةٌ `invoiced` لها
    فائزٌ فتنجو ولو تغيّرت حالتُها لاحقاً. والشرطُ على الحقل الذي يمسك المال.
    """
    from apps.bidding.models import Bid

    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    reason = _reason(request)
    if not reason:
        messages.error(request, "سبب إعادة الجدولة مطلوب.")
        return _back(request, auction)

    problem = _read_window(request, auction)
    if problem:
        messages.error(request, problem)
        return _back(request, auction)

    reminder = (request.POST.get("sms_reminder_at") or "").strip()
    try:
        auction.sms_reminder_at = _moment(reminder) if reminder else None
    except ValidationError:
        messages.error(request, "صيغة موعد التذكير غير مفهومة.")
        return _back(request, auction)

    fields = ["starts_at", "ends_at", "sms_reminder_at"]
    before = audit.snapshot(auction, fields)
    reset = request.POST.get("reset_unsold_bids") == "on"
    cleared = 0

    try:
        with transaction.atomic():
            auction.save(update_fields=fields)
            if reset:
                doomed = Bid.objects.filter(
                    vehicle__auction=auction, vehicle__awarded_to__isnull=True
                )
                cleared = doomed.count()
                doomed.delete()
    except IntegrityError:
        messages.error(request, "وقت النهاية يجب أن يكون بعد وقت البداية.")
        return _back(request, auction)

    audit.record(
        action="console.auction_reschedule",
        entity=auction,
        actor=request.user,
        before=before,
        after=audit.snapshot(auction, fields),
        note=f"{reason} · مزايدات محذوفة: {cleared}",
    )
    messages.success(
        request,
        f"أُعيدت جدولة مزاد {auction.number}."
        + (f" وحُذفت {cleared} مزايدة لمركبات لم تُبَع." if reset else ""),
    )
    return _back(request, auction)


@console_page("console:auction-fees")
def auction_fees(request, pk: int):
    """الرسوم الإدارية ومبلغ التأمين — والضريبةُ تُعرض ولا تُكتب.

    والحقلان مختلفان لا مترادفان: التأمين مبلغٌ **يُحجَز ويُردّ**، والرسم
    مبلغٌ **يُدفَع ولا يُردّ**. ودمجُهما في عمودٍ واحد هو ما جعل ردَّ تأمينٍ
    في v1 يردّ الرسم معه.
    """
    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    reason = _reason(request)
    if not reason:
        messages.error(request, "سبب التعديل مطلوب.")
        return _back(request, auction)

    fields = ["deposit_required", "admin_fee"]
    before = audit.snapshot(auction, fields)

    try:
        # `Decimal` من النصّ مباشرةً لا عبر `float`: المادة ٣-٢، والمال لا
        # يمرّ بعائمٍ ولو في خطوةٍ واحدة.
        deposit = Decimal((request.POST.get("deposit_required") or "").strip())
        fee = Decimal((request.POST.get("admin_fee") or "").strip())
    except (InvalidOperation, TypeError):
        messages.error(request, "المبالغ يجب أن تكون أرقاماً.")
        return _back(request, auction)

    if deposit < 0 or fee < 0:
        messages.error(request, "لا مبلغ بالسالب.")
        return _back(request, auction)

    auction.deposit_required = deposit
    auction.admin_fee = fee
    auction.save(update_fields=fields)

    audit.record(
        action="console.auction_fees",
        entity=auction,
        actor=request.user,
        before=before,
        after=audit.snapshot(auction, fields),
        note=reason,
    )
    messages.success(request, f"حُدِّثت رسوم مزاد {auction.number} وتأمينه.")
    return _back(request, auction)


@console_page("console:auction-end-now")
def auction_end_now(request, pk: int):
    """أنهِ المزاد الآن — والنهايةُ تُثبَّت على هذه اللحظة.

    وتثبيتُ ``ends_at`` ليس تجميلاً: آلةُ الحالات تشترط بلوغَ وقت النهاية
    (`_auction_end_time_reached`)، فإنهاءٌ مبكّرٌ بلا تثبيتٍ يُرفَض بـ«المزاد
    لم ينته بعد» — فيقرأ الموظّف رفضاً على زرٍّ اسمُه «إنهاء فوري».

    والتسويةُ بعده ليست هنا: `_mover` يوجّه `ended → settled` إلى
    `settlement.close_auction`، وهذا الزرّ ينهي المزايدة فقط. فصلُهما مقصود —
    إنهاءُ المزايدة قرارُ توقيت، والتسويةُ حركةُ مال.
    """
    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    reason = _reason(request)
    if not reason:
        messages.error(request, "سبب الإنهاء الفوري مطلوب.")
        return _back(request, auction)

    fields = ["state", "ends_at"]
    before = audit.snapshot(auction, fields)
    now = timezone.now()

    try:
        with transaction.atomic():
            if not engine.has_finished(auction, now=now):
                auction.ends_at = now
                auction.save(update_fields=["ends_at"])
            _mover(auction, AuctionState.ENDED)(reason)
    except Exception as refusal:  # noqa: BLE001
        messages.error(request, str(refusal))
        return _back(request, auction)

    auction.refresh_from_db()
    audit.record(
        action="console.auction_end_now",
        entity=auction,
        actor=request.user,
        before=before,
        after=audit.snapshot(auction, fields),
        note=reason,
    )
    messages.success(
        request,
        f"أُنهي مزاد {auction.number}. التسوية تفكّ التأمينات وتُصدر الفواتير.",
    )
    return _back(request, auction)


@console_page("console:auction-delete")
def auction_delete(request, pk: int):
    """احذف مزاداً **فارغاً** — أو قُل لماذا لا يُحذف، بالأرقام.

    الحذفُ ممكنٌ ومستحيلٌ معاً، والفرقُ هو ما تقوله هذه الشاشة:

    * **مزادٌ فارغ** — مسودّةٌ أُنشئت بالخطأ، أو نسخةٌ مكرّرة — يُحذف. ولا شيء
      يشير إليه فلا شيء يُكسَر.
    * **مزادٌ تحته سيارةٌ أو تأمين** لا يُحذف، ولا في القاعدة أصلاً:
      ``Vehicle.auction`` و``Hold.auction`` و``PaymentSheet.auction`` كلُّها
      ``PROTECT``. فلو أذن الكودُ رفضت القاعدة.

    **والرفضُ يقول العدد.** «لا يمكن الحذف» جملةٌ تُنتج تذكرة دعم؛ و«تحته ٧
    سيارات و٣ تأمينات محجوزة» جملةٌ يتصرّف بها الموظّف. وv1 يرفض بلا عدد.

    **والبديلُ يُقال في الرسالة نفسها:** الإلغاء. وهو ليس حذفاً ألطف — هو
    الفعلُ الصحيح: يفكّ الحجوز ويُبطل الفواتير غير المدفوعة **ثم** ينقل
    الحالة، ويترك صفّاً يُسأل عنه: من ألغاه ومتى ولماذا.
    """
    from apps.money.models import Hold, HoldState

    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    reason = _reason(request)
    if not reason:
        messages.error(request, "سبب الحذف مطلوب.")
        return _back(request, auction)

    cars = auction.vehicles.count()
    holds = Hold.objects.filter(auction=auction, state=HoldState.ACTIVE).count()

    if cars or holds:
        blocking = " و".join(
            part
            for part in (
                f"{cars} سيارة" if cars else "",
                f"{holds} تأميناً محجوزاً" if holds else "",
            )
            if part
        )
        messages.error(
            request,
            f"لا يُحذف مزاد {auction.number}: تحته {blocking}. "
            "والإلغاء هو ما يفكّ التأمينات ويُبطل الفواتير غير المدفوعة — "
            "من نافذة «تغيير الحالة».",
        )
        return _back(request, auction)

    number, title, pk_gone = auction.number, auction.title, auction.pk
    before = audit.snapshot(auction, ["number", "title", "state", "starts_at"])

    try:
        # الحذفُ والسجلُّ في معاملةٍ واحدة. وقعا خارجَها أوّلَ تشغيل، فسقط
        # السجلُّ بعد نجاح الحذف — ومزادٌ اختفى بلا سطرٍ يقول من محاه هو
        # بالضبط ما لا يُحتمل في فعلٍ لا يُعكَس.
        with transaction.atomic():
            auction.delete()
            # `entity_type`/`entity_id` لا `entity`: الصفُّ لم يعد موجوداً،
            # و`record` يشترط أحدهما — وهو ما ينصّ عليه وصفُها حرفياً.
            audit.record(
                action="console.auction_delete",
                entity_type="auctions.auction",
                entity_id=pk_gone,
                actor=request.user,
                before=before,
                after={},
                note=f"حُذف مزاد {number} «{title}» — {reason}",
            )
    except ProtectedError as guarded:
        # القاعدةُ هي الضمانة لا العدُّ أعلاه: صفٌّ يُنشَأ بين العدِّ والحذف
        # يمرّ من الفحص ويصطدم هنا. والرسالةُ تُقال ولا تُبتلَع.
        messages.error(request, f"القاعدة رفضت حذف المزاد: {guarded}")
        return _back(request, auction)
    messages.success(request, f"حُذف مزاد {number} «{title}».")
    return redirect("console:auctions")
