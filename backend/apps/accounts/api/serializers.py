"""What the auth endpoints accept and return.

The rule that shapes this file: no serializer here has a field for the code on
the way *out*. A response body that could ever carry the digits is a response
body that eventually does.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import PHONE_ERROR, PHONE_PATTERN, OtpPurpose


class SendCodeSerializer(serializers.Serializer):
    """Ask for a code."""

    phone = serializers.RegexField(PHONE_PATTERN, error_messages={"invalid": PHONE_ERROR})
    purpose = serializers.ChoiceField(
        choices=OtpPurpose.choices, default=OtpPurpose.LOGIN
    )


class SendCodeResponseSerializer(serializers.Serializer):
    """What the caller learns: that it went, and when it stops working."""

    sent = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
    resend_after = serializers.IntegerField(help_text="ثوانٍ حتى يُسمح بطلب رمز جديد")


class VerifyCodeSerializer(serializers.Serializer):
    """Prove the number."""

    phone = serializers.RegexField(PHONE_PATTERN, error_messages={"invalid": PHONE_ERROR})
    code = serializers.CharField(min_length=4, max_length=8, trim_whitespace=True)
    full_name = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="يُستعمل عند إنشاء الحساب لأول مرة فقط",
    )


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class AuthenticatedUserSerializer(serializers.Serializer):
    """The caller's own account. Never anybody else's — the view reads it off
    the token, never off a request field."""

    id = serializers.IntegerField()
    phone = serializers.CharField()
    display_name = serializers.CharField()
    account_type = serializers.CharField()
    is_new = serializers.BooleanField()


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    expires_in = serializers.IntegerField(help_text="عمر رمز الوصول بالثواني")
    expires_at = serializers.DateTimeField()
    user = AuthenticatedUserSerializer(required=False)
