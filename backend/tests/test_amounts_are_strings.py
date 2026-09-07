"""T619 — every amount in the published contract is a string, not a number.

Article 3-2 forbids a float on a money path. JSON has no decimal type, so a
schema that publishes `type: number` for a riyal amount has already lost it: a
JavaScript client parses `55000.50` into a double before a line of our code
runs, and `0.1 + 0.2` there is the reason this rule exists at all.

**The check reads the schema, not the responses.** The schema is the contract
two generated clients are built from (T621), so a field typed as a number there
becomes a `double` in Dart whatever the server happens to send today. That makes
this a static sweep over `backend/openapi/schema.yaml` — and it fails on an
endpoint nobody remembered to write a response test for, which is the whole
reason to check the contract instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

SCHEMA = Path(__file__).resolve().parents[1] / "openapi" / "schema.yaml"

#: A property whose name contains one of these is money, and money is a string.
#: Substrings rather than exact names so `reserve_price`, `amount_due` and
#: `outstanding_dues` are all caught without a list anybody has to maintain.
MONEY_WORDS = (
    "amount",
    "price",
    "balance",
    "total",
    "outstanding",
    "deposit",
    "paid",
    "due",
    "fee",
    "insurance_free",
    "held",
    "locked",
)

#: Names that contain a money word but are not money. Each is here with its
#: reason; an exemption without one is how a list like this rots.
NOT_MONEY = {
    # A count of cars, not riyals.
    "vehicle_count",
    "open_vehicle_count",
    # How many rows the query matched — paging, not money.
    "total",
    # Fields a customer may read and not write, each with its Arabic reason.
    # It carries the word "locked" for the same reason `insurance_locked` does,
    # and means the opposite kind of lock — a form field, not riyals.
    "locked_fields",
}


def schema() -> dict:
    return yaml.safe_load(SCHEMA.read_text(encoding="utf-8"))


def money_properties() -> list[tuple[str, str, dict]]:
    """Every schema property whose name says it holds money."""
    document = schema()
    found: list[tuple[str, str, dict]] = []

    for name, definition in document.get("components", {}).get("schemas", {}).items():
        for field, spec in (definition.get("properties") or {}).items():
            if field in NOT_MONEY:
                continue
            if any(word in field.lower() for word in MONEY_WORDS):
                found.append((name, field, spec))

    return found


def test_the_sweep_found_money_fields():
    """A sweep that matches nothing passes without checking anything."""
    assert len(money_properties()) >= 3


@pytest.mark.parametrize(
    "schema_name,field,spec",
    money_properties(),
    ids=[f"{name}.{field}" for name, field, _ in money_properties()],
)
def test_a_money_field_is_published_as_a_string(schema_name, field, spec):
    """The failure names the field, so the fix is obvious from the report."""
    kind = spec.get("type")

    # A nullable field is published as a one-of; unwrap it before judging.
    if kind is None and "oneOf" in spec:
        kinds = {member.get("type") for member in spec["oneOf"]}
        kinds.discard("null")
        kind = kinds.pop() if len(kinds) == 1 else None

    assert kind == "string", (
        f"{schema_name}.{field} منشور كـ{kind!r}. "
        "المبالغ نصوص عشرية — عميل JavaScript يقرأ الرقم عائماً قبل أي كود عندنا "
        "(المادة ٣-٢)."
    )


def test_the_exemptions_are_all_still_present_somewhere():
    """An exemption for a field nobody publishes any more is dead weight.

    Worse than dead: the next field to take that name inherits the pass.
    """
    document = schema()
    published = {
        field
        for definition in document.get("components", {}).get("schemas", {}).values()
        for field in (definition.get("properties") or {})
    }
    stale = NOT_MONEY - published

    assert not stale, f"إعفاءات لحقول لم تعد منشورة: {sorted(stale)}"
