"""Fixtures the money tests need and nobody else does.

T013 has landed, so `customer`, `staff` and `auction` now live once in the
root `backend/conftest.py` and were deleted from here rather than kept in two
places. What is left is the second-of-each-kind a money test needs to prove
that one customer's balance is not another's, and the vehicle an invoice
hangs off.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, AuctionState, Vehicle, VehicleState

TEN_K = Decimal("10000.00")


@pytest.fixture
def other_customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000002", full_name="عميل آخر", password="x"
    )


@pytest.fixture
def other_auction():
    now = timezone.now()
    return Auction.objects.create(
        number=2,
        title="مزاد آخر",
        starts_at=now,
        ends_at=now + timedelta(hours=2),
        state=AuctionState.LIVE,
    )


@pytest.fixture
def vehicle(auction):
    return Vehicle.objects.create(
        auction=auction,
        lot_number=1,
        make="تويوتا",
        model="كامري",
        year=2022,
        reserve_price=Decimal("50000.00"),
        state=VehicleState.LISTED,
    )
