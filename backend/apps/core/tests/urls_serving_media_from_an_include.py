"""The same mistake one `include()` deeper — where a top-level-only walk cannot see it."""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [path("", include("apps.core.tests.urls_serving_media"))]
