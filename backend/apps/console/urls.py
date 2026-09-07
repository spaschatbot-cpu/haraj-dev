"""Console routes. Staff-only, and mounted under `APP_BASE`.

Every page here is a row in `apps.console.navigation.PAGES` — the sidebar and
the guard both read it, so there is no second list to keep in step.
"""

from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from apps.bidding import views as bidding_views

from . import (
    actions,
    alerts,
    analytics,
    archive,
    auction_moves,
    auctions,
    audit,
    billing,
    bulk,
    catalog,
    decisions,
    health,
    importexport,
    inbox,
    money,
    partner_console,
    partner_payments,
    partners,
    payments,
    people,
    refunds,
    staff,
    wallet,
)
from . import (
    dashboard as dashboard_views,
)

app_name = "console"

urlpatterns = [
    # الجذر هو اللوحة. لا مسار `dashboard/` ثانٍ يعرض الشيء نفسه: عنوانان
    # لصفحةٍ واحدة يعنيان إشارتين محفوظتين ومسارين في السجلّ لزيارةٍ واحدة.
    path("", dashboard_views.dashboard, name="home"),
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
    path("auctions/<int:pk>/state/", auction_moves.auction_state, name="auction-state"),
    path("auctions/<int:pk>/", auctions.auction_detail, name="auction-detail"),
    path("auctions/<int:pk>/bids/", archive.auction_bids, name="auction-bids"),
    path("archive/", archive.auction_archive, name="auction-archive"),
    path("auctions/manage/", bulk.manage, name="auctions-manage"),
    path("auctions/bulk/", bulk.bulk, name="auctions-bulk"),
    path("auctions/quick-edit/", bulk.quick_edit, name="auctions-quick-edit"),
    # قرارات المزايدات — قسمُ v1 نفسه (T830أ). قراءةٌ محضة: الترسية في
    # `auctions.services` والفاتورة في `money.services`، ولا بابَ إليهما هنا.
    path("bids/accepted/", decisions.accepted_bids, name="accepted-bids"),
    path("bids/accepted/summary/", decisions.accepted_summary, name="accepted-summary"),
    # التقارير والتحليلات — قسمُ v1 نفسه (T830ب).
    path("analytics/", analytics.reports, name="analytics"),
    path("analytics/bids/", analytics.bids_analysis, name="analytics-bids"),
    path("analytics/active/", analytics.active_auction, name="active-auction"),
    path("analytics/profit/", analytics.profit_report, name="profit-report"),
    path("owners/", analytics.owners_console, name="owners-console"),
    path("owners/bids/", refunds.auction_bids_index, name="auction-bids-index"),
    path("refunds/", refunds.refunds, name="refunds"),
    # المحفظة — الشحن والخصم (T830ط). كلاهما يمرّ بـ`money.services` وحدها.
    path("wallet/credit/", wallet.wallet_credit, name="wallet-credit"),
    path("wallet/deduct/", wallet.direct_deduct, name="direct-deduct"),
    path(
        "analytics/insurance/",
        analytics.insurance_report,
        name="insurance-report",
    ),
    # إدارة الأعضاء — قسمُ v1 نفسه (T830ج).
    path("admins/", staff.admins, name="admins"),
    path("admins/page-control/", staff.page_control, name="page-control"),
    # النظام والصلاحيات (T830ﻫ).
    path("settings/", staff.settings_page, name="settings"),
    path("account/password/", staff.password_change, name="password-change"),
    path("users/bids-report/", analytics.user_bids, name="user-bids"),
    # إدارة المزادات — بقيّةُ قسم v1 (T830د).
    path("vehicles/catalog/", catalog.vehicle_catalog, name="vehicle-catalog"),
    path("vehicles/search/", catalog.vehicle_search, name="vehicle-search"),
    path("after-sales/", catalog.after_sales, name="after-sales"),
    path("vehicle-exit/", catalog.vehicle_exit, name="vehicle-exit"),
    path("ended-decisions/", billing.ended_decisions, name="ended-decisions"),
    # الفواتير (T830ز). «حالة فاتورة» قدرتُها أضيق: `invoices.lookup`.
    path("invoices/status/", billing.invoice_lookup, name="invoice-lookup"),
    path("invoices/export/", billing.invoices_export, name="invoices-export"),
    # شريك التسويق — عشرةُ مداخلَ في v1، وخمسُ دوالّ تقرؤها (T830و).
    path("partner/", partner_console.partner_console, name="partner-console"),
    path("partner/auctions/", partner_console.partner_auctions, name="partner-auctions"),
    path("partner/state/soon/", partner_console.partner_soon, name="partner-soon"),
    path("partner/state/active/", partner_console.partner_active, name="partner-active"),
    path("partner/state/ended/", partner_console.partner_ended, name="partner-ended"),
    path("partner/vehicles/", partner_console.partner_vehicles, name="partner-vehicles"),
    path(
        "partner/settlement/unpaid/",
        partner_console.partner_unpaid,
        name="partner-unpaid",
    ),
    path("partner/settlement/paid/", partner_console.partner_paid, name="partner-paid"),
    path("partner/payments/", partner_console.partner_payments, name="partner-payments"),
    path(
        "partner/approve/",
        partner_payments.approve,
        name="partner-payments-approve",
    ),
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
    path(
        "vehicles/<int:pk>/relist/", auction_moves.vehicle_relist, name="vehicle-relist"
    ),
    path("partners/", partners.decisions, name="partner-decisions"),
    path("partners/<int:pk>/", partners.offers, name="partner-offers"),
    path("partners/<int:pk>/award/", partners.award, name="partner-award"),
    path("partners/<int:pk>/reject/", partners.reject, name="partner-reject"),
    path("customers/", people.customers, name="customers"),
    path("customers/<int:pk>/", people.customer_detail, name="customer-detail"),
    path("customers/<int:pk>/edit/", people.customer_edit, name="customer-edit"),
    path("customers/<int:pk>/company/", people.company_edit, name="company-edit"),
    path("customers/<int:pk>/access/", people.customer_access, name="customer-access"),
    path(
        "customers/<int:pk>/delete/",
        people.customer_delete,
        name="customer-delete",
    ),
    path("refunds/queue/", refunds.refund_queue, name="refund-queue"),
    path("refunds/<int:pk>/resolve/", refunds.refund_resolve, name="refund-resolve"),
    path("payments/attempts/", payments.payment_attempts, name="payment-attempts"),
    path("staff/<int:pk>/grants/", people.staff_grants, name="staff-grants"),
    path("admins/new/", staff.admin_new, name="admin-new"),
    path("admins/roles/", staff.roles, name="roles"),
    path("admins/roles/<slug:slug>/delete/", staff.role_delete, name="role-delete"),
    path("invoices/", people.invoices, name="invoices"),
    path("invoices/<int:pk>/", people.invoice_detail, name="invoice-detail"),
    path("payments/", payments.payments, name="payments"),
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
    path("notifications/", alerts.notifications, name="notifications"),
    path("audit/", audit.audit, name="audit"),
    path("inbox/", inbox.inbox, name="odoo-inbox"),
    path("inbox/<int:pk>/", inbox.message, name="odoo-message"),
    path("inbox/<int:pk>/replay/", inbox.replay, name="odoo-replay"),
]
