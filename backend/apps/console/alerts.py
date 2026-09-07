"""سجل الإشعارات — ما أُرسل إلى من، ووصل أم لا. T835.

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

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.accounts.services import find_by_phone
from apps.notifications.models import Notification

from .exports import export, wants_export
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
        matches = Q(user__full_name__icontains=text) | Q(body__icontains=text)
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(user=person)
        rows = rows.filter(matches)

    return rows.order_by("-created_at")


@console_page("console:notifications")
def notifications(request):
    """سجل الإشعارات، وسببُ الفشل مكتوبٌ في الصفّ لا خلف نقرة."""
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

    return render(
        request,
        "console/notifications.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "channel": request.GET.get("channel", ""),
            "states": Notification._meta.get_field("state").choices,
            "channels": Notification._meta.get_field("channel").choices,
        },
    )
