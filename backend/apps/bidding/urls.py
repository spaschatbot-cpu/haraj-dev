"""Support routes. Read-only, and mounted away from the customer API."""

from django.urls import path

from . import views

app_name = "bidding"

urlpatterns = [
    path("why-no-bid/", views.why_no_bid, name="why-no-bid"),
]
