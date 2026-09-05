#!/usr/bin/env python
"""Fail if a vehicle card is assembled anywhere but `apps/auctions/cards.py`.

v1's home page alone had four paths that drew this card and three lists of
permitted fields. Nothing compared them, so a field added for the app appeared
on the web, was missing in the admin, and nobody noticed until a customer
asked why the mileage was gone (E7).

What the check looks for, outside `cards.py`:

* a dict literal whose keys are three or more card fields, **one of which the
  card computes** (`title`, `thumbnail_url`, a `_label`) — someone building
  the payload by hand;
* a `fields = (...)` / `FIELDS = [...]` assignment holding three or more of
  them — a serializer's field list, which is the same drift wearing a
  framework's clothes. No computed field is required here: a serializer
  *publishes* a payload, so a list of four car columns is a second card
  whatever it is called.

An **edit form** is the one exception, and it is a real one rather than a
convenience. A card is something a screen *reads*; a form is a set of boxes
somebody *types into*. They share column names because a car has columns, but a
form publishes nothing, cannot drift from the card, and deliberately omits every
derived name the card computes. The distinction is read off the class's bases —
a `ModelForm` is a form — not guessed from the file it lives in.

A serializer's `class Meta` says which model it is for, and one for anything
but `Vehicle` is skipped. Without that, an invoice serializer listing `id`,
`state` and `state_label` looked exactly like a vehicle card: those three
names are generic to every model in the project, and three generic names are
not evidence of anything. The model name is read from the code rather than
guessed from a list of "generic" field names, so the check keeps working when
a card gains a field.

Three is the threshold because one or two shared names are a coincidence
(`state` and `year` mean things elsewhere) and three is a card. What separates a
card from a plain `Vehicle.objects.create(...)` payload of column values is
either of two marks, and it takes both to cover the shapes that actually occur:

* **a computed field** — `title`, `thumbnail_url`, a `_label`: a name no column
  carries, so somebody assembled it. Derived by reading `models.py` rather than
  listed here, so the check cannot end up guarding an older card;
* **one object behind every value** — a card is a set of facts about the same
  vehicle. A create payload is literals and reads off nothing; a bid row that
  names the car it is on reads off two objects, the bid and the vehicle. A dict
  of seven plain columns all read off one car is a card however plain its names,
  and the computed-field clause alone lets it through.

Run:  python ops/checks/one_vehicle_card.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CARDS = BACKEND / "apps" / "auctions" / "cards.py"
MODELS = BACKEND / "apps" / "auctions" / "models.py"

#: Files that name several card fields and are provably not building a card.
#: Each is a decision recorded here, and each says why in a sentence somebody
#: can disagree with at review time.
NOT_A_CARD = {
    # `apps/bidding/live.py` emits four *public* facts about a car on a live
    # stream: its id, its state, that state's label, and its auction's state.
    # It is not a card and must never become one — a card on every tick would
    # put a price, a thumbnail url and a full specification on the wire every
    # two seconds per connected customer, and the reason the live payload is
    # small is the reason it is affordable at all.
    #
    # The guard's real subject is the *card*: one place assembles it so a field
    # added appears everywhere. Nothing here would want a new card field, which
    # is exactly the test of whether an exemption is honest.
    BACKEND / "apps" / "bidding" / "live.py",
}

SKIP_PARTS = {"__pycache__", "migrations", ".venv", "node_modules"}
THRESHOLD = 3

FIELD_LIST_NAMES = {"fields", "FIELDS", "card_fields", "CARD_FIELDS"}


def card_fields() -> set[str]:
    """Read the field list out of `cards.py` itself.

    Parsed rather than imported so the check runs without Django configured,
    and derived rather than copied so that adding a field to the card cannot
    leave this check guarding yesterday's list.
    """
    tree = ast.parse(CARDS.read_text(encoding="utf-8"), filename=str(CARDS))
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign | ast.Assign):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {t.id for t in targets if isinstance(t, ast.Name)}
            if "_BUILDERS" in names and isinstance(node.value, ast.Dict):
                return {
                    key.value
                    for key in node.value.keys
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                }
    raise SystemExit(f"لم يُعثر على تعريف حقول الكرت في {CARDS}")


#: Django field classes that put a `<name>_id` column on the table.
RELATION_FIELDS = {"ForeignKey", "OneToOneField"}


def model_field_names(model: str = "Vehicle") -> set[str]:
    """Column names on `Vehicle`, read out of `models.py`.

    Used to tell a card from a row: a dict of column values is somebody
    creating a vehicle, a dict that also carries `title` or `thumbnail_url` is
    somebody drawing a card. Only this one class is read — `Auction.title` is
    a column of a different table and says nothing about a vehicle card.

    Two columns Django writes rather than the author: the implicit `id` primary
    key, and the `<name>_id` behind every foreign key. Both are as much a plain
    column value as `year` is, and leaving them out taught the check to read
    `{"id": bid.pk, "auction_id": v.auction_id, "lot_number": v.lot_number}` —
    a *bid* naming the car it is on — as a hand-drawn vehicle card. Derived
    from the field's class, not listed, so a relation added later is covered.
    """
    tree = ast.parse(MODELS.read_text(encoding="utf-8"), filename=str(MODELS))
    names: set[str] = {"pk", "id"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != model:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign) or not isinstance(
                statement.value, ast.Call
            ):
                continue
            function = statement.value.func
            if isinstance(function, ast.Attribute) and isinstance(
                function.value, ast.Name
            ):
                if function.value.id == "models":
                    declared = {
                        t.id for t in statement.targets if isinstance(t, ast.Name)
                    }
                    names |= declared
                    if function.attr in RELATION_FIELDS:
                        names |= {f"{name}_id" for name in declared}
    return names


def _is_a_form(node: ast.ClassDef) -> bool:
    """Does this class derive from a Django form?

    `forms.ModelForm`, `ModelForm`, `AuctionForm` — anything whose base name
    ends in `Form`. Narrow on purpose: a serializer never does, and a class that
    genuinely draws a card has no reason to.
    """
    for base in node.bases:
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if name.endswith("Form"):
            return True
    return False


def _sources(node: ast.AST) -> set[str]:
    """Which objects a value is read off — `vehicle.auction.title` → `vehicle`.

    Only lower-cased names count. `VehicleState.LISTED` is an enum constant, not
    a car: a `Vehicle.objects.create(...)` payload is full of them, and counting
    a class as an object it was read off turns every factory in the test suite
    into a hand-drawn card.
    """
    found: set[str] = set()
    for inner in ast.walk(node):
        if isinstance(inner, ast.Attribute):
            base = inner
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name) and base.id.islower():
                found.add(base.id)
    return found


def _string_elements(node: ast.AST) -> set[str]:
    if not isinstance(node, ast.List | ast.Tuple | ast.Set):
        return set()
    return {
        element.value
        for element in node.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }


class CardHunter(ast.NodeVisitor):
    def __init__(self, fields: set[str], computed: set[str]) -> None:
        self.fields = fields
        self.computed = computed
        self.hits: list[tuple[int, str]] = []

    def visit_Dict(self, node: ast.Dict) -> None:
        keys = {
            key.value
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }
        shared = keys & self.fields
        if len(shared) >= THRESHOLD and (
            shared & self.computed or self._one_object(node, keys & self.fields)
        ):
            self.hits.append(
                (node.lineno, "قاموس يرسم كرت مركبة: " + "، ".join(sorted(shared)))
            )
        self.generic_visit(node)

    def _one_object(self, node: ast.Dict, shared: set[str]) -> bool:
        """Does one object supply THRESHOLD or more of these card fields?

        The second half of "is this a card", and the half that survives `id`
        being counted as the column it is. A card is a set of facts about the
        same vehicle; the two shapes that share its names are not:

        * `Vehicle.objects.create(**{"make": "تويوتا", "year": 2022, ...})` —
          literals and enum constants, read off no object at all;
        * a bid row naming the car it is on — `{"id": bid.pk, "auction_id":
          v.auction_id, "lot_number": v.lot_number}` — where no single object
          supplies three, because the row is about two things.

        Counting per object rather than asking "is there exactly one" is what
        keeps a stray `timezone.now()` in a factory from deciding the answer.
        """
        tally: dict[str, int] = {}
        for key, value in zip(node.keys, node.values, strict=False):
            if not isinstance(key, ast.Constant) or key.value not in shared:
                continue
            for name in _sources(value):
                tally[name] = tally.get(name, 0) + 1
        return any(seen >= THRESHOLD for seen in tally.values())

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Skip a `Meta` for another model, and skip an edit form entirely.

        The form case is read from the bases rather than from the file name: a
        class deriving from something called `...Form` takes input, and a set of
        boxes an operator types into is not a card a screen draws. Everything
        else — serializers above all — is still held to the rule.
        """
        if _is_a_form(node):
            return

        if node.name == "Meta":
            for statement in node.body:
                if not isinstance(statement, ast.Assign):
                    continue
                if not any(
                    isinstance(t, ast.Name) and t.id == "model"
                    for t in statement.targets
                ):
                    continue
                named = statement.value
                model = (
                    named.id
                    if isinstance(named, ast.Name)
                    else named.attr
                    if isinstance(named, ast.Attribute)
                    else ""
                )
                if model and model != "Vehicle":
                    return  # not a vehicle card; do not descend
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        if names & FIELD_LIST_NAMES:
            shared = _string_elements(node.value) & self.fields
            if len(shared) >= THRESHOLD:
                self.hits.append(
                    (node.lineno, "قائمة حقول ثانية للكرت: " + "، ".join(sorted(shared)))
                )
        self.generic_visit(node)


def violations(roots: list[Path], fields: set[str] | None = None) -> list[str]:
    fields = card_fields() if fields is None else fields
    computed = fields - model_field_names()
    found: list[str] = []

    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if SKIP_PARTS & set(path.parts) or path == CARDS or path in NOT_A_CARD:
                continue
            hunter = CardHunter(fields, computed)
            hunter.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
            for line, what in hunter.hits:
                found.append(f"{path}:{line}: {what}")

    return found


def main() -> int:
    found = violations([BACKEND / "apps", BACKEND / "config", BACKEND / "tests"])
    if found:
        print("كرت المركبة يُرسم من apps/auctions/cards.py وحدها (المعيار E7):\n")
        for item in found:
            print(f"  {item}")
        print(f"\n{len(found)} مخالفة. استدعِ vehicle_card().")
        return 1

    print("مسار واحد لرسم كرت المركبة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
