"""How JSON that may carry money is decoded. One rule, one place.

``json.loads`` turns ``10000.50`` into a binary float before any of our code
can refuse it, and Article 3-2 forbids a float anywhere on a money path — the
loss is not theoretical:

    >>> import json
    >>> json.loads('{"amount": 99999999999999.99}')["amount"]
    99999999999999.98

A halala vanishes between the sender's number and ours, and because the parsed
value is what gets stored on the message, ``Decimal(str(...))`` downstream
faithfully preserves the wrong figure. The gateway boundary already knew this
and passed ``parse_float=Decimal``; the Odoo boundary and the Odoo client did
not, and the check that watches for floats is an AST walk, so it could not see
one that is only ever created at run time.

So the rule lives here rather than at each boundary (Article 4-5), and every
place someone else's JSON becomes our numbers calls :func:`loads`.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


def loads(data: str | bytes | bytearray) -> Any:
    """Decode JSON with every fractional number as :class:`~decimal.Decimal`."""
    return json.loads(data, parse_float=Decimal)
