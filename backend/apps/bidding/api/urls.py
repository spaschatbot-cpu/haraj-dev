"""Bidding routes. Mounted under `/api/v1/`, all requiring a signed-in caller.

There is deliberately no route that lists the bids *on* a vehicle. A sealed
auction's whole property is that bidders cannot see each other's numbers, and
the absence of the route is how that is guaranteed — not a permission check
somebody could relax.
"""

from django.urls import path

from . import views

app_name = "bidding_api"

urlpatterns = [
    path(
        "vehicles/<int:pk>/bids/",
        views.PlaceBidView.as_view(),
        name="place-bid",
    ),
    path("bids/mine/", views.MyBidsView.as_view(), name="my-bids"),
    path(
        "participations/",
        views.MyParticipationsView.as_view(),
        name="my-participations",
    ),
    path("bids/<int:pk>/withdraw/", views.WithdrawBidView.as_view(), name="withdraw-bid"),
    path("live/", views.LiveUpdatesView.as_view(), name="live-updates"),
]
