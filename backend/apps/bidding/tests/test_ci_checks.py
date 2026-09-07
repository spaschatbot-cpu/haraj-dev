"""The eligibility gate check, checked.

Run twice, like the auction checks: once over the real tree, where it must be
silent, and once over a small file that breaks the rule, where it must speak.
The second half is the part that matters — a check with a typo in its pattern
passes the first half forever.

No database here: these read source, not rows.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]
SCANNED = [BACKEND / "apps", BACKEND / "config"]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(tmp_path: Path, name: str, source: str) -> Path:
    (tmp_path / name).write_text(source, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# T501 — one decision point
# ---------------------------------------------------------------------------


def test_no_bidding_path_judges_a_bidder_on_its_own():
    assert load("one_eligibility_gate").violations(SCANNED) == []


@pytest.mark.parametrize(
    "source",
    [
        "from apps.bidding.services import place_bid\n"
        "def can_bid(user):\n"
        "    return user.phone_verified_at is not None\n",
        "from apps.bidding.models import Bid\n"
        "def enough(user, auction):\n"
        "    return user.balance >= auction.deposit_required\n",
        "from apps.bidding.models import Bid\n"
        "def clear(user, invoice):\n"
        "    if invoice.outstanding > 0:\n        return False\n    return True\n",
        "from apps.bidding import services\n"
        "def mine(user, vehicle):\n"
        "    return vehicle.owner_company_id == user.pk\n",
        "from apps.bidding.models import Bid\n"
        "def excused(hold):\n"
        "    return bool(hold.exception_note)\n",
    ],
    ids=["phone", "deposit", "dues", "ownership", "exception"],
)
def test_the_gate_check_catches_a_condition_asked_elsewhere(tmp_path, source):
    check = load("one_eligibility_gate")
    root = write(tmp_path, "views.py", source)

    assert len(check.violations([root], gate=tmp_path / "eligibility.py")) == 1


def test_the_gate_check_leaves_the_gate_itself_alone(tmp_path):
    check = load("one_eligibility_gate")
    root = write(
        tmp_path,
        "eligibility.py",
        "from apps.bidding.models import RefusalReason\n"
        "def check_eligibility(user, vehicle):\n"
        "    return user.phone_verified_at is not None\n",
    )

    assert check.violations([root], gate=tmp_path / "eligibility.py") == []


def test_the_gate_check_ignores_an_app_that_never_bids(tmp_path):
    """`Invoice.outstanding` belongs to the money engine, and its rules are
    not this check's business."""
    check = load("one_eligibility_gate")
    root = write(
        tmp_path,
        "money_service.py",
        "def payable(invoice):\n    return invoice.outstanding > 0\n",
    )

    assert check.violations([root], gate=tmp_path / "eligibility.py") == []


def test_the_gate_check_allows_writing_the_exception_it_forbids_reading(tmp_path):
    """Granting an exception is a decision with a name on it; *reading* one is
    judging a bidder, and only the gate may."""
    check = load("one_eligibility_gate")
    root = write(
        tmp_path,
        "services.py",
        "from apps.bidding.models import Bid\n"
        "def grant(hold, note, by):\n"
        "    hold.exception_note = note\n"
        "    hold.exception_granted_by = by\n"
        "    hold.save()\n",
    )

    assert check.violations([root], gate=tmp_path / "eligibility.py") == []


# ---------------------------------------------------------------------------
# T504 — one path to a bid
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "source",
    [
        "from apps.bidding.models import Bid\n"
        "def quick(vehicle, user, amount):\n"
        "    return Bid.objects.create(vehicle=vehicle, bidder=user, amount=amount)\n",
        "from apps.bidding.models import Bid\n"
        "def quick(vehicle, user, amount):\n"
        "    return Bid(vehicle=vehicle, bidder=user, amount=amount)\n",
    ],
    ids=["through the manager", "by hand"],
)
def test_the_gate_check_catches_a_bid_written_outside_place_bid(tmp_path, source):
    check = load("one_eligibility_gate")
    root = write(tmp_path, "views.py", source)

    found = check.violations(
        [root], gate=tmp_path / "eligibility.py", bid_writer=tmp_path / "services.py"
    )
    assert len(found) == 1
    assert "place_bid" in found[0]


def test_the_gate_check_leaves_the_one_bid_writer_alone(tmp_path):
    check = load("one_eligibility_gate")
    root = write(
        tmp_path,
        "services.py",
        "from apps.bidding.models import Bid\n"
        "def place_bid(vehicle, user, amount):\n"
        "    return Bid.objects.create(vehicle=vehicle, bidder=user, amount=amount)\n",
    )

    assert (
        check.violations(
            [root],
            gate=tmp_path / "eligibility.py",
            bid_writer=tmp_path / "services.py",
        )
        == []
    )
