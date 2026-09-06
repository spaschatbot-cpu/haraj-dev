"""نقلات المزاد وإعادةُ عرض مركبة — شاشات اللوحة التي تكلّم التسوية.

T823 و T828.

**ولماذا ملفٌّ خاص، لا دالّةٌ في `auctions.py`.** نطاق
`ops/checks/one_eligibility_gate.py` هو «كلُّ وحدةٍ تستورد من `apps.bidding`»،
لأن من يقترب من المزايدة قد يقرأ حقيقةً من حقائق الأهلية فيفتح باباً ثانياً.
و`auctions.py` يعرض `deposit_required` في تصدير قائمة المزادات — عرضاً لا
قراراً — فاستيراد `settlement` هناك كان يُدخِل الملفَّ كلَّه في النطاق ويُسقط
الحارس على سطرٍ سليم.

والفصل ليس التفافاً على الحارس: هو ما يقوله الحارس. الملفُّ الذي يكلّم المال
غيرُ الملفِّ الذي يرسم القوائم، وهذا الملفُّ لا يقرأ حقيقةَ أهليةٍ واحدة.
"""

from __future__ import annotations

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect

from apps.auctions import services as auction_services
from apps.auctions.models import Auction
from apps.auctions.states import AuctionState
from apps.core import audit

from .views import console_page

# ---------------------------------------------------------------------------
# T823 — نقلات المزاد، وأيُّها يمرّ على المال
# ---------------------------------------------------------------------------
#
# **جدولٌ واحد، لأن الفرق غير مرئيّ من موضع الاستدعاء.** لكل نقلةٍ هنا دالّة في
# `auctions.services` تنقل الحالة وتنتهي، وهي صحيحةٌ تماماً لأكثرها. لكن
# نقلتين تمسّان مالاً، والدالّة الصحيحة لهما في مكانٍ آخر:
#
# * **الإلغاء بعد الانتهاء** — `services.cancel` تجعل المزاد «ملغى» **والودائع
#   ما زالت محجوزة**، والفواتير غير المدفوعة ما زالت مستحقّة. لا استثناء يُرفع
#   ولا اختبار يسقط: مالٌ محبوسٌ لأحدٍ لم يعد عليه شيء، ولا شيء يقول ذلك.
#   `settlement.cancel_auction` هي التي تفكّ وتُبطل ثم تنقل.
# * **التسوية** — `services.settle` تعلن التسوية ولو بقيت مركبةٌ لم تُحسم، وتلك
#   هي الحالة التي تجعل تحريراً لاحقاً يقع على مزايدين ما زالوا يتنافسون.
#   `settlement.close_auction` يرفضها ويقول كم بقي.
#
# والإلغاء وهو **مسودّة أو مجدول** يبقى على `services.cancel`: لا مال تحرّك
# بعد، ونصّ `cancel_auction` نفسه يقول ذلك. فالجدول يقرأ الحالة الحالية لا
# الهدف وحده — وهذا هو الفرق الذي يضيع حين تُكتب القاعدة في القالب.


def _mover(auction, target: str):
    """الدالّة التي تنفّذ هذه النقلة من هذه الحالة — نقطة القرار الوحيدة."""
    from apps.bidding import settlement

    if target == AuctionState.CANCELLED and auction.state == AuctionState.ENDED:
        return lambda reason: settlement.cancel_auction(auction, reason=reason)
    if target == AuctionState.SETTLED:
        return lambda reason: settlement.close_auction(auction)
    return lambda reason: auction_services.move_auction(auction, target)


@console_page("console:auction-state")
def auction_state(request, pk: int):
    """انقل مزاداً بسببٍ مكتوب. الكتابة الوحيدة على هذه الشاشة.

    نظير `vehicle_state` للمركبة، وقد كان غائباً: `AUCTION_MOVES` تعرّف ثماني
    نقلات ولا زرَّ لواحدة منها، بينما نقلات المركبة التسع عشرة كلها لها أزرار.
    فإلغاء مزادٍ — وهو الفعل الذي يفكّ كل حجز ويُبطل كل ترسية — لم يكن يبلغه
    موظّف، و`cancel_auction` بلا مستدعٍ واحد في الإنتاج.
    """
    auction = get_object_or_404(Auction.objects.all(), pk=pk)

    if request.method != "POST":
        return redirect("console:auction-detail", pk=pk)

    target = request.POST.get("target", "")
    reason = (request.POST.get("reason") or "").strip()

    if not reason:
        messages.error(request, "سبب التغيير مطلوب.")
        return redirect("console:auction-detail", pk=pk)

    before = audit.snapshot(auction, ["state", "number", "title"])

    try:
        _mover(auction, target)(reason)
    except Exception as refusal:
        # جملة الآلة كما هي: هي تفرّق بين «لا نقلة» و«ليست جاهزة بعد»،
        # وإعادة صياغتها هنا تفقد التفريق.
        messages.error(request, str(refusal))
        return redirect("console:auction-detail", pk=pk)

    auction.refresh_from_db()
    audit.record(
        action="console.move_auction",
        entity=auction,
        actor=request.user,
        before=before,
        after=audit.snapshot(auction, ["state", "number", "title"]),
        note=reason,
    )
    messages.success(request, f"المزاد صار «{AuctionState(auction.state).label}».")
    return redirect("console:auction-detail", pk=pk)


# ---------------------------------------------------------------------------
# T828 — سيارةٌ رفضها مالكها تعود لمزادٍ لاحق
# ---------------------------------------------------------------------------
#
# `settlement.relist_vehicle` كانت **بلا مستدعٍ**: الشريك يرفض السعر فتصير
# المركبة `rejected`، ثم لا شيء. والدالّة التي تعيدها إلى الدورة مبنيّةٌ
# ومختبَرة ولا يبلغها موظّف.
#
# وهي هنا لا في `auctions.py` لنفس سبب T823: نطاق
# `ops/checks/one_eligibility_gate.py` هو «كلُّ وحدةٍ تستورد من `apps.bidding`»،
# وذاك الملفّ يعرض `deposit_required` عرضاً لا قراراً.


#: المزادات التي تصلح وجهةً. الحيّ ليس منها: لوتٌ يظهر بعد أن قرأ الناس
#: القائمة هو مزادٌ تغيّر تحت من يزايد فيه.
DESTINATION_STATES = (AuctionState.DRAFT, AuctionState.SCHEDULED)


@console_page("console:vehicle-relist")
def vehicle_relist(request, pk: int):
    """أعِد سيارةً إلى دورةٍ لاحقة، بسببٍ مكتوب.

    والقاعدة التي تحرسها هذه الشاشة أدقّ من «انقلها»: الاستبعاد يخصّ الدورة
    التي وقع فيها، والترسيةُ السابقة لا تسافر — سيارةٌ معروضةٌ في أبريل تُظهر
    فائز مارس هي الطريقة التي يُقال بها لعميلٍ إنه يملك ما لا يملك.
    `relist_vehicle` تفعل ذلك؛ وما تضيفه الشاشة هو أن يبلغها إنسان.
    """
    from apps.auctions.models import Auction, Vehicle
    from apps.bidding import settlement

    vehicle = get_object_or_404(Vehicle.objects.select_related("auction"), pk=pk)

    if request.method != "POST":
        return redirect("console:vehicle-detail", pk=pk)

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "سبب الإعادة مطلوب.")
        return redirect("console:vehicle-detail", pk=pk)

    target = Auction.objects.filter(
        pk=request.POST.get("auction") or 0, state__in=DESTINATION_STATES
    ).first()
    if target is None:
        messages.error(request, "اختر مزاداً لم يبدأ بعد.")
        return redirect("console:vehicle-detail", pk=pk)

    try:
        lot_number = int(request.POST.get("lot_number") or 0)
    except ValueError:
        lot_number = 0
    if lot_number <= 0:
        messages.error(request, "رقم اللوت مطلوب.")
        return redirect("console:vehicle-detail", pk=pk)

    before = audit.snapshot(
        vehicle, ["auction_id", "lot_number", "state", "awarded_to_id"]
    )

    try:
        with transaction.atomic():
            settlement.relist_vehicle(vehicle, into=target, lot_number=lot_number)
    except IntegrityError:
        # `one_lot_per_auction` قيدٌ في القاعدة، وبلوغه من شاشةٍ صفحةُ خطأ.
        # ونقطةُ حفظٍ خاصّة لأن `IntegrityError` داخل معاملةٍ قائمة تُسمّمها،
        # فيسقط قيدُ التدقيق أدناه بـ`TransactionManagementError`.
        messages.error(request, f"رقم اللوت {lot_number} مستعمل في المزاد المختار.")
        return redirect("console:vehicle-detail", pk=pk)
    except Exception as refusal:
        # جملة الآلة كما هي — ولا فحصَ للحالة قبلها. كُتب هنا `_may_relist`
        # يرفض مبكراً برسالةٍ من صياغتي، فجُرّب نزعُه ولم يسقط اختبارٌ واحد:
        # `relist_vehicle` ترفض بنفسها عبر `relist`، وآلةُ الحالات هي التي
        # تفرّق بين «لا نقلة» و«ليست جاهزة». فكان السطر يُعيد صياغة جملةٍ
        # أدقّ منه، وذلك ما ينهى عنه `vehicle_state` بنصّه.
        messages.error(request, str(refusal))
        return redirect("console:vehicle-detail", pk=pk)

    vehicle.refresh_from_db()
    audit.record(
        action="console.relist_vehicle",
        entity=vehicle,
        actor=request.user,
        before=before,
        after=audit.snapshot(
            vehicle, ["auction_id", "lot_number", "state", "awarded_to_id"]
        ),
        note=reason,
    )
    messages.success(request, f"أُعيدت إلى مزاد {target.number} باللوت {lot_number}.")
    return redirect("console:vehicle-detail", pk=pk)
