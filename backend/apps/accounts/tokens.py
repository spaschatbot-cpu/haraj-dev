"""Issuing, reading and rotating the two tokens.

Access is short and carried on every request; refresh is long, used once, and
replaced each time it is used. Both are opaque random strings — the database
holds only their digests, and the string itself exists in the client and in the
response that created it, nowhere else.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.errors import InvalidRefreshToken, RefreshTokenReused
from apps.accounts.models import AuthToken, TokenKind, User

#: Bytes of entropy per token. 32 bytes is 256 bits, which is not guessable and
#: is short enough to sit in an Authorization header without comment.
TOKEN_BYTES = 32


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _mint(
    user: User,
    kind: str,
    ttl: timedelta,
    *,
    rotated_from: AuthToken | None = None,
) -> tuple[str, AuthToken]:
    raw = secrets.token_urlsafe(TOKEN_BYTES)
    token = AuthToken.objects.create(
        user=user,
        kind=kind,
        token_hash=_hash(raw),
        expires_at=timezone.now() + ttl,
        rotated_from=rotated_from,
    )
    return raw, token


@transaction.atomic
def issue_pair(user: User, *, rotated_from: AuthToken | None = None) -> dict:
    """Mint an access/refresh pair for ``user``.

    Returns the raw strings — the only moment they exist outside the client.
    The caller puts them in a response body and forgets them; nothing logs them.
    """
    access_ttl = timedelta(seconds=settings.ACCESS_TOKEN_TTL_SECONDS)
    refresh_ttl = timedelta(seconds=settings.REFRESH_TOKEN_TTL_SECONDS)

    access_raw, access = _mint(user, TokenKind.ACCESS, access_ttl)
    refresh_raw, _ = _mint(
        user, TokenKind.REFRESH, refresh_ttl, rotated_from=rotated_from
    )

    return {
        "access": access_raw,
        "refresh": refresh_raw,
        "expires_in": settings.ACCESS_TOKEN_TTL_SECONDS,
        "expires_at": access.expires_at,
    }


def resolve_access(raw: str) -> AuthToken | None:
    """The live access token for ``raw``, or ``None``.

    ``None`` covers unknown, expired and revoked alike: the caller is told to
    authenticate again, and is told nothing about which of the three it was.
    """
    token = (
        AuthToken.objects.select_related("user")
        .filter(token_hash=_hash(raw), kind=TokenKind.ACCESS)
        .first()
    )
    if token is None or not token.is_live or not token.user.is_active:
        return None
    return token


def rotate(raw: str) -> dict:
    """Spend a refresh token and return a fresh pair.

    Rotation on every use, plus reuse detection: a refresh token that arrives
    after it was already exchanged means two parties hold it, so every token in
    that user's chain is revoked and both are logged out. Losing a session is
    the cheap outcome; leaving a stolen one alive is not.

    The mass revocation happens **after** the transaction closes. Raising inside
    it would roll the revocation back along with everything else, leaving the
    caller a 409 and the thief a working session — the exact opposite of what
    the refusal says happened.
    """
    reused: AuthToken | None = None
    pair: dict = {}

    with transaction.atomic():
        token = (
            AuthToken.objects.select_for_update()
            .select_related("user")
            .filter(token_hash=_hash(raw), kind=TokenKind.REFRESH)
            .first()
        )

        if token is None:
            raise InvalidRefreshToken("refresh token not found")

        if token.revoked_at is not None:
            reused = token
        else:
            if token.expires_at <= timezone.now():
                raise InvalidRefreshToken(f"refresh token {token.pk} expired")

            if not token.user.is_active:
                raise InvalidRefreshToken(f"user {token.user_id} is not active")

            now = timezone.now()
            token.revoked_at = now
            token.last_used_at = now
            token.save(update_fields=["revoked_at", "last_used_at"])

            # The access token minted alongside the spent refresh stays valid
            # until it expires on its own. It is minutes long, and killing it
            # here would log out the very request that asked for the refresh.
            pair = issue_pair(token.user, rotated_from=token)

    if reused is not None:
        revoke_all_for(reused.user)
        raise RefreshTokenReused(f"refresh token {reused.pk} presented after rotation")

    return pair


def revoke_all_for(user: User) -> int:
    """Kill every live token this user holds. Returns how many were killed."""
    return AuthToken.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )
