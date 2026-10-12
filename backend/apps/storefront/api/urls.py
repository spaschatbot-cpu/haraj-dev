from django.urls import path

from . import views

urlpatterns = [
    path("appearance/", views.AppAppearanceView.as_view(), name="app-appearance"),
]
