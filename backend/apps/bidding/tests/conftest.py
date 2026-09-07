"""Fixtures for the bidding tests.

The default bidder here is a person who can actually bid: verified, complete,
and funded. Every refusal test then breaks exactly one of those facts, so what
the test is about is the line that differs from this file.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, AuctionState, Vehicle, VehicleState
from apps.money import services as money

TEN_K = Decimal("10000.00")


def make_user(django_user_model, *, phone: str, national_id: str = "", **extra):
    """A user, verified and complete unless the caller says otherwise."""
    return django_user_model.objects.create_user(
        phone=phone,
        full_name=extra.pop("full_name", "مزايد اختبار"),
        password="x",
        national_id=national_id,
        **extra,
    )


@pytest.fixture
def verified(db, django_user_model):
    """Everything a bidder needs except money."""
    return make_user(
        django_user_model,
        phone="966501000001",
        national_id="1000000001",
        phone_verified_at=timezone.now(),
    )


@pytest.fixture
def bidder(verified):
    """The ordinary case: verified, complete, and funded with one deposit."""
    money.deposit_insurance(
        user=verified, amount=TEN_K, source="cash", reference="dep/bidder"
    )
    return verified


@pytest.fixture
def outsider(db, django_user_model):
    """Somebody else entirely — every ownership test needs one."""
    return make_user(
        django_user_model,
        phone="966501000002",
        national_id="1000000002",
        full_name="مزايد آخر",
        phone_verified_at=timezone.now(),
    )


@pytest.fixture
def live_auction(db):
    now = timezone.now()
    return Auction.objects.create(
        number=606,
        title="مزاد المزايدة",
        starts_at=now - timedelta(minutes=5),
        ends_at=now + timedelta(hours=2),
        state=AuctionState.LIVE,
        deposit_required=TEN_K,
    )


def make_vehicle(auction, *, lot: int = 1, **extra) -> Vehicle:
    return Vehicle.objects.create(
        auction=auction,
        lot_number=lot,
        make="تويوتا",
        model="كامري",
        year=2022,
        reserve_price=Decimal("50000.00"),
        state=extra.pop("state", VehicleState.LISTED),
        **extra,
    )


@pytest.fixture
def vehicle(live_auction):
    return make_vehicle(live_auction)
