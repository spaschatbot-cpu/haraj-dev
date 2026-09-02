"""Auth routes. Mounted under `/api/v1/` beside the wallet's."""

from django.urls import path

from apps.accounts.api.auth import (
    ConfirmPhoneChangeView,
    RefreshView,
    SendCodeView,
    StartPhoneChangeView,
    VerifyCodeView,
)
from apps.accounts.api.profile import (
    CompanyProfileView,
    NationalIdView,
    ProfileView,
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
    # The account, read off the token. No path parameter names a user here and
    # no body field could — the v1 wallet hole was exactly that parameter.
    path("profile/", ProfileView.as_view(), name="profile"),
    path(
        "profile/national-id/",
        NationalIdView.as_view(),
        name="profile-national-id",
    ),
    path("profile/company/", CompanyProfileView.as_view(), name="profile-company"),
]
