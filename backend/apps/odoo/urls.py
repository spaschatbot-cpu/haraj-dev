from django.urls import path

from . import views

app_name = "odoo"

urlpatterns = [
    path("odoo/", views.odoo_webhook, name="webhook"),
]
