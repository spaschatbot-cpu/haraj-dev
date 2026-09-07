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

    # التواريخ أوّلاً: النقلة إلى `live` تفحص أن وقت البدء حلّ، فكتابةُ الموعد
    # **بعدها** تجعل النقلة تُرفض بموعدٍ قديم ثم يُكتب الجديد — فتبقى الحالة
    # على ما كانت والموظّف يقرأ نجاحاً.
    if badge in ("soon", "active"):
        problem = _read_window(request, auction)
        if problem:
            messages.error(request, problem)
            return _back(request, auction)

    try:
        with transaction.atomic():
            if badge in Showcase.values:
                auction.showcase = badge
                auction.save(update_fields=["showcase", "starts_at", "ends_at"])
                if auction.state == AuctionState.DRAFT:
                    # مسودّةٌ عليها لافتةُ عرضٍ ليست معروضةً على أحد: الجدولة
                    # هي ما يُخرجها من المسودّة، واللافتة تقول كيف تظهر بعدها.
                    auction_services.move_auction(auction, AuctionState.SCHEDULED)
            elif badge == "active":
                auction.save(update_fields=["starts_at", "ends_at"])
                _mover(auction, AuctionState.LIVE)(reason)
            elif badge == "ended":
                _mover(auction, AuctionState.ENDED)(reason)
            else:
                messages.error(request, "حالة غير معروفة.")
                return _back(request, auction)
    except IntegrityError:
        messages.error(request, "وقت النهاية يجب أن يكون بعد وقت البداية.")
        return _back(request, auction)
    except Exception as refusal:  # noqa: BLE001
        # جملةُ الآلة كما هي: هي تفرّق بين «لا نقلة» و«ليست جاهزة بعد»،
        # وإعادةُ صياغتها هنا تُفقد التفريق.
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
