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


def test_the_card_check_leaves_a_bid_row_alone(tmp_path):
    """A bid naming the car it is on is not a card of that car.

    `id`, `auction_id` and `lot_number` are three plain column values — two of
    them written by Django rather than by the author, which is exactly why the
    check used to read them as *computed* and call this a hand-drawn card. It is
    the opposite: `bid_row` deliberately carries three identifiers and no card,
    because a live bid list that shipped a thumbnail and a specification per row
    is the payload T624 exists to avoid.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "views.py",
        "def bid_row(bid):\n"
        "    vehicle = bid.vehicle\n"
        "    return {\n"
        "        'id': bid.pk,\n"
        "        'auction_id': vehicle.auction_id,\n"
        "        'lot_number': vehicle.lot_number,\n"
        "        'amount': str(bid.amount),\n"
        "    }\n",
    )

    assert check.violations([root]) == []


def test_the_card_check_still_catches_a_card_that_names_the_auction(tmp_path):
    """The widening above must not blind the check to the thing it guards.

    The same three identifiers plus one field the card *computes* — the
    auction's title, which no column on `Vehicle` carries — is somebody drawing
    a card by hand, and it is still refused.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "views.py",
        "def payload(vehicle):\n"
        "    return {\n"
        "        'id': vehicle.pk,\n"
        "        'auction_id': vehicle.auction_id,\n"
        "        'lot_number': vehicle.lot_number,\n"
        "        'auction_title': vehicle.auction.title,\n"
        "    }\n",
    )

    assert len(check.violations([root])) == 1


def test_the_card_check_still_catches_a_card_of_nothing_but_columns(tmp_path):
    """The regression the `id` widening opened, and the test that was missing.

    `id` is a column — Django writes the primary key, the author does not — so
    counting it as one is right, and it is what lets `bid_row` through. But the
    check's only other mark for "this is a card" was a computed field, and a
    payload of seven plain columns has none. Between the two, a view could ship
    a hand-drawn vehicle card and pass CI: exactly E7, the defect the guard was
    written for.

    What tells them apart is not the names but where the values come from — all
    seven of these are read off one car.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "views.py",
        "def payload(vehicle):\n"
        "    return {\n"
        "        'id': vehicle.pk,\n"
        "        'make': vehicle.make,\n"
        "        'model': vehicle.model,\n"
        "        'year': vehicle.year,\n"
        "        'odometer_km': vehicle.odometer_km,\n"
        "        'reserve_price': vehicle.reserve_price,\n"
        "        'state': vehicle.state,\n"
        "    }\n",
    )

    assert len(check.violations([root])) == 1


def test_the_card_check_leaves_a_factory_of_literals_alone(tmp_path):
    """Enum constants are not an object the card was read off.

    `VehicleState.LISTED` next to `"make": "تويوتا"` is somebody creating a car,
    and a check that reads `VehicleState` as the thing being described flags
    every factory in this suite — which is how a guard gets switched off.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "factory.py",
        "from apps.auctions.models import Vehicle\n"
        "from apps.auctions.states import VehicleState\n"
        "def a_car(auction, lot):\n"
        "    fields = {\n"
        "        'lot_number': lot,\n"
        "        'make': 'تويوتا',\n"
        "        'model': 'كامري',\n"
        "        'year': 2020,\n"
        "        'state': VehicleState.LISTED,\n"
        "        'reserve_price': '55000.00',\n"
        "    }\n"
        "    return Vehicle.objects.create(auction=auction, **fields)\n",
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


def test_the_card_check_leaves_an_edit_form_alone(tmp_path):
    """A form is boxes somebody types into; a card is what a screen draws.

    They share column names because a car has columns. The form publishes
    nothing, omits every derived name the card computes, and cannot drift from
    a card it never claimed to draw — so holding it to the card rule would be a
    check complaining about correct code, which is how checks get switched off.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "forms.py",
        "from django import forms\n"
        "class VehicleForm(forms.ModelForm):\n"
        "    class Meta:\n"
        "        model = Vehicle\n"
        "        fields = ('make', 'model', 'year', 'reserve_price')\n",
    )

    assert check.violations([root]) == []


def test_the_form_exemption_does_not_cover_a_serializer(tmp_path):
    """The exemption is about *input*, and an exemption nobody tests widens.

    A serializer publishing the same four columns is still a second card — it
    is read by a screen, and that is the whole difference.
    """
    check = load("one_vehicle_card")
    root = write(
        tmp_path,
        "serializers.py",
        "class VehicleSerializer(serializers.ModelSerializer):\n"
        "    class Meta:\n"
        "        model = Vehicle\n"
        "        fields = ('make', 'model', 'year', 'reserve_price')\n",
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


# ---------------------------------------------------------------------------
# Article 1-2 — one writer of the ledger
# ---------------------------------------------------------------------------


def test_nothing_writes_the_ledger_outside_the_money_service():
    assert load("money_single_writer").violations(SCANNED) == []


@pytest.mark.parametrize(
    ("label", "source"),
    [
        (
            "constructing an entry",
            "from apps.money.models import Entry\n"
            "def book(txn, account):\n"
            "    Entry(transaction=txn, account=account, amount=1).save()\n",
        ),
        (
            "creating through the manager",
            "from apps.money.models import Entry\n"
            "def book(txn):\n"
            "    Entry.objects.create(transaction=txn, amount=1)\n",
        ),
        (
            "bulk creating transactions",
            "from apps.money.models import Transaction\n"
            "def book(rows):\n"
            "    Transaction.objects.bulk_create(rows)\n",
        ),
        (
            "assigning a balance",
            "def top_up(account):\n    account.balance = 10\n    account.save()\n",
        ),
        (
            "adding to a balance",
            "def top_up(account):\n    account.balance += 10\n    account.save()\n",
        ),
        (
            "updating a balance in a query",
            "def top_up(qs):\n    qs.update(balance=10)\n",
        ),
    ],
)
def test_the_ledger_check_catches_each_way_of_writing_it(tmp_path, label, source):
    """The rule the constitution calls the sharpest of all had no guard at all
    — while auction state, the vehicle price, the vehicle card, spreadsheets
    and floats each had one. A guard nobody has seen refuse anything proves
    only that it runs."""
    check = load("money_single_writer")
    root = write(tmp_path, "views.py", source)

    found = check.violations([root], allowed=set())

    assert len(found) == 1, f"{label} slipped past the guard: {found}"


def test_reading_the_ledger_is_not_writing_it(tmp_path):
    """Querying is how the rest of the system looks at the ledger, which is
    the whole point of keeping one."""
    check = load("money_single_writer")
    root = write(
        tmp_path,
        "views.py",
        "from apps.money.models import Entry, Transaction\n"
        "def statement(user):\n"
        "    return Entry.objects.filter(owner=user), Transaction.objects.count()\n",
    )

    assert check.violations([root], allowed=set()) == []


def test_a_test_may_forge_a_balance_but_never_an_entry(tmp_path):
    """The one narrowing, stated in the check rather than discovered.

    Article 4-2 says an untested constraint does not exist, and the only way to
    test `customer_buckets_never_go_negative` is to set a balance the service
    would never set. The rows themselves stay forbidden.
    """
    check = load("money_single_writer")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_thing.py").write_text(
        "from apps.money.models import Entry\n"
        "def test_floor(account, txn):\n"
        "    account.balance = -1\n"
        "    Entry.objects.create(transaction=txn, amount=1)\n",
        encoding="utf-8",
    )

    found = check.violations([tmp_path], allowed=set())

    assert len(found) == 1
    assert "Entry" in found[0]
