"""Generating and checking the one-time code.

Kept apart from :mod:`apps.accounts.services` so the rules about the code itself
— how long it lives, how many guesses it tolerates, how it is compared — are
readable in one screen, and so nothing else in the project has an opinion about
them.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings


def generate_code() -> str:
    """A fresh code, zero-padded to the configured length.

    `secrets`, not `random`: the module whose numbers are unpredictable, rather
    than the one whose numbers merely look it.
    """
    digits = settings.OTP_CODE_DIGITS
    return f"{secrets.randbelow(10**digits):0{digits}d}"


def hash_code(code: str) -> str:
    """The digest stored in place of the code.

    Unsalted SHA-256 on purpose: the row is found by phone and purpose, not by
    digest, and a salt would only be a second column to compare. What matters is
    that a database dump contains no typeable code — and six digits expire in
    minutes, so the offline attack a salt defends against has nothing to reach.
    """
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def codes_match(code: str, code_hash: str) -> bool:
    """Constant-time comparison, so timing says nothing about how close a guess was."""
    return hmac.compare_digest(hash_code(code), code_hash)
