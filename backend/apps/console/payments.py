"""سجل الدفعات — كل محاولة سدادٍ وما صارت إليه. T826.

الشاشة من لوحة v1 (`/payments`)، وأعمدتها هناك أربعة: رقم الفاتورة، والمبلغ،
والحالة، ومعرّف الصفّ. وهذه تعرض ما لم يكن هناك، لأن الأسئلة التي فُتحت لأجلها
الشاشة في v1 لم تكن تُجاب منها:

* **المحاولة الفاشلة تُعرَض.** v1 يعرض ما نجح، فيسأل العميل «دفعتُ ولم يصل»
  ولا صفَّ يُرى. و`PaymentIntent` يحمل `state` بستّ قيمٍ منها `failed`
  و`expired` و`disputed` — والفاشلةُ هي الصفُّ الذي يُبحث عنه، لا الناجحة.
* **الحركة الناتجة مربوطة.** `resulting_transaction` يقول أي قيدٍ في الدفتر
  نتج عن هذه الدفعة — وهو الجسر بين «العميل يقول دفع» و«الدفتر يقول ماذا».
  وكُتب هنا أوّلاً فرعٌ يصرخ «نجحت بلا قيد»، ثم حُذف: القاعدة نفسها فيها
  `a_succeeded_intent_names_its_transaction`، فالصفُّ لا يُكتب أصلاً. الحارس
  في القاعدة لا في القالب، وفرعٌ لا يقع أبداً يُقرأ حالةً ممكنة.
* **جواب البوابة الخام لا يُعرَض هنا.** `gateway_status_raw` سلسلةٌ من مزوّد
  الدفع تُقرأ في `console:audit` عند الخلاف؛ وضعُها في جدولٍ من ٥٠ صفّاً يجعل
  الصفَّ سطرين ولا يُقرأ.

لا شيء في هذه الشاشة يكتب
==========================
تسجيلُ دفعةٍ بيد موظّف **غير مبنيّ** في v2 — وهو مكتوبٌ صراحةً في
`apps/core/permissions.py` عند حذف `invoices.manage`. فهذه الشاشة تقرأ، ويوم
يُبنى الفعل يأتي بقدرته وصفحته معاً. زرٌّ هنا اليوم يعني قاعدةَ مالٍ في وحدة
عرض، وهو ما يرفضه `ops/checks/money_single_writer.py` أصلاً.
"""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from apps.accounts.services import find_by_phone
from apps.money.models import PaymentIntent

from .exports import export, wants_export
from .tones import with_tones
from .views import console_page

#: صفوفٌ في الصفحة. أكبر من قوائم الإدارة لأن هذه تُقرأ مسحاً بحثاً عن مرجعٍ
#: بعينه، والمرجع يُلصَق من رسالةٍ لا يُتصفَّح إليه.
PAGE_SIZE = 50

#: حالات الدفعة كما يعرّفها النموذج — تُقرأ منه ولا تُكرَّر هنا. قائمةٌ مكتوبةٌ
#: بيدٍ تتوقّف عن عرض حالةٍ يوم تُضاف واحدة، والحالة التي لا تُرشَّح هي الحالة
#: التي لا يجدها أحد.
STATES = {value for value, _ in PaymentIntent._meta.get_field("state").choices}


def search(*, text: str = "", state: str = ""):
    """الدفعات، منقّاةً بما كُتب. مفصولةٌ عن العرض ليسألها الاختبار مباشرةً."""
    rows = PaymentIntent.objects.select_related(
        "user", "auction", "resulting_transaction"
    )

    state = (state or "").strip()
    if state in STATES:
        rows = rows.filter(state=state)

    text = (text or "").strip()
    if text:
        # ثلاثة مداخل، لأن ثلاثةً هي ما يصل به السؤال: المرجع من إشعار
        # البوابة، والجوّال من العميل على الهاتف، والاسم حين لا يُتذكّر غيره.
        matches = Q(reference__icontains=text) | Q(user__full_name__icontains=text)
        person = find_by_phone(text)
        if person is not None:
            matches |= Q(user=person)
        rows = rows.filter(matches)

    return rows.order_by("-created_at")


@console_page("console:payments")
def payments(request):
    """سجل الدفعات، والفاشلةُ فيه مرئيّةٌ كالناجحة."""
    rows = search(
        text=request.GET.get("q", ""),
        state=request.GET.get("state", ""),
    )

    if wants_export(request):
        return export(
            rows,
            name="سجل-الدفعات",
            headers=[
                "المرجع",
                "العميل",
                "الجوال",
                "المبلغ",
                "العملة",
                "الغرض",
                "المزاد",
                "البوابة",
                "الحالة",
                "الحركة الناتجة",
                "متى",
            ],
            cell=lambda row: [
                row.reference,
                row.user.full_name,
                row.user.phone,
                row.amount,
                row.currency,
                row.get_purpose_display(),
                row.auction.number if row.auction_id else "",
                row.gateway,
                row.get_state_display(),
                row.resulting_transaction_id or "",
                row.created_at,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/payments.html",
        {
            "page": page,
            "q": request.GET.get("q", ""),
            "state": request.GET.get("state", ""),
            "states": PaymentIntent._meta.get_field("state").choices,
        },
    )
