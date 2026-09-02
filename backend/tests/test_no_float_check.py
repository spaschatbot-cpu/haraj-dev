"""The no-float guard has to fail on a float, or it is decoration.

A check that has never refused anything proves nothing about the code it
watches — it only proves it runs. These tests plant each shape of floating
point the guard claims to catch and assert it is caught, and plant the Decimal
equivalent and assert it is not.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

CHECK_PATH = (
    Path(__file__).resolve().parents[2] / "ops" / "checks" / "no_float_in_money.py"
)


def _load() -> ModuleType:
    """Import the check from ops/, which is outside any Python package."""
    spec = importlib.util.spec_from_file_location("no_float_in_money", CHECK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Registered before execution because @dataclass resolves its own module
    # out of sys.modules while the class body is being processed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load()


def _findings(tmp_path: Path, source: str) -> list[str]:
    planted = tmp_path / "planted.py"
    planted.write_text(source, encoding="utf-8")
    return [f.what for f in check.inspect(planted)]


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("cast", "def f(x):\n    return float(x)\n"),
        ("model field", "amount = models.FloatField()\n"),
        ("argument", "def f(amount: float) -> None:\n    pass\n"),
        ("return", "def f(x) -> float:\n    return x\n"),
        ("nested annotation", "def f(rows: dict[str, float]) -> None:\n    pass\n"),
        ("variable", "total: float = 0\n"),
        ("literal", "price = 10.5\n"),
    ],
)
def test_every_shape_of_float_is_caught(tmp_path: Path, label: str, source: str) -> None:
    assert _findings(tmp_path, source), f"{label} slipped past the guard"


def test_decimal_money_is_left_alone(tmp_path: Path) -> None:
    source = (
        "from decimal import Decimal\n"
        "\n"
        'ZERO = Decimal("0.00")\n'
        "MONEY = {'max_digits': 14, 'decimal_places': 2}\n"
        "\n"
        "\n"
        "def total(amount: Decimal) -> Decimal:\n"
        "    return amount + ZERO\n"
    )
    assert _findings(tmp_path, source) == []


def test_the_real_tree_is_clean() -> None:
    """The repository itself passes — the criterion CI enforces."""
    assert check.main() == 0
