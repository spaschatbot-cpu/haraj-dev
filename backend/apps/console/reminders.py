"""تذكيراتُ انطلاق المزاد — إدراجٌ في الطابور بعينِ إنسان. T891.

v1 يحمل `sms_reminder_time` منذ سنة، وتملؤه استمارةُ إنشاء المزاد، **ولا شيء
يقرؤه**: بحثٌ في شجرته كلّها يعطي المخطَّطَ والمتحكّماتِ التي تكتبه وحدها — لا
كرون ولا خدمةَ رسائل. فالميزةُ موعودةٌ ولم تُبنَ، ونقلُها «كما هي» نقلُ حقلٍ
ميّت.

فهذه الشاشة هي الميزةُ التي وعد بها الحقل: تقول أيُّ مزادٍ حان تذكيرُه، وكم
شخصاً سيصله، وهل أُدرج سلفاً — والإدراجُ فعلُ إنسانٍ يراه لا مهمّةٍ تعمل وحدها.
والفرقُ ليس تحفّظاً: كلُّ رسالةٍ تكلّف مالاً لا يُسترد، والمادة ٥-٢ تمنع
الإنفاق المجدول بلا موافقةٍ صريحة.
"""

from __future__ import annotations

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.auctions import services as auction_services
from apps.auctions.models import Auction

from .views import console_page


@console_page("console:reminders")
def reminders(request):
    """المزادات التي لها موعدُ تذكير — ما حان منها وما أُدرج."""
    now = timezone.now()
    rows = (
        Auction.objects.exclude(sms_reminder_at__isnull=True)
        .annotate(
            # الجمهور: من وضع سيارةً من هذا المزاد في مفضّلته.
            audience=Count("vehicles__favourited_by__user", distinct=True)
        )
        .order_by("-sms_reminder_at")
    )
    due = [
        a
        for a in rows
        if a.reminder_sent_at is None
        and a.sms_reminder_at <= now
        and a.starts_at > now
    ]
    return render(
        request,
        "console/reminders.html",
        {"rows": rows[:100], "due": due, "now": now},
    )


@console_page("console:reminder-send")
def reminder_send(request, pk: int):
    """أدرِج تذكيرَ مزادٍ في الطابور — مرّةً واحدة، بضغطة إنسان."""
    auction = get_object_or_404(Auction, pk=pk)
    back = redirect("console:reminders")
    if request.method != "POST":
        return back

    try:
        result = auction_services.queue_auction_reminder(auction, actor=request.user)
    except ValueError as refusal:
        messages.error(request, str(refusal))
        return back

    if result["queued"]:
        messages.success(
            request,
            f"أُدرج {result['queued']} تذكيراً لمزاد {auction.number} في الطابور "
            "(لم يُرسل بعد).",
        )
    else:
        messages.warning(
            request,
            f"لا أحدَ في مفضّلته سيارةٌ من مزاد {auction.number} — لم يُدرَج شيء.",
        )
    return back
