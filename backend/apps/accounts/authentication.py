"""Reading the access token off a request.

`Authorization: Bearer <token>`. One class, registered as a project default, so
no view decides for itself how a caller is identified — and every view that
reads `request.user` gets the user the token names, never one a request
parameter named (the IDOR rule in the phase 007 spec).
"""

from __future__ import annotations

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework import authentication, exceptions

from apps.accounts import tokens as token_service

KEYWORD = "Bearer"


class BearerTokenAuthentication(authentication.BaseAuthentication):
    """Authenticate by opaque access token.

    Returns ``None`` when there is no Bearer header at all — that leaves session
    auth and AllowAny views working, and lets DRF answer with 401 rather than
    this class deciding an anonymous request is an error.
    """

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).split()

        if not header or header[0].lower() != KEYWORD.lower().encode():
            return None

        if len(header) == 1:
            raise exceptions.AuthenticationFailed("رمز الوصول ناقص")
        if len(header) > 2:
            raise exceptions.AuthenticationFailed("رمز الوصول غير صالح")

        try:
            raw = header[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed("رمز الوصول غير صالح") from None

        token = token_service.resolve_access(raw)
        if token is None:
            # Unknown, expired and revoked all answer the same way. Telling a
            # caller which one it was tells an attacker whether they guessed a
            # real token.
            raise exceptions.AuthenticationFailed("انتهت الجلسة. سجّل الدخول من جديد.")

        # Cheap, and it is what makes "which sessions are live" answerable on
        # the support screen later.
        token.last_used_at = timezone.now()
        token.save(update_fields=["last_used_at"])

        return token.user, token

    def authenticate_header(self, request) -> str:
        return KEYWORD


class BearerTokenScheme(OpenApiAuthenticationExtension):
    """Teach drf-spectacular what `BearerTokenAuthentication` is.

    Without this the schema omits the security scheme entirely and every
    generated client — Flutter's in T702, the web's in T1002 — ships with no way
    to attach a token. `check --deploy` reports the gap as a warning per view,
    which is how it was caught here rather than in the app.
    """

    target_class = BearerTokenAuthentication
    name = "bearerAuth"

    def get_security_definition(self, auto_schema) -> dict:
        return {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "رمز الوصول من `/api/v1/auth/verify/`. صالح لخمس عشرة دقيقة، "
                "ويُجدَّد من `/api/v1/auth/refresh/`."
            ),
        }
