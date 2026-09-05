"""T808 and T809 — a bad value names its field, and a draft is not a payment.

Two v1 incidents, one file:

* Under `STRICT_TRANS_TABLES` a single value that did not fit its column aborted
  the **whole** update. An operator correcting six fields lost all six because
  the seventh had a stray character, and the message named the SQL statement
  rather than the box.
* Odoo's invoice state was mirrored into a column written once at insert, so a
  bank transfer sitting in Odoo as a *draft* read here as settled — and a car
  was released against it.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.accounts.models import Company, User
from apps.core.models import AuditLog
from apps.core.permissions import Role
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

from .conftest import stamp_from

pytestmark = pytest.mark.django_db

VALID_ID = "1000000008"
ANOTHER_VALID_ID = "2000000006"
MISTYPED_ID = "1000000001"


def staff(role: str, phone: str = "966500000041") -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف", password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def manager(client):
    user = staff(Role.OWNER)
    client.force_login(user)
    return user


@pytest.fixture
def customer(db) -> User:
    return User.objects.create_user(phone="966501234567", full_name="عميل الاختبار")


def body_of(client, url, **params) -> str:
    response = client.get(url, params)
    assert response.status_code == 200, f"{url} أجاب {response.status_code}"
    return response.content.decode()


def edit_payload(**extra) -> dict:
    fields = {
        "full_name": "الاسم المصحَّح",
        "email": "a@b.com",
        "national_id": "",
        "account_type": "individual",
        "reason": "تصحيح بطلب العميل",
    }
    fields.update(extra)
    return fields


# ---------------------------------------------------------------------------
# T808 — the list and the detail
# ---------------------------------------------------------------------------


def test_a_customer_is_found_by_phone(client, manager, customer):
    body = body_of(client, reverse("console:customers"), q="1234567")

    assert "عميل الاختبار" in body


def test_a_customer_is_found_by_name(client, manager, customer):
    body = body_of(client, reverse("console:customers"), q="عميل")

    assert "966501234567" in body


def test_an_empty_search_says_so(client, manager, customer):
    body = body_of(client, reverse("console:customers"), q="لا أحد بهذا الاسم")

    assert "لا مستخدمين مطابقين" in body


def test_the_detail_shows_the_wallet_itemised_not_as_one_number(
    client, manager, customer
):
    """v1 showed one figure and a customer read it as money he could withdraw."""
    money.deposit_insurance(
        user=customer, amount=Decimal("10000.00"), source="cash", reference="d/1"
    )

    body = body_of(client, reverse("console:customer-detail", args=[customer.pk]))

    assert "10000.00" in body
    assert "الإجمالي" in body


# ---------------------------------------------------------------------------
# T808's acceptance criterion — the boundary values
# ---------------------------------------------------------------------------


def test_one_bad_field_does_not_abort_the_whole_edit(client, manager, customer):
    """The v1 failure, stated as three assertions.

    Nothing is written, the offending field is named, and every good value the
    operator typed is still on the screen waiting for them.
    """
    response = client.post(
        reverse("console:customer-edit", args=[customer.pk]),
        edit_payload(full_name="الاسم المصحَّح", email="ليس بريداً"),
    )
    body = response.content.decode()

    customer.refresh_from_db()
    assert customer.full_name == "عميل الاختبار", "حُفظ جزء من التعديل رغم خطأ"
    assert "الاسم المصحَّح" in body, "ضاع ما كتبه المشغّل في الحقول السليمة"
    assert not AuditLog.objects.filter(action="console.edit_customer").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        pytest.param("account_type", "ملك", id="an enum value that does not exist"),
        pytest.param("email", "@", id="a malformed email"),
        pytest.param("full_name", "", id="an empty required field"),
        pytest.param("national_id", "12", id="an identity too short"),
    ],
)
def test_a_boundary_value_is_a_field_message_not_a_crash(
    client, manager, customer, field, value
):
    """Every one of these aborted the entire statement in v1."""
    response = client.post(
        reverse("console:customer-edit", args=[customer.pk]),
        edit_payload(**{field: value}),
    )

    assert response.status_code == 200, "انهار التحديث بدل أن يرفض الحقل"
    customer.refresh_from_db()
    assert customer.full_name == "عميل الاختبار"


def test_a_good_edit_saves_and_is_recorded(client, manager, customer):
    url = reverse("console:customer-edit", args=[customer.pk])
    # ختم HR-13: الاستمارة الحقيقية تحمله، فالإرسال اليدويّ يحمله كذلك.
    client.post(url, edit_payload(row_stamp=stamp_from(client, url)))

    customer.refresh_from_db()
    entry = AuditLog.objects.get(action="console.edit_customer")

    assert customer.full_name == "الاسم المصحَّح"
    assert entry.actor_id == manager.pk
    assert entry.note == "تصحيح بطلب العميل"
    assert entry.before["full_name"] == "عميل الاختبار"


def test_an_edit_without_a_reason_is_refused(client, manager, customer):
    client.post(
        reverse("console:customer-edit", args=[customer.pk]), edit_payload(reason=" ")
    )

    customer.refresh_from_db()
    assert customer.full_name == "عميل الاختبار"


def test_staff_cannot_overwrite_a_verified_identity_by_hand(client, manager, customer):
    """The rule the customer's own screen enforces, applied to support too.

    Otherwise support does by hand what the customer is refused — and that is
    how v1's identity column ended up holding two people's numbers.
    """
    customer.national_id = VALID_ID
    customer.save(update_fields=["national_id"])

    client.post(
        reverse("console:customer-edit", args=[customer.pk]),
        edit_payload(national_id=ANOTHER_VALID_ID),
    )

    customer.refresh_from_db()
    assert customer.national_id == VALID_ID


def test_staff_can_correct_a_mistyped_identity(client, manager, customer):
    customer.national_id = MISTYPED_ID
    customer.save(update_fields=["national_id"])

    url = reverse("console:customer-edit", args=[customer.pk])
    client.post(
        url,
        edit_payload(national_id=VALID_ID, row_stamp=stamp_from(client, url)),
    )

    customer.refresh_from_db()
    assert customer.national_id == VALID_ID


def test_the_edit_form_offers_no_way_to_grant_console_access(client, manager, customer):
    """A grant has its own reason and its own row; one buried here is unreviewed."""
    body = body_of(client, reverse("console:customer-edit", args=[customer.pk]))

    assert 'name="is_staff"' not in body
    assert 'name="console_role"' not in body
    assert 'name="phone"' not in body


# ---------------------------------------------------------------------------
# The company
# ---------------------------------------------------------------------------


def test_an_old_company_can_be_corrected_without_producing_a_vat_number(
    client, manager, customer
):
    """Staff fixing a district must not be blocked on a field they do not have.

    The customer's own screen refuses an incomplete *new* company (T607); the
    invoice is what refuses to issue for an old one.
    """
    Company.objects.create(user=customer, name="شركة قديمة")

    url = reverse("console:company-edit", args=[customer.pk])
    client.post(
        url,
        {
            "name": "شركة قديمة",
            "district": "العليا",
            "reason": "تصحيح الحي",
            "row_stamp": stamp_from(client, url),
        },
    )

    company = Company.objects.get(user=customer)
    assert company.district == "العليا"
    assert company.vat_number == ""
    assert AuditLog.objects.filter(action="console.edit_company").exists()


def test_a_company_with_no_name_is_refused_by_the_form_not_the_database(
    client, manager, customer
):
    """The table has a CHECK on this; reaching it would be a 500."""
    response = client.post(
        reverse("console:company-edit", args=[customer.pk]),
        {"name": "", "reason": "محاولة"},
    )

    assert response.status_code == 200
    assert not Company.objects.filter(user=customer).exists()


# ---------------------------------------------------------------------------
# T809 — what "paid" is allowed to mean
# ---------------------------------------------------------------------------


@pytest.fixture
def invoice(customer) -> Invoice:
    return money.issue_invoice(customer=customer, amount=Decimal("20000.00"))


def test_an_invoice_with_no_posted_payment_reads_open(client, manager, invoice):
    body = body_of(client, reverse("console:invoice-detail", args=[invoice.pk]))

    assert invoice.state == InvoiceState.OPEN
    assert "لا دفعات مرحَّلة" in body


def test_odoos_draft_transfer_does_not_make_an_invoice_paid(client, manager, invoice):
    """T809's acceptance criterion, exactly.

    Odoo is holding a transfer as a draft. Nothing has been posted here, so the
    invoice is still owed — in v1 this row read "settled" and a car went out.
    """
    invoice.odoo_state_raw = "draft"
    invoice.save(update_fields=["odoo_state_raw"])

    body = body_of(client, reverse("console:invoice-detail", args=[invoice.pk]))
    invoice.refresh_from_db()

    assert invoice.state == InvoiceState.OPEN
    assert invoice.amount_paid == Decimal("0.00")
    assert money.derive_invoice_state(invoice) == InvoiceState.OPEN
    # Their word is shown, marked as theirs, and never as ours (Article 2-3).
    assert "كلام أودو" in body
    assert "مسدَّدة" not in body.split("حالة أودو")[0]


def test_a_posted_payment_does_make_it_paid(client, manager, invoice):
    money.record_payment(
        invoice=invoice,
        amount=Decimal("20000.00"),
        source="cash",
        reference="bank/1",
    )

    invoice.refresh_from_db()
    body = body_of(client, reverse("console:invoice-detail", args=[invoice.pk]))

    assert invoice.state == InvoiceState.PAID
    assert "لا دفعات مرحَّلة" not in body


def test_a_partial_payment_is_partial_not_paid(client, manager, invoice):
    money.record_payment(
        invoice=invoice, amount=Decimal("5000.00"), source="cash", reference="bank/2"
    )

    invoice.refresh_from_db()

    assert invoice.state == InvoiceState.PARTIAL
    assert invoice.outstanding == Decimal("15000.00")


def test_the_invoice_list_filters_on_the_derived_state(client, manager, invoice):
    body = body_of(client, reverse("console:invoices"), state=InvoiceState.OPEN)

    assert invoice.number in body


def test_the_invoice_list_says_so_when_empty(client, manager):
    body = body_of(client, reverse("console:invoices"), q="لا فاتورة بهذا الاسم")

    assert "لا فواتير مطابقة" in body


# ---------------------------------------------------------------------------
# The guard
# ---------------------------------------------------------------------------


def test_reading_a_customer_does_not_imply_editing_them(client, customer):
    reader = staff(Role.SUPPORT, phone="966500000042")
    client.force_login(reader)

    assert client.get(reverse("console:customers")).status_code == 200
    assert (
        client.post(
            reverse("console:customer-edit", args=[customer.pk]), edit_payload()
        ).status_code
        == 403
    )

    customer.refresh_from_db()
    assert customer.full_name == "عميل الاختبار"


def test_operations_cannot_read_invoices_it_was_not_given(client, invoice):
    """`invoices.view` is its own capability and operations happens to hold it.

    Asserted rather than assumed: the roles table is the kind of thing that
    drifts silently, and this is the screen that shows what customers owe.
    """
    from apps.core.permissions import Capability, can

    operations = staff(Role.OPERATIONS, phone="966500000043")

    assert can(operations, Capability.INVOICES_VIEW)
    assert not can(operations, Capability.INVOICES_MANAGE)
