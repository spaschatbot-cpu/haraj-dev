"""T815 — the audit search, held to «كل فعل مالي إداري يظهر في البحث».

The acceptance criterion names the money actions specifically, so the file plays
all three for real — a confiscation, an exception and a correction, through the
T811 screens — and then asks the search for each of them by every filter it
offers. Nothing is inserted into `AuditLog` by hand: a search proven against rows
a test wrote is a search proven against rows the product does not produce.

There is a fourth test that matters more than the three, and it is
`test_no_recorded_action_is_missing_from_the_filter`. The criterion as written
would be satisfied by a screen that finds today's actions and quietly stops
offering tomorrow's — the dropdown is the part that rots, because it is the part
somebody has to remember to update. So it is derived from the rows, and the test
asserts the derivation rather than the current contents.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, AuctionState
from apps.console.audit import search
from apps.core.models import AuditLog
from apps.core.permissions import Capability, Role, can
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

from .conftest import screen_of

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")

#: The actions T811 produces. Named here because the criterion names them.
MONEY_ACTIONS = ("money.confiscate", "bidding.exception_granted", "money.correct")


def staff_user(phone: str, role: str, name: str) -> User:
    user = User.objects.create_user(phone=phone, full_name=name, password="x")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


@pytest.fixture
def auditor(client) -> User:
    user = staff_user("966500000091", Role.FINANCE, "مدقّق")
    client.force_login(user)
    return user


@pytest.fixture
def customer(db) -> User:
    person = User.objects.create_user(
        phone="966555556001", full_name="عميل التدقيق", password="x"
    )
    money.deposit_insurance(
        user=person, amount=Decimal("40000.00"), source="cash", reference="pay-815-1"
    )
    return person


@pytest.fixture
def played(client, customer) -> User:
    """All three admin money actions, performed through the screens, for real.

    Returns the owner who performed them: the owner holds every capability, so
    one session can play all three — and «من فعل هذا؟» having a single answer
    across three actions is what the actor filter is then tested against.
    """
    actor = staff_user("966500000092", Role.OWNER, "المالك")
    client.force_login(actor)

    now = timezone.now()
    auction = Auction.objects.create(
        number=815,
        title="مزاد التدقيق",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )
    bidding_hold = money.hold_for_auction(user=customer, auction=auction)
    client.post(
        reverse("console:money-confiscate", args=[bidding_hold.pk]),
        {"reason": "انسحب بعد الترسية"},
    )

    invoice = Invoice.objects.create(
        customer=customer,
        number="INV/815/1",
        amount=Decimal("5000.00"),
        state=InvoiceState.OPEN,
        issued_at=now,
    )
    dues_hold = money.lock_for_invoice(user=customer, invoice=invoice)
    client.post(
        reverse("console:money-exception", args=[dues_hold.pk]),
        {"reason": "اتفاق سداد مكتوب"},
    )

    wrong = money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-815-wrong"
    )
    client.post(
        reverse("console:money-correct", args=[wrong.pk]),
        {"reason": "مرجع الدفعة لعميل آخر"},
    )

    return actor


# ---------------------------------------------------------------------------
# The acceptance criterion
# ---------------------------------------------------------------------------


def test_every_admin_money_action_is_findable(played):
    """The criterion, one filter at a time.

    Each of the three is asked for by its action name, and the row that comes
    back is the row the service wrote — same actor, same typed sentence.
    """
    for action in MONEY_ACTIONS:
        found = list(search(action=action))
        assert len(found) == 1, action
        assert found[0].actor_id == played.pk
        assert found[0].note

    assert set(AuditLog.objects.values_list("action", flat=True)) >= set(MONEY_ACTIONS)


def test_no_recorded_action_is_missing_from_the_filter(client, played, auditor):
    """The dropdown is derived from the rows, so it cannot go stale.

    A hardcoded list satisfies the criterion today and silently stops offering
    the action somebody adds next month — and an action nobody can filter for is
    an action nobody audits.
    """
    client.force_login(auditor)
    body = client.get(reverse("console:audit")).content.decode()

    for action in AuditLog.objects.values_list("action", flat=True).distinct():
        assert f'value="{action}"' in body, action


def test_the_search_finds_them_by_who_did_it(played, customer):
    """«ماذا فعل هذا الموظف؟» — the way a dispute about an operator starts."""
    by_phone = list(search(actor=played.phone))
    by_name = list(search(actor="المالك"))

    assert len(by_phone) >= 3
    assert {row.pk for row in by_phone} == {row.pk for row in by_name}
    assert {row.actor_id for row in by_phone} == {played.pk}
    assert set(MONEY_ACTIONS) <= {row.action for row in by_phone}


def test_the_search_finds_them_by_subject(played, customer):
    """«كل ما جرى على هذا الحجز» — the way a dispute about a balance starts."""
    confiscation = AuditLog.objects.get(action="money.confiscate")

    by_full = list(search(entity=f"{confiscation.entity_type}:{confiscation.entity_id}"))
    by_type = list(search(entity=confiscation.entity_type))

    assert [row.pk for row in by_full] == [confiscation.pk]
    assert confiscation.pk in {row.pk for row in by_type}


def test_the_search_finds_them_by_window(played):
    """A whole day, not midnight.

    «to 2026-09-03» means everything that happened on the third in the mind of
    whoever typed it, and the row people are looking for is disproportionately
    often the last one of the day.
    """
    today = timezone.localtime(timezone.now()).date().isoformat()

    same_day = list(search(since=today, until=today))
    assert set(MONEY_ACTIONS) <= {row.action for row in same_day}

    tomorrow = (
        (timezone.localtime(timezone.now()) + timezone.timedelta(days=1))
        .date()
        .isoformat()
    )
    assert list(search(since=tomorrow)) == []


def test_the_filters_narrow_together(played, customer):
    """Actor and action and window, all at once — one row, not three lists."""
    today = timezone.localtime(timezone.now()).date().isoformat()

    found = list(
        search(actor=played.phone, action="money.correct", since=today, until=today)
    )

    assert len(found) == 1
    assert found[0].note == "مرجع الدفعة لعميل آخر"


def test_an_unparseable_date_narrows_nothing_rather_than_hiding_everything(played):
    """A half-typed date must not silently empty the page.

    Returning nothing for `2026-09-` reads as "this never happened", which is
    the one answer an audit search must never give by accident.
    """
    everything = search().count()

    assert search(since="2026-09-").count() == everything
    assert search(until="غير تاريخ").count() == everything


# ---------------------------------------------------------------------------
# The screen
# ---------------------------------------------------------------------------


def test_the_page_renders_the_rows_it_found(client, played, auditor):
    client.force_login(auditor)

    body = client.get(
        reverse("console:audit"), {"action": "money.confiscate"}
    ).content.decode()

    assert "انسحب بعد الترسية" in body
    assert played.full_name in body
    assert "1 قيداً" in body


def test_a_platform_action_says_so_rather_than_leaving_a_blank(client, auditor):
    """A NULL actor is information — a cron, a webhook — not a missing value."""
    from apps.core import audit as recorder

    recorder.record(
        action="odoo.settled_invoice",
        entity_type="money.invoice",
        entity_id="9",
        note="من رسالة أودو",
    )

    body = client.get(reverse("console:audit")).content.decode()

    assert "النظام" in body


def test_the_page_offers_no_way_to_change_a_row(client, played, auditor):
    """An audit trail that can be edited proves nothing about the trail."""
    client.force_login(auditor)

    body = screen_of(client.get(reverse("console:audit")).content.decode()).lower()

    assert 'method="post"' not in body


def test_it_needs_audit_view(client, played):
    """Operations runs auctions and does not read who moved money."""
    operator = staff_user("966500000093", Role.OPERATIONS, "مشغّل")
    assert not can(operator, Capability.AUDIT_VIEW)

    client.force_login(operator)
    assert client.get(reverse("console:audit")).status_code == 403


def test_support_cannot_read_it_either(client, played):
    agent = staff_user("966500000094", Role.SUPPORT, "دعم")
    assert not can(agent, Capability.AUDIT_VIEW)

    client.force_login(agent)
    assert client.get(reverse("console:audit")).status_code == 403
