"""Console routes. Staff-only, and mounted under `APP_BASE`.

Every page here is a row in `apps.console.navigation.PAGES` — the sidebar and
the guard both read it, so there is no second list to keep in step.
"""

from django.urls import path

from apps.bidding import views as bidding_views

from . import views

app_name = "console"

urlpatterns = [
    path("", views.home, name="home"),
    # The support answer from phase 006, now a page of the console rather than
    # a URL somebody had to be told about.
    path("why-no-bid/", bidding_views.why_no_bid, name="why-no-bid"),
]
