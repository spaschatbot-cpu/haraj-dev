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

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.core import audit, uploads
from apps.core.permissions import Capability, can
from apps.money import services as money
from apps.money.models import Invoice

from .views import console_page

#: ما لا يُعرض في «البيانات الكاملة». مسمّىً واحداً واحداً.
#: الآيبان سرٌّ ماليّ لا يُعرض إلا لمن يملك صلاحية المال (T850).
SECRET_FIELDS = frozenset({"password", "iban"})

#: كم صفّاً لكل قائمة نشاط. v1 يقطع عند ٢٠٠ وهو محقّ في المبدأ: صفحةٌ تجرّ
#: كلَّ مزايدات عميلٍ نشط لا تُفتح، والسؤال الذي تُفتح لأجله «ماذا فعل
#: مؤخّراً» لا «كم مرّة».
ACTIVITY_LIMIT = 50


def _activity_card(title: str, kind: str, queryset, *, is_open: bool = False) -> dict:
    """قائمةُ نشاطٍ واحدة: شريحةٌ تُعرض، **وعددٌ صادق** في عنوانها.

    وكان العدّاد يقول طولَ الشريحة لا عددَ الصفوف — فعميلٌ له ٦٬٦٧٢ مزايدةً
    و٦١٠ فواتيرَ يُقرأ على شاشته «المزايدات ٥٠» و«الفواتير ٥٠» (قِيس على
    العميل ٧١٩٣ في ١٣ سبتمبر ٢٠٢٦). وذلك عطلُ «الرصيد صفرٌ في كل صفّ» بعينه:
    **رقمٌ يُقرأ إجابةً وهو حدُّ العرض**، ومن يفتح الملفّ ليعرف «كم زايد» يخرج
    برقمٍ يظنّه جواباً. والمطويُّ خاصّةً لا يُصحَّح بالفتح: من يقرأ «٥٠» لا
    يفتح ليعدّ.

    والعدُّ لا يُسأل إلا حين تمتلئ الشريحة: من له تسعُ فواتيرَ عددُه في يدنا
    أصلاً، فاستعلامُ `COUNT` له ثمنٌ بلا مقابل — وستُّ قوائمَ في صفحةٍ واحدة.
    """
    rows = list(queryset[:ACTIVITY_LIMIT])
    total = len(rows) if len(rows) < ACTIVITY_LIMIT else queryset.count()
    return {
        "title": title,
        "kind": kind,
        "open": is_open,
        "rows": rows,
        "total": total,
        # ما يُعرض أقلُّ مما هو: يُقال صريحاً تحت العنوان، لأن جدولاً ينتهي
        # بلا كلمة يُقرأ كاملاً.
        "shown": len(rows),
        "clipped": total > len(rows),
    }


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
        # أوّلُ قائمةٍ تُفتح، والباقي مطويّ. والسبب أن الصفحة ستُّ قوائمَ
        # بمئتي صفٍّ مجتمعة، ومن يفتحها يسأل عن **واحدة** — وستٌّ مفتوحةٌ
        # تعني تمريراً طويلاً قبل الوصول إلى المقصود. والعددُ في العنوان يبقى
        # ظاهراً، فالمطويُّ يُعرف حجمُه.
        cards.append(
            _activity_card(
                "المزايدات",
                "bids",
                Bid.objects.filter(bidder=customer)
                .select_related("vehicle", "vehicle__auction")
                .order_by("-placed_at"),
                is_open=True,
            )
        )

    if can(viewer, Capability.INVOICES_VIEW):
        cards.append(
            _activity_card(
                "الفواتير",
                "invoices",
                Invoice.objects.filter(customer=customer).order_by("-issued_at"),
            )
        )
        cards.append(
            _activity_card(
                "محاولات الدفع",
                "payments",
                PaymentIntent.objects.filter(user=customer)
                .select_related("resulting_transaction")
                .order_by("-created_at"),
            )
        )

    if can(viewer, Capability.MONEY_VIEW):
        cards.append(
            _activity_card(
                "طلبات الاسترداد",
                "refunds",
                RefundRequest.objects.filter(user=customer).order_by("-created_at"),
            )
        )
        cards.append(
            _activity_card(
                "دفتر المحفظة",
                "entries",
                Entry.objects.filter(owner=customer)
                .select_related("transaction", "account")
                .order_by("-id"),
            )
        )
        cards.append(
            _activity_card(
                "الحجوزات القائمة",
                "holds",
                Hold.objects.filter(owner=customer, state=HoldState.ACTIVE)
                .select_related("auction", "invoice")
                .order_by("-created_at"),
            )
        )

    return cards


def _document_cards(customer: User) -> list[dict]:
    """الأربعةُ بترتيبها الثابت — والغائبُ يُعرض غائباً.

    الأنواعُ الأربعة تُعرض دائماً حتى ما لم يُرفع منها، لأن السؤال على الهاتف هو
    «هل عنده صورة آيبان؟» — وقائمةٌ تعرض المرفوعَ وحده تجيب عنه بالصمت، فيُقرأ
    الصمتُ «لم أبحث جيّداً» لا «غير موجودة».
    """
    from apps.accounts.models import CustomerDocument, DocumentKind

    cards = []
    for kind in DocumentKind:
        history = list(
            CustomerDocument.objects.filter(user=customer, kind=kind.value)[:10]
        )
        cards.append(
            {
                "kind": kind.value,
                "label": kind.label,
                "current": history[0] if history else None,
                "older": history[1:],
            }
        )
    return cards


@console_page("console:customer-detail")
def customer_detail(request, pk: int):
    """ملفُّ عميلٍ واحد: من هو، وكم له، وماذا فعل — وما لا يُعرض له سبب."""
    from apps.accounts.models import NationalAddress, PhoneVerification
    from apps.bidding.eligibility import money_snapshot
    from apps.odoo.models import CustomerLink

    customer = get_object_or_404(
        User.objects.select_related("company", "national_address"), pk=pk
    )

    return render(
        request,
        "console/customer_detail.html",
        {
            "customer": customer,
            "company": Company.objects.filter(user=customer).first(),
            "national_address": NationalAddress.objects.filter(user=customer).first(),
            "login_attempts": PhoneVerification.objects.filter(
                phone=customer.phone
            ).order_by("-created_at")[:10],
            "can_view_money": can(request.user, Capability.MONEY_VIEW),
            # الربطُ يقرّر مالَ مَن هذا، فهو فعلٌ ماليّ لا عرضُ ملفّ. والقالبُ
            # يقرأ نفسَ القدرة التي يفحصها `odoo_link` — لا زرَّ يظهر ثم يُرفض.
            "can_act_money": can(request.user, Capability.MONEY_ACT),
            "can_manage_users": can(request.user, Capability.USERS_MANAGE),
            # الوثائق: الساري من كل نوع، والتاريخُ تحته. `current` هي التعريفُ
            # الوحيد لـ«الساري» — لا `order_by` ثانية في قالبٍ تختلف عنها غداً.
            "documents": _document_cards(customer),
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


# ---------------------------------------------------------------------------
# الربط بأودو — الكاتبُ الذي لم يكن موجوداً
# ---------------------------------------------------------------------------
#
# `CustomerLink` كان له في المستودع كلِّه **أربعُ قراءاتٍ وصفرُ كتابة**: النموذج
# مبنيّ، والقيود مكتوبة، والشاشة تعرض القائمة — ولا سبيل لإنشاء صفٍّ فيها.
# فـ`_resolve_customer` تُرجع `None` دائماً، وكلُّ دفعةٍ من أودو تذهب إلى الحساب
# المعلَّق. النظامُ لا يُخطئ الإسناد لأنه **لا يُسنِد أبداً**.
#
# ولماذا شاشةٌ لا مطابقةٌ آليّة: لأن المطابقة بالجوّال أو بالاسم هي عينُ العطل
# الذي يُغلقه T218 — صفٌّ واحدٌ بجوّالٍ فارغ في v1 طابقَ الجميع. والربطُ قرارٌ
# يقول «مالُ هذا الرقم لهذا الشخص»، فله فاعلٌ مسمّى وأثرٌ في `AuditLog`.
#
# والمفتاحُ الحقيقيّ لاحقاً هو رَدُّ أودو على `create/customer` — يومَ تُبنى تلك
# النقطة الصادرة يُكتب الصفُّ من الرقم الذي أعطَوه، لا من قرارِ موظّف. وحتى ذلك
# اليوم هذه هي الطريقة الوحيدة، وهي أفضلُ من لا شيء بفارقٍ هو كلُّ مالِ أودو.


@console_page("console:customer-detail")
def odoo_link(request, pk: int):
    """اربط عميلاً برقمه في أودو، أو افكَّ ربطاً — بقرارٍ مسمّى وأثرٍ مكتوب.

    محروسةٌ بـ`money.act` فوق حراسة الصفحة: فتحُ ملفِّ عميلٍ قراءة، وتغييرُ من
    تُنسب إليه دفعاتُ أودو فعلٌ ماليّ. وv1 خلط الاثنين فصار كلُّ من يرى الملفّ
    يملك تحويلَ المال.

    و**«الأساسي» لا يُنتزع من حسابٍ آخر بصمت.** قيدُ
    `one_primary_account_per_odoo_customer` يمنع أساسيَّين لرقمٍ واحد؛ ولو
    حُلَّ ذلك بمسحِ الأساسيِّ القديم تلقائياً لصار زرٌّ واحدٌ يحوّل مالَ عميلٍ
    إلى عميلٍ آخر بلا أن يقرأ أحدٌ اسمَ الأول. فيُرفض ويُسمّى صاحبُه.
    """
    if request.method != "POST":
        return redirect("console:customer-detail", pk=pk)
    if not can(request.user, Capability.MONEY_ACT):
        raise PermissionDenied("money.act غير مسموحة لهذا المستخدم")

    from apps.odoo.models import CustomerLink

    customer = get_object_or_404(User, pk=pk)
    back = reverse("console:customer-detail", args=[pk])

    unlink_id = (request.POST.get("unlink") or "").strip()
    if unlink_id:
        link = CustomerLink.objects.filter(pk=unlink_id, user=customer).first()
        if link is None:
            messages.error(request, "لا يوجد هذا الربط لهذا العميل.")
            return redirect(back)
        audit.record(
            action="odoo.unlink_customer",
            entity_type=CustomerLink._meta.label_lower,
            entity_id=link.pk,
            actor=request.user,
            before={
                "user": customer.pk,
                "odoo_customer_id": link.odoo_customer_id,
                "is_primary": link.is_primary,
            },
            note=(request.POST.get("reason") or "").strip(),
        )
        odoo_id = link.odoo_customer_id
        link.delete()
        messages.success(request, f"فُكَّ الربط برقم أودو {odoo_id}.")
        return redirect(back)

    odoo_id = (request.POST.get("odoo_customer_id") or "").strip()
    if not odoo_id:
        messages.error(request, "اكتب رقم العميل في أودو.")
        return redirect(back)

    is_primary = request.POST.get("is_primary") == "on"
    note = (request.POST.get("note") or "").strip()

    if is_primary:
        holder = (
            CustomerLink.objects.filter(odoo_customer_id=odoo_id, is_primary=True)
            .exclude(user=customer)
            .select_related("user")
            .first()
        )
        if holder is not None:
            messages.error(
                request,
                f"رقم أودو {odoo_id} أساسيٌّ للحساب {holder.user_id} "
                f"({holder.user.full_name or holder.user.phone}). "
                "فُكَّ ذلك الربط أولاً إن كان خطأً — لا يُنتزع بزرّ.",
            )
            return redirect(back)

    link, created = CustomerLink.objects.get_or_create(
        user=customer,
        odoo_customer_id=odoo_id,
        defaults={"is_primary": is_primary, "note": note, "linked_by": request.user},
    )
    before = None
    if not created:
        before = {"is_primary": link.is_primary, "note": link.note}
        link.is_primary = is_primary
        link.note = note or link.note
        try:
            link.save(update_fields=["is_primary", "note"])
        except IntegrityError:
            messages.error(request, "تعارضٌ في قيد «أساسيٍّ واحدٍ لكل رقم أودو».")
            return redirect(back)

    audit.record(
        action="odoo.link_customer" if created else "odoo.update_customer_link",
        entity_type=CustomerLink._meta.label_lower,
        entity_id=link.pk,
        actor=request.user,
        before=before,
        after={
            "user": customer.pk,
            "odoo_customer_id": odoo_id,
            "is_primary": is_primary,
        },
        note=note,
    )
    messages.success(
        request,
        f"{'رُبط' if created else 'حُدِّث الربط'} بحساب أودو {odoo_id}"
        f"{' (أساسي)' if is_primary else ''}.",
    )
    return redirect(back)


# ---------------------------------------------------------------------------
# وثائقُ العميل — الرفعُ والعرض
# ---------------------------------------------------------------------------
#
# أربعُ وثائقٍ في v1 ولا واحدةَ منها هنا: السجل التجاريّ · الشهادة الضريبيّة ·
# صورة الهويّة · صورة الآيبان. وأخطرُ ما يترتّب على غيابها أن **الاسترداد كان
# يُفتح إلى رقمِ آيبانٍ نصّيٍّ بلا مستندٍ يُثبته** — وv1 يفرض الصورة لهذا السبب.
#
# ولماذا يرفعها الموظّف أصلاً: لأن العميل يتّصل بالهاتف ومعه الصورة في واتساب،
# والطريقُ الوحيدُ لولا ذلك أن يُقال له «ثبّت التطبيق وارفعها» وهو ينتظر
# استرداداً. فالرفعُ عنه ممكن، **والرافعُ مكتوبٌ في الصفّ** (`uploaded_by`) —
# فسؤالُ «من رفع صورةَ هويّة هذا العميل؟» له جوابٌ لا تخمين.


@console_page("console:customer-detail")
def customer_documents(request, pk: int):
    """ارفع وثيقةً لعميل. محروسةٌ بـ`users.edit` فوق حراسة الصفحة.

    وليست `money.act`: رفعُ سجلٍّ تجاريٍّ عملُ خدمةِ عملاء لا عملٌ ماليّ. لكنها
    ليست القراءةَ أيضاً — من يفتح الملفّ يقرأ، ومن يرفع يغيّر ما تُبنى عليه
    قراراتٌ لاحقة، وأوّلُها أن صورةَ الآيبان تفتح بابَ الاسترداد.

    ولا حذف. الوثيقةُ القديمةُ هي التي صدرت بها فاتورةُ العام الماضي؛ والجديدةُ
    صفٌّ يعلوها (:meth:`CustomerDocument.current`) ولا يمحوها.
    """
    if request.method != "POST":
        return redirect("console:customer-detail", pk=pk)
    if not can(request.user, Capability.USERS_MANAGE):
        raise PermissionDenied("users.manage غير مسموحة لهذا المستخدم")

    from apps.accounts.models import CustomerDocument, DocumentKind

    customer = get_object_or_404(User, pk=pk)
    back = reverse("console:customer-detail", args=[pk])

    kind = (request.POST.get("kind") or "").strip()
    if kind not in DocumentKind.values:
        messages.error(request, "اختر نوع الوثيقة.")
        return redirect(back)

    uploaded = request.FILES.get("file")
    if uploaded is None:
        messages.error(request, "اختر ملفاً.")
        return redirect(back)

    try:
        # **عبر البوّابة الوحيدة** (T912): المحتوى يقرّر لا الاسم، والبايتات
        # يُعاد ترميزها فيسقط ما لم يكن جزءاً من الصورة. وصورةُ هويّةٍ تحمل
        # سكربتاً هي بالضبط ما عاش شهوراً في مجلّد صور v1.
        safe = uploads.sanitise_image(uploaded)
    except uploads.UploadRejected as exc:
        messages.error(request, str(exc.user_message or exc))
        return redirect(back)

    document = CustomerDocument(
        user=customer,
        kind=kind,
        note=(request.POST.get("note") or "").strip(),
        uploaded_by=request.user,
    )
    # `save=False`: الاسمُ يأتي من `upload_to` والصفُّ يُكتب مرّةً واحدة.
    document.file.save(f"upload{safe.suffix}", safe.content, save=False)
    document.save()
    audit.record(
        action="customer.upload_document",
        entity_type=CustomerDocument._meta.label_lower,
        entity_id=document.pk,
        actor=request.user,
        after={"user": customer.pk, "kind": kind},
        note=document.note,
    )
    messages.success(request, f"رُفعت {document.get_kind_display()}.")
    return redirect(back)
