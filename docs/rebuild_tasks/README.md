# حراج واحد — المخطط الشامل لإعادة البناء: شاشات الأدمن ومحركات النظام

> **دليل وثائق إعادة البناء الموجهة للتطوير:**
> تم تفريغ كافة الشاشات ومحركات النظام في ملفات تاسكات مفصلة ومستقلة تركز على: **المشاكل الحقيقية، الحقول والأعمدة والداتا المعروضة، والشروط والقيود الإلزامية** لتمكين فريق التطوير من بناء المنطق الأفضل بأعلى درجات الأمان المالي.

---

## ١. خريطة المراحل وتوزيع ملفات التاسكات التفصيلية (Rebuild Phases)

```
rebuild_tasks/
├── PHASE_01_AUCTION_ENGINE/               # محرك المزاد والمزايدة ودورة الحياة
│   ├── TASK_01_AUCTION_LIFECYCLE.md
│   ├── TASK_02_BIDDING_VALIDATION_ENGINE.md
│   ├── TASK_03_BID_DOWNGRADE_AND_CONFIRMATION.md
│   └── TASK_04_BID_AUDIT_AND_INTEGRITY.md
│
├── PHASE_02_WALLET_AND_INSURANCE/         # محرك المحفظة والتأمين والودائع
│   ├── TASK_01_INSURANCE_DEPOSIT_UNIT_MODEL.md
│   ├── TASK_02_DOUBLE_LOCK_AND_DUES_ENCUMBRANCE.md
│   ├── TASK_03_INSURANCE_TOPUP_AND_GATEWAYS.md
│   └── TASK_04_REFUND_POLICY_AND_SETTLEMENT.md
│
├── PHASE_03_INVOICES_AND_BILLING/         # محرك الفواتير والتحصيل والربط المالي مع Odoo
│   ├── TASK_01_INVOICE_LIFECYCLE_AND_ODOO_SYNC.md
│   ├── TASK_02_BILLING_CALCULATION_AND_TAX_RULES.md
│   └── TASK_03_ODOO_INTEGRATION_MASTER_MAP.md    # وثيقة التكامل الشاملة وقواعد أودو
│
├── PHASE_04_AUCTION_VEHICLE_ADMIN/        # شاشات إدارة المزادات والمركبات
│   ├── TASK_01_PAGE_AUCTIONS_LIST_AND_CREATE.md
│   ├── TASK_02_PAGE_AUCTION_MANAGE_AND_VEHICLES.md
│   ├── TASK_03_PAGE_QUICK_EDIT_MILEAGE_PARK.md
│   ├── TASK_04_PAGE_VEHICLE_SEARCH.md
│   └── TASK_05_PAGE_AUCTIONS_BULK_OPS.md          # شاشة العمليات المجمعة والإيقاف الطارئ
│
├── PHASE_05_DECISION_AND_AFTER_SALES/     # لوحة قرارات الترسية وما بعد البيع
│   ├── TASK_01_PAGE_DECISION_BOARD_ACTIVE_BIDS.md
│   ├── TASK_02_PAGE_ACCEPTED_BIDS_INVOICING.md
│   ├── TASK_03_PAGE_VEHICLE_EXIT_ELECTRONIC.md
│   ├── TASK_04_PAGE_OWNERSHIP_TRANSFER_FOLLOWUP.md
│   └── TASK_05_PAGE_AFTER_SALES_AND_ARCHIVE.md    # شاشة أرشيف المزادات وما بعد البيع
│
├── PHASE_06_CUSTOMER_AND_USER_ADMIN/      # إدارة العملاء والملف الشامل 360
│   ├── TASK_01_PAGE_CUSTOMER_360_PROFILE.md
│   ├── TASK_02_PAGE_USERS_MANAGEMENT.md
│   └── TASK_03_PAGE_USER_BIDS_REPORT.md
│
├── PHASE_07_FINANCIAL_OPS_ADMIN/          # العمليات المالية وصحة المحفظة والمطابقة
│   ├── TASK_01_PAGE_WALLET_HEALTH_MONITOR.md
│   ├── TASK_02_PAGE_BID_ELIGIBILITY_DIAGNOSTIC.md
│   ├── TASK_03_PAGE_REFUNDS_MANAGEMENT.md
│   ├── TASK_04_PAGE_PAYMENTS_MANAGEMENT.md        # شاشة إدارة المدفوعات وتحديث السداد
│   ├── TASK_05_PAGE_WALLET_CREDIT_AND_DEDUCT.md
│   └── TASK_06_PAGE_PACKAGES_AND_SUBSCRIPTIONS.md # شاشات باقات واشتراكات المعارض
│
└── PHASE_08_SYSTEM_AND_PARTNER/           # صلاحيات النظام وشريك التسويق
    ├── TASK_01_PAGE_ADMINS_AND_PAGE_CONTROL.md
    ├── TASK_02_PAGE_CARDS_AND_ROLE_PERMISSIONS.md
    ├── TASK_03_PAGE_PARTNER_CONSOLE_AND_PAYMENTS.md # بوابة شريك التسويق واعتماد مدفوعاته
    └── TASK_04_PAGE_NEWS_AND_NOTIFICATIONS.md
```

---

## ٢. فهرس الشاشات حسب معدل الاستخدام والأهمية التشغيلية

| الشاشة / الوحدة | المسار (Route) | الأهمية | معدل الاستخدام | ملف التاسك المخصص |
|---|---|---|---|---|
| **اتخاذ القرار وقبول العروض** | `/bills/active` & `/owners-console` | 🔴 حرجة جداً | أسبوعياً (نهاية كل مزاد) | [`PHASE_05/TASK_01_PAGE_DECISION_BOARD_ACTIVE_BIDS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_05_DECISION_AND_AFTER_SALES/TASK_01_PAGE_DECISION_BOARD_ACTIVE_BIDS.md) |
| **المزايدات المقبولة والفوترة** | `/bills/accepted` | 🔴 حرجة جداً | أسبوعياً (بعد اتخاذ القرار) | [`PHASE_05/TASK_02_PAGE_ACCEPTED_BIDS_INVOICING.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_05_DECISION_AND_AFTER_SALES/TASK_02_PAGE_ACCEPTED_BIDS_INVOICING.md) |
| **إدارة المزاد والسيارات والكروت** | `/auctions/manage` | 🔴 حرجة جداً | يومياً (أثناء التجهيز) | [`PHASE_04/TASK_02_PAGE_AUCTION_MANAGE_AND_VEHICLES.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_04_AUCTION_VEHICLE_ADMIN/TASK_02_PAGE_AUCTION_MANAGE_AND_VEHICLES.md) |
| **ملف العميل الشامل (Customer 360)** | `/customers/{id}` | 🔴 حرجة جداً | يومياً بشكل متكرر | [`PHASE_06/TASK_01_PAGE_CUSTOMER_360_PROFILE.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_06_CUSTOMER_AND_USER_ADMIN/TASK_01_PAGE_CUSTOMER_360_PROFILE.md) |
| **الاستردادات والتدقيق المالي** | `/refunds` | 🔴 حرجة جداً | يومياً عند طلبات العملاء | [`PHASE_07/TASK_03_PAGE_REFUNDS_MANAGEMENT.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_03_PAGE_REFUNDS_MANAGEMENT.md) |
| **أمر الخروج الإلكتروني بالباركود** | `/vehicle-exit` | 🔴 حرجة جداً | يومياً (عند تسليم المركبات) | [`PHASE_05/TASK_03_PAGE_VEHICLE_EXIT_ELECTRONIC.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_05_DECISION_AND_AFTER_SALES/TASK_03_PAGE_VEHICLE_EXIT_ELECTRONIC.md) |
| **تشخيص أهلية المزايدة** | `/bid-eligibility` | 🟠 عالية جداً | لحظياً عند شكاوى العملاء | [`PHASE_07/TASK_02_PAGE_BID_ELIGIBILITY_DIAGNOSTIC.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_02_PAGE_BID_ELIGIBILITY_DIAGNOSTIC.md) |
| **صحة المحفظة والفحص الذاتي** | `/wallet-health` | 🟠 عالية جداً | يومياً لمسؤولي النظام | [`PHASE_07/TASK_01_PAGE_WALLET_HEALTH_MONITOR.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_01_PAGE_WALLET_HEALTH_MONITOR.md) |
| **إنشاء مزاد جديد مجمع** | `/auctions/create` | 🟠 عالية جداً | أسبوعياً | [`PHASE_04/TASK_01_PAGE_AUCTIONS_LIST_AND_CREATE.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_04_AUCTION_VEHICLE_ADMIN/TASK_01_PAGE_AUCTIONS_LIST_AND_CREATE.md) |
| **التعديل السريع للعدادات والمواقف** | `/auctions/quick-edit` | 🟠 عالية جداً | أسبوعياً أثناء الفحص الميداني | [`PHASE_04/TASK_03_PAGE_QUICK_EDIT_MILEAGE_PARK.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_04_AUCTION_VEHICLE_ADMIN/TASK_03_PAGE_QUICK_EDIT_MILEAGE_PARK.md) |
| **البحث الشامل عن المركبات** | `/vehicles/search` | 🟡 متوسطة - عالية | مستمر للبحث السريع | [`PHASE_04/TASK_04_PAGE_VEHICLE_SEARCH.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_04_AUCTION_VEHICLE_ADMIN/TASK_04_PAGE_VEHICLE_SEARCH.md) |
| **العمليات المجمعة وإيقاف المزاد** | `/auctions/bulk` | 🟡 طوارئ | عند الطوارئ والجدولة | [`PHASE_04/TASK_05_PAGE_AUCTIONS_BULK_OPS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_04_AUCTION_VEHICLE_ADMIN/TASK_05_PAGE_AUCTIONS_BULK_OPS.md) |
| **متابعة نقل الملكية والتنبيهات** | `/vehicle-exit/transfer` | 🟡 متوسطة - عالية | يومياً لمسؤولي التسجيل | [`PHASE_05/TASK_04_PAGE_OWNERSHIP_TRANSFER_FOLLOWUP.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_05_DECISION_AND_AFTER_SALES/TASK_04_PAGE_OWNERSHIP_TRANSFER_FOLLOWUP.md) |
| **أرشيف المزادات وما بعد البيع** | `/after-sales` | 🟡 دورية | بعد تسليم المزاد بالكامل | [`PHASE_05/TASK_05_PAGE_AFTER_SALES_AND_ARCHIVE.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_05_DECISION_AND_AFTER_SALES/TASK_05_PAGE_AFTER_SALES_AND_ARCHIVE.md) |
| **إدارة المدفوعات وتحديث السداد** | `/payments` | 🟡 متوسطة - عالية | يومياً لقسم المحاسبة | [`PHASE_07/TASK_04_PAGE_PAYMENTS_MANAGEMENT.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_04_PAGE_PAYMENTS_MANAGEMENT.md) |
| **إدارة المستخدمين والحظر** | `/users` | 🟡 متوسطة | يومياً لخدمة العملاء | [`PHASE_06/TASK_02_PAGE_USERS_MANAGEMENT.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_06_CUSTOMER_AND_USER_ADMIN/TASK_02_PAGE_USERS_MANAGEMENT.md) |
| **تقرير مزايدات العميل والتدقيق** | `/users/bids-report` | 🟡 متوسطة | عند مراجعة نزاعات الأسعار | [`PHASE_06/TASK_03_PAGE_USER_BIDS_REPORT.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_06_CUSTOMER_AND_USER_ADMIN/TASK_03_PAGE_USER_BIDS_REPORT.md) |
| **الشحن اليدوي والخصم المباشر** | `/finance/wallet-credit` | 🟡 متوسطة | عند تسويات خاصة من الإدارة | [`PHASE_07/TASK_05_PAGE_WALLET_CREDIT_AND_DEDUCT.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_05_PAGE_WALLET_CREDIT_AND_DEDUCT.md) |
| **باقات الاشتراكات للمعارض** | `/finance/packages` | 🟢 دورية | شهرية / ربع سنوية | [`PHASE_07/TASK_06_PAGE_PACKAGES_AND_SUBSCRIPTIONS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_07_FINANCIAL_OPS_ADMIN/TASK_06_PAGE_PACKAGES_AND_SUBSCRIPTIONS.md) |
| **بوابة شريك التسويق (التعاونية)** | `/partner` | 🟢 دورية للشريك | أسبوعياً للشركاء | [`PHASE_08/TASK_03_PAGE_PARTNER_CONSOLE_AND_PAYMENTS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_08_SYSTEM_AND_PARTNER/TASK_03_PAGE_PARTNER_CONSOLE_AND_PAYMENTS.md) |
| **إدارة المشرفين وتجاوزات الصفحات** | `/admins` & `/page-control` | 🟢 إدارية | عند إضافة موظف جديد | [`PHASE_08/TASK_01_PAGE_ADMINS_AND_PAGE_CONTROL.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_08_SYSTEM_AND_PARTNER/TASK_01_PAGE_ADMINS_AND_PAGE_CONTROL.md) |
| **إدارة الكروت ومصفوفة الصلاحيات** | `/cards` & `/permissions` | 🟢 إدارية عليا | نادراً (ضبط أمني) | [`PHASE_08/TASK_02_PAGE_CARDS_AND_ROLE_PERMISSIONS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_08_SYSTEM_AND_PARTNER/TASK_02_PAGE_CARDS_AND_ROLE_PERMISSIONS.md) |
| **شريط الأخبار والإشعارات** | `/news` & `/notifications` | 🟢 محتوى ودعم | عند إطلاق تنبيهات للمستخدمين | [`PHASE_08/TASK_04_PAGE_NEWS_AND_NOTIFICATIONS.md`](file:///d:/haraj%201/applicationtest/rebuild_tasks/PHASE_08_SYSTEM_AND_PARTNER/TASK_04_PAGE_NEWS_AND_NOTIFICATIONS.md) |
