"""What makes a Saudi national or iqama number valid.

One module, because T606's whole rule depends on the answer: a **correct** id is
pinned forever, a **wrong** one may still be corrected. Without a definition of
"correct" that rule collapses into "the first value wins", which is the v1
behaviour it exists to replace — a customer who fat-fingered a digit had to ask
support to edit the database.

The check is the Luhn variant the Saudi identity uses: ten digits, the first of
which says which kind of identity it is (1 = citizen, 2 = resident). Numbers
starting with anything else are not identities at all, whatever their checksum.
"""

from __future__ import annotations

#: The two leading digits that name a real identity type. Any other first digit
#: belongs to a document this platform does not deal in, and accepting one would
#: pin a value nobody can ever correct.
CITIZEN = "1"
RESIDENT = "2"


def is_valid(value: str) -> bool:
    """True when ``value`` is a well-formed Saudi national id or iqama.

    Well-formed is not the same as *real* — no register is consulted here, and
    none should be from a request path. It is enough to separate a typo from a
    number that could exist, which is the whole of what T606 needs to decide
    whether a value may still be corrected.
    """
    digits = (value or "").strip()

    if len(digits) != 10 or not digits.isdigit():
        return False
    if digits[0] not in (CITIZEN, RESIDENT):
        return False

    return _checksum_holds(digits)


def _checksum_holds(digits: str) -> bool:
    """The Luhn pass over the first nine digits against the tenth.

    Doubling from the left because the check digit is last and the doubling
    starts at the first digit — the mirror of the card-number convention, and
    the reason a Luhn helper written for cards gets this wrong.
    """
    total = 0
    for position, character in enumerate(digits[:9]):
        digit = int(character)
        if position % 2 == 0:
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += digit

    return (10 - total % 10) % 10 == int(digits[9])


__all__ = ["CITIZEN", "RESIDENT", "is_valid"]
