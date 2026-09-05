"""Console routes. Staff-only, and mounted under `APP_BASE`.

Every page here is a row in `apps.console.navigation.PAGES` — the sidebar and
the guard both read it, so there is no second list to keep in step.
"""

from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from apps.bidding import views as bidding_views

from . import (
    actions,
    auctions,
    audit,
    health,
    importexport,
    inbox,
    money,
    partners,
    people,
    views,
)

app_name = "console"

urlpatterns = [
    path("", views.home, name="home"),
    # The way out. Deliberately **not** a row in `navigation.PAGES`: a row there
    # is a screen with a capability that both reveals and guards it, and signing
    # out is neither — it is an action, and no capability gates it, because
    # everyone who got in gets out.
    #
    # POST only, which `LogoutView` has enforced since Django 5.0 and which the
    # template honours with a form rather than a link: a URL that ends a session
    # on GET ends it from any `<img src>` on any page the operator visits next.
    path(
        "sign-out/",
        LogoutView.as_view(next_page=reverse_lazy("admin-login")),
        name="sign-out",
    ),
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
    path("customers/", people.customers, name="customers"),
    path("customers/<int:pk>/", people.customer_detail, name="customer-detail"),
    path("customers/<int:pk>/edit/", people.customer_edit, name="customer-edit"),
    path("customers/<int:pk>/company/", people.company_edit, name="company-edit"),
    path("staff/<int:pk>/grants/", people.staff_grants, name="staff-grants"),
    path("invoices/", people.invoices, name="invoices"),
    path("invoices/<int:pk>/", people.invoice_detail, name="invoice-detail"),
    path("money/", money.ledger, name="money-ledger"),
    path("money/<int:pk>/", money.customer_ledger, name="money-customer"),
    path("money/<int:pk>/actions/", actions.actions, name="money-actions"),
    path(
        "money/holds/<int:pk>/confiscate/",
        actions.confiscate,
        name="money-confiscate",
    ),
    path(
        "money/holds/<int:pk>/exception/",
        actions.grant_exception,
        name="money-exception",
    ),
    path(
        "money/transactions/<int:pk>/correct/",
        actions.correct,
        name="money-correct",
    ),
    path("health/", health.health, name="money-health"),
    path("audit/", audit.audit, name="audit"),
    path("inbox/", inbox.inbox, name="odoo-inbox"),
    path("inbox/<int:pk>/", inbox.message, name="odoo-message"),
    path("inbox/<int:pk>/replay/", inbox.replay, name="odoo-replay"),
]
