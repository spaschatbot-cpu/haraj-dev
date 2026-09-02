"""Sign in with a phone number: three endpoints, no decisions.

Each view reads a request, calls one service function, and renders the result.
Every refusal these paths can produce is a `DomainError` subclass in
`apps.accounts.errors`, and `apps.core.exceptions` turns it into the one
envelope — so there is no error body written anywhere in this file.

Every path here that can cause an SMS carries `OTP_SEND_THROTTLES`, and the one
that spends codes carries `OTP_VERIFY_THROTTLES` — the per-code attempt cap and
the per-number cooldown live in the service layer because they are properties of
a *code*, and these are properties of a *caller*. The lists are named symbols
rather than classes written out here, so a limit added later reaches every send
path at once; `ops/checks/one_otp_rate_limit.py` fails the build if a path that
sends a code is ever added without them.
"""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import services
from apps.accounts import tokens as token_service
from apps.accounts.api.serializers import (
    RefreshSerializer,
    SendCodeResponseSerializer,
    SendCodeSerializer,
    TokenPairSerializer,
    VerifyCodeSerializer,
)
from apps.accounts.throttling import OTP_SEND_THROTTLES, OTP_VERIFY_THROTTLES


class SendCodeView(APIView):
    """`POST /api/v1/auth/code/` — send a one-time code to a mobile number."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = OTP_SEND_THROTTLES

    @extend_schema(
        request=SendCodeSerializer,
        responses={200: SendCodeResponseSerializer},
        summary="إرسال رمز تحقق",
    )
    def post(self, request: Request) -> Response:
        payload = SendCodeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        verification = services.send_verification_code(
            phone=payload.validated_data["phone"],
            purpose=payload.validated_data["purpose"],
        )

        # `expires_at` and the cooldown, and nothing else. The code went to the
        # phone; it does not come back here (T601's hardest rule).
        body = SendCodeResponseSerializer(
            {
                "sent": True,
                "expires_at": verification.expires_at,
                "resend_after": settings.OTP_RESEND_COOLDOWN_SECONDS,
            }
        )
        return Response(body.data, status=status.HTTP_200_OK)


class VerifyCodeView(APIView):
    """`POST /api/v1/auth/verify/` — exchange a correct code for a token pair."""

    authentication_classes: list = []
    permission_classes = [AllowAny]
    throttle_classes = OTP_VERIFY_THROTTLES

    @extend_schema(
        request=VerifyCodeSerializer,
        responses={200: TokenPairSerializer},
        summary="التحقق من الرمز وإصدار الرموز",
    )
    def post(self, request: Request) -> Response:
        payload = VerifyCodeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        user, created = services.sign_in_with_code(
            phone=payload.validated_data["phone"],
            code=payload.validated_data["code"],
            full_name=payload.validated_data.get("full_name", ""),
        )
        pair = token_service.issue_pair(user)
        pair["user"] = {
            "id": user.pk,
            "phone": user.phone,
            "display_name": services.display_name(user),
            "account_type": user.account_type,
            "is_new": created,
        }
        return Response(TokenPairSerializer(pair).data, status=status.HTTP_200_OK)


class RefreshView(APIView):
    """`POST /api/v1/auth/refresh/` — spend a refresh token for a fresh pair."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=RefreshSerializer,
        responses={200: TokenPairSerializer},
        summary="تجديد رمز الوصول",
    )
    def post(self, request: Request) -> Response:
        payload = RefreshSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        pair = token_service.rotate(payload.validated_data["refresh"])
        return Response(TokenPairSerializer(pair).data, status=status.HTTP_200_OK)
