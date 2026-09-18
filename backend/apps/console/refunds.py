"""الاستردادات، وطابور العجز، ومزايدات حسب المزاد. T826 · T830ل · T835 · T933.

شاشتان من قائمتين مختلفتين، وتجمعهما ملاحظةٌ واحدة: كلتاهما في v1 **تعرض
رقماً لا يطابق شاشةً أخرى تعرض الشيء نفسه**.

الاستردادات — ثلاثةُ أرقامٍ لشيءٍ واحد
======================================
في إنتاج v1:

* «لوحة التقارير» تقول **طلبات الاسترداد `3,342`**
* «إدارة الطلبات ← استرداد» تقول **`500`**
* «الاستردادات» نفسها تقول **`0`**

ولا واحدةٌ منها تقول أي مرشّحٍ تطبّق. فمن يسأل «كم طلبَ استردادٍ عندنا؟» يجد
ثلاثة أجوبةٍ ولا يعرف أيَّها يقول للمحاسب.

وهنا مصدرٌ واحد: :class:`~apps.money.models.RefundRequest`، وحالاتُه خمسٌ
مسمّاة. والشاشةُ تعرض **العددَ لكل حالة** بدل رقمٍ واحدٍ لا يُعرف ما يعدّه —
فالسؤال يصير «كم مُقدَّماً وكم نُفِّذ» وله جوابٌ واحد.

و«ما زال يكلّفنا» ليس تصنيفاً بل مجموعة: `RefundRequestState.open_states()`
تُسمّيها مرّةً، ويقرأها القيدُ في القاعدة وهذه الشاشة معاً.

تبويبان، لأن العطلَ هو عطلُ «إدارة المدفوعات» نفسُه. T933
=========================================================
الشاشةُ كانت تعرض `RefundRequest` وحدَه. وعلى الإنتاج (قِيس ١٨ سبتمبر ٢٠٢٦
على `haraj2_v1`): **طلباتُ الاسترداد صفر، وفي الدفتر ١٬١٥٥ استرداداً
منفَّذاً** — لأن الترحيل بنى أثرَ الاسترداد في الدفتر
(`insurance_deposits.status='refunded'` ← `refund_insurance`) ولم يبنِ صفوفَ
`refunds_requests` الثلاثةَ آلافٍ ومئتين وتسعةً وثمانين. فمن يفتح «الاستردادات»
يقرأ جدولاً فارغاً وقد استُرِدَّ أحدَ عشرَ مليوناً ونصف.

فتبويبان: **«طلباتُ الاسترداد»** وهو الطابورُ الذي يُعمَل عليه، و**«ما نُفِّذ»**
وهو ما تحرّك في الدفتر فعلاً. وعددُ كلٍّ منهما مكتوبٌ على لسانِ تبويبه، فجدولٌ
فارغٌ يُقرأ «صفر طلبات» لا «الصفحةُ معطوبة».

وتبويبُ «ما نُفِّذ» يضمّ المصادرةَ مع الاسترداد لأن v1 يضمّهما: تبويبُ
«المبالغ المخصومة» هناك يقرأ `status='deducted'` ويفرّق بينهما بـ`payment_code`
وحده («استرداد التأمين كاش» و«مصادرة التأمين»). وهنا نوعُ القيد يفرّق، وهو
عمودٌ في الجدول ومرشِّحٌ فوقه.

والأفعال — وما لا يُنقل منها
=============================
v1 يعطي الصفَّ أربعةَ أزرار: موافقة، ورفض، وتعديل، وحذف. والأولان هنا فعلان:
**«أرسِلْه للمحاسبة»** و**«ارفضه بسبب»** — يمرّان بـ
:func:`apps.money.services.decide_refund` وحدَها، وهي التي تقفل الصفّ وتحكم
الانتقال وتكتب من قرّر ومتى ولماذا.

و**الحذفُ لا يُنقل**. `delete_refund.php` سطرٌ واحد: ``DELETE FROM
refunds_requests WHERE id = ?`` — بلا صلاحيةٍ خاصّة وبلا أثر. وطلبُ استردادِ
عشرةِ آلافٍ يختفي فلا يبقى ما يُسأل عنه: لا من حذفه ولا لماذا ولا أنه كان.
ونظيرُه هنا الرفضُ بسببٍ مكتوب — يبقى الصفُّ ويبقى جوابُه.

و**التعديلُ لا يُنقل كذلك**: `update_refund.php` يكتب المبلغَ والآيبان فوق
القديم بلا أثر، ومبلغُ الطلب هو ما يُصرَف. فمن أراد مبلغاً آخر يرفض الطلبَ
بسببٍ ويفتح العميلُ طلباً جديداً — خطوةٌ أطول، ولها سجلّ.

و**«موافقة» ليست صرفاً**، وهذا الخلطُ عطلُ v1 الصامت: `approve` هناك كلمةٌ في
عمود، ثمّ تُقرأ على أن المبلغ خرج. وهنا «أُرسل للمحاسبة» حالةٌ صريحة، والدفترُ
لا يتحرّك إلا حين يؤكّد أودو الصرفَ عبر المسار الوارد
(`apps.odoo.processing._close_refund_request`) — والقيدُ
`a_confirmed_refund_names_its_transaction` يمنع «نُفِّذ» بلا حركة.

مزايدات حسب المزاد
==================
في v1 مدخلان مختلفان (`owners_console` و`managepage`) يشيران إلى **المسار
نفسه** — أحدُ سبعة تكرارات في جدول الكروت (الشاشة ٣٧-ب). وهي شاشةُ اختيار:
اختر مزاداً لترى مزايداته.

و`console:auction-bids` مبنيّةٌ منذ T835 وتعرض مزايدات مزادٍ بعينه بحالة كلٍّ
منها. فما ينقص مدخلُها: قائمةٌ تُختار منها. وهذا ما هنا.


طابور العجز
===========
`HR-09` بنى `odoo.RefundShortfall`: أودو يطلب سحب وديعةٍ مرهونة، فيُفتح صفٌّ
يقول كم طُلب وكم كان متاحاً وكم العجز، ولا يُنفَّذ شيء آلياً. ومُسجَّلٌ في
`tasks.md` أن **«لا شاشة للطابور بعد»** — أي أن الصفّ يُكتب ولا يبلغه موظّف،
والعميل يسأل «أين استردادي؟» وجوابه مكتوبٌ عندنا في جدولٍ لا باب له.

**والقراءة والإغلاق صلاحيتان لا واحدة.** المستودع يقسم المال ثلاثاً — قراءةُ
الدفتر، والفعل فيه، ومنحُ استثناء — لأن v1 جمعها في علمٍ واحد «فمن يقرأ رصيداً
كان يستطيع مصادرته». والقراءة هنا تشخيصٌ يحتاجه الدعم ليجيب العميل؛ والإغلاق
قرارٌ يقول «لا استرداد» أو «صُرف بطريقةٍ أخرى»، وهو من ثقة `money.act`.

**ولا يُصلَح شيءٌ آلياً هنا،** لنفس سبب `BalanceCheck`: حسابُ المنصّة لا يقرّر
هل سُلّمت السيارة. يقرّر إنسانٌ، ويقول كيف.
"""

from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.services import find_by_phone
from apps.auctions.models import Auction
from apps.bidding.models import Bid
from apps.core import audit
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import (
    RefundRequest,
    RefundRequestState,
    Transaction,
    TransactionKind,
)
from apps.odoo.models import RefundShortfall

from .exports import export, wants_export
from .paging import paged, pager
from .tones import with_tones
from .views import console_page

ZERO = Decimal("0.00")
PAGE_SIZE = 50


def refund_rows(*, text: str = "", state: str = ""):
    """طلبات الاسترداد — مصدرٌ واحد، وحالاتٌ مسمّاة."""
    rows = RefundRequest.objects.select_related(
        "user", "decided_by", "outbox_message", "resulting_transaction"
    ).order_by("-created_at", "-id")

    text = (text or "").strip()
    if text:
        rows = rows.filter(search_q(text, "user__full_name", "user__phone", "reference"))

    if (state or "").strip() in RefundRequestState.values:
        rows = rows.filter(state=state)
    return rows


def refund_counts() -> list[dict]:
    """العددُ لكل حالة — بدل رقمٍ واحدٍ لا يُعرف ما يعدّه.

    وv1 يعرض رقماً واحداً في ثلاث شاشات بثلاث قيم. والقائمة هنا تُبنى من
    `RefundRequestState` نفسها، فحالةٌ تُضاف تظهر ولا تُنسى.
    """
    counted = {
        row["state"]: row["n"]
        for row in RefundRequest.objects.values("state").annotate(n=Count("id"))
    }
    return [
        {
            "value": value,
            "label": RefundRequestState(value).label,
            "count": counted.get(value, 0),
            # «ما زال يكلّفنا» تُقرأ من `open_states` لا تُكتب ثانيةً: القيدُ
            # في القاعدة يقرأ المجموعة نفسها (المادة ٤-٥).
            "open": value in RefundRequestState.open_states(),
        }
        for value in RefundRequestState.values
    ]


# -------------------------------------------------------------------------
# ما نُفِّذ فعلاً — التبويب الثاني. T933
# -------------------------------------------------------------------------

#: أنواعُ القيود التي **يخرج فيها تأمينٌ من يد العميل**. والمصادرةُ معها لأن
#: v1 يضمّهما في تبويبٍ واحد («المبالغ المخصومة») ويفرّق بينهما بـ
#: `payment_code` وحده. وهنا `kind` عمودٌ يُقرأ ويُرشَّح به.
OUTFLOW_KINDS = (
    TransactionKind.INSURANCE_REFUND,
    TransactionKind.INSURANCE_CONFISCATE,
)


def executed(*, text: str = "", kind: str = ""):
    """ما تحرّك في الدفتر استرداداً أو مصادرة — الأحدثُ أوّلاً.

    **وهذا هو الرقمُ الذي كانت الشاشةُ لا تعرضه.** على الإنتاج ١٬١٥٥ قيدَ
    استرداد وصفرُ طلبات، لأن الترحيل بنى الأثرَ ولم يبنِ الطلب.
    """
    rows = (
        Transaction.objects.filter(kind=kind)
        if kind in OUTFLOW_KINDS
        else Transaction.objects.filter(kind__in=OUTFLOW_KINDS)
    )
    rows = rows.prefetch_related("entries__owner")

    text = (text or "").strip()
    if text:
        matches = Q(idempotency_key__icontains=text) | search_q(text, "memo")
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(entries__owner=person)
        else:
            matches |= Q(entries__owner__full_name__icontains=text)
        rows = rows.filter(matches).distinct()
    return rows.order_by("-occurred_at", "-id")


def decorate(page_rows) -> None:
    """يعلّق على كلّ قيدٍ ما تعرضه الشاشة: صاحبُه ومبلغُه ومرجعُه.

    والقيودُ مجلوبةٌ بـ`prefetch_related` للصفحة كلّها، فلا رحلةَ إلى القاعدة
    لكلّ صفّ — خمسون صفّاً وخمسون رحلةً هي الفرقُ بين جزءٍ من ثانيةٍ وثانيتين.
    """
    for row in page_rows:
        entries = list(row.entries.all())
        # صاحبُ الحركة هو صاحبُ القيد الذي على حسابِ عميل — والطرفُ الآخر
        # حسابُ منصّة (`external_refund` أو `confiscated`) لا مالكَ له.
        owned = [entry for entry in entries if entry.owner_id]
        row.customer = owned[0].owner if owned else None
        row.amount = sum(entry.amount for entry in entries if entry.amount > 0)
        # المرجعُ ذيلُ مفتاح المنع: `refund:v1-refund-77` و`confiscate:912`.
        row.reference = row.idempotency_key.rsplit(":", 1)[-1]
        row.source = "مُرحَّل من v1" if row.reference.startswith("v1-") else "قرارٌ في اللوحة"


# -------------------------------------------------------------------------
# الشاشة
# -------------------------------------------------------------------------


def _decide(request):
    """الفعلُ على طلبٍ — إرسالٌ للمحاسبة أو رفضٌ بسبب. لا يحرّك الدفتر.

    والبابُ واحد: `money.decide_refund` هي التي تقفل وتحكم وتكتب وتُدقّق.
    وهنا قراءةُ الاستمارة والجملةُ للموظّف، لا قاعدةُ مالٍ ثانية.
    """
    back = f"{request.path}?{request.POST.get('back', '')}"
    refund = RefundRequest.objects.filter(pk=request.POST.get("refund")).first()
    if refund is None:
        messages.error(request, "لم يُختَر طلبُ استرداد.")
        return redirect(back)

    target = {
        "send": RefundRequestState.SENT.value,
        "reject": RefundRequestState.REJECTED.value,
    }.get((request.POST.get("op") or "").strip())
    if target is None:
        messages.error(request, "فعلٌ غير معروف.")
        return redirect(back)

    try:
        money.decide_refund(
            refund=refund,
            to=target,
            by=request.user,
            reason=request.POST.get("reason", ""),
        )
    except Exception as refusal:  # noqa: BLE001
        # جملةُ الخدمة نفسها: هي تفرّق بين «الانتقال غير مسموح» و«السبب
        # مطلوب»، وإعادةُ صياغتها هنا تُضيّع ذلك الفرق.
        #
        # و`user_message` قبل `str`: `DomainError.__init__` يمرّر النصَّ
        # **الإنجليزيّ** إلى `Exception` حين يُعطى الاثنان، فـ`str(refusal)`
        # يطبع `refund 2: rejection without a reason` في وجه الموظّف. قِيس في
        # المتصفّح قبل أن يُصلَح.
        messages.error(request, getattr(refusal, "user_message", "") or str(refusal))
        return redirect(back)

    messages.success(
        request,
        (
            f"أُرسل طلبُ {refund.amount} ريال للمحاسبة — ولم يُصرف شيءٌ بعد."
            if target == RefundRequestState.SENT.value
            else f"رُفض طلبُ {refund.amount} ريال، والسببُ مكتوبٌ باسمك."
        ),
    )
    return redirect(back)


def _totals() -> dict:
    """عددُ كلِّ تبويبٍ — يُكتب على لسانه.

    وهو ما يمنع قراءةَ الجدول الفارغ على أن الشاشة معطوبة: «طلبات الاسترداد
    (٠)» جملةٌ تامّة، وجدولٌ فارغٌ بلا رقمٍ فوقه ليس جملةً.
    """
    return {
        "requests_total": RefundRequest.objects.count(),
        "executed_total": Transaction.objects.filter(kind__in=OUTFLOW_KINDS).count(),
    }


def _executed_screen(request):
    """تبويبُ «ما نُفِّذ»: القيودُ التي خرج فيها تأمينٌ من يد العميل."""
    text = request.GET.get("q", "")
    kind = request.GET.get("kind", "")
    rows = executed(text=text, kind=kind)

    if wants_export(request):
        page_rows = list(rows[:5000])
        decorate(page_rows)
        return export(
            page_rows,
            name="الاستردادات-المنفذة",
            headers=[
                "المعرّف",
                "النوع",
                "المصدر",
                "رقم العميل",
                "الاسم",
                "الجوال",
                "المبلغ",
                "المرجع",
                "البيان",
                "التاريخ",
            ],
            cell=lambda row: [
                row.pk,
                row.get_kind_display(),
                row.source,
                row.customer.pk if row.customer else "",
                row.customer.full_name if row.customer else "",
                row.customer.phone if row.customer else "",
                row.amount,
                row.reference,
                row.memo,
                row.occurred_at,
            ],
        )

    page = paged(request, rows)
    decorate(page.object_list)
    return render(
        request,
        "console/refunds.html",
        {
            "which": "done",
            "page": page,
            "pager": pager(request, page, "قيداً"),
            "q": text,
            "kind": kind,
            "kinds": [(value, TransactionKind(value).label) for value in OUTFLOW_KINDS],
            "export_url": f"?which=done&q={text}&kind={kind}&export=1",
            **_totals(),
        },
    )


@console_page("console:refunds")
def refunds(request):
    """الاستردادات: طلباتٌ يُعمَل عليها، وما نُفِّذ منها في تبويبٍ ثانٍ.

    **والافتراضيُّ الطلبات** — وهو تبويبُ v1 الأوّل، وهو الوحيدُ الذي يُعمَل
    عليه. وما نُفِّذ خلف `?which=done`: قراءةٌ لا فعلَ فيها، وقيدُ الدفتر
    يُصحَّح بقيدٍ عاكسٍ لا بتحريرِ صفّ.
    """
    # الفعلُ من هذه الشاشة، والحارسُ هنا صراحةً: الصفحةُ تُفتح بـ`money.view`،
    # والقرارُ يحتاج `money.act`. فمن يقرأ الطابور — والدعمُ يقرؤه ليجيب «أين
    # استردادي؟» — لا يقرّر فيه، ولو وصل إلى الاستمارة بيده.
    if request.method == "POST":
        if not can(request.user, Capability.MONEY_ACT):
            raise PermissionDenied("money.act غير مسموحة لهذا المستخدم")
        return _decide(request)

    if request.GET.get("which", "") == "done":
        return _executed_screen(request)

    text = request.GET.get("q", "")
    state = request.GET.get("state", "")
    rows = refund_rows(text=text, state=state)

    if wants_export(request):
        return export(
            rows,
            name="الاستردادات",
            headers=[
                "المرجع",
                "العميل",
                "الجوال",
                "المبلغ",
                "الحالة",
                "ملاحظة العميل",
                "قُدِّم",
                "من قرّر",
                "متى",
                "سببُ القرار",
            ],
            cell=lambda row: [
                row.reference,
                row.user.full_name,
                row.user.phone,
                row.amount,
                row.get_state_display(),
                row.note,
                row.created_at,
                row.decided_by.full_name if row.decided_by_id else "",
                row.decided_at or "",
                row.decision_note,
            ],
        )

    still_open = RefundRequest.objects.filter(state__in=RefundRequestState.open_states())

    page = paged(request, rows)
    with_tones(page.object_list)
    # ما يجوز فعلُه بكلّ صفّ يُقرأ من الجدول نفسه الذي تحكم به الخدمة، ولا
    # يُستنتَج في القالب: زرٌّ يظهر ثمّ يُرفض هو زرٌّ يُعلّم أن اللوحة معطوبة.
    for row in page.object_list:
        moves = money.STAFF_REFUND_MOVES.get(row.state, ())
        row.may_send = RefundRequestState.SENT.value in moves
        row.may_reject = RefundRequestState.REJECTED.value in moves

    return render(
        request,
        "console/refunds.html",
        {
            "which": "requests",
            "page": page,
            "pager": pager(request, page, "طلباً"),
            "counts": refund_counts(),
            "open_count": still_open.count(),
            "open_value": still_open.aggregate(t=Sum("amount"))["t"] or ZERO,
            "may_act": can(request.user, Capability.MONEY_ACT),
            # يُحمل في الاستمارة ليعود القرارُ إلى الصفحة والمرشّح نفسِه:
            # من رشّح بحالةٍ ثمّ قرّر يجد نفسه في أوّل الجدول كلِّه بدونه.
            "back": f"which=requests&q={text}&state={state}",
            "export_url": f"?q={text}&state={state}&export=1",
            "q": text,
            "state": state,
            **_totals(),
        },
    )


def auctions_with_bids(text: str = ""):
    """المزادات ومعها عددُ مزايداتها ومزايديها — قائمةُ اختيار."""
    rows = Auction.objects.annotate(
        bids=Count("vehicles__bids", distinct=True),
        bidders=Count("vehicles__bids__bidder", distinct=True),
        cars=Count("vehicles", distinct=True),
    ).order_by("-starts_at", "-number")

    text = (text or "").strip()
    if text:
        matches = search_q(text, "title")
        if text.isdigit():
            matches |= Q(number=int(text))
        rows = rows.filter(matches)
    return rows


@console_page("console:auction-bids-index")
def auction_bids_index(request):
    """مزايدات حسب المزاد: اختر مزاداً لتفتح مزايداته.

    و`console:auction-bids` هي التي تعرضها، وهي مبنيّةٌ منذ T835 بحالة كل
    مزايدة — مسحوبةً ومستبدَلةً وقائمة. فما ينقص هو المدخل، وهو هذا.
    """
    rows = auctions_with_bids(request.GET.get("q", ""))
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))

    return render(
        request,
        "console/auction_bids_index.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "total": Bid.objects.count(),
        },
    )


# -------------------------------------------------------------------------
# طابور العجز — الرقم في اللوحة له باب. T826
# -------------------------------------------------------------------------

LIMIT = 200


@console_page("console:refund-queue")
def refund_queue(request):
    """ما ينتظر قراراً، أطولُه انتظاراً أوّلاً.

    الترتيب بالانتظار لا بالمعرّف: السؤال الذي تجيبه هذه الصفحة هو «من ينتظر
    استرداده منذ متى»، والمعرّف لا يقول شيئاً عن ذلك. نظير ترتيب
    `partner-decisions` بالسبب نفسه.
    """
    open_cases = (
        RefundShortfall.objects.filter(resolved_at__isnull=True)
        .select_related("user", "message")
        .order_by("opened_at")[:LIMIT]
    )
    closed = (
        RefundShortfall.objects.filter(resolved_at__isnull=False)
        .select_related("user", "resolved_by")
        .order_by("-resolved_at")[:20]
    )
    return render(
        request,
        "console/refund_queue.html",
        {"cases": open_cases, "closed": closed},
    )


@console_page("console:refund-resolve")
def refund_resolve(request, pk: int):
    """أغلق قضيةً بقرارٍ مكتوب. الكتابة الوحيدة على هذه الشاشة."""
    case = get_object_or_404(RefundShortfall.objects.select_related("user"), pk=pk)

    if request.method != "POST":
        return redirect("console:refund-queue")

    resolution = (request.POST.get("resolution") or "").strip()
    if not resolution:
        # القيد `a_closed_shortfall_names_its_decision` يمنع الفارغ في القاعدة،
        # لكن بلوغه من شاشةٍ صفحةُ خطأ لا جملةٌ بجانب الخانة. ومسافاتٌ بيضاء
        # تمرّ من `CHECK` وليست قراراً.
        messages.error(request, "قرار الإغلاق مطلوب.")
        return redirect("console:refund-queue")

    if case.resolved_at is not None:
        # إغلاقٌ ثانٍ يمحو اسم من أغلق أولاً وقراره — وهو ما يُسأل عنه لاحقاً.
        # والرفض هنا لا في القاعدة: لا قيدَ يمنعه، ولأن صفحتين مفتوحتين على
        # الطابور حالةٌ عاديّة لا نادرة.
        messages.error(request, "هذه القضية مُغلقة، ولها قرارٌ واسم من أغلقها.")
        return redirect("console:refund-queue")

    before = audit.snapshot(case, ["resolved_at", "resolution", "shortfall"])

    case.resolved_at = timezone.now()
    case.resolution = resolution
    case.resolved_by = request.user
    case.save(update_fields=["resolved_at", "resolution", "resolved_by"])

    audit.record(
        action="console.resolve_refund_shortfall",
        entity=case,
        actor=request.user,
        before=before,
        after=audit.snapshot(case, ["resolved_at", "resolution", "shortfall"]),
        note=resolution,
    )
    messages.success(request, "أُغلقت القضية.")
    return redirect("console:refund-queue")
