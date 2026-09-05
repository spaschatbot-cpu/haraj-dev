"""HR-05 — the source of an invoice is what says whether its amount has tax in it.

``PHASE_03`` §2, which the rebuild notes call the finest trap in the v1 files.
It is not a rounding bug. It is a silent 15% overcharge:

* an invoice **we** raise carries the awarded price, which is *before* tax;
* an invoice **Odoo** sends back carries a total that *already includes* it.

Apply one equation to both and every Odoo invoice is taxed twice — correctly as
far as any single line of code can tell, and visible to nobody until a customer
adds up their own invoice.

Nothing computed tax when this was written, and that is exactly why the source
is recorded now: the day something does, the answer has to already exist. A
column added afterwards can only guess at rows already written.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from apps.money import services
from apps.money.models import Invoice, InvoiceSource, InvoiceState

pytestmark = pytest.mark.django_db


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966501234567", full_name="عميل", national_id="1234567890"
    )


def an_invoice(customer, *, amount: str, source: str) -> Invoice:
    return Invoice.objects.create(
        customer=customer,
        number=f"T-{source}-{amount}",
        amount=Decimal(amount),
        state=InvoiceState.OPEN,
        source=source,
        issued_at=timezone.now(),
    )


# ---------------------------------------------------------------------------
# The rule itself
# ---------------------------------------------------------------------------


def test_our_own_invoice_is_taxed_on_top(customer):
    """The awarded price is the base; the tax is added to it."""
    invoice = an_invoice(customer, amount="100000.00", source=InvoiceSource.LOCAL)

    breakdown = services.tax_of(invoice)

    assert breakdown.base == Decimal("100000.00")
    assert breakdown.tax == Decimal("15000.00")
    assert breakdown.total == Decimal("115000.00")
    assert breakdown.amount_was_inclusive is False


def test_an_odoo_invoice_is_taxed_out_of_the_total(customer):
    """The trap. Multiplying this by 1.15 would bill 132,250 for a 115,000 car."""
    invoice = an_invoice(customer, amount="115000.00", source=InvoiceSource.ODOO_SYNC)

    breakdown = services.tax_of(invoice)

    assert breakdown.base == Decimal("100000.00")
    assert breakdown.tax == Decimal("15000.00")
    assert breakdown.total == Decimal("115000.00"), "تُحصَّل الضريبة مرتين"
    assert breakdown.amount_was_inclusive is True


def test_the_same_number_means_two_different_totals(customer):
    """Side by side, because this is the whole point of recording the source."""
    ours = an_invoice(customer, amount="50000.00", source=InvoiceSource.LOCAL)
    theirs = an_invoice(customer, amount="50000.00", source=InvoiceSource.ODOO_SYNC)

    assert services.tax_of(ours).total == Decimal("57500.00")
    assert services.tax_of(theirs).total == Decimal("50000.00")


@pytest.mark.parametrize("amount", ["0.01", "1.00", "33333.33", "99999.99", "1000000.00"])
def test_the_parts_always_add_up_to_the_total(customer, amount):
    """An invoice whose lines do not sum to its total is one no auditor accepts.

    Rounding base and tax independently is how that happens, so the tax is
    derived from the base rather than computed beside it.
    """
    for source in (InvoiceSource.LOCAL, InvoiceSource.ODOO_SYNC):
        invoice = an_invoice(customer, amount=amount, source=source)

        breakdown = services.tax_of(invoice)

        assert breakdown.base + breakdown.tax == breakdown.total
        assert breakdown.base.as_tuple().exponent == -2
        assert breakdown.tax.as_tuple().exponent == -2


def test_an_odoo_total_survives_the_round_trip(customer):
    """Taking the tax out and putting it back must land on the same riyal."""
    invoice = an_invoice(customer, amount="115000.00", source=InvoiceSource.ODOO_SYNC)

    breakdown = services.tax_of(invoice)

    assert breakdown.total == invoice.amount


def test_the_rate_comes_from_the_setting(customer):
    invoice = an_invoice(customer, amount="100.00", source=InvoiceSource.LOCAL)

    with override_settings(VAT_RATE="0.05"):
        assert services.tax_of(invoice).tax == Decimal("5.00")


def test_the_rate_is_a_decimal_and_never_a_float():
    """Article 3-2, on the one path that would be most tempting to shortcut."""
    assert isinstance(services.vat_rate(), Decimal)
    assert services.vat_rate() == Decimal("0.15")


# ---------------------------------------------------------------------------
# Where the source comes from
# ---------------------------------------------------------------------------


def test_an_invoice_we_raise_says_it_is_ours(customer):
    invoice = services.issue_invoice(customer=customer, amount=Decimal("70000.00"))

    assert invoice.source == InvoiceSource.LOCAL


def test_the_database_refuses_an_invoice_that_names_no_source(customer):
    """A default would be the trap itself, so there is none — the schema refuses.

    An Odoo invoice filed as `local` by a caller who forgot reads as pre-tax and
    gets taxed a second time, correctly as far as any code can tell. Article 3-3:
    the rule that can live in the schema lives there.
    """
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            customer=customer,
            number="T-NO-SOURCE",
            amount=Decimal("100.00"),
            state=InvoiceState.OPEN,
            issued_at=timezone.now(),
        )


def test_only_the_two_known_sources_are_accepted(customer):
    with pytest.raises(IntegrityError), transaction.atomic():
        Invoice.objects.create(
            customer=customer,
            number="T-BAD-SOURCE",
            amount=Decimal("100.00"),
            state=InvoiceState.OPEN,
            source="guessed",
            issued_at=timezone.now(),
        )
