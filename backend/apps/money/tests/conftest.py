"""Shared ground for the wallet API tests."""

from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auctions.models import Auction, AuctionState
from apps.money import services
from apps.money.models import AccountKind

TEN_K = Decimal("10000.00")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def bidder(django_user_model):
    return django_user_model.objects.create_user(
        phone="966511111111", full_name="مزايد أول", password="x"
    )


@pytest.fixture
def stranger(django_user_model):
    """Somebody else entirely — every ownership test needs one."""
    return django_user_model.objects.create_user(
        phone="966522222222", full_name="مزايد آخر", password="x"
    )


@pytest.fixture
def live_auction():
    now = timezone.now()
    return Auction.objects.create(
        number=77,
        title="مزاد الرياض",
        starts_at=now,
        ends_at=now + timedelta(hours=3),
        state=AuctionState.LIVE,
    )


@pytest.fixture
def as_bidder(api_client, bidder) -> APIClient:
    api_client.force_authenticate(user=bidder)
    return api_client


def free_balance(user) -> Decimal:
    return services.account_for(user, AccountKind.INSURANCE_FREE).balance


def _refuse_float(raw: str):
    raise AssertionError(
        f"a money response carried the JSON number {raw!r}; amounts cross the wire "
        "as decimal strings so no client can round them"
    )


def parsed_without_floats(response):
    """Parse a response and fail if any JSON number was a float.

    This is G4 enforced at its sharpest point: not "are the fields I remembered
    to check strings?" but "did a float appear anywhere in this body at all?"
    """
    return json.loads(response.content.decode(), parse_float=_refuse_float)
