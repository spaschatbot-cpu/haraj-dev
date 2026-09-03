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


class StartPhoneChangeSerializer(serializers.Serializer):
    """Ask for the pair of codes that a phone change needs."""

    new_phone = serializers.RegexField(
        PHONE_PATTERN, error_messages={"invalid": PHONE_ERROR}
    )


class StartPhoneChangeResponseSerializer(serializers.Serializer):
    """That both messages went, and when they stop working.

    Two booleans rather than one, because the screen has to tell the customer to
    go and look at two phones — one of which may be in a drawer.
    """

    sent_to_current = serializers.BooleanField()
    sent_to_new = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
    resend_after = serializers.IntegerField(help_text="ثوانٍ حتى يُسمح بطلب رمز جديد")


class ConfirmPhoneChangeSerializer(serializers.Serializer):
    """Both codes, in one request.

    One request, not two, and that is the rule rather than a convenience: two
    requests would mean a server-side half-finished state in which one number is
    proven and the other is not — which is exactly the single-proof change that
    T604 exists to make impossible.
    """

    new_phone = serializers.RegexField(
        PHONE_PATTERN, error_messages={"invalid": PHONE_ERROR}
    )
    current_code = serializers.CharField(
        min_length=4,
        max_length=8,
        trim_whitespace=True,
        help_text="الرمز المُرسَل إلى الرقم الحالي",
    )
    new_code = serializers.CharField(
        min_length=4,
        max_length=8,
        trim_whitespace=True,
        help_text="الرمز المُرسَل إلى الرقم الجديد",
    )


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


class LockedFieldSerializer(serializers.Serializer):
    """A field the customer can read but not write, and why not.

    `reason` is Arabic and ready to put on a screen. It is a sentence rather
    than a code because there is no behaviour to branch on — the client shows
    the field closed and prints this beside it.
    """

    field = serializers.CharField()
    reason = serializers.CharField(help_text="سبب عربي جاهز للعرض")


class ProfileSerializer(serializers.Serializer):
    """The caller's own account, as a screen shows it.

    Read-only fields are marked as such rather than merely ignored on write:
    a client generated from this schema then cannot offer a form field that
    silently does nothing, which is how v1's "edit profile" screen let people
    type a new phone number into a box that never saved it.
    """

    id = serializers.IntegerField(read_only=True)
    phone = serializers.CharField(read_only=True, help_text="يتغيّر عبر مسار خاص")
    display_name = serializers.CharField(read_only=True)
    full_name = serializers.CharField(max_length=200)
    email = serializers.EmailField(required=False, allow_blank=True)
    account_type = serializers.CharField(read_only=True)
    national_id = serializers.CharField(read_only=True, allow_blank=True)
    national_id_verified = serializers.BooleanField(read_only=True)
    phone_verified_at = serializers.DateTimeField(read_only=True, allow_null=True)
    has_company_profile = serializers.BooleanField(read_only=True)
    company_profile_complete = serializers.BooleanField(read_only=True)
    locked_fields = LockedFieldSerializer(many=True, read_only=True)


class ProfileUpdateSerializer(serializers.Serializer):
    """What a customer may change about themselves, and nothing else.

    Every field here is optional, and `validate` refuses an empty body: a PATCH
    that changes nothing is almost always a client bug, and answering 200 to it
    hides the bug behind a success.

    Unknown keys are refused rather than dropped (T605). DRF's default is to
    ignore them, which turns a client's typo into a silent no-op — the customer
    presses save, sees no error, and the value never changes.
    """

    full_name = serializers.CharField(max_length=200, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {name: "حقل غير معروف." for name in sorted(unknown)}
            )
        if not attrs:
            raise serializers.ValidationError("ما فيه شيء لتعديله.")
        return attrs


class NationalIdSerializer(serializers.Serializer):
    """Ten digits. Whether they are a *valid* identity is the service's call.

    The length check is here because it is a property of the field; the checksum
    is not, because T606's rule — a correct id is pinned, a wrong one may be
    corrected — needs one definition of "correct" and it lives in
    `apps.accounts.identity`.
    """

    national_id = serializers.RegexField(
        r"^\d{10}$",
        error_messages={"invalid": "رقم الهوية عشرة أرقام."},
    )


class CompanyProfileSerializer(serializers.Serializer):
    """The company and its ZATCA national address.

    Nothing is `required` at this layer even though most of it is required for a
    *new* company: the exemption for companies that predate ZATCA's national
    address is a business rule with a date attached, and business rules live in
    the service layer. A serializer that hard-coded `required=True` would refuse
    an existing company its own edit form.
    """

    name = serializers.CharField(max_length=200, required=False)
    representative_name = serializers.CharField(
        max_length=200, required=False, allow_blank=True
    )
    commercial_register = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    vat_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    building_number = serializers.CharField(
        max_length=8, required=False, allow_blank=True
    )
    street = serializers.CharField(max_length=200, required=False, allow_blank=True)
    district = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    postal_code = serializers.CharField(max_length=8, required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(
                {name: "حقل غير معروف." for name in sorted(unknown)}
            )
        return attrs


class CompanyProfileReadSerializer(CompanyProfileSerializer):
    """The same fields plus whether they add up to something invoiceable."""

    is_complete = serializers.BooleanField(read_only=True)
