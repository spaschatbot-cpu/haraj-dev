"""HR-09 — a pledged deposit is never paid back automatically, however asks.

``PHASE_02`` §4-3: a deposit in ``locked`` that secures a sold car may not
become a refund, and if Odoo asks for one "تُسجل الحالة فوراً في طابور عجز
لمراجعة الإدارة ولا تُنفذ آلياً".

The incident: v1 paid back a deposit securing a car the customer had already
won **and collected**, "مما ترك الشركة دون أي غطاء قانوني أو مالي". There was no
money left to hold and no claim left to make.

The ledger already refuses this on arithmetic — the free bucket is empty and
the CHECK stops the posting. **That refusal was not enough.** It arrived as one
more `failed` message carrying an arithmetic sentence, and nothing anywhere
said a delivered car might be uncovered. These tests are about the difference
between refusing and *saying what was refused, and how short it was*.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState
from apps.bidding import services as bidding
from apps.bidding import settlement
from apps.money import services
from apps.money.models import AccountKind
from apps.money.verification import verify_ledger
from apps.odoo.models import (
    CustomerLink,
    InboundMessage,
    InboundState,
    RefundShortfall,
)
from apps.odoo.processing import process

pytestmark = pytest.mark.django_db

TEN_K = Decimal("10000.00")


@pytest.fixture
def linked(customer):
    CustomerLink.objects.create(user=customer, odoo_customer_id="ODOO-1", is_primary=True)
    return customer


def stored(event: str, payload: dict) -> InboundMessage:
    return InboundMessage.objects.create(
        source="odoo",
        event=event,
        delivery_id=f"D-{event}-{payload.get('refund_id', '')}",
        payload={**payload, "event": event},
        state=InboundState.RECEIVED,
    )


def free(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def locked(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_LOCKED).balance


def a_winner_with_a_pledged_deposit(linked) -> None:
    """One deposit, one car won, one invoice — the deposit is pledged to it."""
    # The eligibility gate is real, and `place_bid` goes through it: a bidder
    # with an unverified phone is refused before any money moves.
    linked.phone_verified_at = timezone.now()
    if not linked.national_id:
        linked.national_id = "1098765432"
    linked.save(update_fields=["phone_verified_at", "national_id"])
    services.deposit_insurance(
        user=linked, amount=TEN_K, source="cash", reference="SEED/HR09"
    )
    now = timezone.now()
    auction = Auction.objects.create(
        number=930,
        title="مزاد",
        starts_at=now - timezone.timedelta(hours=2),
        ends_at=now + timezone.timedelta(hours=1),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )
    car = Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2020,
        state=VehicleState.LISTED,
        reserve_price=Decimal("40000.00"),
    )
    bidding.place_bid(user=linked, vehicle=car, amount=Decimal("70000.00"))
    settlement.settle_auction(auction)
    car.refresh_from_db()
    settlement.invoice_award(car)


# ---------------------------------------------------------------------------
# The refusal
# ---------------------------------------------------------------------------


def test_odoo_cannot_pay_back_a_deposit_that_is_pledged(linked):
    """The v1 incident, refused — and recorded rather than merely refused."""
    a_winner_with_a_pledged_deposit(linked)
    assert free(linked) == Decimal("0.00")
    assert locked(linked) == TEN_K

    message = stored(
        "refund.confirmed",
        {"refund_id": "R-PLEDGED", "amount": "10000.00", "customer_id": "ODOO-1"},
    )
    process(message)

    message.refresh_from_db()
    # Refused **on purpose**, so `ignored` with a written reason — not `failed`,
    # which is for a message we could not understand (Article 2-2).
    assert message.state == InboundState.IGNORED
    assert "عجز" in message.note
    assert locked(linked) == TEN_K, "سُحب المرهون"
    assert services.system_account(AccountKind.EXTERNAL_REFUND).balance == Decimal("0.00")
    assert verify_ledger() == []


def test_the_case_photographs_the_money_at_that_moment(linked):
    """A snapshot, because the buckets move before anybody reads the queue."""
    a_winner_with_a_pledged_deposit(linked)
    process(
        stored(
            "refund.confirmed",
            {"refund_id": "R-SNAP", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
    )

    case = RefundShortfall.objects.get(refund_ref="odoo:R-SNAP")

    assert case.user_id == linked.pk
    assert case.requested == TEN_K
    assert case.free == Decimal("0.00")
    assert case.locked == TEN_K
    assert case.shortfall == TEN_K
    assert case.resolved_at is None, "قضية تُفتح للمراجعة، لا تُغلق آلياً"
    assert "لا يُسحب المرهون آلياً" in case.note


def test_a_partly_covered_refund_is_refused_whole(linked):
    """Not part-paid. Half a refund leaves a car half-covered and a case half-shut."""
    services.deposit_insurance(
        user=linked, amount=TEN_K, source="cash", reference="SEED/PART"
    )

    process(
        stored(
            "refund.confirmed",
            {"refund_id": "R-PART", "amount": "15000.00", "customer_id": "ODOO-1"},
        )
    )

    case = RefundShortfall.objects.get(refund_ref="odoo:R-PART")
    assert case.shortfall == Decimal("5000.00")
    assert free(linked) == TEN_K, "خرج جزءٌ من المال"
    assert verify_ledger() == []


def test_odoo_retrying_does_not_grow_the_queue(linked):
    """A queue with a row per retry is a queue nobody reads."""
    a_winner_with_a_pledged_deposit(linked)
    payload = {
        "refund_id": "R-RETRY",
        "amount": "10000.00",
        "customer_id": "ODOO-1",
    }

    for attempt in range(3):
        message = InboundMessage.objects.create(
            source="odoo",
            event="refund.confirmed",
            delivery_id=f"D-retry-{attempt}",
            payload=payload,
            state=InboundState.RECEIVED,
        )
        process(message)
        message.refresh_from_db()
        assert message.state == InboundState.IGNORED

    assert RefundShortfall.objects.filter(refund_ref="odoo:R-RETRY").count() == 1
    assert locked(linked) == TEN_K


# ---------------------------------------------------------------------------
# And a genuine refund still goes through
# ---------------------------------------------------------------------------


def test_free_insurance_is_still_refunded(linked):
    """The queue must not become a wall. Free money leaves as it always did."""
    services.deposit_insurance(
        user=linked, amount=TEN_K, source="cash", reference="SEED/OK"
    )

    message = stored(
        "refund.confirmed",
        {"refund_id": "R-OK", "amount": "4000.00", "customer_id": "ODOO-1"},
    )
    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == Decimal("6000.00")
    assert not RefundShortfall.objects.exists()
    assert verify_ledger() == []


def test_a_refund_of_exactly_what_is_free_goes_through(linked):
    """The boundary: `free == amount` is enough, and must not open a case."""
    services.deposit_insurance(
        user=linked, amount=TEN_K, source="cash", reference="SEED/EXACT"
    )

    message = stored(
        "refund.confirmed",
        {"refund_id": "R-EXACT", "amount": "10000.00", "customer_id": "ODOO-1"},
    )
    process(message)

    message.refresh_from_db()
    assert message.state == InboundState.PROCESSED
    assert free(linked) == Decimal("0.00")
    assert not RefundShortfall.objects.exists()


# ---------------------------------------------------------------------------
# Closing a case is a decision with a name on it
# ---------------------------------------------------------------------------


def test_a_case_cannot_be_closed_without_saying_how(linked, django_user_model):
    from django.db import IntegrityError, transaction

    a_winner_with_a_pledged_deposit(linked)
    process(
        stored(
            "refund.confirmed",
            {"refund_id": "R-CLOSE", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
    )
    case = RefundShortfall.objects.get(refund_ref="odoo:R-CLOSE")

    case.resolved_at = timezone.now()
    with pytest.raises(IntegrityError), transaction.atomic():
        case.save(update_fields=["resolved_at"])


def test_a_case_closed_with_a_reason_and_a_name_is_accepted(linked, staff):
    a_winner_with_a_pledged_deposit(linked)
    process(
        stored(
            "refund.confirmed",
            {"refund_id": "R-DONE", "amount": "10000.00", "customer_id": "ODOO-1"},
        )
    )
    case = RefundShortfall.objects.get(refund_ref="odoo:R-DONE")

    case.resolved_at = timezone.now()
    case.resolution = "السيارة لم تُسلَّم؛ أُلغيت الفاتورة وأُعيد الطلب."
    case.resolved_by = staff
    case.save(update_fields=["resolved_at", "resolution", "resolved_by"])

    case.refresh_from_db()
    assert case.resolved_by_id == staff.pk
