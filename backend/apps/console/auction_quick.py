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
from .forms import DisplayDateTimeField, row_stamp_of
from .views import atomic_write, console_page, row_for_write

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


#: أعمدةُ ختم HR-13 لكل نافذة — **بالضبط ما تكتبه**، لا أوسع ولا أضيق.
#:
#: كان الختمُ على نافذة «التعديل» وحدها من خمس: `grep -n row_stamp
#: templates/console/*.html` أعطى سطرين، كلاهما نافذةُ التعديل. فالرسومُ
#: والجدولةُ والحالةُ والإنهاء تكتب بلا ختم — وأسوأُها **الرسوم**، وهي التي
#: تكتب التأمين والرسم: موظّفان يفتحان الصفّ بدقائقَ بينهما فيمحو الثاني
#: تأمينَ الأوّل بلا سطرٍ يقول ذلك.
#:
#: والقسمةُ بعمودٍ عمود لا بختمٍ واحدٍ للصفّ: ختمٌ واحدٌ واسعٌ يرفض تعديلَ
#: الرسوم لأن زميلاً غيّر الموعد من نافذةٍ أخرى — وذلك رفضٌ لكتابةٍ لا تدهس
#: أحداً، وهو ما يعلّم الموظّف أن يتجاهل الرفض. (القاعدةُ نفسُها مكتوبةٌ في
#: `ReasonMixin.__init__`: «لا أوسع فيزعج، ولا أضيق فيفوته ما يحرسه».)
STAMP_FIELDS = {
    "showcase": ("state", "showcase", "starts_at", "ends_at"),
    "reschedule": ("starts_at", "ends_at", "sms_reminder_at"),
    "fees": ("deposit_required", "admin_fee"),
    "end_now": ("state", "ends_at"),
}

#: ما يُقال لمن وصل ثانياً — **فعلاً يُفعَل لا تشخيصاً تقنياً**.
#:
#: «تعارضٌ في النسخة» جملةٌ تُنتج تذكرةَ دعم؛ وهذه تقول ما جرى وما يُفعل.
#: والموظّفُ يعود إلى القائمة بعد الرفض، والنافذةُ تُملأ من الصفّ ساعةَ
#: تُفتح — ففتحُها ثانيةً يريه القيمةَ الجديدة بلا أن نطبعها في الرسالة.
_STALE = (
    "عُدِّل الصفُّ من نافذةٍ أخرى بعد أن فتحتَ هذه — "
    "أعِد الفتح وطبّق تعديلك على القيمة الجديدة. "
    "الحفظ الآن يمحو عمل غيرك بلا أن يعلم."
)


def _stale(request, auction: Auction, window: str) -> bool:
    """هل كُتب في هذه الأعمدة بعد أن رُسمت النافذة؟

    يُنادى **بعد** `row_for_write`، أي والصفُّ مقفولٌ ومقروءٌ من القاعدة:
    الختمُ يغلق النافذةَ الواسعة (دقائقُ بين فتح الشاشة والحفظ)، والقفلُ
    يغلق الضيّقة (طلبان في العشرات نفسِها من الميلي‑ثانية يقرآن الصفَّ
    فيتطابق ختماهما معاً). وأحدُهما بلا الآخر حارسٌ نصفُه مفتوح.

    والختمُ الفارغ يمرّ — نافذةٌ في صفحةٍ قديمةٍ من ذاكرة المتصفّح لا تحمله،
    وذلك عقدُ `ReasonMixin` نفسُه (`if expected and …`). وهذا ثمنُ التوافق
    مع صفحةٍ رُسمت قبل النشر، ويُدفَع مرّةً واحدة.
    """
    sent = (request.POST.get("row_stamp") or "").strip()
    if not sent:
        return False
    return sent != row_stamp_of(auction, STAMP_FIELDS[window])


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
@atomic_write
def auction_showcase(request, pk: int):
    """غيّر لافتة المزاد أو حالته من القائمة — نافذةُ «تغيير الحالة».

    **واللافتة غيرُ الحالة**: «لاحقاً» و«قادم» و«قريباً» ثلاثُ طرقِ عرضٍ لمزادٍ
    مجدولٍ واحد، فتغييرُها كتابةٌ في `showcase`. و«نشط» و«منتهٍ» **نقلتان**،
    فتمرّان بـ`_mover` — الكاتب نفسه الذي يستعمله زرّ صفحة المزاد، فلا يوجد
    بابان إلى الحالة.

    **ولافتةٌ على مسودّة تجدولها أيضاً**، وهذا ليس تفصيلاً: مزادٌ `draft` يمرّ
    بـ`move_auction(SCHEDULED)` في الفرع نفسِه، فيخضع لحرّاسها — ومزادٌ بلا
    مركبات يُرَدّ بـ«لا يمكن جدولة مزاد بلا مركبات» ولا تُكتب لافتتُه (قِيس على
    مزاد ٩٨٦٨ في ١٤ سبتمبر ٢٠٢٦). وكان مكتوباً هنا أن تغيير اللافتة «لا نقلةٌ
    في آلة الحالات» على إطلاقه — وهو صحيحٌ لمزادٍ مجدولٍ وحده.
    """
    auction = row_for_write(request, Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    if _stale(request, auction, "showcase"):
        messages.error(request, _STALE)
        return _back(request, auction)

    badge = request.POST.get("badge", "")
    reason = _reason(request)

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
@atomic_write
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

    auction = row_for_write(request, Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    # قبل `_read_window`: تلك تكتب الموعدين على الكائن، فيصير الختمُ بعدها
    # مبصوماً على ما أراده المرسِل لا على ما في القاعدة — وهو بعينه ما يحذّر
    # منه `ReasonMixin.clean` («`_post_clean` يكون قد كتب قيم الإرسال…»).
    if _stale(request, auction, "reschedule"):
        messages.error(request, _STALE)
        return _back(request, auction)

    reason = _reason(request)

    # **و`before` تُلتقط هنا، قبل `_read_window`، للعلّة نفسِها.** كانت تُلتقط
    # بعدها — و`_read_window` تكتب الموعدين على الكائن — فيُبصَم «قبلُ» على ما
    # أرسله الموظّف لا على ما في القاعدة. والأثرُ مقيسٌ في `haraj2_t307`:
    # القيدان ٤٨ و٦١ من `console.auction_reschedule` **`before` فيهما يساوي
    # `after` حرفاً بحرف** — أي أن السجلَّ يقول إن شيئاً لم يتغيّر بينما تغيّر
    # الموعد. وقيدٌ لا يقول القيمةَ السابقة قيدٌ لا يُسأل.
    fields = ["starts_at", "ends_at", "sms_reminder_at"]
    before = audit.snapshot(auction, fields)

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
@atomic_write
def auction_fees(request, pk: int):
    """الرسوم الإدارية ومبلغ التأمين — والضريبةُ تُعرض ولا تُكتب.

    والحقلان مختلفان لا مترادفان: التأمين مبلغٌ **يُحجَز ويُردّ**، والرسم
    مبلغٌ **يُدفَع ولا يُردّ**. ودمجُهما في عمودٍ واحد هو ما جعل ردَّ تأمينٍ
    في v1 يردّ الرسم معه.

    **وهذه أولى النوافذ بالختم**، وحكمُ المالك فيها بالحرف: «مسارُ رفضٍ يراه
    الموظّف أرخصُ من كتابةٍ تدهس أخرى بلا أثر، ونافذةُ الرسوم تكتب التأمينَ
    والرسم». وكانت تقرأ المبلغين من ``POST`` بيدها — فلا `Form` ولا
    `ReasonMixin` ولا ختم — فيمحو الثاني تأمينَ الأوّل ولا يبقى إلا قيدان
    متتاليان لا يقول أيٌّ منهما إن الأوّل دُهس.
    """
    auction = row_for_write(request, Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    if _stale(request, auction, "fees"):
        messages.error(request, _STALE)
        return _back(request, auction)

    reason = _reason(request)

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
@atomic_write
def auction_end_now(request, pk: int):
    """أنهِ المزاد الآن — والنهايةُ تُثبَّت على هذه اللحظة.

    وتثبيتُ ``ends_at`` ليس تجميلاً: آلةُ الحالات تشترط بلوغَ وقت النهاية
    (`_auction_end_time_reached`)، فإنهاءٌ مبكّرٌ بلا تثبيتٍ يُرفَض بـ«المزاد
    لم ينته بعد» — فيقرأ الموظّف رفضاً على زرٍّ اسمُه «إنهاء فوري».

    والتسويةُ بعده ليست هنا: `_mover` يوجّه `ended → settled` إلى
    `settlement.close_auction`، وهذا الزرّ ينهي المزايدة فقط. فصلُهما مقصود —
    إنهاءُ المزايدة قرارُ توقيت، والتسويةُ حركةُ مال.
    """
    auction = row_for_write(request, Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    if _stale(request, auction, "end_now"):
        messages.error(request, _STALE)
        return _back(request, auction)

    reason = _reason(request)

    fields = ["state", "ends_at"]
    before = audit.snapshot(auction, fields)
    now = timezone.now()

    # **مزادٌ لم يبدأ بعد لا يُنهى الآن**، ويُقال ذلك بجملة.
    #
    # التثبيتُ أدناه يكتب `ends_at = now`؛ ومزادٌ بدايتُه في المستقبل يجعل
    # النهايةَ قبل البداية، فيرفضه قيدُ `auction_ends_after_it_starts` في
    # القاعدة. وكان `except Exception` وحده تحته، فيخرج نصُّ الخطأ الخام إلى
    # الموظّف: «new row for relation "auctions_auction" violates check
    # constraint "auction_ends_after_it_starts"» — قِيس على مزاد ٩٨٦٨ في
    # ١٤ سبتمبر ٢٠٢٦. ونافذةُ «تغيير الحالة» تُعالج الحالةَ نفسَها وتقول
    # `_BAD_WINDOW`، فكان لفعلٍ واحدٍ رسالتان وأسوأُهما على أوضح زرّ.
    #
    # والفحصُ قبل الكتابة لا `IntegrityError` بعدها: `IntegrityError` داخل
    # معاملةٍ تُسمّمها، وهو ما يجعل الإمساك بها هنا أثقل من منعها.
    if auction.starts_at is not None and auction.starts_at > now:
        messages.error(
            request,
            f"مزاد {auction.number} لم يبدأ بعد — يبدأ "
            f"{_CLOCK.prepare_value(auction.starts_at):%Y-%m-%d %H:%M} بتوقيت الرياض. "
            "لا يُنهى الآن: أعِد جدولته أو ألغِه من «تغيير الحالة».",
        )
        return _back(request, auction)

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
    * **مزادٌ تحته سيارةٌ أو تأمين أو نيّةُ دفع** لا يُحذف، ولا في القاعدة
      أصلاً: ``Vehicle.auction`` و``Hold.auction`` و``PaymentIntent.auction``
      ثلاثتُها ``PROTECT``. فلو أذن الكودُ رفضت القاعدة.

      وكان مكتوباً هنا ``PaymentSheet.auction`` — **و``PaymentSheet`` بلا حقل
      مزادٍ أصلاً**؛ الثالثُ هو ``PaymentIntent``. فُحص في القاعدة: مفاتيحُ
      `auctions_auction` الواردة ثلاثةٌ، من `auctions_vehicle` و`money_hold`
      و`money_paymentintent`. واسمٌ خاطئٌ في وصفٍ يُقرأ بدل الشيفرة هو كيف
      يسقط عدٌّ ناقصٌ من المراجعة.

    **والرفضُ يقول العدد.** «لا يمكن الحذف» جملةٌ تُنتج تذكرة دعم؛ و«تحته ٧
    سيارات و٣ تأمينات محجوزة» جملةٌ يتصرّف بها الموظّف. وv1 يرفض بلا عدد.

    **والبديلُ يُقال في الرسالة نفسها:** الإلغاء. وهو ليس حذفاً ألطف — هو
    الفعلُ الصحيح: يفكّ الحجوز ويُبطل الفواتير غير المدفوعة **ثم** ينقل
    الحالة، ويترك صفّاً يُسأل عنه: من ألغاه ومتى ولماذا.
    """
    from apps.money.models import Hold, HoldState, PaymentIntent

    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auctions")

    reason = _reason(request)

    cars = auction.vehicles.count()
    holds = Hold.objects.filter(auction=auction, state=HoldState.ACTIVE).count()
    # نيّاتُ الدفع تُعدّ كالبقيّة: هي المفتاحُ الثالثُ الحامي، وكانت خارج العدّ
    # — فمزادٌ بلا سيارةٍ ولا تأمينٍ وعليه نيّةُ دفعٍ كان يمرّ من الفحص ويصطدم
    # بـ`ProtectedError`، فيقرأ الموظّفُ نصَّ جانغو الخام بدل الجملة التي
    # يَعِد بها وصفُ هذه الدالّة. (صفرُ صفٍّ اليوم في `haraj2_t307` — العطلُ
    # كامنٌ لا قائم.)
    intents = PaymentIntent.objects.filter(auction=auction).count()

    if cars or holds or intents:
        blocking = " و".join(
            part
            for part in (
                f"{cars} سيارة" if cars else "",
                f"{holds} تأميناً محجوزاً" if holds else "",
                f"{intents} نيّةَ دفع" if intents else "",
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
