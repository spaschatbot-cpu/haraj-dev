"""Browsing routes: auctions, their cars, and one car.

Mounted under `/api/v1/` beside the wallet's and the auth paths. All read-only —
nothing here writes, and bidding lives in `apps.bidding` where the rules that
decide a bid already are.
"""

from django.urls import path

from . import views

app_name = "auctions_api"

urlpatterns = [
    path("auctions/", views.AuctionListView.as_view(), name="auction-list"),
    path("auctions/<int:pk>/", views.AuctionDetailView.as_view(), name="auction-detail"),
    path(
        "auctions/<int:pk>/vehicles/",
        views.AuctionVehicleListView.as_view(),
        name="auction-vehicles",
    ),
    path("vehicles/", views.VehicleListView.as_view(), name="vehicle-list"),
    path("vehicles/<int:pk>/", views.VehicleDetailView.as_view(), name="vehicle-detail"),
    path("favourites/", views.FavouriteListView.as_view(), name="favourite-list"),
    path("favourites/<int:pk>/", views.FavouriteView.as_view(), name="favourite-detail"),
]
