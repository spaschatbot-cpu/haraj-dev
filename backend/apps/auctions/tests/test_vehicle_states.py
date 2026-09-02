"""T404 — the enum stays wide, and every v1 value has a home.

Article 3-5: states are defined with everything known and never squeezed into
a narrower set. v1 squeezed once and lost the difference between "nobody bid"
and "the owner refused the highest bid" — two situations whose next steps are
opposite, recorded as one value, and unrecoverable afterwards.

The comparison table is `V1_VEHICLE_STATE_MAP`. It was reconstructed from the
documented v1 lifecycle, not read out of a v1 database — nobody on this branch
has access to one. That limitation is stated in `states.py` and is the first
thing the migration phase should check against the real table.
"""

from __future__ import annotations

from apps.auctions.states import (
    V1_VEHICLE_STATE_MAP,
    VEHICLE_MOVES,
    VehicleState,
)


def test_every_v1_value_maps_to_a_state_that_exists():
    unknown = {
        v1: mapped
        for v1, mapped in V1_VEHICLE_STATE_MAP.items()
        if mapped not in VehicleState.values
    }

    assert unknown == {}


def test_the_two_v1_endings_stay_apart():
    """`not_sold` and `pending_approval` were one value after the squash."""
    assert V1_VEHICLE_STATE_MAP["not_sold"] != V1_VEHICLE_STATE_MAP["pending_approval"]
    assert V1_VEHICLE_STATE_MAP["pending_approval"] == VehicleState.AWAITING_DECISION


def test_the_enum_is_not_narrower_than_the_v1_vocabulary():
    """Distinct v1 meanings must not collapse below what v1 could express."""
    assert len(set(V1_VEHICLE_STATE_MAP.values())) >= 9
    assert len(VehicleState.values) >= len(set(V1_VEHICLE_STATE_MAP.values()))


def test_every_state_is_reachable_or_a_starting_point():
    """A state nothing can enter is either the birth state or a mistake."""
    reachable = {move.target for move in VEHICLE_MOVES} | {VehicleState.DRAFT}

    assert set(VehicleState.values) - reachable == set()


def test_every_state_has_an_arabic_label():
    """Article 4-3 — English in the code, Arabic in front of a person."""
    for choice in VehicleState:
        assert choice.label
        assert choice.label != choice.value
