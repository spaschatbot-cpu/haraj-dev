"""Notification routes. Mounted under `/api/v1/`."""

from django.urls import path

from . import views

app_name = "notifications_api"

urlpatterns = [
    path("devices/", views.DeviceView.as_view(), name="devices"),
]
