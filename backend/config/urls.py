from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health

urlpatterns = [
    # Unauthenticated and unprefixed: a load balancer probes it before anything
    # else is known to work.
    path("health", health, name="health"),
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
