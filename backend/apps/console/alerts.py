"""الإشعارات: السجلُّ والإرسالُ وتذكيراتُ المزادات — شاشةٌ واحدة. T835 · T941.

## ثلاثٌ صارت واحدة

قرارُ المالك (١٨ سبتمبر ٢٠٢٦): «ادمج دول في بعض». وثلاثتُها عن **الشيء
نفسِه**: صفُّ :class:`~apps.notifications.models.Notification`. «إرسال إشعار»
يُدرجه، و«تذكيرات المزادات» تُدرجه، و«السجلّ» يعرضه — والموظّفُ كان يرسل ثمّ
يخرج إلى شاشةٍ أخرى ليرى أين وصل ما أرسله.

**وv1 يجمعها كذلك**: `NotificationController` واحدةٌ فيها `index` (الإرسالُ
الفرديُّ والجماعيّ) و`log` (السجلّ).

## وثلاثُ صلاحياتٍ على شاشةٍ واحدة — والحارسُ على الفعل لا على الباب

هذا هو ثمنُ الدمج، ويُدفَع كما دُفع في «إدارة المدفوعات» و«الاستردادات»:

* الصفحةُ تُفتح بـ``notifications.view`` — يحملها **الدعم**، وسؤالُه اليوميّ
  «هل وصلته الرسالة؟».
* والإرسالُ خلف ``notifications.send`` — وهي **إنفاقٌ لا يُسترد**: رسالةٌ
  نصّيّةٌ إلى ٤٤ ألف عميلٍ تُحاسَب بالرسالة، ولا تراجُعَ عن واحدةٍ وصلت. فهي
  للمالك وحده (انظر `apps/core/permissions.py`).
* والتذكيرُ خلف ``auctions.manage``.

**والتبويبُ الذي لا يملكه القارئُ لا يُعرَض له أصلاً**، وفعلُه محروسٌ في
الخادم لا في القالب — فمن وصل إلى الاستمارة بيده يُرفَض.

## سجل الإشعارات — ما أُرسل إلى من، ووصل أم لا. T835

الشاشة من لوحة v1 (`/notifications/log`)، وأعمدتها هناك أربعة: المستخدم،
والرسالة، والحالة، والتاريخ. وتُفتح لسؤالٍ واحدٍ يتكرّر في الدعم: «قال إنه لم
تصله الرسالة» — والجواب لا يكون «أُرسلت» بل **في أي حالةٍ توقّفت**.

فالحالات الأربع تُقرأ كسلسلةٍ لا كوسم:

* `queued` — عندنا ولم تُسلَّم إلى المزوّد بعد. عطلٌ عندنا.
* `sent` — سُلِّمت إلى المزوّد. عطلٌ محتملٌ عنده أو عند المشغّل.
* `delivered` — أقرّ المزوّد بوصولها إلى الجهاز. الجواب هنا «وصلت».
* `failed` — رُفضت، و`error` يقول لماذا.

و`error` معروضٌ في الجدول لا مخفيّاً خلف صفحة: من يفتح هذا السجلّ يفتحه بسبب
فشل، فإخفاءُ نصّ الفشل خلف نقرةٍ ثانية يجعل الشاشة كلها خطوةً زائدة.

ما لا يُعرَض: `data`
=====================
حمولةُ القالب (`data`) قد تحمل مبلغاً أو اسم مركبةٍ أو رمزاً — ولا تُعرض في
الجدول. `body` هو النصّ الذي وصل فعلاً إلى الجهاز، وهو ما يُقارَن بما يقوله
العميل؛ وعرضُ الحمولة بجواره يُغري بقراءتها على أنها «الرسالة» وهي ليست.

ولا زرَّ «أعد الإرسال»
======================
إعادةُ الإرسال إنشاءُ إشعارٍ جديد لا تعديلُ صفٍّ قائم، وهي فعلٌ في
`apps.notifications` لم يُبنَ بعد. زرٌّ هنا يعني قاعدةً في وحدة عرض — وهو
النمط نفسه الذي رفضه `money_single_writer` في المال.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from apps.accounts.services import find_by_phone
from apps.core.arabic import search_q
from apps.core.permissions import Capability, can
from apps.notifications.models import DeliveryState, Notification

from .broadcast import broadcast as broadcast_tab
from .exports import export, wants_export
from .reminders import reminders as reminders_tab
from .tones import with_tones
from .views import console_page

#: صفوفٌ في الصفحة. السجلّ يُقرأ بحثاً عن رسالةٍ بعينها، والبحث بالجوال يضيّق
#: النتيجة إلى صفوفٍ معدودة قبل أن تُهمّ الصفحات.
PAGE_SIZE = 50

#: القنوات والحالات كما يعرّفها النموذج — تُقرأ منه ولا تُكرَّر هنا. قائمةٌ
#: مكتوبةٌ بيدٍ تتوقّف عن عرض قناةٍ يوم تُضاف واحدة (بريد، واتساب)، والقناة
#: التي لا تُرشَّح هي القناة التي لا يُشتكى منها لأن أحداً لا يراها.
STATES = {value for value, _ in Notification._meta.get_field("state").choices}
CHANNELS = {value for value, _ in Notification._meta.get_field("channel").choices}


def search(*, text: str = "", state: str = "", channel: str = ""):
    """الإشعارات، منقّاةً بما كُتب. مفصولةٌ عن العرض ليسألها الاختبار مباشرةً."""
    rows = Notification.objects.select_related("user")

    state = (state or "").strip()
    if state in STATES:
        rows = rows.filter(state=state)

    channel = (channel or "").strip()
    if channel in CHANNELS:
        rows = rows.filter(channel=channel)

    text = (text or "").strip()
    if text:
        # الجوّال أولاً لأنه ما في يد الدعم والعميل على الهاتف؛ ثم الاسم، ثم
        # نصُّ الرسالة نفسه لمن يبحث عن «كل من وصلته هذه الرسالة».
        matches = search_q(text, "user__full_name", "body")
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(user=person)
        rows = rows.filter(matches)

    return rows.order_by("-created_at")


@console_page("console:notifications")
def notifications(request):
    """الإشعارات: السجلُّ افتراضاً، والإرسالُ والتذكيراتُ تبويبان. T941.

    **والافتراضيُّ السجلّ** لأنه ما يُفتح يومياً: «قال إنه لم تصله الرسالة»
    سؤالُ الدعم المتكرّر، والإرسالُ فعلٌ يُقصَد قصداً.
    """
    which = (request.GET.get("which") or "").strip()
    may_send = can(request.user, Capability.NOTIFICATIONS_SEND)
    may_remind = can(request.user, Capability.AUCTIONS_MANAGE)

    # الحارسُ على الفعل لا على الباب: الصفحةُ `notifications.view`، والتبويبان
    # قدرتاهما أوسع. ومن كتب `?which=send` بيده بلا قدرةٍ يُرَدُّ إلى السجلّ —
    # لا يُرفَض بـ403: التبويبُ ليس شيئاً «محظوراً» عليه، هو شيءٌ لا وجودَ له
    # في شاشته.
    # غلافُ الشاشة: أيُّ تبويبٍ مفتوحٌ وأيُّها يُعرَض أصلاً. يُحسب هنا مرّةً
    # ويُمرَّر — لا يُعاد حسابُه في كلّ تبويب، ولا يُستنتَج في القالب.
    shell = {"which": which or "log", "may_send": may_send, "may_remind": may_remind}

    if which == "send" and may_send:
        return broadcast_tab(request, shell)
    if which == "reminders" and may_remind:
        return reminders_tab(request, shell)
    if request.method == "POST":
        # استمارةُ الإرسال تُرسل إلى الصفحة نفسِها بلا `?which=`؛ والرفضُ هنا
        # صريحٌ لأن هذه **كتابة** لا عرضُ تبويب.
        if not may_send:
            raise PermissionDenied("notifications.send غير مسموحة لهذا المستخدم")
        return broadcast_tab(request, shell | {"which": "send"})

    rows = search(
        text=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
        channel=request.GET.get("channel", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="سجل-الاشعارات",
            headers=[
                "العميل",
                "الجوال",
                "القناة",
                "القالب",
                "الرسالة",
                "الحالة",
                "سبب الفشل",
                "مرجع المزوّد",
                "أُنشئت",
                "أُرسلت",
                "قُرئت",
            ],
            cell=lambda row: [
                row.user.full_name,
                row.user.phone,
                row.get_channel_display(),
                row.template,
                row.body,
                row.get_state_display(),
                row.error,
                row.provider_reference,
                row.created_at,
                row.sent_at,
                row.read_at,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    # عدٌّ على **المرشَّح نفسِه** لا على الجدول كلِّه: رقمٌ في ترويسةٍ لا يتبع
    # ما تحته هو كيف صار مركزُ تقارير v1 يقول غيرَ ما تقول شاشتُه. واستعلامٌ
    # واحدٌ مجموعٌ بالحالة، لا استعلامٌ لكلّ حالة.
    # **`order_by()` فارغةٌ قبل التجميع**: جانغو تُضيف حقولَ الترتيب إلى
    # `GROUP BY`، و`rows` مرتَّبةٌ بالتاريخ — فالتجميعُ يخرج صفّاً لكلّ
    # (حالة، تاريخ) لا صفّاً لكلّ حالة، و`dict()` تُبقي آخرَ صفٍّ لكلّ حالة
    # فيضيع الباقي. قِيس: البطاقةُ قالت «2» والجدولُ تحتها أربعةُ صفوف.
    tally = dict(rows.order_by().values_list("state").annotate(n=Count("id")))
    counts = {
        "all": sum(tally.values()),
        "failed": tally.get(DeliveryState.FAILED, 0),
        "queued": tally.get(DeliveryState.QUEUED, 0),
        # «وصل» و«أُرسل» واحدٌ في هذه البطاقة: الفرقُ بينهما إقرارُ المزوّد،
        # وهو تفصيلٌ يُقرأ في الصفّ لا رقمٌ يُعدّ في الترويسة.
        "sent": tally.get(DeliveryState.SENT, 0)
        + tally.get(DeliveryState.DELIVERED, 0),
    }

    return render(
        request,
        "console/notifications.html",
        {
            "which": "log",
            "may_send": may_send,
            "may_remind": may_remind,
            "page": page,
            "counts": counts,
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "channel": request.GET.get("channel", ""),
            "states": Notification._meta.get_field("state").choices,
            "channels": Notification._meta.get_field("channel").choices,
        },
    )
