"""مظهرُ التطبيق كما تحدّده الإدارة — يقرؤه تطبيقُ الجوّال عند كلّ إقلاع."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.storefront.models import AppAppearance, app_appearance


class AppAppearanceSerializer(serializers.Serializer):
    accent = serializers.ChoiceField(choices=AppAppearance.Accent.choices)
    mode = serializers.ChoiceField(choices=AppAppearance.Mode.choices)
    customers_choose = serializers.BooleanField()


class AppAppearanceView(APIView):
    """`GET /api/v1/appearance/` — اللونُ والإضاءةُ وهل يغيّرهما العميل.

    **بلا دخول**: شاشةُ البدء والترحيب تُرسَمان قبل أن يدخل أحد، ومظهرُهما
    من هنا. ولا شيءَ فيه يخصّ عميلاً — إعدادٌ واحدٌ للجميع.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    @extend_schema(
        operation_id="appearance_retrieve",
        responses={200: AppAppearanceSerializer},
        summary="مظهر التطبيق",
    )
    def get(self, request: Request) -> Response:
        return Response(
            AppAppearanceSerializer(app_appearance()).data, status=status.HTTP_200_OK
        )
