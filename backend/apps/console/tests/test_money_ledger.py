"""T810 — the deposits ledger, and the number it is not allowed to invent.

The acceptance criterion is one sentence — *the totals match `verify_ledger`
exactly* — and it has two halves that need separate tests:

* on a healthy book, every figure the screen prints equals what the entries
  add up to;
* on a book that has drifted, the screen **says so** rather than printing the
  stored number as though it were the answer. A screen that silently picks the
  cached balance turns a hole in the books into a healthy-looking balance, and
  that is the failure mode the whole verification module exists to catch.

The drift is created the only way it can be — by writing `Account.balance`
straight through `QuerySet.update`, which is the one path in the codebase that
does not go through `post`. That is not a supported operation; it is a
simulation of the bug (a crashed process between the entry and the cache) that
the screen has to survive.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.db.models import Sum
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, AuctionState
from apps.console.money import derived_total, ledger_for
from apps.core.permissions import Capability, Role, can
from apps.money import services as money
from apps.money.models import Account, AccountKind, Entry, Hold, HoldReason, HoldState
from apps.money.verification import verify_customer, verify_ledger

from .conftest import screen_of

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")
ZERO = Decimal("0.00")


@pytest.fixture
def reader(client) -> User:
    """Support: may read the ledger, may not move a riyal in it."""
    user = User.objects.create_user(
        phone="966500000041", full_name="موظف دعم", password="x"
    )
    user.is_staff = True
    user.console_role = Role.SUPPORT
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def depositor(db) -> User:
    """A customer with real money, deposited the way real money arrives."""
    customer = User.objects.create_user(
        phone="966555555501", full_name="عميل الدفتر", password="x"
    )
    money.deposit_insurance(
        user=customer,
        amount=Decimal("25000.00"),
        source="cash",
        reference="pay-810-1",
    )
    return customer


@pytest.fixture
def live_auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=810,
        title="مزاد الدفتر",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


def body_for(reader: User, customer: User) -> str:
    """One customer's page, rendered, as the person guarding it would see it."""
    client = Client()
    client.force_login(reader)
    response = client.get(reverse("console:money-customer", args=[customer.pk]))
    assert response.status_code == 200
    return response.content.decode()


# ---------------------------------------------------------------------------
# The acceptance criterion
# ---------------------------------------------------------------------------


def test_the_total_shown_equals_what_the_entries_add_up_to(depositor, live_auction):
    """The screen's total is the entries' sum, not a figure computed beside it."""
    money.hold_for_auction(user=depositor, auction=live_auction)

    data = ledger_for(depositor)

    assert data.snapshot.total == derived_total(depositor)
    assert data.snapshot.total == Decimal("25000.00")
    assert verify_ledger() == []
    assert data.is_sound


def test_every_bucket_shown_equals_its_own_entries(depositor, live_auction):
    """Not just the grand total — each pot separately.

    A screen whose grand total is right while two buckets are wrong in opposite
    directions is a screen telling somebody a held deposit is free money.
    """
    money.hold_for_auction(user=depositor, auction=live_auction)
    data = ledger_for(depositor)

    for bucket in data.snapshot.buckets:
        from_entries = (
            Entry.objects.filter(owner=depositor, account__kind=bucket.kind).aggregate(
                total=Sum("amount")
            )["total"]
            or ZERO
        )
        assert bucket.amount == from_entries, bucket.kind

    held = next(b for b in data.snapshot.buckets if b.kind == AccountKind.INSURANCE_HELD)
    free = next(b for b in data.snapshot.buckets if b.kind == AccountKind.INSURANCE_FREE)
    assert held.amount == TEN_K
    assert free.amount == Decimal("15000.00")


def test_a_drifted_balance_is_reported_and_not_presented_as_the_answer(reader, depositor):
    """The cache disagrees with the entries — and the page says which two numbers.

    This is what the criterion is really about. Without it the page would render
    the stored 99,000 with no hint that the entries say 25,000.
    """
    Account.objects.filter(owner=depositor, kind=AccountKind.INSURANCE_FREE).update(
        balance=Decimal("99000.00")
    )

    data = ledger_for(depositor)

    assert not data.is_sound
    assert [f.check for f in data.findings] == ["cached_balance"]
    # The same finding the whole-book run produces. Not a similar one.
    assert [str(f) for f in data.findings] == [
        str(f) for f in verify_ledger() if f.check == "cached_balance"
    ]

    body = body_for(reader, depositor)
    assert "لا تتفق مع القيود" in body
    assert "99000.00" in body
    assert "25000.00" in body


def test_a_healthy_page_carries_no_alarm(reader, depositor):
    assert "لا تتفق مع القيود" not in body_for(reader, depositor)


def test_one_customers_drift_does_not_appear_on_anothers_page(depositor):
    """Otherwise every page in the console shouts about one broken row."""
    neighbour = User.objects.create_user(
        phone="966555555502", full_name="جار", password="x"
    )
    money.deposit_insurance(
        user=neighbour, amount=TEN_K, source="cash", reference="pay-810-2"
    )
    Account.objects.filter(owner=neighbour, kind=AccountKind.INSURANCE_FREE).update(
        balance=Decimal("1.00")
    )

    assert verify_customer(depositor) == []
    assert len(verify_customer(neighbour)) == 1
    assert len(verify_ledger()) == 1


# ---------------------------------------------------------------------------
# What the screen shows besides the totals
# ---------------------------------------------------------------------------


def test_each_hold_is_shown_with_the_auction_it_secures(reader, depositor, live_auction):
    """«أي مزاد يحجز هذه العشرة آلاف؟» — the question v1 stored no answer to."""
    money.hold_for_auction(user=depositor, auction=live_auction)

    body = body_for(reader, depositor)

    assert HoldReason.BIDDING.label in body
    assert f"مزاد {live_auction.number}" in body


def test_the_lines_are_the_entries_themselves(reader, depositor):
    body = body_for(reader, depositor)

    count = Entry.objects.filter(owner=depositor).count()
    assert count > 0
    assert f"{count} حركة" in body
    assert ledger_for(depositor).name in body


def test_the_page_offers_nothing_that_writes(reader, depositor):
    """Read-only by construction, and asserted so it stays that way.

    A `<form method="post">` appearing here later is somebody adding an
    adjustment button to the screen support trusts to tell them the truth.
    """
    body = screen_of(body_for(reader, depositor)).lower()
    assert 'method="post"' not in body
    assert "للقراءة فقط" in body_for(reader, depositor)


def test_a_released_hold_is_no_longer_a_claim(depositor, live_auction):
    """Only *active* holds are shown — a released one is history, not a claim."""
    hold = money.hold_for_auction(user=depositor, auction=live_auction)
    money.release_hold(hold)

    assert Hold.objects.filter(owner=depositor, state=HoldState.ACTIVE).count() == 0
    data = ledger_for(depositor)
    assert data.snapshot.holds == []
    assert data.is_sound


# ---------------------------------------------------------------------------
# Who may read it
# ---------------------------------------------------------------------------


def test_the_ledger_needs_money_view_and_nothing_more(client, depositor):
    """Operations runs auctions; it has no business reading deposits."""
    operator = User.objects.create_user(
        phone="966500000042", full_name="مشغّل", password="x"
    )
    operator.is_staff = True
    operator.console_role = Role.OPERATIONS
    operator.save(update_fields=["is_staff", "console_role"])

    assert not can(operator, Capability.MONEY_VIEW)
    client.force_login(operator)
    assert client.get(reverse("console:money-ledger")).status_code == 403
    assert (
        client.get(reverse("console:money-customer", args=[depositor.pk])).status_code
        == 403
    )


def test_a_customer_cannot_open_it_at_all(client, depositor):
    client.force_login(depositor)
    assert client.get(reverse("console:money-ledger")).status_code == 403


# ---------------------------------------------------------------------------
# Finding the customer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed", ["966555555501", "0555555501", "+966555555501", "555555501"]
)
def test_any_way_the_number_is_written_reaches_the_same_customer(
    client, reader, depositor, typed
):
    """Support types what the customer said aloud, in whatever shape that was."""
    response = client.get(reverse("console:money-ledger"), {"q": typed})

    assert response.status_code == 302
    assert response["Location"].endswith(
        reverse("console:money-customer", args=[depositor.pk])
    )


def test_the_list_shows_only_customers_who_hold_something(client, reader, depositor):
    """A search that returns every account ever opened answers nothing."""
    User.objects.create_user(phone="966555555503", full_name="بلا رصيد", password="x")

    body = client.get(reverse("console:money-ledger")).content.decode()

    assert "عميل الدفتر" in body
    assert "بلا رصيد" not in body


def test_an_unknown_customer_id_answers_with_the_search_box(client, reader):
    body = client.get(reverse("console:money-customer", args=[999999])).content.decode()

    assert "لا يوجد عميل بهذا الرقم" in body
