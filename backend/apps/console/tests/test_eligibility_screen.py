"""T812 — the eligibility screen as a console screen, and the minute it must fit in.

The lookup itself landed in phase 006 (T503) and is not rewritten here: the
refusals, their snapshots and the phone matching all already existed and are
tested in `apps/bidding/tests/test_support_page.py`. What T812 asks is a
different thing — that this be a **screen of this console** and that a real
support case be answerable on it in under a minute.

"Under a minute" is not something a test can time, so it is tested as the three
things that actually cost the minute:

* the agent must not have to know a url — the page is in their sidebar, guarded
  by the same row that lists it;
* the whole answer must be on one page, from the one fact the customer supplies
  on the phone: their number;
* and the follow-up question must not be a second search. «وكم عنده الآن؟» is a
  link to the deposits ledger, not a form to fill in again.

The case played out below is a real one and the most common one: a bidder whose
deposit is locked against an unpaid invoice tries to bid and is refused. The
number he quotes on the phone — «كان عندي عشرة آلاف» — is true and is not the
number that mattered.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.auctions.models import Auction, AuctionState, Vehicle, VehicleState
from apps.bidding import services as bidding
from apps.bidding.models import BidRefusal, RefusalReason
from apps.console.navigation import PAGES, pages_for
from apps.core.permissions import Capability, Role
from apps.money import services as money
from apps.money.models import Invoice, InvoiceState

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")

PAGE = "console:why-no-bid"


@pytest.fixture
def agent(client) -> User:
    user = User.objects.create_user(
        phone="966500000071", full_name="موظف دعم", password="x"
    )
    user.is_staff = True
    user.console_role = Role.SUPPORT
    user.save(update_fields=["is_staff", "console_role"])
    client.force_login(user)
    return user


@pytest.fixture
def live_auction(db) -> Auction:
    now = timezone.now()
    return Auction.objects.create(
        number=812,
        title="مزاد الأهلية",
        starts_at=now - timezone.timedelta(hours=1),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


@pytest.fixture
def car(live_auction) -> Vehicle:
    return Vehicle.objects.create(
        auction=live_auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2022,
        reserve_price=Decimal("20000.00"),
        state=VehicleState.LISTED,
    )


@pytest.fixture
def caller(db, car) -> User:
    """«كان عندي عشرة آلاف» — and he is right, and it is locked against a debt.

    The most common real case, and the one that used to take support twenty
    minutes across three screens: the money is there, the customer can see it in
    the app, and it is not available to bid with.
    """
    customer = User.objects.create_user(
        phone="966555555801",
        full_name="عميل متصل",
        password="x",
        national_id="1000000001",
        phone_verified_at=timezone.now(),
    )
    money.deposit_insurance(
        user=customer, amount=TEN_K, source="cash", reference="pay-812-1"
    )
    invoice = Invoice.objects.create(
        customer=customer,
        number="INV/812/1",
        amount=Decimal("8000.00"),
        state=InvoiceState.OPEN,
        issued_at=timezone.now(),
    )
    money.lock_for_invoice(user=customer, invoice=invoice)

    with pytest.raises(bidding.BidRefused):
        bidding.place_bid(user=customer, vehicle=car, amount=Decimal("25000.00"))

    return customer


# ---------------------------------------------------------------------------
# It is a screen of this console
# ---------------------------------------------------------------------------


def test_the_agent_finds_it_without_being_told_a_url(agent):
    """It is in their sidebar, by the same row that guards it."""
    listed = [page.url_name for page in pages_for(agent)]

    assert PAGE in listed
    row = next(page for page in PAGES if page.url_name == PAGE)
    assert row.capability == Capability.DIAGNOSTICS_VIEW
    assert row.section == "diagnostics"


def test_the_page_wears_the_console_frame(client, agent, caller):
    """Sidebar, environment banner, and a way back — like every other screen.

    It was written standalone in phase 006 and listed in the console in 009,
    which left an agent who followed the link with the back button and nothing
    else. A screen inside a console that does not look like the console also
    reads as a different system.
    """
    body = client.get(reverse(PAGE), {"phone": caller.phone}).content.decode()

    assert "لوحة حراج" in body
    assert reverse("console:home") in body
    assert reverse("console:money-ledger") in body


# ---------------------------------------------------------------------------
# The whole answer, from the one thing the customer says
# ---------------------------------------------------------------------------


def test_one_number_answers_the_real_case_completely(client, agent, caller):
    """Reason, the money as it stood, and the debt behind it — on one page."""
    body = client.get(reverse(PAGE), {"phone": caller.phone}).content.decode()

    refusal = BidRefusal.objects.get(bidder=caller)
    assert refusal.reason == RefusalReason.UNPAID_DUES

    assert caller.full_name in body
    assert RefusalReason.UNPAID_DUES.label in body
    # Both numbers are on the page: his ten thousand, and the eight thousand he
    # owes. That is what lets the agent say a true sentence instead of
    # contradicting a customer who is not wrong about his own balance.
    assert "10000.00" in body
    assert "8000.00" in body
    assert "وقت الرفض" in body


def test_the_numbers_are_the_moment_of_the_refusal_not_of_now(
    client, agent, caller, live_auction
):
    """The balances will have moved by the time anybody asks. These do not."""
    money.deposit_insurance(
        user=caller, amount=Decimal("50000.00"), source="cash", reference="pay-812-2"
    )

    body = client.get(reverse(PAGE), {"phone": caller.phone}).content.decode()

    assert "50000.00" not in body, "the snapshot must not follow the balance"


def test_the_follow_up_question_is_one_click(client, agent, caller):
    """«وكم عنده الآن؟» is a different question, and it is a link not a column.

    A fresh balance printed beside a snapshot is two numbers that look like one,
    and whichever the agent's eye lands on is what the customer is told.
    """
    body = client.get(reverse(PAGE), {"phone": caller.phone}).content.decode()

    assert reverse("console:money-customer", args=[caller.pk]) in body


def test_the_page_asks_the_database_once_per_thing_it_shows(client, agent, caller):
    """The minute is spent waiting, if it is spent anywhere.

    A bound rather than an exact count: what this catches is the refusal loop
    growing a query per row, which is how this page went from instant to eight
    seconds in v1 once a bidder had a few dozen attempts behind him.
    """
    for lot, amount in enumerate(range(21000, 21500, 100), start=2):
        car = Vehicle.objects.create(
            auction=Auction.objects.get(number=812),
            lot_number=lot,
            make="نيسان",
            model="التيما",
            year=2021,
            reserve_price=Decimal("20000.00"),
            state=VehicleState.LISTED,
        )
        with pytest.raises(bidding.BidRefused):
            bidding.place_bid(user=caller, vehicle=car, amount=Decimal(amount))

    assert BidRefusal.objects.filter(bidder=caller).count() == 6

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as captured:
        client.get(reverse(PAGE), {"phone": caller.phone})

    assert len(captured) < 20, [q["sql"][:90] for q in captured]


# ---------------------------------------------------------------------------
# Read-only, still
# ---------------------------------------------------------------------------


def test_nothing_on_it_writes(client, agent, caller):
    body = client.get(reverse(PAGE), {"phone": caller.phone}).content.decode().lower()

    assert 'method="post"' not in body
