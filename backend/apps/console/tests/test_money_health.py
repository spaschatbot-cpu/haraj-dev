"""T813 — the money health screen, and the amounts it is forbidden to inflate.

The acceptance criterion is *every amount shown equals what is actually missing
— a test that compares against the ledger*, and the task carries a warning
beside it: **⚠️ لا يُبالَغ في أي مبلغ معروض.** One inflated figure and the
screen loses its meaning, because the next real one reads like the last false
one.

There are exactly three ways this page could inflate a number, and there is a
test here for each:

* by keeping a note whose cause is gone — so the notes are recomputed, and
  `test_a_finding_disappears_when_its_cause_does` fixes the cause and asserts
  the page goes quiet;
* by reading every historical `BalanceCheck` as an open item — so only the
  latest per customer counts, and a customer who has since been reconciled
  leaves the list;
* by presenting the suspense receipts' sum as what is unattributed — so the
  figure is the bucket's balance, and a receipt that has been attributed away
  is a movement in the list and not a riyal in the total.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db.models import Sum
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.console.health import health_report, suspense_state
from apps.core.permissions import Capability, Role, can
from apps.money import services as money
from apps.money.models import Account, AccountKind, Entry
from apps.money.verification import verify_ledger
from apps.odoo.models import BalanceCheck
from apps.odoo.reconciliation import open_differences

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")
ZERO = Decimal("0.00")


@pytest.fixture
def diagnostician(client) -> User:
    user = User.objects.create_user(
        phone="966500000051", full_name="موظف تشخيص", password="x"
    )
    user.is_staff = True
    user.console_role = Role.FINANCE
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def holder(db) -> User:
    customer = User.objects.create_user(
        phone="966555555601", full_name="عميل الصحة", password="x"
    )
    money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-813-1"
    )
    return customer


def page(client) -> str:
    response = client.get(reverse("console:money-health"))
    assert response.status_code == 200
    return response.content.decode()


# ---------------------------------------------------------------------------
# 1. The ledger against itself — notes that open and close by themselves
# ---------------------------------------------------------------------------


def test_a_healthy_book_says_so_and_lists_nothing(client, diagnostician, holder):
    report = health_report()

    assert report.is_clean
    assert report.findings == []
    assert "لا ملاحظات" in page(client)


def test_a_drift_appears_with_the_ledgers_own_words(client, diagnostician, holder):
    """Not a rephrasing — the finding `verify_ledger` produced, as it produced it."""
    Account.objects.filter(owner=holder, kind=AccountKind.INSURANCE_FREE).update(
        balance=Decimal("15000.00")
    )

    report = health_report()

    assert [str(f) for f in report.findings] == [str(f) for f in verify_ledger()]
    assert len(report.findings) == 1

    body = page(client)
    assert report.findings[0].detail in body
    assert "لا ملاحظات" not in body


def test_a_finding_disappears_when_its_cause_does(client, diagnostician, holder):
    """The self-closing note, which is the whole of T220's acceptance.

    Nothing is marked resolved. The cause is repaired and the page is asked
    again — a stored note would still be sitting there, and the reason v1's
    reconciliation queue went unread is that its oldest items had all been
    fixed months earlier.
    """
    account = Account.objects.get(owner=holder, kind=AccountKind.INSURANCE_FREE)
    real = account.balance

    Account.objects.filter(pk=account.pk).update(balance=Decimal("15000.00"))
    assert len(health_report().findings) == 1

    Account.objects.filter(pk=account.pk).update(balance=real)

    assert health_report().findings == []
    assert "لا ملاحظات" in page(client)


# ---------------------------------------------------------------------------
# 2. The ledger against Odoo — the latest comparison, not every one ever made
# ---------------------------------------------------------------------------


def _check(user: User, *, ours: Decimal, theirs: Decimal) -> BalanceCheck:
    return BalanceCheck.objects.create(
        user=user,
        ours=ours,
        theirs=theirs,
        difference=ours - theirs,
        method="test",
        detail={},
    )


def test_a_difference_against_odoo_is_shown_with_both_sides(
    client, diagnostician, holder
):
    """Both numbers and the gap. A gap alone cannot be investigated."""
    _check(holder, ours=TEN_K, theirs=ZERO)

    report = health_report()

    assert len(report.differences) == 1
    body = page(client)
    assert "10000.00" in body
    assert "0.00" in body


def test_a_customer_reconciled_since_is_no_longer_reported(client, diagnostician, holder):
    """The inflation this closes: a shortfall fixed in March, still shown in September.

    `check_customer` writes a row on every run, agreement or not — that is what
    distinguishes «فُحص وطابق» from «لم يُفحص». Reading them all back as open
    items means the agreeing row does not replace the disagreeing one, it merely
    joins it.
    """
    old = _check(holder, ours=TEN_K, theirs=ZERO)
    assert list(open_differences()) == [old]

    BalanceCheck.objects.filter(pk=old.pk).update(
        checked_at=timezone.now() - timezone.timedelta(days=30)
    )
    _check(holder, ours=TEN_K, theirs=TEN_K)

    assert list(open_differences()) == []
    assert health_report().differences == []
    assert "لا فروق مفتوحة" in page(client)


def test_a_difference_a_person_explained_is_closed_too(client, diagnostician, holder):
    """The other way a note ends: examined and explained rather than removed."""
    check = _check(holder, ours=TEN_K, theirs=ZERO)
    BalanceCheck.objects.filter(pk=check.pk).update(
        resolved_at=timezone.now(), resolution="دفعة سجّلتها المحاسبة يدوياً"
    )

    assert health_report().differences == []


def test_the_difference_links_to_that_customers_ledger(client, diagnostician, holder):
    """The next question is always «ماذا في دفتره؟», and it should be one click."""
    _check(holder, ours=TEN_K, theirs=ZERO)

    assert reverse("console:money-customer", args=[holder.pk]) in page(client)


# ---------------------------------------------------------------------------
# 3. Suspense — the pool, never the sum of what has ever landed in it
# ---------------------------------------------------------------------------


def test_the_suspense_figure_is_the_bucket_not_the_receipts(
    client, diagnostician, holder
):
    """20,000 arrived unattributed, 10,000 was given an owner. 10,000 is missing.

    A screen adding the receipts reports 20,000 — twice what is actually
    unattributed, and precisely the exaggeration the task warns about. The
    assertion below is written as the comparison against the ledger that the
    acceptance criterion asks for.
    """
    money.receive_unattributed(amount=TEN_K, source="cash", reference="susp-1")
    money.receive_unattributed(amount=TEN_K, source="cash", reference="susp-2")
    money.attribute(user=holder, amount=TEN_K, reference="susp-1")

    state = suspense_state()

    receipts_ever = Entry.objects.filter(
        account__kind=AccountKind.SUSPENSE, amount__gt=ZERO
    ).aggregate(total=Sum("amount"))["total"]
    assert receipts_ever == Decimal("20000.00")

    # The figure shown is the bucket, and the bucket is what its entries say.
    assert state.balance == TEN_K
    assert state.derived == TEN_K
    assert state.agrees

    body = page(client)
    assert "20000.00" not in body

    # And it equals what the ledger holds, read independently of this screen.
    assert (
        Account.objects.get(kind=AccountKind.SUSPENSE, owner__isnull=True).balance
        == TEN_K
    )


def test_the_movements_are_shown_as_movements(client, diagnostician, holder):
    """In and out, both. A list of arrivals only reads as a list of open claims."""
    money.receive_unattributed(amount=TEN_K, source="cash", reference="susp-3")
    money.attribute(user=holder, amount=TEN_K, reference="susp-3")

    state = suspense_state()

    assert len(state.movements) == 2
    assert {entry.amount for entry in state.movements} == {TEN_K, -TEN_K}
    assert state.balance == ZERO


def test_nothing_suspended_is_a_clean_page(client, diagnostician, holder):
    state = suspense_state()

    assert state.balance == ZERO
    assert state.movements == []
    assert health_report().is_clean


def test_a_drifted_suspense_bucket_is_called_out(client, diagnostician, holder):
    """The pool is a cache like any other balance, and is checked like one."""
    money.receive_unattributed(amount=TEN_K, source="cash", reference="susp-4")
    Account.objects.filter(kind=AccountKind.SUSPENSE, owner__isnull=True).update(
        balance=Decimal("50000.00")
    )

    state = suspense_state()

    assert not state.agrees
    assert state.derived == TEN_K
    body = page(client)
    assert "لا تطابق" in body or "لا يطابق" in body
    assert "10000.00" in body


# ---------------------------------------------------------------------------
# The three are never added together
# ---------------------------------------------------------------------------


def test_the_three_kinds_are_never_summed(client, diagnostician, holder):
    """A cache drift of 5,000 and an Odoo gap of 5,000 may be one 5,000.

    Adding them reports 10,000 missing where 5,000 is missing — a screen that
    overstates a shortfall once is a screen nobody opens again.
    """
    Account.objects.filter(owner=holder, kind=AccountKind.INSURANCE_FREE).update(
        balance=Decimal("15000.00")
    )
    _check(holder, ours=Decimal("15000.00"), theirs=TEN_K)
    money.receive_unattributed(
        amount=Decimal("5000.00"), source="cash", reference="susp-5"
    )

    body = page(client)

    assert "15000.00" in body
    assert "5000.00" in body
    assert "20000.00" not in body, "the three kinds must not be added together"
    assert "25000.00" not in body


# ---------------------------------------------------------------------------
# Who may open it
# ---------------------------------------------------------------------------


def test_the_page_needs_diagnostics_view(client, holder):
    outsider = User.objects.create_user(
        phone="966500000052", full_name="غريب", password="x"
    )
    assert not can(outsider, Capability.DIAGNOSTICS_VIEW)

    client.force_login(outsider)
    assert client.get(reverse("console:money-health")).status_code == 403


def test_support_may_read_it(holder):
    """Support is asked «هل فلوسه ناقصة؟» before anybody else is."""
    agent = User.objects.create_user(phone="966500000053", full_name="دعم", password="x")
    agent.is_staff = True
    agent.console_role = Role.SUPPORT
    agent.save(update_fields=["is_staff", "console_role"])

    client = Client()
    client.force_login(agent)
    assert client.get(reverse("console:money-health")).status_code == 200
