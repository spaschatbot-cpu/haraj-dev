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

from django import forms
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import Company, User
from apps.core import audit
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState, Transaction

from .forms import ReasonMixin
from .views import console_page

PAGE_SIZE = 25


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


@console_page("console:customers")
def customers(request):
    """Find a customer by phone, name or identity number."""
    rows = User.objects.all().select_related("company").order_by("-date_joined")

    search = (request.GET.get("q") or "").strip()
    if search:
        digits = "".join(character for character in search if character.isdigit())
        terms = Q(full_name__icontains=search)
        if digits:
            terms = terms | Q(phone__contains=digits) | Q(national_id=digits)
        rows = rows.filter(terms)

    return render(
        request,
        "console/customers.html",
        {
            "page": Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page")),
            "q": search,
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

    return render(
        request,
        "console/invoices.html",
        {
            "page": Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page")),
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
