"""Fixtures for the auction and vehicle tests.

Rows are created in whatever state a test needs, with `objects.create` — that
is a birth, not a transition, and the single-writer rule is about transitions.
Every *move* in these tests goes through `services`.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Company
from apps.auctions.models import Auction, Vehicle
from apps.auctions.states import AuctionState, VehicleState

START = timezone.now() + timedelta(hours=1)


@pytest.fixture
def make_auction(db):
    counter = {"n": 0}

    def build(state: str = AuctionState.DRAFT, *, starts_at=None, ends_at=None, **extra):
        counter["n"] += 1
        starts_at = starts_at or START
        return Auction.objects.create(
            number=counter["n"],
            title=f"مزاد {counter['n']}",
            starts_at=starts_at,
            ends_at=ends_at or (starts_at + timedelta(hours=3)),
            state=state,
            **extra,
        )

    return build


@pytest.fixture
def make_vehicle(db, django_user_model):
    counter = {"n": 0}
    winner = {"user": None}

    def a_winner():
        """A car born `awarded` needs a winner — the database says so.

        Created lazily so the ordinary case does not pay for a user row, and
        created here rather than passed in so a test about state machines does
        not have to know about the check constraint.
        """
        if winner["user"] is None:
            winner["user"] = django_user_model.objects.create_user(
                phone="966500000999", full_name="فائز افتراضي", password="x"
            )
        return winner["user"]

    def build(auction, state: str = VehicleState.DRAFT, **extra):
        counter["n"] += 1
        fields = {
            "make": "تويوتا",
            "model": "كامري",
            "year": 2022,
            "reserve_price": Decimal("50000.00"),
        }
        fields.update(extra)
        if state == VehicleState.AWARDED and fields.get("awarded_to") is None:
            fields["awarded_to"] = a_winner()
            fields.setdefault("awarded_price", Decimal("61000.00"))

        return Vehicle.objects.create(
            auction=auction,
            lot_number=fields.pop("lot_number", counter["n"]),
            state=state,
            **fields,
        )

    return build


@pytest.fixture
def customer(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000101", full_name="مزايد", password="x"
    )


@pytest.fixture
def staff(django_user_model):
    return django_user_model.objects.create_user(
        phone="966500000901", full_name="موظف", password="x", is_staff=True
    )


@pytest.fixture
def partner(django_user_model):
    """A partner account: a user with a company that owns vehicles."""
    user = django_user_model.objects.create_user(
        phone="966500000201", full_name="ممثل الشريك", password="x"
    )
    Company.objects.create(
        user=user, name="شركة الشريك", representative_name="ممثل الشريك"
    )
    return user


@pytest.fixture
def other_partner(django_user_model):
    user = django_user_model.objects.create_user(
        phone="966500000202", full_name="ممثل شريك آخر", password="x"
    )
    Company.objects.create(user=user, name="شركة أخرى", representative_name="ممثل آخر")
    return user
