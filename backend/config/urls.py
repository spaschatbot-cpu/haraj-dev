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
    path("api/v1/", include("apps.money.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
