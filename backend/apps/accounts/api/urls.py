"""Auth routes. Mounted under `/api/v1/` beside the wallet's."""

from django.urls import path

from apps.accounts.api.auth import (
    ConfirmPhoneChangeView,
    RefreshView,
    SendCodeView,
    StartPhoneChangeView,
    VerifyCodeView,
)

app_name = "accounts_api"

urlpatterns = [
    path("auth/code/", SendCodeView.as_view(), name="send-code"),
    path("auth/verify/", VerifyCodeView.as_view(), name="verify-code"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
    # Two steps, and the second takes both codes at once — a server-side state
    # holding "the old number is proven, the new one is not" is the single-proof
    # change T604 exists to make impossible.
    path(
        "auth/phone/change/",
        StartPhoneChangeView.as_view(),
        name="start-phone-change",
    ),
    path(
        "auth/phone/change/confirm/",
        ConfirmPhoneChangeView.as_view(),
        name="confirm-phone-change",
    ),
]
