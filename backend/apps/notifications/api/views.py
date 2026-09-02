"""Registering a handset for push. One endpoint, and one rule.

The rule: **the owner comes from the token.** `apps.notifications.models.Device`
says why at length; the short version is that v1 took the account id from the
request body, and the alerts on this channel say what somebody is bidding on.
"""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Device

from .serializers import DeviceRegistrationSerializer, DeviceSerializer


def device_row(device: Device) -> dict:
    return {
        "id": device.pk,
        "platform": device.platform,
        "created_at": device.created_at,
        "token_tail": device.token_tail,
    }


class DeviceView(APIView):
    """`POST`/`GET /api/v1/devices/` — register this handset, or list mine."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="devices_register",
        request=DeviceRegistrationSerializer,
        responses={201: DeviceSerializer},
        summary="تسجيل جهاز للإشعارات",
    )
    def post(self, request: Request) -> Response:
        payload = DeviceRegistrationSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        # `update_or_create` on the token, not on (user, token): a handset that
        # changed hands re-registers with the same provider token under a new
        # account, and the row must *move* rather than double. Without this the
        # previous owner keeps receiving the new owner's bid alerts.
        device, created = Device.objects.update_or_create(
            token=payload.validated_data["token"],
            defaults={
                "user": request.user,
                "platform": payload.validated_data["platform"],
            },
        )
        return Response(
            DeviceSerializer(device_row(device)).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="devices_list",
        responses={200: DeviceSerializer(many=True)},
        summary="أجهزتي",
    )
    def get(self, request: Request) -> Response:
        devices = Device.objects.filter(user=request.user).order_by("-created_at")
        return Response(
            DeviceSerializer([device_row(d) for d in devices], many=True).data,
            status=status.HTTP_200_OK,
        )
