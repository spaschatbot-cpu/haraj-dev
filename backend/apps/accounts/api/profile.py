"""The customer's own account: read it, edit the two fields they own, pin an
identity, and keep a company profile.

Every endpoint here reads the account **off the token**. There is no path
parameter naming a user and no field in any body that could — which is why
none of these views appears in T618's IDOR sweep with an id to tamper with.
That is the v1 wallet hole restated: the profile endpoint there took a user id
from the query string.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import identity, services
from apps.accounts.models import Company, CustomerDocument, DocumentKind
from apps.core import uploads

from .serializers import (
    CompanyProfileReadSerializer,
    CompanyProfileSerializer,
    CustomerDocumentSerializer,
    CustomerDocumentUploadSerializer,
    NationalIdSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
)


def profile_of(user) -> dict:
    """The account as every screen shows it. One builder, like the vehicle card.

    `national_id_verified` is derived rather than stored: a boolean column would
    be a second source of truth about the same value, and the two would disagree
    the first time somebody corrected a typo directly in the database.
    """
    company = Company.objects.filter(user=user).first()
    return {
        "id": user.pk,
        "phone": user.phone,
        "display_name": services.display_name(user),
        "full_name": user.full_name,
        "email": user.email,
        "account_type": user.account_type,
        "national_id": user.national_id,
        "national_id_verified": identity.is_valid(user.national_id),
        "phone_verified_at": user.phone_verified_at,
        "has_company_profile": company is not None,
        "company_profile_complete": services.company_profile_is_complete(company),
        "locked_fields": services.locked_fields(user),
    }


class ProfileView(APIView):
    """`GET`/`PATCH /api/v1/profile/` — the caller's own account."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="profile_retrieve",
        responses={200: ProfileSerializer},
        summary="ملفي الشخصي",
    )
    def get(self, request: Request) -> Response:
        return Response(
            ProfileSerializer(profile_of(request.user)).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        operation_id="profile_update",
        request=ProfileUpdateSerializer,
        responses={200: ProfileSerializer},
        summary="تعديل الملف الشخصي",
    )
    def patch(self, request: Request) -> Response:
        payload = ProfileUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            services.update_profile(
                user=request.user, changes=dict(payload.validated_data)
            )
        except ValueError as unknown:
            # Belt and braces. The serializer already refuses an unknown key, so
            # reaching here means the allowlist and the serializer disagreed —
            # a 400 naming the field, never the 500 that T605 exists to stop.
            raise ValidationError({"detail": str(unknown)}) from unknown

        return Response(
            ProfileSerializer(profile_of(request.user)).data, status=status.HTTP_200_OK
        )


class NationalIdView(APIView):
    """`PUT /api/v1/profile/national-id/` — set it once it is right.

    A valid id already on the account is refused (`national_id_already_verified`);
    an invalid one may be replaced. `services.set_national_id` says why at
    length — the short version is that a customer who mistyped a digit must be
    able to fix themselves, and a correct id must not be swappable for
    somebody else's.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="profile_set_national_id",
        request=NationalIdSerializer,
        responses={200: ProfileSerializer},
        summary="تثبيت رقم الهوية",
    )
    def put(self, request: Request) -> Response:
        payload = NationalIdSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        services.set_national_id(
            user=request.user, national_id=payload.validated_data["national_id"]
        )
        return Response(
            ProfileSerializer(profile_of(request.user)).data, status=status.HTTP_200_OK
        )


class CompanyProfileView(APIView):
    """`GET`/`PUT /api/v1/profile/company/` — the company and its ZATCA address."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="profile_company_retrieve",
        responses={200: CompanyProfileReadSerializer},
        summary="ملف الشركة",
    )
    def get(self, request: Request) -> Response:
        company = Company.objects.filter(user=request.user).first()
        if company is None:
            # 404 rather than an empty object: "this account has no company" and
            # "this company has blank fields" are different answers, and a screen
            # that cannot tell them apart shows an edit form for a thing that
            # does not exist.
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(
            CompanyProfileReadSerializer(_company_body(company)).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="profile_company_save",
        request=CompanyProfileSerializer,
        responses={200: CompanyProfileReadSerializer},
        summary="حفظ ملف الشركة",
    )
    def put(self, request: Request) -> Response:
        payload = CompanyProfileSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        company = services.save_company_profile(
            user=request.user, fields=dict(payload.validated_data)
        )
        return Response(
            CompanyProfileReadSerializer(_company_body(company)).data,
            status=status.HTTP_200_OK,
        )


def _company_body(company: Company) -> dict:
    body = {
        field: getattr(company, field)
        for field in (
            "name",
            "representative_name",
            "commercial_register",
            "vat_number",
            "building_number",
            "street",
            "district",
            "city",
            "postal_code",
        )
    }
    body["is_complete"] = services.company_profile_is_complete(company)
    return body


class DocumentsView(APIView):
    """`GET`/`POST /api/v1/profile/documents/` — وثائقُ صاحب الرمز وحده.

    الوثائقُ الأربع (سجل تجاريّ · شهادة ضريبيّة · هويّة · آيبان) لم يكن لها
    طريقٌ في v2 إطلاقاً، ولا يزال في v1 ثلاثةُ أعمدةِ مسارٍ على صفّ المستخدم.
    وصورةُ الآيبان **شرطٌ لفتح طلب الاسترداد** (`request_refund`)، فبلا هذه
    النقطة لا سبيل للعميل إلى استرداده إلا بموظّفٍ يرفع عنه.

    ولا معرّفَ مستخدمٍ في المسار ولا في الجسم — كبقيّة هذا الملفّ. صاحبُ الوثيقة
    هو صاحبُ الرمز، ولا شيء آخر يقرّر ذلك: ثغرةُ محفظة v1 كانت بالضبط معرّفاً
    يُقرأ من الطلب.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(responses=CustomerDocumentSerializer(many=True))
    def get(self, request: Request) -> Response:
        """الساري من كل نوع — أربعةُ صفوفٍ دائماً، والغائبُ `file: null`.

        الأربعةُ كلُّها لا المرفوعُ منها، لأن الشاشة تسأل «ماذا ينقصني؟» وقائمةٌ
        بما رُفع تجيب عن سؤالٍ آخر.
        """
        rows = [
            {
                "kind": kind.value,
                "label": kind.label,
                "document": CustomerDocument.current(request.user, kind.value),
            }
            for kind in DocumentKind
        ]
        return Response(CustomerDocumentSerializer(rows, many=True).data)

    @extend_schema(
        request=CustomerDocumentUploadSerializer,
        responses={201: CustomerDocumentSerializer},
    )
    def post(self, request: Request) -> Response:
        form = CustomerDocumentUploadSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            # البوّابةُ الوحيدة (T912): المحتوى يقرّر، والبايتات يُعاد ترميزها.
            safe = uploads.sanitise_image(form.validated_data["file"])
        except uploads.UploadRejected as exc:
            raise ValidationError({"file": [str(exc.user_message or exc)]}) from exc

        document = CustomerDocument(
            user=request.user,
            kind=form.validated_data["kind"],
            note=form.validated_data.get("note", ""),
            # `uploaded_by` فارغٌ عمداً حين يرفع العميل نفسُه: الفراغُ هنا **معلومة**
            # — «رفعها صاحبُها» — وملؤه بـ`request.user` كان سيجعل رفعَ الموظّف
            # ورفعَ العميل صفّين لا يُفرَّق بينهما.
            uploaded_by=None,
        )
        document.file.save(f"upload{safe.suffix}", safe.content, save=False)
        document.save()

        payload = {
            "kind": document.kind,
            "label": document.get_kind_display(),
            "document": document,
        }
        return Response(
            CustomerDocumentSerializer(payload).data, status=status.HTTP_201_CREATED
        )
