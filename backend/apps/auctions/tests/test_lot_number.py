"""E2 — one lot number per auction, enforced by the database.

The test writes with raw SQL on purpose. A `full_clean()` or a service-level
guard proves only that our code checks; it says nothing about the import that
bulk-inserts, the admin action, the data migration, or the shell session at
2 a.m. Article 3-3: a rule that can live in the schema lives in the schema, and
the way to prove it is there is to go around every line of Python that might
otherwise be doing the work.
"""

from __future__ import annotations

import pytest
from django.db import IntegrityError, connection, transaction

from apps.auctions.models import Vehicle, VehicleImage

pytestmark = pytest.mark.django_db


def _insert_raw(auction_id: int, lot_number: int) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO auctions_vehicle
                (auction_id, lot_number, make, model, year, vin, plate_number,
                 plate_type, transmission, fuel_type, condition, state,
                 created_at, updated_at)
            VALUES (%s, %s, 'تويوتا', 'كامري', 2022, '', '', 'private',
                    'unknown', 'unknown', 'unknown', 'draft', now(), now())
            """,
            [auction_id, lot_number],
        )


def test_a_duplicate_lot_number_fails_in_the_database(make_auction, make_vehicle):
    auction = make_auction()
    make_vehicle(auction, lot_number=7)

    with pytest.raises(IntegrityError, match="one_lot_number_per_auction"):
        with transaction.atomic():
            _insert_raw(auction.pk, 7)

    assert Vehicle.objects.filter(auction=auction, lot_number=7).count() == 1


def test_the_same_lot_number_in_another_auction_is_fine(make_auction, make_vehicle):
    """The constraint is per auction, not global — lot 7 exists in every sale."""
    first = make_auction()
    second = make_auction()
    make_vehicle(first, lot_number=7)

    with transaction.atomic():
        _insert_raw(second.pk, 7)

    assert Vehicle.objects.filter(lot_number=7).count() == 2


def test_the_constraint_exists_under_the_name_the_code_expects(make_auction):
    """Names drift when a migration is hand-edited; the error message that
    reaches an operator is built from this one."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conname FROM pg_constraint
            WHERE conrelid = 'auctions_vehicle'::regclass AND conname = %s
            """,
            ["one_lot_number_per_auction"],
        )
        assert cursor.fetchone() is not None


def _insert_cover(vehicle_id: int, name: str, position: int) -> None:
    """Insert straight through SQL, so the *index* answers and not `full_clean`.

    The columns are read off the model rather than typed out. A hand-written
    list here is a second list of this table's columns, and it broke the moment
    HR-12 added `preview`: a test about **covers** failed with a NOT NULL error
    about a thumbnail tier, which tells a reader nothing about what it guards.
    Bypassing the ORM is the point of this helper; bypassing it for the column
    *names* was never part of that.
    """
    values = {"vehicle_id": vehicle_id, "image": name, "position": position}
    values["is_cover"] = True
    for field in VehicleImage._meta.fields:
        if field.primary_key or field.attname in values:
            continue
        if not field.null:
            values[field.attname] = field.get_default()

    columns = ", ".join(values)
    placeholders = ", ".join(["%s"] * len(values))
    with connection.cursor() as cursor:
        cursor.execute(
            f"INSERT INTO auctions_vehicleimage ({columns}) VALUES ({placeholders})",
            list(values.values()),
        )


def test_only_one_cover_image_per_vehicle(make_auction, make_vehicle):
    """The same discipline for the card's cover — a partial unique index."""
    vehicle = make_vehicle(make_auction())
    _insert_cover(vehicle.pk, "a.jpg", 0)

    with pytest.raises(IntegrityError, match="one_cover_image_per_vehicle"):
        with transaction.atomic():
            _insert_cover(vehicle.pk, "b.jpg", 1)
