"""T801 — one gate, and the question it refuses to answer.

v1's `hasRole()` returned true for every role when the asker was the owner.
Generous, until somebody used it to ask *"is this user's role X?"* about a
specific person: for the owner it said yes to every role at once, the menu code
took the first match, and the console locked the owner out of his own platform.

The fix is not a better `hasRole`. It is that the role question does not exist:
`can(user, capability)` is the only permission question in the codebase, and
`ops/checks/one_permission_gate.py` fails the build when another shape appears.

The owner's "everything" is a role that **lists** every capability, never a
branch that returns true — a short-circuit is invisible at the call site and
answers questions nobody meant to ask.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from apps.accounts.models import StaffGrant, User
from apps.core.permissions import (
    ROLE_CAPABILITIES,
    Capability,
    Role,
    can,
    capabilities_of,
    require,
)

pytestmark = pytest.mark.django_db

CHECKS = Path(__file__).resolve().parents[4] / "ops" / "checks"
BACKEND = Path(__file__).resolve().parents[3]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, CHECKS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staff(role: str, phone: str = "966501111111") -> User:
    user = User.objects.create_user(phone=phone, full_name="موظف")
    user.is_staff = True
    user.console_role = role
    user.save(update_fields=["is_staff", "console_role"])
    return user


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_the_owner_holds_every_capability():
    owner = staff(Role.OWNER)

    assert capabilities_of(owner) == frozenset(Capability.values)


def test_the_owner_is_not_a_short_circuit_but_a_list():
    """The v1 incident, stated as a property of the code rather than a comment.

    If the owner's access were `return True` in the gate, this would still pass
    — so it checks the *table* instead: every capability is named in the owner's
    bundle, which means adding one and forgetting the owner is a visible
    omission rather than an invisible wildcard.
    """
    assert ROLE_CAPABILITIES[Role.OWNER] == frozenset(Capability.values)


def test_a_customer_holds_nothing_at_all():
    """A customer token reaching a console view is a routing bug, not a 403."""
    customer = User.objects.create_user(phone="966502222222", full_name="عميل")

    assert capabilities_of(customer) == frozenset()
    assert not can(customer, Capability.CONSOLE_ACCESS)


def test_an_anonymous_caller_holds_nothing():
    from django.contrib.auth.models import AnonymousUser

    assert capabilities_of(AnonymousUser()) == frozenset()
    assert capabilities_of(None) == frozenset()


@pytest.mark.parametrize(
    "role,capability,allowed",
    [
        (Role.SUPPORT, Capability.DIAGNOSTICS_VIEW, True),
        (Role.SUPPORT, Capability.MONEY_VIEW, True),
        (Role.SUPPORT, Capability.MONEY_ACT, False),
        (Role.SUPPORT, Capability.AUCTIONS_MANAGE, False),
        (Role.OPERATIONS, Capability.AUCTIONS_MANAGE, True),
        (Role.OPERATIONS, Capability.MONEY_ACT, False),
        (Role.OPERATIONS, Capability.MONEY_EXCEPTION, False),
        (Role.FINANCE, Capability.MONEY_ACT, True),
        (Role.FINANCE, Capability.AUCTIONS_MANAGE, False),
        # Granting a deposit exception is the owner's alone: it is the one
        # action that lets somebody bid without the money behind it.
        (Role.FINANCE, Capability.MONEY_EXCEPTION, False),
        (Role.OWNER, Capability.MONEY_EXCEPTION, True),
    ],
)
def test_each_role_gets_what_it_needs_and_no_more(role, capability, allowed):
    assert can(staff(role), capability) is allowed


def test_reading_money_does_not_imply_moving_it():
    """v1 collapsed these into one "finance" flag, so a reader could confiscate."""
    reader = staff(Role.SUPPORT)

    assert can(reader, Capability.MONEY_VIEW)
    assert not can(reader, Capability.MONEY_ACT)


# ---------------------------------------------------------------------------
# T803 — grants above the role, and revokes below it
# ---------------------------------------------------------------------------


def test_a_grant_adds_a_capability_immediately():
    person = staff(Role.OPERATIONS)
    assert not can(person, Capability.MONEY_ACT)

    StaffGrant.objects.create(
        user=person,
        capability=Capability.MONEY_ACT,
        granted=True,
        reason="يغطّي الاستردادات أثناء إجازة زميله",
    )

    assert can(person, Capability.MONEY_ACT)


def test_a_revoke_takes_one_away_without_touching_the_role():
    """Somebody's access to one screen has to stop today.

    Editing the role would change it for the dozen others who share it.
    """
    person = staff(Role.OPERATIONS)
    colleague = staff(Role.OPERATIONS, phone="966503333333")

    StaffGrant.objects.create(
        user=person,
        capability=Capability.AUCTIONS_MANAGE,
        granted=False,
        reason="تحت المراجعة",
    )

    assert not can(person, Capability.AUCTIONS_MANAGE)
    assert can(colleague, Capability.AUCTIONS_MANAGE)


def test_a_revoke_beats_a_grant_for_the_same_capability():
    """One row per pair, so there is never a contradiction to resolve."""
    from django.db.utils import IntegrityError

    person = staff(Role.SUPPORT)
    StaffGrant.objects.create(
        user=person,
        capability=Capability.MONEY_ACT,
        granted=True,
        reason="مؤقتاً",
    )

    with pytest.raises(IntegrityError):
        StaffGrant.objects.create(
            user=person,
            capability=Capability.MONEY_ACT,
            granted=False,
            reason="انتهى المؤقت",
        )


def test_a_grant_without_a_reason_is_refused_by_the_database():
    """An access change nobody can explain is what an audit asks about first."""
    from django.db.utils import IntegrityError

    person = staff(Role.SUPPORT)

    with pytest.raises(IntegrityError):
        StaffGrant.objects.create(
            user=person, capability=Capability.MONEY_ACT, granted=True, reason=""
        )


def test_removing_a_grant_restores_the_role():
    person = staff(Role.OPERATIONS)
    grant = StaffGrant.objects.create(
        user=person,
        capability=Capability.AUCTIONS_MANAGE,
        granted=False,
        reason="مؤقت",
    )
    assert not can(person, Capability.AUCTIONS_MANAGE)

    grant.delete()

    assert can(person, Capability.AUCTIONS_MANAGE)


# ---------------------------------------------------------------------------
# `require` — a guard that cannot be ignored
# ---------------------------------------------------------------------------


def test_require_raises_for_a_capability_the_person_lacks():
    from django.core.exceptions import PermissionDenied

    person = staff(Role.SUPPORT)

    with pytest.raises(PermissionDenied):
        require(person, Capability.MONEY_ACT)


def test_require_is_silent_when_allowed():
    require(staff(Role.FINANCE), Capability.MONEY_ACT)


# ---------------------------------------------------------------------------
# The check that keeps the role question from coming back
# ---------------------------------------------------------------------------


def test_nothing_in_the_tree_asks_about_a_role():
    assert (
        load("one_permission_gate").violations([BACKEND / "apps", BACKEND / "config"])
        == []
    )


COMPARES_THE_FIELD = """
def may_edit(user):
    return user.console_role == "owner"
"""

COMPARES_A_VALUE = """
def may_edit(user, role):
    return role in ("finance", "support")
"""

ROLE_HELPER = """
def is_owner(user):
    return False
"""

HAS_ROLE_HELPER = """
def has_role(user, role):
    return False
"""

READS_THE_FIELD = """
def label_for(user):
    return user.console_role.upper()
"""


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(COMPARES_THE_FIELD, id="comparing the role field"),
        pytest.param(COMPARES_A_VALUE, id="comparing against role values"),
        pytest.param(ROLE_HELPER, id="an is_owner helper"),
        pytest.param(HAS_ROLE_HELPER, id="a has_role helper"),
        pytest.param(READS_THE_FIELD, id="reading the field outside the gate"),
    ],
)
def test_the_check_speaks_when_somebody_asks_about_a_role(tmp_path: Path, source):
    (tmp_path / "screen.py").write_text(source, encoding="utf-8")

    found = load("one_permission_gate").violations([tmp_path])

    assert found, "الفحص سكت عن سؤال دور"


def test_the_gate_itself_is_allowed_to_know_what_a_role_is():
    """The one exemption, tested — an exemption nobody tests quietly widens."""
    check = load("one_permission_gate")
    gate = BACKEND / "apps" / "core" / "permissions.py"

    assert check.violations([gate], gate=gate) == []
