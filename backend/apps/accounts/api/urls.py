"""Auth routes. Mounted under `/api/v1/` beside the wallet's."""

from django.urls import path

from apps.accounts.api.auth import RefreshView, SendCodeView, VerifyCodeView

app_name = "accounts_api"

urlpatterns = [
    path("auth/code/", SendCodeView.as_view(), name="send-code"),
    path("auth/verify/", VerifyCodeView.as_view(), name="verify-code"),
    path("auth/refresh/", RefreshView.as_view(), name="refresh"),
]
