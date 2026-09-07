"""Customers, companies, invoices and payments. T808 and T809.

Two screens with one rule between them, and each carries its own v1 scar.

**T808 — a bad value names its own field.** Under `STRICT_TRANS_TABLES` v1
aborted the whole update when one value did not fit its column, so an operator
correcting six fields lost all six because the seventh had a stray character —
and the message named the SQL statement, not the box. Every save here goes
through a form, so the refusal arrives beside the field that caused it and every
other value the operator typed is still on the screen.

**T809 — "paid" means posted payments, and only those.** v1 mirrored Odoo's
invoice state into a column written once at insert, so a bank transfer sitting
in Odoo as a *draft* showed here as settled. Somebody released a car against it.
The state on this screen is `derive_invoice_state`, computed from the payments
actually recorded — Odoo's own word is displayed beside it as evidence, never as
truth.
"""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.accounts import services as accounts_services
from apps.accounts.models import AccountType, Company, StaffGrant, User
from apps.core import audit
from apps.core.permissions import Capability, can, capabilities_of
from apps.money import services as money
from apps.money.models import (
    Account,
    AccountKind,
    Invoice,
    InvoiceState,
    Transaction,
)

from .dashboard import Stat
from .exports import export, wants_export
from .forms import ReasonMixin
from .tones import with_tones
from .views import console_page

PAGE_SIZE = 25

#: صفرُ الريال كما يكتبه بقيّة المستودع — عشريّ لا عائم.
ZERO = Decimal("0.00")


class CustomerForm(ReasonMixin, forms.ModelForm):
    """What staff may correct about a customer.

    The phone is absent: changing it is T604 and needs a code to each number.
    `is_staff` and `console_role` are absent because granting console access is
    T803's grant, which demands its own reason and leaves its own row — an
    access change buried in a profile edit is an access change nobody reviews.
    """

    class Meta:
        model = User
        fields = ("full_name", "email", "national_id", "account_type")
        labels = {
            "full_name": "الاسم",
            "email": "البريد",
            "national_id": "رقم الهوية",
            "account_type": "نوع الحساب",
        }

    def clean_national_id(self) -> str:
        """Correcting an identity is allowed; overwriting a correct one is not.

        The same rule the customer's own screen enforces (T606), applied here so
        support cannot do by hand what the customer is refused — which is
        exactly how v1's identity column ended up with two people's numbers.
        """
        from apps.accounts import identity

        incoming = (self.cleaned_data.get("national_id") or "").strip()
        current = self.instance.national_id or ""

        if current and identity.is_valid(current) and incoming != current:
            raise forms.ValidationError(
                "رقم الهوية مثبَّت ولا يمكن تغييره. راجع الدعم لو فيه خطأ."
            )
        if incoming and not identity.is_valid(incoming):
            raise forms.ValidationError("رقم الهوية غير صحيح.")
        return incoming


class CompanyForm(ReasonMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            "name",
            "representative_name",
            "commercial_register",
            "vat_number",
            "building_number",
            "street",
            "district",
            "city",
            "postal_code",
        )
        labels = {
            "name": "اسم الشركة",
            "representative_name": "اسم الممثل",
            "commercial_register": "السجل التجاري",
            "vat_number": "الرقم الضريبي",
            "building_number": "رقم المبنى",
            "street": "الشارع",
            "district": "الحي",
            "city": "المدينة",
            "postal_code": "الرمز البريدي",
        }


# ---------------------------------------------------------------------------
# إدارة المستخدمين — أعمدة v1 نفسها، وعمودُ الرصيد يقول رقماً. T830ن
# ---------------------------------------------------------------------------
#
# شاشة v1 (`/users`) فوقها خمس بطاقات وتحتها جدولٌ بثمانية أعمدة، وأرقامها في
# الإنتاج متّسقة: ٤٤٬١٧٩ نشطاً + ١٢ محظوراً = ٤٤٬١٩١، و١٬٣١٦ شركة + ٤٢٬٨٧٥
# فرداً = ٤٤٬١٩١ كذلك. فالعدّ سليم — والعطل في مكانٍ آخر.
#
# **عمود «الرصيد» فيها `0 SAR` في كل صفٍّ من الأربعة والأربعين ألفاً.** وهو
# بعينه ما وجده جرد T302: `userss` فيها ثلاثة أعمدة رصيدٍ مشتقّة — `wallet`
# و`purchases_balance` و`total_insurance_paid` — تُكتب مرّةً ثم لا يحدّثها
# شيء، فتُقرأ صفراً إلى الأبد. وعمودٌ يعرض صفراً دائماً أسوأ من عمودٍ غائب:
# الغائبُ يُسأل عنه، والصفرُ يُصدَّق.
#
# فالرصيد هنا **مجموعُ حسابات العميل في الدفتر** (`money.Account.balance`،
# والدفترُ كاتبُها الوحيد بحكم `ops/checks/money_single_writer.py`)، ويُقرأ
# لصفحةٍ كاملة باستعلامٍ واحدٍ مجمَّع لا باستعلامٍ لكل صفّ.
#
# وثلاثةُ فروقٍ أخرى عن v1، كلٌّ منها من صفٍّ في الشاشة المنقولة:
#
# **١. «غير معرف» ليست اسماً.** في v1 صفوفٌ اسمُها الحرفيُّ «غير معرف» وخانةُ
# هويّتها فارغة — أي حسابٌ لا يملك إلا جوّالاً. وكتابةُ الغياب كأنه اسم تجعله
# غيرَ قابلٍ للبحث وغيرَ قابلٍ للعدّ. وهنا الفراغُ يُعرض فراغاً موسوماً.
#
# **٢. الحالة تُرشَّح، والمحظور له بابٌ من الصفّ.** v1 يعرض «نشط» ولا يفتح
# منها شيئاً؛ والإيقافُ صار شاشةً في T825، فالصفُّ يشير إليها.
#
# **٣. والترقيم يقول عدد الصفحات الحقيقيّ.** شاشة v1 تقول «إجمالي النتائج
# ٤٤٬١٩١» ثم تعرض «‹ ١ ٢ ٣ ٤ ›» — وأربعةٌ وأربعون ألفاً على ٢٥ صفّاً ألفٌ
# وسبعمئة وثمانٍ وستون صفحة، لا أربع.

#: كم صفّاً في الصفحة. v1 يعطي المستخدم الاختيار («النتائج — ٢٥ صفوف») وهو
#: اختيارٌ حقيقيّ: من يبحث عن اسمٍ يريد ٢٥، ومن يمسح مدينةً يريد ١٠٠.
ROW_CHOICES = (25, 50, 100)

#: الحالة كما تُسأل لا كما تُخزَّن: الحقل `is_active` منطقيّ، والسؤال ثلاثيّ
#: («الكل» أيضاً جواب). ومكتوبةٌ هنا مرّةً يقرأها المرشّح والقائمةُ المعروضة.
STATUSES = (("active", "نشط"), ("stopped", "محظور"))


def customer_rows(*, text: str = "", kind: str = "", status: str = ""):
    """الحسابات، منقّاةً بما كُتب. مفصولةٌ عن العرض ليسألها الاختبار مباشرةً."""
    rows = User.objects.all().select_related("company").order_by("-date_joined")

    text = (text or "").strip()
    if text:
        digits = "".join(character for character in text if character.isdigit())
        terms = Q(full_name__icontains=text)
        if digits:
            terms = terms | Q(phone__contains=digits) | Q(national_id=digits)
        rows = rows.filter(terms)

    if kind in AccountType.values:
        rows = rows.filter(account_type=kind)
    if status == "active":
        rows = rows.filter(is_active=True)
    elif status == "stopped":
        rows = rows.filter(is_active=False)
    return rows


def customer_tallies() -> list[Stat]:
    """البطاقات الخمس، باستعلامٍ واحدٍ مجمَّع لا بخمسة.

    **والعنوان «حسابات» لا «عملاء».** v1 يقول «إجمالي العملاء» وهو يعدّ جدولاً
    لا موظّفين فيه أصلاً — المشرفون عنده جدولٌ آخر. وهنا الجدول واحد
    و`is_staff` عمودٌ فيه، فالصفحةُ تعرض الجميع عمداً: موظّفٌ يزايد بحسابه
    سؤالٌ يصل الدعمَ فعلاً، وv1 لا يستطيع الإجابة عليه. فالبطاقة تقول ما تعدّه،
    وسطرُها يسمّي حصّة الموظّفين بدل أن تُخفى.
    """
    counted = User.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        stopped=Count("id", filter=Q(is_active=False)),
        companies=Count("id", filter=Q(account_type=AccountType.COMPANY)),
        individuals=Count("id", filter=Q(account_type=AccountType.INDIVIDUAL)),
        staff=Count("id", filter=Q(is_staff=True)),
    )
    stopped_href = f"{reverse('console:customers')}?q=&account_type=&status=stopped"
    return [
        Stat(
            label="إجمالي الحسابات",
            value=f"{counted['total']:,}",
            detail=f"ومنها {counted['staff']:,} حساب موظّف — الجدول واحد هنا.",
            tone="people",
            icon="users",
        ),
        Stat(
            label="حسابات نشطة",
            value=f"{counted['active']:,}",
            detail="تدخل وتزايد الآن.",
            icon="check",
        ),
        Stat(
            label="حسابات محظورة",
            value=f"{counted['stopped']:,}",
            detail="لا تدخل ولا تطلب رمزاً جديداً (T825).",
            tone="warn",
            icon="lock",
            href=stopped_href,
            action="اعرضها",
        ),
        Stat(
            label="حسابات شركات",
            value=f"{counted['companies']:,}",
            detail="تزايد باسم الشركة لا باسم ممثّلها.",
            icon="briefcase",
        ),
        Stat(
            label="حسابات أفراد",
            value=f"{counted['individuals']:,}",
            icon="person-search",
        ),
    ]


def with_balances(users):
    """علّق `wallet_total` على كل صفٍّ في الصفحة، باستعلامٍ واحد، وأعِدها.

    مجموعُ حسابات العميل المملوكة له في الدفتر — لا عمودٌ مخزَّنٌ على `User`.
    وv1 يقرأ عموداً كهذا فيعرض `0 SAR` في كل صفّ (T302)، وهذه الدالّة هي سببُ
    ألّا يتكرّر ذلك: لا مكانَ هنا يمكن أن يُهمَل تحديثُه، لأن لا شيء يُكتب.

    وعلى صفوف **الصفحة** لا على الاستعلام كلّه، ومن العرض لا من القالب —
    كـ`with_tones` وللسبب نفسه (المادة ٤-٤).
    """
    rows = list(users)
    totals = {
        row["owner_id"]: row["total"]
        for row in Account.objects.filter(
            owner_id__in=[user.pk for user in rows],
            kind__in=AccountKind.customer_owned(),
        )
        .values("owner_id")
        .annotate(total=Sum("balance"))
    }
    for user in rows:
        # الصفرُ هنا **محسوب**: عميلٌ بلا حسابٍ في الدفتر رصيدُه صفرٌ حقيقة،
        # لا عمودٌ لم يُكتب. والفرق هو كلُّ ما تقوله هذه الشاشة.
        #
        # والاسم `wallet_total` لا `balance`: الثاني اسمُ عمودٍ في
        # `money.Account`، وإسنادٌ إليه في وحدة عرضٍ يقرؤه
        # `ops/checks/money_single_writer.py` كتابةً في الدفتر — وهو محقٌّ في
        # الشكّ، فالتمييزُ في الاسم أرخص من استثناءٍ في الحارس.
        user.wallet_total = totals.get(user.pk, ZERO)
    return rows


class DeleteForm(ReasonMixin, forms.Form):
    """سببٌ وحده. لا حقلَ يُعدَّل هنا — الفعل واحدٌ لا يقبل درجات."""


@console_page("console:customers")
def customers(request):
    """إدارة المستخدمين: من هو، وحالته، وكم له عندنا — بأعمدة v1 وأرقامٍ حيّة."""
    # أسماء المعاملات هي أسماء v1 حرفياً — `q` و`account_type` و`status`
    # و`page` و`per_page`. فالرابط الذي في يد الموظّف اليوم يفتح هنا كما هو،
    # ولا يُطلب منه أن يتعلّم عنواناً ثانياً للسؤال نفسه.
    text = (request.GET.get("q") or "").strip()
    kind = request.GET.get("account_type", "")
    status = request.GET.get("status", "")
    rows = customer_rows(text=text, kind=kind, status=status)

    if wants_export(request):
        return export(
            rows,
            name="المستخدمون",
            headers=[
                "المعرف",
                "الاسم",
                "المدينة",
                "الجوال",
                "الهوية",
                "النوع",
                "الحالة",
                "الرصيد",
                "مسجَّل منذ",
            ],
            cell=lambda u: [
                u.pk,
                u.full_name,
                getattr(getattr(u, "company", None), "city", ""),
                u.phone,
                u.national_id,
                u.get_account_type_display(),
                "نشط" if u.is_active else "محظور",
                # التصدير يقرأ الدفتر صفّاً صفّاً: ملفٌّ يُفتح مرّةً غيرُ صفحةٍ
                # تُفتح كلَّ دقيقة، والدقّة هنا أهمّ من الاستعلام الموفَّر.
                money.wallet_snapshot(u).total,
                u.date_joined,
            ],
        )

    asked = request.GET.get("per_page") or ""
    size = int(asked) if asked.isdigit() and int(asked) in ROW_CHOICES else PAGE_SIZE
    page = Paginator(rows, size).get_page(request.GET.get("page"))

    return render(
        request,
        "console/customers.html",
        {
            "page": page,
            "cards": customer_tallies(),
            "rows": with_balances(page.object_list),
            # الرابط يُعرض لمن يملكه وحده — والحارس على الشاشة نفسها لا
            # على إخفاء الرابط: إخفاءٌ بلا حراسةٍ زينة.
            "can_delete": can(request.user, Capability.USERS_DELETE),
            "types": AccountType.choices,
            "statuses": STATUSES,
            "row_choices": ROW_CHOICES,
            "q": text,
            "kind": kind,
            "status": status,
            "size": size,
        },
    )


@console_page("console:customer-detail")
def customer_detail(request, pk: int):
    """One customer: who they are, what they owe, and what their deposit is doing."""
    customer = get_object_or_404(User.objects.select_related("company"), pk=pk)

    return render(
        request,
        "console/customer_detail.html",
        {
            "customer": customer,
            "company": Company.objects.filter(user=customer).first(),
            "wallet": money.wallet_snapshot(customer),
            "invoices": Invoice.objects.filter(customer=customer).order_by("-issued_at")[
                :20
            ],
        },
    )


@console_page("console:customer-edit")
def customer_edit(request, pk: int):
    customer = get_object_or_404(User.objects.all(), pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)

    if request.method == "POST" and form.is_valid():
        before = audit.snapshot(
            User.objects.get(pk=pk),
            ["full_name", "email", "national_id", "account_type"],
        )
        saved = form.save()
        audit.record(
            action="console.edit_customer",
            entity=saved,
            actor=request.user,
            before=before,
            after=audit.snapshot(
                saved, ["full_name", "email", "national_id", "account_type"]
            ),
            note=form.cleaned_data["reason"],
        )
        messages.success(request, "حُفظت التعديلات.")
        return redirect("console:customer-detail", pk=pk)

    return render(
        request, "console/customer_form.html", {"form": form, "customer": customer}
    )


@console_page("console:company-edit")
def company_edit(request, pk: int):
    """Edit a company's ZATCA details.

    No completeness rule is applied here, and that is deliberate: the customer's
    own screen refuses an incomplete *new* company (T607), but staff correcting
    an old one must be able to save a fixed district without producing a VAT
    number they do not have. The invoice is what refuses to issue.
    """
    customer = get_object_or_404(User.objects.all(), pk=pk)
    company = Company.objects.filter(user=customer).first()
    form = CompanyForm(request.POST or None, instance=company)

    if request.method == "POST" and form.is_valid():
        fields = tuple(CompanyForm.Meta.fields)
        before = audit.snapshot(company, fields) if company else None
        saved = form.save(commit=False)
        saved.user = customer
        saved.save()
        audit.record(
            action="console.edit_company",
            entity=saved,
            actor=request.user,
            before=before,
            after=audit.snapshot(saved, fields),
            note=form.cleaned_data["reason"],
        )
        messages.success(request, "حُفظت بيانات الشركة.")
        return redirect("console:customer-detail", pk=pk)

    return render(
        request,
        "console/company_form.html",
        {"form": form, "customer": customer, "company": company},
    )


# ---------------------------------------------------------------------------
# T809 — invoices, and what "paid" is allowed to mean
# ---------------------------------------------------------------------------


@console_page("console:invoices")
def invoices(request):
    """Every invoice, with its state derived from its own payments.

    The filter offers the *derived* states. Odoo's word is not a filter option
    at all: it is evidence about what they think, and a screen that let an
    operator filter by it would be a screen that answers "what does Odoo say"
    when the question was "what are we owed".
    """
    rows = Invoice.objects.select_related("customer", "vehicle").order_by("-issued_at")

    state = request.GET.get("state", "")
    if state in InvoiceState.values:
        rows = rows.filter(state=state)

    search = (request.GET.get("q") or "").strip()
    if search:
        digits = "".join(character for character in search if character.isdigit())
        terms = Q(number__icontains=search) | Q(customer__full_name__icontains=search)
        if digits:
            terms = terms | Q(customer__phone__contains=digits)
        rows = rows.filter(terms)

    if wants_export(request):
        return export(
            rows,
            name="invoices",
            headers=[
                "الرقم",
                "العميل",
                "الجوال",
                "المبلغ",
                "المسدَّد",
                "المتبقّي",
                "الحالة",
                "صدرت",
            ],
            cell=lambda i: [
                i.number,
                i.customer.full_name,
                i.customer.phone,
                i.amount,
                i.amount_paid,
                i.outstanding,
                i.get_state_display(),
                i.issued_at,
            ],
        )

    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    with_tones(page.object_list)

    return render(
        request,
        "console/invoices.html",
        {
            "page": page,
            "states": InvoiceState.choices,
            "state": state,
            "q": search,
        },
    )


@console_page("console:invoice-detail")
def invoice_detail(request, pk: int):
    """One invoice, its posted payments, and what Odoo happens to call it.

    `derive_invoice_state` recomputes the state from the payments here rather
    than reading the column, so a screen can never show a stale word: the column
    is maintained by `record_payment`, and re-deriving on read is what proves
    the two agree.

    A bank transfer that Odoo is holding as a draft has no posted payment, so it
    contributes nothing to `amount_paid` and the invoice reads open — which is
    T809's whole acceptance criterion, and the state in which somebody released
    a car in v1.
    """
    invoice = get_object_or_404(
        Invoice.objects.select_related("customer", "vehicle"), pk=pk
    )

    # Posted payments only, found by their idempotency key rather than by a
    # column on the entry: `record_payment` derives the key from the invoice, so
    # this finds exactly the movements that were actually recorded against it —
    # and nothing that merely mentions it.
    payments = Transaction.objects.filter(
        idempotency_key__startswith=f"payment:{invoice.pk}:"
    ).order_by("-occurred_at")

    return render(
        request,
        "console/invoice_detail.html",
        {
            "invoice": invoice,
            "derived": money.derive_invoice_state(invoice),
            "payments": payments,
        },
    )


__all__ = [
    "CompanyForm",
    "CustomerForm",
    "company_edit",
    "customer_detail",
    "customer_edit",
    "customers",
    "invoice_detail",
    "invoices",
]


class GrantForm(forms.Form):
    """صلاحيةٌ واحدة، ومنحٌ أو سحب، وسبب.

    القدرات من `Capability.choices` لا من قائمةٍ مكتوبة هنا: قدرةٌ جديدة تظهر
    في هذه الشاشة بمجرّد وجودها، وقائمةٌ ثانية تنحرف عن الأولى بصمت — وذلك
    بعينه ما كسر لوحة v1 حين اختلفت نسخة القائمة عن نسخة الحارس.
    """

    capability = forms.ChoiceField(label="الصلاحية", choices=Capability.choices)
    granted = forms.BooleanField(label="ممنوحة", required=False)
    reason = forms.CharField(
        label="السبب",
        max_length=500,
        widget=forms.TextInput(attrs={"placeholder": "لماذا هذا التغيير؟"}),
        error_messages={"required": "سبب المنح أو السحب مطلوب."},
    )

    def clean_reason(self) -> str:
        reason = (self.cleaned_data.get("reason") or "").strip()
        if not reason:
            raise forms.ValidationError("سبب المنح أو السحب مطلوب.")
        return reason


@console_page("console:staff-grants")
def staff_grants(request, pk: int):
    """صلاحيات موظّفٍ فوق دوره — ومن أعطاها ولماذا.

    الشاشة التي لم تكن: `StaffGrant` كان يُقرأ ولا يُكتب، فمنحُ صلاحيةٍ لا يقع
    إلا بيدٍ على قاعدة البيانات — بلا سببٍ مقروء ولا اسم مانح ولا صفٍّ في
    السجلّ. وهو أخطر تغييرٍ في النظام، فكان الوحيد بلا أثر.

    والصفحة تعرض **الوصول الفعلي** لا الدور وحده: سؤال المراجعة هو «ماذا
    يستطيع هذا الشخص اليوم؟»، وجوابه ليس في الدور ولا في المنح بل في تركيبهما
    (`capabilities_of`) — وقراءتها هنا تعني أن الشاشة لا تحمل نسخةً ثانية من
    قاعدة الأسبقية.
    """
    member = get_object_or_404(User.objects.filter(is_staff=True), pk=pk)
    form = GrantForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        accounts_services.set_capability(
            user=member,
            capability=form.cleaned_data["capability"],
            granted=form.cleaned_data["granted"],
            reason=form.cleaned_data["reason"],
            actor=request.user,
        )
        messages.success(request, "حُدِّثت الصلاحية.")
        return redirect("console:staff-grants", pk=pk)

    effective = sorted(capabilities_of(member))
    return render(
        request,
        "console/staff_grants.html",
        {
            "member": member,
            "form": form,
            "effective": effective,
            "grants": StaffGrant.objects.filter(user=member).order_by("capability"),
        },
    )


class AccessForm(forms.Form):
    """يدخل أو لا يدخل، وسبب. لا حقلَ ثالث.

    مفصولةٌ عن `CustomerForm` عمداً: تصحيحُ اسمٍ وإيقافُ وصولٍ ثقتان مختلفتان،
    وإيقافٌ مدفونٌ في استمارة ملفٍّ شخصيّ إيقافٌ لا يراجعه أحد — وهو نفس سبب
    غياب `is_staff` عن تلك الاستمارة.
    """

    is_active = forms.BooleanField(label="يستطيع الدخول", required=False)
    reason = forms.CharField(
        label="السبب",
        max_length=500,
        widget=forms.TextInput(attrs={"placeholder": "لماذا؟"}),
        error_messages={"required": "سبب الإيقاف أو الإعادة مطلوب."},
    )

    def clean_reason(self) -> str:
        reason = (self.cleaned_data.get("reason") or "").strip()
        if not reason:
            raise forms.ValidationError("سبب الإيقاف أو الإعادة مطلوب.")
        return reason


@console_page("console:customer-access")
def customer_access(request, pk: int):
    """أوقف عميلاً أو أعِده. الشاشة التي لم تكن.

    والإعادة موجودة كالإيقاف: حارسٌ يمنع العودة يجعل الإيقاف عقوبةً نهائية بيد
    موظّف، وv1 كان يعالج ذلك بإنشاء حسابٍ ثانٍ للعميل نفسه.
    """
    customer = get_object_or_404(User.objects.filter(is_staff=False), pk=pk)
    form = AccessForm(request.POST or None, initial={"is_active": customer.is_active})

    if request.method == "POST" and form.is_valid():
        accounts_services.set_customer_access(
            user=customer,
            active=form.cleaned_data["is_active"],
            reason=form.cleaned_data["reason"],
            actor=request.user,
        )
        messages.success(request, "حُدِّث وصول العميل.")
        return redirect("console:customer-detail", pk=pk)

    return render(
        request,
        "console/customer_access.html",
        {"customer": customer, "form": form},
    )


# ---------------------------------------------------------------------------
# حذف حساب — ولماذا يُرفض أكثرَ ممّا يقع. T830ن
# ---------------------------------------------------------------------------
#
# في v1 زرُّ الحذف بجوار زرّ التعديل وبالثقة نفسها، ويحذف الصفَّ حذفاً. وثلاثة
# أشياء تتبعه:
#
# **١. أثرُ المال يبقى بلا صاحب.** الفواتير والقيود والمزايدات صفوفٌ تشير إلى
# المستخدم؛ وحذفُه يترك «فاتورةً لمن؟» بلا جواب. وv2 يمنع ذلك في القاعدة
# (`on_delete=PROTECT`)، فالحذفُ هنا لا يكسر شيئاً — **يُرفض** ويقول لماذا.
#
# **٢. والحساب يعود بجوّالٍ آخر.** من حُذف حسابُه بالخطأ يفتح واحداً جديداً،
# فيصير للشخص الواحد سجلّان ولا يُعرف أنهما هو — وهو أحدُ مصادر التكرار في
# `userss`.
#
# **٣. والسؤال الحقيقيّ غالباً «أوقفه» لا «امحُه».** فالشاشة تعرض الإيقاف
# (T825) بديلاً مسمّى، لا كنصيحةٍ في الهامش.
#
# فالحذف هنا **مسموحٌ في حالةٍ واحدة**: حسابٌ لا أثر له إطلاقاً — لا مزايدة،
# ولا فاتورة، ولا قيد في الدفتر، ولا سيارة، ولا صلاحية. وهو الحساب الذي فُتح
# بالخطأ ولم يُستعمل، وذلك بالضبط ما يُراد حذفُه فعلاً.


#: ما يمنع الحذف، وكلٌّ منها يُعدّ ويُسمّى. مكتوبةٌ قائمةً لا شرطاً متسلسلاً:
#: الشاشة تقول **كلَّ** ما يمنع لا أوّلَه، فمن يزيل واحداً لا يعود ليكتشف ثانياً.
def what_holds(customer: User) -> list[tuple[str, int]]:
    """ما يربط هذا الحساب بالمنصّة — بالاسم والعدد."""
    from apps.money.models import Entry, PaymentIntent

    held = [
        # `customer.bids` لا `Bid.objects` عمداً: استيرادُ `apps.bidding` هنا
        # يُدخل هذا الملفَّ كلَّه في نطاق `ops/checks/one_eligibility_gate.py`،
        # وهو ملفُّ قوائمَ لا ملفُّ أهلية. والعلاقةُ العكسية تعطي العدد نفسه.
        ("مزايدات", customer.bids.count()),
        ("فواتير", Invoice.objects.filter(customer=customer).count()),
        ("قيود في الدفتر", Entry.objects.filter(owner=customer).count()),
        ("محاولات دفع", PaymentIntent.objects.filter(user=customer).count()),
        ("صلاحيات ممنوحة", StaffGrant.objects.filter(user=customer).count()),
    ]
    return [(label, count) for label, count in held if count]


@console_page("console:customer-delete")
def customer_delete(request, pk: int):
    """احذف حساباً لا أثر له، أو اعرف لماذا لا يُحذف.

    والرفضُ هو الحالة الشائعة عمداً: حسابٌ زايد أو صدرت له فاتورة يبقى، لأن
    صفوفه تشير إليه. والشاشة تقول **كلَّ** ما يمنع لا أوّلَه.
    """
    customer = get_object_or_404(User.objects.select_related("company"), pk=pk)
    holds = what_holds(customer)

    # نفسُك ليست صفّاً تحذفه: من يحذف حسابه يخرج من اللوحة في منتصف الفعل،
    # ولا يبقى من يعكسه.
    is_self = customer.pk == request.user.pk
    # وحسابُ موظّفٍ يشير إليه سجلُّ التدقيق نفسه: «من فعل هذا؟» سؤالٌ يُسأل
    # بعد سنة، وجوابُه لا يُحذف بضغطة من شاشة عملاء.
    is_staff = customer.is_staff

    form = DeleteForm(request.POST or None)
    blocked = bool(holds) or is_self or is_staff

    if request.method == "POST" and not blocked and form.is_valid():
        # القيدُ يُكتب **قبل** الحذف وبالمعرّف صراحةً: بعد لحظةٍ لا يبقى صفٌّ
        # يشير إليه، فلو مرّ `entity=` لكان المؤشّر معلّقاً.
        audit.record(
            action="console.delete_customer",
            entity_type=User._meta.label_lower,
            entity_id=customer.pk,
            actor=request.user,
            before=audit.snapshot(
                customer, ["phone", "full_name", "national_id", "account_type"]
            ),
            note=form.cleaned_data["reason"],
        )
        customer.delete()
        messages.success(request, "حُذف الحساب، والقيد مكتوبٌ بجوّاله واسمه.")
        return redirect("console:customers")

    return render(
        request,
        "console/customer_delete.html",
        {
            "customer": customer,
            "form": form,
            "holds": holds,
            "is_self": is_self,
            "is_staff_row": is_staff,
            "blocked": blocked,
        },
    )
