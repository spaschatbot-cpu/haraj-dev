"""Routes for the wallet, top-ups, refunds, purchases and invoices.

There is deliberately no route that charges a card for a purchase. The absence
is the feature: see :class:`apps.money.models.PaymentMethod`.
"""

from django.urls import path

from . import views

app_name = "money"

urlpatterns = [
    path("wallet/", views.WalletView.as_view(), name="wallet"),
    path(
        "wallet/transactions/",
        views.WalletStatementView.as_view(),
        name="wallet-statement",
    ),
    path("wallet/topups/", views.TopupListCreateView.as_view(), name="topup-list"),
    path(
        "wallet/topups/<str:reference>/",
        views.TopupDetailView.as_view(),
        name="topup-detail",
    ),
    path(
        "wallet/topups/<str:reference>/checkout/",
        views.TopupCheckoutView.as_view(),
        name="topup-checkout",
    ),
    path(
        "wallet/refund-requests/",
        views.RefundRequestListCreateView.as_view(),
        name="refund-request-list",
    ),
    path("purchases/", views.PurchaseListView.as_view(), name="purchase-list"),
    path("invoices/", views.InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice-detail"),
    path("invoices/<int:pk>/pay/", views.InvoicePayView.as_view(), name="invoice-pay"),
    path(
        "payments/callback/",
        views.PaymentCallbackView.as_view(),
        name="payment-callback",
    ),
]
