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


# `customer` و`staff` في `backend/conftest.py` — كانا معرَّفين هنا أيضاً قبل
# الدمج، لأن هذا الفرع كُتب قبل أن يصل conftest الجذر. حُذفت النسخة المحلية،
# لا الأصل (المادة ٤-٥).


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


def insert_raw(model, /, **values):
    """Insert a row straight through SQL, so the **database** answers.

    Bypassing the ORM is the point of every caller: a constraint that only
    `full_clean` enforces is not a constraint. Bypassing it for the *column
    names* was never part of that — and a hand-written list here has now
    broken three times for a reason unrelated to what the test guards: once
    when `preview` was added to images (HR-12), and twice more when `colour`
    was added to vehicles. A test about **lot numbers** failing with a NOT NULL
    error about paint tells its reader nothing.

    So the names are read off the model: every non-null column without a value
    of its own is filled with its Django default. Add a column tomorrow and
    these tests keep guarding what they were written to guard.

    ‏`model` موضعيٌّ بحت (`/`) لأن **`model` اسمُ عمودٍ في `Vehicle`** — بدونه
    يصطدم اسم الوسيط باسم الحقل، ويفشل النداء برسالةٍ عن «قيمتين لـmodel» لا
    علاقة لها بما يجري.
    """
    from django.db import connection

    row = dict(values)
    for field in model._meta.fields:
        if field.primary_key or field.attname in row or field.name in row:
            continue
        if not field.null:
            # ‏`auto_now_add`/`auto_now` لا يعطيان قيمةً افتراضية: تملؤهما
            # طبقةُ الـORM عند الحفظ، وهذا المسار يتخطّاها عمداً. فبدونهما
            # يفشل الإدراج بـNOT NULL على `created_at` — وهي رسالةٌ ثالثة لا
            # تدلّ على شيء ممّا يحرسه الاختبار.
            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                row[field.attname] = timezone.now()
            else:
                row[field.attname] = field.get_default()

    columns = ", ".join(row)
    placeholders = ", ".join(["%s"] * len(row))
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO {model._meta.db_table} ({columns}) VALUES ({placeholders})",
            list(row.values()),
        )
