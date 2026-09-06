"""محاولات الدفع عبر البوابة — الجواب عن «دفعتُ ولم يصل». T827.

`PaymentIntent` صفٌّ يُكتب **قبل** أن يصل العميل البوابة، وبستّ حالات فيها
`failed` و`expired` و`disputed`. ولم تكن في اللوحة شاشةٌ تقرؤه: فالمحاولة
الفاشلة مكتوبةٌ عندنا، والعميل يسأل، والدعم لا يبلغها.

**والسؤال واحد، وجوابه أحد ثلاثة** — وكلّها في الصفّ:

* **لم يصل البوابة** — `pending` عمرها ساعات. المحاولة فُتحت ولم تُكمَل.
* **البوابة رفضت** — `failed`، ومعها كلمةُ البوابة الحرفية في
  `gateway_status_raw`. وهي الفرق بين «بطاقتك مرفوضة» و«رصيدك لا يكفي»:
  الأولى تُحوَّل إلى البنك، والثانية يعالجها العميل بنفسه.
* **نجحت ولم نقيّدها** — `succeeded` بلا `resulting_transaction`. وهذه الحالة
  **يمنعها قيدٌ في القاعدة** (`a_succeeded_intent_names_its_transaction`)،
  فعرضُها ليس تحوّطاً من عطلٍ نتوقّعه: هو ما يجعل الصفر جواباً ذا معنى بدل أن
  يكون صمتاً.

**قراءةٌ فقط، ولا زرّ.** تحريكُ مالٍ لمحاولةٍ فاشلة هو `money-actions` بعينه،
وله صلاحيتُه وسببُه المكتوب. وشاشةٌ تشخيصيّة تنمو زرّاً هي شاشةٌ صار لها ثقةٌ
ثانية بلا قرارٍ يقولها.
"""

from __future__ import annotations

from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from apps.money.models import PaymentIntent, PaymentIntentState

from .views import console_page

#: بعد كم يصير `pending` سؤالاً لا انتظاراً.
#:
#: ساعةٌ لا دقائق: صفحة البوابة تُترك مفتوحة، ويُعاد إليها من إشعارٍ بعد
#: عشرين دقيقة. وساعةٌ أقصر من أي مهلةٍ تعطيها بوابةٌ لجلسة دفع، فما تجاوزها
#: لم يُكمَل عند البوابة أيضاً.
STALE_AFTER = timezone.timedelta(hours=1)

#: كم صفّاً يُعرض بلا بحث. الشاشة تُفتح بسؤالٍ عن عميلٍ بعينه غالباً، وقائمةٌ
#: طويلة بلا سؤال ليست تشخيصاً.
LIMIT = 100


@console_page("console:payment-attempts")
def payment_attempts(request):
    """محاولاتُ الدفع، وأحدثُها أوّلاً؛ ويُبحَث بجوّالٍ أو مرجع.

    البحث بالجوّال لأن سؤال الدعم يبدأ منه: العميل يعرف رقمه ولا يعرف
    `reference` كتبه الخادم لنفسه.
    """
    query = (request.GET.get("q") or "").strip()

    rows = PaymentIntent.objects.select_related("user", "resulting_transaction")
    if query:
        rows = rows.filter(
            Q(user__phone__icontains=query)
            | Q(reference__icontains=query)
            | Q(gateway_payment_id__icontains=query)
        )

    cutoff = timezone.now() - STALE_AFTER
    attempts = []
    for intent in rows.order_by("-created_at")[:LIMIT]:
        stale = intent.state == PaymentIntentState.PENDING and intent.created_at < cutoff
        # نجحت ولم تُقيَّد: يمنعها قيدٌ في القاعدة، وتُحسب هنا ليكون الصفر
        # جواباً لا صمتاً.
        unposted = (
            intent.state == PaymentIntentState.SUCCEEDED
            and intent.resulting_transaction_id is None
        )
        attempts.append({"intent": intent, "stale": stale, "unposted": unposted})

    return render(
        request,
        "console/payment_attempts.html",
        {"attempts": attempts, "q": query, "stale_after_hours": 1},
    )
