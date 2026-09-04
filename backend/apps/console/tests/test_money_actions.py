"""T811 — the three admin money actions, and the two criteria they answer.

**I3 — nothing writes the ledger outside `money.services`.** There is already a
text check for it (`ops/checks/money_single_writer.py`), and this file runs it
against the whole tree rather than trusting that it is wired into CI: a guard
that exists and is not run is a guard that starts failing quietly.

**I4 — every admin money action is in the audit log, by actor and reason.** One
test per action, each asserting the row exists, names the person who pressed the
button, and carries the sentence they typed. And, in each case, that a missing
reason moves nothing at all — because the useful half of "a reason is required"
is not the error message, it is that the money stays where it was.

The three actions are three different trusts and the tests say so: confiscation
and correction need `money.act`, and an exception needs `money.exception` on top
of it. In v1 all three sat behind one "finance" flag, so whoever could read a
balance could confiscate it.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, AuctionState
from apps.core.models import AuditLog
from apps.core.permissions import Capability, Role, can
from apps.money import services as money
from apps.money.models import (
    Account,
    AccountKind,
    Hold,
    HoldState,
    Invoice,
    InvoiceState,
    Transaction,
    TransactionKind,
)
from apps.money.verification import verify_ledger

from .conftest import screen_of

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


def staff_user(phone: str, role: str, name: str = "موظف") -> User:
    user = User.objects.create_user(phone=phone, full_name=name, password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def finance(client) -> User:
    """`money.act`, but not `money.exception`. The ordinary money operator."""
    user = staff_user("966500000081", Role.FINANCE, "موظف مالية")
    client.force_login(user)
    return user


@pytest.fixture
def owner(db) -> User:
    return staff_user("966500000082", Role.OWNER, "المالك")


@pytest.fixture
def customer(db) -> User:
    person = User.objects.create_user(
        phone="966555555901", full_name="عميل الأفعال", password="x"
    )
    money.deposit_insurance(
        user=person, amount=Decimal("25000.00"), source="cash", reference="pay-811-1"
    )
    return person


@pytest.fixture
def live_auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=811,
        title="مزاد الأفعال",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


@pytest.fixture
def bidding_hold(customer, live_auction) -> Hold:
    return money.hold_for_auction(user=customer, auction=live_auction)


@pytest.fixture
def dues_hold(customer) -> Hold:
    invoice = Invoice.objects.create(
        customer=customer,
        number="INV/811/1",
        amount=Decimal("8000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
    )
    return money.lock_for_invoice(user=customer, invoice=invoice)


def free_balance(person: User) -> Decimal:
    return money.account_for(person, AccountKind.INSURANCE_FREE).balance


# ---------------------------------------------------------------------------
# I3 — the ledger has one writer, and the guard that says so actually runs
# ---------------------------------------------------------------------------


def test_nothing_in_the_tree_writes_the_ledger_outside_the_service():
    """I3, run rather than assumed.

    The check is a file in `ops/checks`. A file is only a guard while something
    executes it, and this is the test that does — including against the three
    actions added by T811, which are exactly the shape of write it exists to
    catch (spec 009's own words: "an admin action in phase 009 that writes an
    `Entry` directly").
    """
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / "ops" / "checks"))
    try:
        import money_single_writer as guard
    finally:
        sys.path.pop(0)

    backend = root / "backend"
    found = guard.violations([backend / "apps", backend / "config", backend / "tests"])
    assert found == [], found


def test_the_actions_module_posts_nothing_itself(finance):
    """Every write it performs is a call into a service, by name."""
    import ast
    import pathlib

    source = pathlib.Path("apps/console/actions.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert {"confiscate", "grant_bidding_exception", "correct"} <= called
    assert "post" not in called


# ---------------------------------------------------------------------------
# I4 — confiscation
# ---------------------------------------------------------------------------


def test_confiscation_moves_the_money_and_names_who_decided(
    client, finance, customer, bidding_hold
):
    response = client.post(
        reverse("console:money-confiscate", args=[bidding_hold.pk]),
        {"reason": "انسحب بعد الترسية ثلاث مرات"},
    )

    assert response.status_code == 302
    bidding_hold.refresh_from_db()
    assert bidding_hold.state == HoldState.CONSUMED

    entry = AuditLog.objects.get(action="money.confiscate")
    assert entry.actor_id == finance.pk
    assert "انسحب بعد الترسية ثلاث مرات" in entry.note
    assert entry.before["state"] == HoldState.ACTIVE
    assert entry.after["state"] == HoldState.CONSUMED

    confiscated = Account.objects.get(kind=AccountKind.CONFISCATED, owner__isnull=True)
    assert confiscated.balance == TEN_K
    assert verify_ledger() == []


def test_a_confiscation_with_no_reason_moves_nothing(
    client, finance, customer, bidding_hold
):
    """The useful half of «سبب مطلوب» is that the money stays where it was."""
    before = free_balance(customer)

    client.post(reverse("console:money-confiscate", args=[bidding_hold.pk]), {})

    bidding_hold.refresh_from_db()
    assert bidding_hold.state == HoldState.ACTIVE
    assert free_balance(customer) == before
    assert not AuditLog.objects.filter(action="money.confiscate").exists()
    assert not Transaction.objects.filter(
        kind=TransactionKind.INSURANCE_CONFISCATE
    ).exists()


def test_a_whitespace_reason_is_not_a_reason(client, finance, bidding_hold):
    client.post(
        reverse("console:money-confiscate", args=[bidding_hold.pk]),
        {"reason": "     "},
    )

    bidding_hold.refresh_from_db()
    assert bidding_hold.state == HoldState.ACTIVE


def test_confiscation_needs_money_act(client, customer, bidding_hold):
    """Support reads balances all day and may not take one."""
    agent = staff_user("966500000083", Role.SUPPORT, "دعم")
    assert can(agent, Capability.MONEY_VIEW)
    assert not can(agent, Capability.MONEY_ACT)

    client.force_login(agent)
    response = client.post(
        reverse("console:money-confiscate", args=[bidding_hold.pk]),
        {"reason": "محاولة"},
    )

    assert response.status_code == 403
    bidding_hold.refresh_from_db()
    assert bidding_hold.state == HoldState.ACTIVE


# ---------------------------------------------------------------------------
# I4 — the exception, and the third trust
# ---------------------------------------------------------------------------


def test_the_owner_grants_an_exception_and_it_is_recorded(
    client, owner, customer, dues_hold
):
    client.force_login(owner)

    client.post(
        reverse("console:money-exception", args=[dues_hold.pk]),
        {"reason": "اتفاق سداد مكتوب على ثلاث دفعات"},
    )

    dues_hold.refresh_from_db()
    assert dues_hold.exception_granted_by_id == owner.pk
    assert dues_hold.exception_note == "اتفاق سداد مكتوب على ثلاث دفعات"

    entry = AuditLog.objects.get(action="bidding.exception_granted")
    assert entry.actor_id == owner.pk
    assert "اتفاق سداد" in entry.note


def test_an_exception_moves_no_money(client, owner, customer, dues_hold):
    """The lock stays where it is and the debt stays a debt."""
    before = free_balance(customer)
    locked = money.account_for(customer, AccountKind.INSURANCE_LOCKED).balance

    client.force_login(owner)
    client.post(
        reverse("console:money-exception", args=[dues_hold.pk]),
        {"reason": "اتفاق سداد"},
    )

    assert free_balance(customer) == before
    assert money.account_for(customer, AccountKind.INSURANCE_LOCKED).balance == locked
    assert verify_ledger() == []


def test_money_act_alone_cannot_grant_an_exception(client, finance, dues_hold):
    """The one action that puts a bidder in an auction with nothing behind them.

    Finance may confiscate — taking money that is already ours to take — and may
    not do this. v1 collapsed both into one flag.
    """
    assert can(finance, Capability.MONEY_ACT)
    assert not can(finance, Capability.MONEY_EXCEPTION)

    response = client.post(
        reverse("console:money-exception", args=[dues_hold.pk]),
        {"reason": "محاولة"},
    )

    assert response.status_code == 403
    dues_hold.refresh_from_db()
    assert dues_hold.exception_granted_by_id is None


def test_an_exception_with_no_reason_grants_nothing(client, owner, dues_hold):
    client.force_login(owner)

    client.post(reverse("console:money-exception", args=[dues_hold.pk]), {})

    dues_hold.refresh_from_db()
    assert dues_hold.exception_note == ""
    assert dues_hold.exception_granted_by_id is None


# ---------------------------------------------------------------------------
# I4 — the correction
# ---------------------------------------------------------------------------


def test_a_correction_reverses_the_movement_and_leaves_the_original(
    client, finance, customer
):
    """History gains a row. Nothing in this system edits one."""
    original = money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-811-wrong"
    )
    before = free_balance(customer)

    client.post(
        reverse("console:money-correct", args=[original.pk]),
        {"reason": "أُودعت في حساب العميل الخطأ"},
    )

    original.refresh_from_db()
    assert original.kind == TransactionKind.INSURANCE_TOPUP, "the original is untouched"

    reversal = Transaction.objects.get(reverses=original)
    assert reversal.kind == TransactionKind.REVERSAL
    assert reversal.created_by_id == finance.pk
    assert free_balance(customer) == before - TEN_K
    assert verify_ledger() == []


def test_a_correction_names_its_operator_in_the_audit_log(client, finance, customer):
    """The reversal says what moved; the audit row says who decided it should.

    A dispute about a correction is always about the decision, never about the
    arithmetic — the arithmetic is in the entries and cannot be argued with.
    """
    original = money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-811-audit"
    )

    client.post(
        reverse("console:money-correct", args=[original.pk]),
        {"reason": "مرجع الدفعة كان لعميل آخر"},
    )

    entry = AuditLog.objects.get(action="money.correct")
    assert entry.actor_id == finance.pk
    assert entry.note == "مرجع الدفعة كان لعميل آخر"
    assert entry.entity_id == str(original.pk)


def test_a_correction_with_no_reason_reverses_nothing(client, finance, customer):
    original = money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-811-noreason"
    )
    before = free_balance(customer)

    client.post(reverse("console:money-correct", args=[original.pk]), {})

    assert not Transaction.objects.filter(reverses=original).exists()
    assert free_balance(customer) == before
    assert not AuditLog.objects.filter(action="money.correct").exists()


def test_the_same_movement_cannot_be_corrected_twice(client, finance, customer):
    """Correcting a correction is how a balance ends up wrong in both directions."""
    original = money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-811-twice"
    )

    client.post(reverse("console:money-correct", args=[original.pk]), {"reason": "مرة"})
    client.post(reverse("console:money-correct", args=[original.pk]), {"reason": "مرتين"})

    assert Transaction.objects.filter(reverses=original).count() == 1
    assert verify_ledger() == []


# ---------------------------------------------------------------------------
# The screen itself
# ---------------------------------------------------------------------------


def test_a_get_performs_no_action(client, finance, customer, bidding_hold):
    """A link that takes a deposit is a link the back button presses."""
    for name, pk in (
        ("console:money-confiscate", bidding_hold.pk),
        ("console:money-correct", Transaction.objects.first().pk),
    ):
        client.get(reverse(name, args=[pk]))

    bidding_hold.refresh_from_db()
    assert bidding_hold.state == HoldState.ACTIVE
    assert not AuditLog.objects.filter(action__startswith="money.").exists()


def test_the_page_shows_what_each_button_would_act_on(
    client, finance, customer, bidding_hold, live_auction
):
    """«صادر الحجز 4102» is not a sentence anybody can check before pressing it."""
    body = client.get(
        reverse("console:money-actions", args=[customer.pk])
    ).content.decode()

    assert "10000.00" in body
    assert f"مزاد {live_auction.number}" in body
    assert "يحرّك فلوساً ويُسجَّل باسمك" in body


def test_the_exception_form_is_offered_only_to_whoever_may_use_it(
    client, finance, owner, customer, dues_hold
):
    """A form that always answers 403 teaches its reader that the console is broken."""
    url = reverse("console:money-actions", args=[customer.pk])

    for_finance = client.get(url).content.decode()
    assert reverse("console:money-exception", args=[dues_hold.pk]) not in for_finance

    client.force_login(owner)
    for_owner = client.get(url).content.decode()
    assert reverse("console:money-exception", args=[dues_hold.pk]) in for_owner


def test_the_read_only_ledger_still_offers_no_button(client, finance, customer):
    """T810's guarantee survives T811: the reading screen gained a link, not a form."""
    body = client.get(
        reverse("console:money-customer", args=[customer.pk])
    ).content.decode()

    assert 'method="post"' not in screen_of(body).lower()
    assert reverse("console:money-actions", args=[customer.pk]) in body


def test_support_is_not_shown_the_way_to_the_actions(client, customer):
    agent = staff_user("966500000084", Role.SUPPORT, "دعم آخر")
    client.force_login(agent)

    body = client.get(
        reverse("console:money-customer", args=[customer.pk])
    ).content.decode()

    assert reverse("console:money-actions", args=[customer.pk]) not in body
