from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.login import throttled_staff_login
from apps.core.views import health

urlpatterns = [
    # Unauthenticated and unprefixed: a load balancer probes it before anything
    # else is known to work.
    path("health", health, name="health"),
    # Staff sign-in, metered, mounted **before** the admin so this route wins
    # (T914). Customers' one-time codes have been rate limited since T602;
    # this is the password path, and it is the one that opens `money.act` and
    # `money.exception`. `apps.accounts.login` says why it is a route rather
    # than a decorator on Django's own view.
    path("admin/login/", throttled_staff_login, name="admin-login"),
    # The raw Django index shows a developer screen (login landed here via an
    # explicit `?next=/admin/`, and no setting overrides an explicit `next`).
    # Staff belong in the console: this exact path — and only it, everything
    # under `/admin/` keeps working — hands them over by name, so it follows
    # APP_BASE wherever the console moves.
    path(
        "admin/",
        RedirectView.as_view(pattern_name="console:home", permanent=False),
        name="admin-index-to-console",
    ),
    path("admin/", admin.site.urls),
    path("webhooks/", include("apps.odoo.urls")),
    # Staff-only, read-only, and deliberately not under /api: the customer
    # apps have no business here, and the admin panel (phase 009) will grow
    # around this page rather than replace it.
    # The console, under APP_BASE. v1's panels each hard-coded their prefix and
    # every link broke the three times one moved; here the prefix is a setting
    # and every link is a `{% url %}` (T804).
    path(f"{settings.APP_BASE}/", include("apps.console.urls")),
    path("api/v1/", include("apps.accounts.api.urls")),
    path("api/v1/", include("apps.auctions.api.urls")),
    path("api/v1/", include("apps.bidding.api.urls")),
    path("api/v1/", include("apps.money.api.urls")),
    path("api/v1/", include("apps.notifications.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
