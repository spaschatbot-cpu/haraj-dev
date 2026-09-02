"""The CI checks, checked.

A guard nobody has ever seen fail is a guard nobody knows works. Each check
here is run twice: once over the real tree, where it must be silent, and once
over a small file that breaks its rule, where it must speak. The second half
is the part that matters — a check with a typo in its pattern passes the first
half forever.

These need no database: they read source, not rows.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]
SCANNED = [BACKEND / "apps", BACKEND / "config", BACKEND / "tests"]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# T402 — one writer of state
# ---------------------------------------------------------------------------


def test_no_state_is_written_outside_the_service():
    assert load("auction_state_single_writer").violations(SCANNED) == []


def test_the_state_check_catches_a_direct_assignment(tmp_path):
    check = load("auction_state_single_writer")
    root = write(
        tmp_path,
        "views.py",
        "from apps.auctions.models import Auction\n"
        "def close(auction):\n"
        "    auction.state = 'ended'\n"
        "    auction.save()\n",
    )

    found = check.violations([root], allowed=set())

    assert len(found) == 1
    assert ".state" in found[0]


def test_the_state_check_catches_a_bulk_update(tmp_path):
    check = load("auction_state_single_writer")
    root = write(
        tmp_path,
        "tasks.py",
        "from apps.auctions.models import Auction\n"
        "def close_all():\n"
        "    Auction.objects.filter(state='live').update(state='ended')\n",
    )

    assert len(check.violations([root], allowed=set())) == 1


def test_the_state_check_allows_choosing_the_state_a_row_is_born_in(tmp_path):
    """Creation is not a transition; forbidding it would outlaw fixtures."""
    check = load("auction_state_single_writer")
    root = write(
        tmp_path,
        "factory.py",
        "from apps.auctions.models import Auction\n"
        "def build():\n"
        "    return Auction.objects.create(number=1, state='draft')\n",
    )

    assert check.violations([root], allowed=set()) == []


def test_the_state_check_ignores_apps_that_never_touch_an_auction(tmp_path):
    """`Hold.state` and `Invoice.state` belong to the money engine and are
    none of this check's business."""
    check = load("auction_state_single_writer")
    root = write(
        tmp_path,
        "money_service.py",
        "def settle(hold):\n    hold.state = 'released'\n    hold.save()\n",
    )

    assert check.violations([root], allowed=set()) == []


# ---------------------------------------------------------------------------
# T406 / E4 — one price
# ---------------------------------------------------------------------------


def test_there_is_only_one_price_field():
    assert load("one_vehicle_price").violations(SCANNED) == []


@pytest.mark.parametrize(
    "source",
    [
        "from apps.auctions.models import Vehicle\n"
        "def show(vehicle):\n    return vehicle.starting_price\n",
        "from apps.auctions.models import Vehicle\n"
        "def calculate_price(vehicle):\n    return vehicle.reserve_price * 2\n",
        "from apps.auctions.models import Vehicle\n"
        "def show(vehicle):\n"
        "    min_price = vehicle.reserve_price\n"
        "    return min_price\n",
    ],
    ids=["a second attribute", "a price calculation", "a local second price"],
)
def test_the_price_check_catches_a_second_price(tmp_path, source):
    check = load("one_vehicle_price")
    root = write(tmp_path, "screen.py", source)

    assert check.violations([root]) != []


def test_the_price_check_allows_the_two_legitimate_names(tmp_path):
    check = load("one_vehicle_price")
    root = write(
        tmp_path,
        "screen.py",
        "from apps.auctions.models import Vehicle\n"
        "def show(vehicle):\n"
        "    return vehicle.reserve_price, vehicle.awarded_price\n",
    )

    assert check.violations([root]) == []


# ---------------------------------------------------------------------------
# T413 / E7 — one card
# ---------------------------------------------------------------------------


def test_the_card_is_built_in_one_place():
    assert load("one_vehicle_card").violations(SCANNED) == []


def test_the_card_check_catches_a_hand_built_payload(tmp_path):
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "api.py",
        "def payload(vehicle):\n"
        "    return {\n"
        "        'make': vehicle.make,\n"
        "        'year': vehicle.year,\n"
        "        'title': f'{vehicle.make} {vehicle.model}',\n"
        "    }\n",
    )

    assert len(check.violations([root])) == 1


def test_the_card_check_leaves_a_row_of_column_values_alone(tmp_path):
    """A dict of columns is a vehicle being created, not a card being drawn —
    and a check that cannot tell them apart is a check people switch off."""
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "factory.py",
        "from apps.auctions.models import Vehicle\n"
        "def build(auction):\n"
        "    values = {'make': 'تويوتا', 'model': 'كامري', 'year': 2022}\n"
        "    return Vehicle.objects.create(auction=auction, **values)\n",
    )

    assert check.violations([root]) == []


def test_the_card_check_catches_a_second_field_list(tmp_path):
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "serializers.py",
        "class VehicleSerializer:\n"
        "    fields = ('make', 'model', 'year', 'reserve_price')\n",
    )

    assert len(check.violations([root])) == 1


def test_the_card_check_still_catches_a_second_card_on_the_vehicle_itself(tmp_path):
    """The Meta escape hatch must not be an escape hatch for a real card."""
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "serializers.py",
        "class VehicleCardSerializer(ModelSerializer):\n"
        "    class Meta:\n"
        "        model = Vehicle\n"
        "        fields = ('make', 'model', 'year', 'reserve_price')\n",
    )

    assert len(check.violations([root])) == 1


def test_the_card_check_leaves_another_models_serializer_alone(tmp_path):
    """`id`, `state` and `state_label` are generic to every model here.

    Three generic names shared with the card is a coincidence, not a second
    card — an invoice serializer tripped this check before the model name was
    consulted.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "serializers.py",
        "class InvoiceSerializer(ModelSerializer):\n"
        "    class Meta:\n"
        "        model = Invoice\n"
        "        fields = ('id', 'state', 'state_label', 'number')\n",
    )

    assert check.violations([root]) == []


def test_the_card_check_reads_its_field_list_from_the_card_module():
    """Derived, not copied: adding a card field must not need this check
    edited, or the check will be guarding last month's card."""
    from apps.auctions.cards import VEHICLE_CARD_FIELDS

    assert load("one_vehicle_card").card_fields() == set(VEHICLE_CARD_FIELDS)


# ---------------------------------------------------------------------------
# T410 — one spreadsheet reader/writer
# ---------------------------------------------------------------------------


def test_no_controller_opens_a_spreadsheet_library():
    assert load("one_sheet_writer").violations(SCANNED) == []


def test_the_sheet_check_catches_a_second_csv_writer(tmp_path):
    check = load("one_sheet_writer")
    root = write(
        tmp_path,
        "export_view.py",
        "import csv\ndef export(response, rows):\n"
        "    writer = csv.writer(response)\n    writer.writerows(rows)\n",
    )

    assert len(check.violations([root], allowed=set())) == 1


def test_the_sheet_check_catches_a_second_workbook_library(tmp_path):
    check = load("one_sheet_writer")
    root = write(tmp_path, "report.py", "from openpyxl import Workbook\n")

    assert len(check.violations([root], allowed=set())) == 1
