"""Fixtures shared by the money tests.

These are local to this app on purpose for now. T013 adds project-wide
fixtures in the root `conftest.py`; when it lands, the overlapping ones here
should be deleted rather than kept in two places.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.auctions.models import Auction, AuctionState, Vehicle, VehicleState

TEN_K = Decimal("10000.00")


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000001", full_name="عميل اختبار", password="x"
    )


@pytest.fixture
def other_customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000002", full_name="عميل آخر", password="x"
    )


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000900", full_name="موظف", password="x", is_staff=True
    )


@pytest.fixture
def auction():
    now = timezone.now()
    return Auction.objects.create(
        number=1,
        title="مزاد الاختبار",
        starts_at=now,
        ends_at=now + timedelta(hours=2),
        state=AuctionState.LIVE,
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
