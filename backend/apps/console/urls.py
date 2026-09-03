"""Console routes. Staff-only, and mounted under `APP_BASE`.

Every page here is a row in `apps.console.navigation.PAGES` — the sidebar and
the guard both read it, so there is no second list to keep in step.
"""

from django.urls import path

from apps.bidding import views as bidding_views

from . import auctions, health, importexport, inbox, money, partners, views

app_name = "console"

urlpatterns = [
    path("", views.home, name="home"),
    # The support answer from phase 006, now a page of the console rather than
    # a URL somebody had to be told about.
    path("why-no-bid/", bidding_views.why_no_bid, name="why-no-bid"),
    path("auctions/", auctions.auctions, name="auctions"),
    path("auctions/new/", auctions.auction_new, name="auction-new"),
    path("auctions/<int:pk>/edit/", auctions.auction_edit, name="auction-edit"),
    path("auctions/<int:pk>/", auctions.auction_detail, name="auction-detail"),
    path("vehicles/", auctions.vehicles, name="vehicles"),
    path("vehicles/new/", auctions.vehicle_new, name="vehicle-new"),
    path("vehicles/export/", importexport.export, name="vehicles-export"),
    path("vehicles/import/", importexport.upload, name="vehicles-import"),
    path(
        "vehicles/import/rejections/",
        importexport.rejections,
        name="vehicles-import-errors",
    ),
    path("vehicles/<int:pk>/edit/", auctions.vehicle_edit, name="vehicle-edit"),
    path("vehicles/<int:pk>/", auctions.vehicle_detail, name="vehicle-detail"),
    path("vehicles/<int:pk>/state/", auctions.vehicle_state, name="vehicle-state"),
    path("partners/", partners.decisions, name="partner-decisions"),
    path("partners/<int:pk>/", partners.offers, name="partner-offers"),
    path("partners/<int:pk>/award/", partners.award, name="partner-award"),
    path("partners/<int:pk>/reject/", partners.reject, name="partner-reject"),
    path("money/", money.ledger, name="money-ledger"),
    path("money/<int:pk>/", money.customer_ledger, name="money-customer"),
    path("health/", health.health, name="money-health"),
    path("inbox/", inbox.inbox, name="odoo-inbox"),
    path("inbox/<int:pk>/", inbox.message, name="odoo-message"),
    path("inbox/<int:pk>/replay/", inbox.replay, name="odoo-replay"),
]
