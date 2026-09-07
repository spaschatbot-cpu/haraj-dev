"""ملفّ العميل الكامل — وثلاثةُ أعطالٍ في نظيره عند v1. T849.

شاشة v1 المقابلة (`/users/{id}/details`) تعرض كلَّ ما نعرفه عن عميل: بياناته،
ومرفقاته، وستَّ قوائم نشاط. والفكرة صحيحة — سؤال الدعم يبدأ من شخصٍ لا من
جدول. وثلاثةُ أشياء فيها تُصلَح هنا:

**١. معرّفٌ فارغ يُقرأ صفراً، فيُعرض مالُ الآخرين.**
هناك تُقرأ `id_customer` (رقم العميل في أودو)، وإن كانت فارغةً صارت `0` في
الاستعلام — فتُعرض على هذه الصفحة **مالياتُ وصورُ آيبان كلِّ عميلٍ يحمل
`customer_id = 0`**. وهو تسريبٌ لا يظهر في أي فحص: الصفحة تعمل، والأرقام
تُقرأ، وهي لشخصٍ آخر.

والعلاج هنا بنيويٌّ لا حَذِر: الربط صفٌّ في :class:`~apps.odoo.models.CustomerLink`،
فغيابُه غيابُ صفٍّ لا قيمةٌ فارغة — **ولا استعلامَ يُبنى على معرّفٍ لا وجود
له**، لأن القائمة تُقرأ من علاقة المستخدم نفسه.

**٢. «الحرّ» ليس حرّاً.** أذكى ما في شاشة v1 أنها تُعيد تسمية الوديعة المتاحة
«محجوز لمستحقات ⚠️» حين تكون أوّلُ مزايدةٍ ستبتلعها. والفكرة تُنقَل كما هي —
**لكن الحساب يأتي من البوّابة** (:func:`~apps.bidding.eligibility.money_snapshot`)
ولا يُعاد هنا: حسابٌ ثانٍ للأهلية هو بوّابةٌ ثانية، وذلك ما يرفضه
`ops/checks/one_eligibility_gate.py`. فما يقوله هذا القسم هو نفسه ما سيقوله
الرفضُ لحظةَ المزايدة، حرفياً.

**٣. وقائمةُ ما يُخفى مكتوبةٌ باليد.** هناك تُعرض «كل الأعمدة عدا ٧ صور و٧
أسرار» — قائمتان بأربعة عشر اسماً في الشيفرة. وعمودٌ يُضاف غداً يظهر على
الشاشة بلا قرار، وقد يكون سرّاً. فالقائمة هنا **مقلوبة**: تُبنى من
`_meta.fields` ويُطرح منها السرُّ المسمّى، فالحقلُ الجديد يظهر — ويكشفه
اختبارٌ يوجب تسميته سرّاً أو قبولَه معروضاً.

وهذا ملفٌّ وحده لا قسمٌ في :mod:`apps.console.people` بسببٍ مكتوب: هو الوحيد
هنا الذي يستورد من :mod:`apps.bidding`، وذلك الاستيراد يُدخل ملفَّه كلَّه في
نطاق حارس الأهلية. **والملفُّ الذي يكلّم البوّابة غيرُ الملفِّ الذي يرسم
القوائم** — وقع الدرسُ نفسه في `auctions.py` من قبل.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404, render

from apps.accounts.models import Company, User
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import Invoice

from .views import console_page

#: ما لا يُعرض أبداً. مسمّىً واحداً واحداً لأن الطرح لا يقبل «تقريباً».
SECRET_FIELDS = frozenset({"password"})

#: كم صفّاً لكل قائمة نشاط. v1 يقطع عند ٢٠٠ وهو محقّ في المبدأ: صفحةٌ تجرّ
#: كلَّ مزايدات عميلٍ نشط لا تُفتح، والسؤال الذي تُفتح لأجله «ماذا فعل
#: مؤخّراً» لا «كم مرّة».
ACTIVITY_LIMIT = 50


def full_record(customer: User) -> list[tuple[str, object]]:
    """كلُّ عمودٍ في الصفّ إلا السرّ — مبنيّاً من النموذج لا من قائمةٍ باليد.

    v1 يكتب قائمتين بأربعة عشر اسماً لما يُخفى، فعمودٌ يُضاف غداً يظهر بلا
    قرار. وهنا العكس: يُعرض كلُّ شيء إلا ما سُمّي سرّاً، وحقلٌ جديد يظهر —
    ويكشفه اختبارٌ يوجب أن يُقرَّر فيه.
    """
    rows: list[tuple[str, object]] = []
    for field in customer._meta.fields:
        if field.name in SECRET_FIELDS:
            continue
        if field.choices:
            value = getattr(customer, f"get_{field.name}_display")()
        else:
            value = getattr(customer, field.name, None)
        # `True` و`False` ليستا عربيّتين ولا مقروءتين: صفٌّ يقول
        # «superuser status: False» يُقرأ كأنه رسالةُ عطل لا معلومة.
        if isinstance(value, bool):
            value = "نعم" if value else "لا"
        rows.append((str(field.verbose_name or field.name), value))
    return rows


def activity_of(customer: User, *, viewer) -> list[dict]:
    """قوائم النشاط الستّ — كلٌّ منها محدودة، **وكلٌّ منها خلف قدرتها**.

    وv1 يعرض الستّ لكل من يفتح الصفحة. والمستودع يقسم المال ثلاثاً منذ T801:
    من يملك `users.view` يعرف من هو العميل، ولا يرى دفترَه ما لم يملك
    `money.view`.

    ولا `try/except` حول القوائم: v1 يلفّ الستّ به كي لا تسقط الصفحة بعمودٍ
    مفقود — وهو علاجُ عرَض. العمودُ المفقود هنا يكسر الاختبار عند الهجرة، لا
    الصفحة عند الموظّف.
    """
    from apps.bidding.models import Bid
    from apps.money.models import Entry, Hold, HoldState, PaymentIntent, RefundRequest

    cards: list[dict] = []

    if can(viewer, Capability.AUCTIONS_VIEW):
        cards.append(
            {
                "title": "المزايدات",
                "kind": "bids",
                "rows": Bid.objects.filter(bidder=customer)
                .select_related("vehicle", "vehicle__auction")
                .order_by("-placed_at")[:ACTIVITY_LIMIT],
            }
        )

    if can(viewer, Capability.INVOICES_VIEW):
        cards.append(
            {
                "title": "الفواتير",
                "kind": "invoices",
                "rows": Invoice.objects.filter(customer=customer).order_by("-issued_at")[
                    :ACTIVITY_LIMIT
                ],
            }
        )
        cards.append(
            {
                "title": "محاولات الدفع",
                "kind": "payments",
                "rows": PaymentIntent.objects.filter(user=customer)
                .select_related("resulting_transaction")
                .order_by("-created_at")[:ACTIVITY_LIMIT],
            }
        )

    if can(viewer, Capability.MONEY_VIEW):
        cards.append(
            {
                "title": "طلبات الاسترداد",
                "kind": "refunds",
                "rows": RefundRequest.objects.filter(user=customer).order_by(
                    "-created_at"
                )[:ACTIVITY_LIMIT],
            }
        )
        cards.append(
            {
                "title": "دفتر المحفظة",
                "kind": "entries",
                "rows": Entry.objects.filter(owner=customer)
                .select_related("transaction", "account")
                .order_by("-id")[:ACTIVITY_LIMIT],
            }
        )
        cards.append(
            {
                "title": "الحجوزات القائمة",
                "kind": "holds",
                "rows": Hold.objects.filter(owner=customer, state=HoldState.ACTIVE)
                .select_related("auction", "invoice")
                .order_by("-created_at")[:ACTIVITY_LIMIT],
            }
        )

    return cards


@console_page("console:customer-detail")
def customer_detail(request, pk: int):
    """ملفُّ عميلٍ واحد: من هو، وكم له، وماذا فعل — وما لا يُعرض له سبب."""
    from apps.bidding.eligibility import money_snapshot
    from apps.odoo.models import CustomerLink

    customer = get_object_or_404(User.objects.select_related("company"), pk=pk)

    return render(
        request,
        "console/customer_detail.html",
        {
            "customer": customer,
            "company": Company.objects.filter(user=customer).first(),
            "wallet": money.wallet_snapshot(customer),
            "record": full_record(customer),
            # اللقطة من البوّابة نفسها التي ترفض المزايدة — فما يقوله قسمُ
            # التأمين هو ما سيقوله الرفضُ حرفياً، لا حسابٌ ثانٍ يشبهه.
            "gate": money_snapshot(customer),
            # **من علاقة المستخدم لا من معرّف.** معرّفٌ فارغ في v1 يُقرأ صفراً
            # فتُعرض مالياتُ كل عميلٍ يحمل صفراً؛ وغيابُ الربط هنا غيابُ صفٍّ
            # لا قيمةٌ فارغة، فلا استعلامَ يُبنى على ما لا وجود له.
            "odoo_links": CustomerLink.objects.filter(user=customer).order_by(
                "-is_primary", "odoo_customer_id"
            ),
            "activity": activity_of(customer, viewer=request.user),
        },
    )
