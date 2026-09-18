"""Console routes. Staff-only, and mounted under `APP_BASE`.

Every page here is a row in `apps.console.navigation.PAGES` — the sidebar and
the guard both read it, so there is no second list to keep in step.
"""

from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import (
    actions,
    after_sales,
    alerts,
    analytics,
    archive,
    auction_moves,
    auction_quick,
    auctions,
    audit,
    bids,
    billing,
    broadcast,
    bulk,
    catalog,
    customer_file,
    decisions,
    exits,
    health,
    importexport,
    inbox,
    manual_payment,
    money,
    news,
    partner_console,
    partner_payments,
    partners,
    payments,
    people,
    refunds,
    reminders,
    staff,
    support,
    vehicle_bulk,
    vehicle_images,
)
from . import (
    dashboard as dashboard_views,
)
from . import views as console_views

app_name = "console"

urlpatterns = [
    # الجذر هو اللوحة. لا مسار `dashboard/` ثانٍ يعرض الشيء نفسه: عنوانان
    # لصفحةٍ واحدة يعنيان إشارتين محفوظتين ومسارين في السجلّ لزيارةٍ واحدة.
    path("", dashboard_views.dashboard, name="home"),
    # تخصيصُ أعمدة أيّ جدول — نقطةُ كتابةٍ يستدعيها مكوّنُ الأعمدة. T869
    path("columns/save/", console_views.columns_save, name="columns-save"),
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
    path("auctions/", auctions.auctions, name="auctions"),
    path("auctions/new/", auctions.auction_new, name="auction-new"),
    path("auctions/<int:pk>/edit/", auctions.auction_edit, name="auction-edit"),
    path("auctions/<int:pk>/state/", auction_moves.auction_state, name="auction-state"),
    # العمليّات السريعة من الصفّ — T846. كلُّها POST: نافذةٌ تغيّر حالةً
    # بـGET هي رابطٌ يُفتح بالخطأ من سجلّ المتصفّح.
    path(
        "auctions/<int:pk>/showcase/",
        auction_quick.auction_showcase,
        name="auction-showcase",
    ),
    path(
        "auctions/<int:pk>/reschedule/",
        auction_quick.auction_reschedule,
        name="auction-reschedule",
    ),
    path("auctions/<int:pk>/fees/", auction_quick.auction_fees, name="auction-fees"),
    path(
        "auctions/<int:pk>/delete/",
        auction_quick.auction_delete,
        name="auction-delete",
    ),
    path(
        "auctions/<int:pk>/end-now/",
        auction_quick.auction_end_now,
        name="auction-end-now",
    ),
    path("auctions/<int:pk>/", auctions.auction_detail, name="auction-detail"),
    # الشريطُ المجمَّع على مركبات المزاد — نظيرُ v1. T865
    path(
        "auctions/<int:pk>/vehicles/bulk/",
        vehicle_bulk.vehicles_bulk,
        name="auction-vehicles-bulk",
    ),
    # رفعُ ملف سيارات لهذا المزاد — الخطوة ٢، كـ v1. T885
    path(
        "auctions/<int:pk>/vehicles/import/",
        importexport.import_auction_vehicles,
        name="auction-vehicles-import",
    ),
    path("auctions/<int:pk>/bids/", archive.auction_bids, name="auction-bids"),
    path("archive/", archive.auction_archive, name="auction-archive"),
    path(
        "archive/<int:pk>/vehicles/",
        archive.archive_auction_vehicles,
        name="archive-auction-vehicles",
    ),
    path("auctions/manage/", bulk.manage, name="auctions-manage"),
    path("auctions/bulk/", bulk.bulk, name="auctions-bulk"),
    path("auctions/quick-edit/", bulk.quick_edit, name="auctions-quick-edit"),
    # حفظُ سيارةٍ واحدة من كارت التعديل السريع — نظيرُ `quick-update` في v1.
    path(
        "vehicles/<int:pk>/quick-update/",
        bulk.vehicle_quick_update,
        name="vehicle-quick-update",
    ),
    # قرارات المزايدات — قسمُ v1 نفسه (T830أ). قراءةٌ محضة: الترسية في
    # `auctions.services` والفاتورة في `money.services`، ولا بابَ إليهما هنا.
    # مزايدات المزاد الجاري، وكلُّ المزايدات بمركباتها. T890
    # تذكيراتُ انطلاق المزاد — إدراجٌ في الطابور لا إرسال. T891
    path("reminders/", reminders.reminders, name="reminders"),
    path(
        "reminders/<int:pk>/send/",
        reminders.reminder_send,
        name="reminder-send",
    ),
    path("bids/live/", bids.live_bids, name="live-bids"),
    path("bids/vehicles/", bids.vehicle_bids, name="vehicle-bids"),
    path(
        "bids/vehicles/<int:pk>/list/",
        bids.vehicle_bid_list,
        name="vehicle-bid-list",
    ),
    path("bids/accepted/", decisions.accepted_bids, name="accepted-bids"),
    path(
        "bids/accepted/<int:pk>/invoice/",
        decisions.accepted_invoice,
        name="accepted-invoice",
    ),
    path(
        "bids/accepted/invoice-all/",
        decisions.accepted_invoice_all,
        name="accepted-invoice-all",
    ),
    path("bids/accepted/summary/", decisions.accepted_summary, name="accepted-summary"),
    # التقارير والتحليلات — قسمُ v1 نفسه (T830ب).
    # تقرير المزايدات — المزايدون مجمَّعين، بمسار v1 نفسِه (T832).
    # «احصائيات المزاد النشط» دُمجت في `console:live-bids` (T938) —
    # شاشتان عن المزاد المفتوح نفسِه: تلك تعدّ وهذه تسرد.
    path("owners/", analytics.owners_console, name="owners-console"),
    path("owners/bids/", refunds.auction_bids_index, name="auction-bids-index"),
    path("refunds/", refunds.refunds, name="refunds"),
    # مسارٌ واحدٌ للشاشة كلِّها، كـ«شريط الأخبار» — و`op` يميّز الفعل. T921
    #
    # **قسمُ «المحفظة» صار شاشتين** (قرار المالك، ١٨ سبتمبر ٢٠٢٦): «صحّة
    # المحفظة» ابتلعت «لماذا لا يستطيع العميل المزايدة؟»، و«سجل المحفظة»
    # ابتلعت «تقرير المحفظة». وأُلغيت «شحن يدوي» و«طلبات الشحن البنكي»
    # و«خصم مباشر من التأمين» — والتفصيل في `navigation.py`.
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
    path("after-sales/", after_sales.after_sales, name="after-sales"),
    # الخروج ونقل الملكية — دورةُ حياةٍ كاملة (T887). الكتابةُ عبر
    # `apps.auctions.exits` وحدها؛ وكلُّ فعلٍ POST فلا يُطلَق برابطٍ من السجلّ.
    path("vehicle-exit/", exits.vehicle_exit, name="vehicle-exit"),
    path("vehicle-exit/<int:pk>/create/", exits.exit_create, name="exit-create"),
    path(
        "vehicle-exit/<int:pk>/declaration/",
        exits.exit_declaration,
        name="exit-declaration",
    ),
    # البحثُ قبل التأكيد: `GET` لأنه قراءةٌ لا كتابة — الحارسُ يقرأ ما بيده
    # قبل أن يفتح البوّابة، والتأكيدُ وحده `POST`.
    path("vehicle-exit/gate/lookup/", exits.exit_gate_lookup, name="exit-gate-lookup"),
    path("vehicle-exit/gate/", exits.exit_gate, name="exit-gate"),
    path("vehicle-exit/<int:pk>/transfer/", exits.exit_transfer, name="exit-transfer"),
    path("vehicle-exit/<int:pk>/lift-ban/", exits.exit_lift_ban, name="exit-lift-ban"),
    path("vehicle-exit/<int:pk>/upload/", exits.exit_upload, name="exit-upload"),
    path("vehicle-exit/<int:pk>/edit/", exits.exit_edit, name="exit-edit"),
    path("vehicle-exit/<int:pk>/note/", exits.exit_note, name="exit-note"),
    path("ended-decisions/", billing.ended_decisions, name="ended-decisions"),
    # الفواتير — شاشةٌ واحدة (T936 · T937). و«حالة فاتورة» و«تصدير الفواتير»
    # حُذفتا: بحثُ الأولى بالشاصي واللوحة صار مدخلاً في «مركز الفواتير»،
    # ومدى الثانية مرشِّحاً فيه.
    # شريك التسويق — عشرةُ مداخلَ في v1، وخمسُ دوالّ تقرؤها (T830و).
    path("partner/", partner_console.partner_console, name="partner-console"),
    path("partner/auctions/", partner_console.partner_auctions, name="partner-auctions"),
    path("partner/state/soon/", partner_console.partner_soon, name="partner-soon"),
    path("partner/state/active/", partner_console.partner_active, name="partner-active"),
    path("partner/state/ended/", partner_console.partner_ended, name="partner-ended"),
    path("partner/vehicles/", partner_console.partner_vehicles, name="partner-vehicles"),
    # حكمُ شريك التسويق على سيارته — يفكّ قفل القرار (نظير `stampDecision` في v1).
    path(
        "partner/vehicles/<int:pk>/rule/",
        partner_console.partner_rule,
        name="partner-rule",
    ),
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
    # معرضُ صور المركبة — يُفتح من عمود «الصور» في صفّ المزاد. T866
    path(
        "vehicles/<int:pk>/images/",
        vehicle_images.gallery,
        name="vehicle-images",
    ),
    # صورةُ العرض بضغطةٍ من الكارت — نظيرُ `set-display-image` في v1.
    path(
        "vehicles/<int:pk>/display-image/",
        vehicle_images.set_display_image,
        name="vehicle-display-image",
    ),
    path("vehicles/<int:pk>/", auctions.vehicle_detail, name="vehicle-detail"),
    path("vehicles/<int:pk>/state/", auctions.vehicle_state, name="vehicle-state"),
    # قلبُ وسم التسويق على مركبةٍ واحدة — زرُّ الصفّ. T877
    path(
        "vehicles/<int:pk>/marketing/",
        vehicle_bulk.marketing_toggle,
        name="vehicle-marketing",
    ),
    # قلبُ رؤية مركبةٍ عن العملاء — إخفاء/إظهار من كارتها. نظيرُ v1.
    path(
        "vehicles/<int:pk>/visibility/",
        vehicle_bulk.visibility_toggle,
        name="vehicle-visibility",
    ),
    path(
        "vehicles/<int:pk>/relist/", auction_moves.vehicle_relist, name="vehicle-relist"
    ),
    path("partners/", partners.decisions, name="partner-decisions"),
    path("partners/<int:pk>/", partners.offers, name="partner-offers"),
    path("partners/<int:pk>/award/", partners.award, name="partner-award"),
    path("partners/<int:pk>/reject/", partners.reject, name="partner-reject"),
    path("customers/", people.customers, name="customers"),
    path("customers/<int:pk>/", customer_file.customer_detail, name="customer-detail"),
    # ليست صفّاً في `PAGES`: فعلٌ على صفحةٍ قائمة لا وجهةٌ في الشريط. حراستُها
    # حراسةُ ملفّ العميل، وفوقها `money.act` داخل المنظر نفسه.
    path(
        "customers/<int:pk>/odoo-link/",
        customer_file.odoo_link,
        name="customer-odoo-link",
    ),
    path(
        "customers/<int:pk>/documents/",
        customer_file.customer_documents,
        name="customer-documents",
    ),
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
    path("admins/<int:pk>/edit/", staff.admin_edit, name="admin-edit"),
    path(
        "admins/<int:pk>/password-reset/",
        staff.admin_password_reset,
        name="admin-password-reset",
    ),
    path("admins/<int:pk>/delete/", staff.admin_delete, name="admin-delete"),
    path("admins/roles/<slug:slug>/edit/", staff.role_edit, name="role-edit"),
    path("admins/roles/<slug:slug>/delete/", staff.role_delete, name="role-delete"),
    # وحدتُهما `billing` لا `people` (T936): كُتبتا هناك أوّلاً، ووحدةُ
    # الفواتير هي تلك.
    path("invoices/", billing.invoices, name="invoices"),
    path("invoices/<int:pk>/", billing.invoice_detail, name="invoice-detail"),
    path("payments/", payments.payments, name="payments"),
    # «إنشاء دفعة» — قيدٌ على فاتورةٍ بيد موظّف. صفحةٌ واحدة تبحث وتقيّد:
    # البحثُ `GET` والقيدُ `POST` على المسار نفسه، فلا عنوانٌ ثانٍ يُفتح بلا
    # فاتورةٍ في يده.
    path("payments/create/", manual_payment.payment_create, name="payment-create"),
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
    # «إرسال إشعار» — ثلاثُ خطواتٍ على مسارٍ واحد: `GET` يفتح الاستمارة،
    # و`POST step=preview` يعدّ الجمهور ويقدّر الكلفة، و`POST step=send` ينفّذ
    # برمز المعاينة. ومسارٌ واحد لأن الخطوات الثلاث شيءٌ واحدٌ لا يُدخَل من
    # منتصفه: عنوانٌ للتنفيذ وحده هو عنوانٌ يُفتح بلا عدٍّ رآه أحد.
    path("notifications/send/", broadcast.broadcast, name="broadcast"),
    # مسارٌ واحدٌ للشاشة كلِّها: الإضافةُ والتعديلُ والإيقاف `POST` عليه
    # يميّزها حقلُ `op`. ومسارٌ لكلّ فعلٍ كان يعني صفوفاً في `DETAIL_PAGES`
    # لصفحاتٍ لا تُفتح — كلُّها تُعيد التوجيه. T921.
    path("news/", news.news, name="news"),
    # شاشةٌ واحدةٌ بثلاثة أجزاء (الأقسامُ · القائمةُ · النصّ)، ومسارٌ
    # واحدٌ لها: المحادثةُ المفتوحةُ معاملٌ في الرابط لا صفحةٌ ثانية —
    # فالرابطُ الذي يُرسله موظّفٌ لزميله يفتح **ما كان يراه** بقسمه
    # ومرشّحه وصفحته، لا الشاشةَ من أوّلها. T924.
    path("support/", support.support, name="support"),
    path("audit/", audit.audit, name="audit"),
    path("inbox/", inbox.inbox, name="odoo-inbox"),
    path("inbox/<int:pk>/", inbox.message, name="odoo-message"),
    path("inbox/<int:pk>/replay/", inbox.replay, name="odoo-replay"),
    # الطابورُ كلُّه دفعةً واحدة — المنادي الوحيد لـ`retry_failed_gateway`.
    path("inbox/gateway-retry/", inbox.gateway_retry, name="gateway-retry"),
]
