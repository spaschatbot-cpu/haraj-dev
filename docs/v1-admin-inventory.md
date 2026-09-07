# جرد لوحة v1 (`admin_v2`) مقابل لوحة v2

مصدر هذا الجرد **كود v1 على القرص** (`D:\taskss\harajj`)، لا الموقع الحيّ:
`https://haraj1.com.sa/application/admin_v2/` لوحةٌ خلف تسجيل دخول على نظام
إنتاجٍ يعمل، ولا يُدخَل إليها من هنا. والكود يقول ما تقوله الشاشة وزيادة —
يقول أيضاً ما هو محروسٌ بماذا، وهو ما لا يظهر في لقطة شاشة.

**كيف يُحدَّث:** `python ops/preview_console.py` لا علاقة له بهذا الملف. الأرقام
أدناه مستخرجةٌ بـ`grep` على `admin_v2/index.php` و`src/Views/Admin/`؛ أعِد
استخراجها قبل الاعتماد عليها إن تغيّر v1.

---

## الأرقام كما هي (٦ سبتمبر ٢٠٢٦، بعد T826)

| | v1 (`admin_v2`) | v2 (`apps/console`) |
|---|---|---|
| مسارات (GET + POST) | **٢٥١** | ٤٣ |
| منها GET | **١٤٠** | — |
| متحكّمات / وحدات | **٣٢** | ١٥ |
| قوالب عرض | **١٠٨** | ٣٤ |
| صفحات في الشريط الجانبي | (انظر لقطة المالك) | **١٦** |
| صفحات تفصيل محروسة | — | **٢٦** |

الفجوة ليست «تصميماً»: هي **٣٢ متحكّماً مقابل ١٥**. أي أن الشكل الجديد جاهزٌ
قبل أن يكون له ما يعرضه في أكثر من نصف الأقسام.

(الأرقام أعلاه بعد T826، معدودةً من `apps/console/urls.py` و`navigation.PAGES`
ومجلّد القوالب. كانت قبله: ٣٩ مساراً، و١٢ وحدة، و٣٠ قالباً، و١٣ صفحة.)

---

## v1: المتحكّمات بحجمها، وما يقابلها في v2

الترتيب بعدد المسارات — الأثقل أولاً، لأنه أثقل عملاً.

| متحكّم v1 | GET/POST | يقابله في v2 | الحالة |
|---|---|---|---|
| `AuctionController` | ٢١/٢٨ | `console:auctions` + شاشات المزاد | 🟡 جزئي — v2 فيه دورة الحياة والنقلات، ولا فيه: `bulk`, `end-control`, `quick-edit`, `edit-hub`, `management`, صور المركبات |
| `AfterSalesController` | ١١/٩ | — | ⬜ غائب كلياً (ما بعد البيع، الخروج ونقل الملكية) |
| `BillController` | ١٠/٩ | `console:invoices` | 🟡 جزئي — `accepted`/`active`/`live`/`equal`/`cooperative`/`completed-decisions` كلها غائبة |
| `PartnerConsoleController` | ١٤/٢ | `console:partner-decisions` | 🟡 جزئي — v2 فيه القرار وحده؛ لوحة الشريك والتسويات والحالات غائبة |
| `AnalyticsController` | ١٥/٠ | `console:dashboard` | 🟡 جزئي — v2 فيه لوحة واحدة؛ v1 فيه ١٥ تقريراً (أرباح، تأمين، مزايدات، محفظة، مزاد نشط) |
| `UserController` | ٩/٣ | `console:customers` | 🟡 جزئي — المرفقات وتقرير المزايدات وبحث الهاتف غائبة |
| `FinanceController` | ٥/٦ | `console:money-actions` | 🟡 جزئي — الاشتراكات والباقات والخصم المباشر والاسترداد اليدوي غائبة |
| `AccountController` | ٤/٦ | — | ⬜ غائب (الملف الشخصي، تغيير كلمة المرور، الإعدادات) |
| `PaymentController` | ٦/٤ | `console:payments` | 🟡 السجلّ والفلاتر — تسجيل دفعةٍ بيد موظّف لم يُبنَ |
| `RefundController` | ٣/٥ | `console:odoo-inbox` جزئياً | 🟡 المراجعة والإحصاءات غائبة |
| `BookingController` | ٤/٣ | — | ⬜ غائب (الحجوزات) |
| `AuctionBidsAdminController` | ٥/٢ | `console:auction-bids` | 🟡 القائمة والحالات — تعديل المزايدة لم يُبنَ |
| `InvoiceController` | ٥/٢ | `console:invoices` | 🟡 PDF وodoo وlookup غائبة |
| `OwnersAuctionBidsController` | ٤/٣ | — | ⬜ غائب (منصّة الملّاك) |
| `AdminUserController` | ٣/٣ | `console:staff-grants` | 🟡 التحكّم بالصفحات لكل موظف غائب |
| `PackageController` | ٣/٣ | — | ⬜ غائب (الباقات) |
| `CampaignController` | ٣/٢ | — | ⬜ غائب (الحملات) |
| `CardsController` | ٢/٣ | — | ⬜ غائب (إدارة الكروت وصلاحياتها) |
| `PartnerPaymentsController` | ٢/٣ | — | ⬜ غائب (اعتماد مدفوعات الشريك) |
| `VehicleDetailController` | ١/٣ | `console:vehicle-detail` | ✅ |
| `NewsTickerController` | ١/٣ | — | ⬜ غائب (الشريط الإخباري) |
| `NotificationController` | ٢/٢ | `console:notifications` | 🟡 السجلّ — إعادة الإرسال لم تُبنَ |
| `CustomerController` | ٢/٠ | `console:customer-detail` | ✅ |
| `VehicleCatalogController` | ١/١ | `console:vehicles` | ✅ |
| `OrderRequestController` | ١/١ | — | ⬜ غائب (الطلبات) |
| `WalletHealthController` | ١/١ | `console:money-health` | ✅ وأوسع في v2 |
| `LoginController` | ١/٠ | `console:sign-in` | ✅ |
| `DashboardController` | ١/٠ | `console:home` | ✅ |
| `SectionController` | ١/٠ | — | ⬜ غائب (مركز الأقسام) |
| `AuctionArchiveController` | ١/٠ | `console:auction-archive` | ✅ وأوسع: الإجمالي مشتقٌّ لا مخزَّن |
| `OwnersConsoleController` | ١/٠ | — | ⬜ غائب (لوحة الملّاك) |
| `BidEligibilityController` | ١/٠ | `console:why-no-bid` | ✅ |

**الحصيلة بعد T826:** ٩ متحكّمات مغطّاة، ١٢ جزئية، **١١ غائبة كلياً**.
(كانت ٨ / ٩ / ١٥ قبله.)

---

## ما لا يُنقَل كما هو

الجرد ليس قائمة نسخ. ثلاثة أشياء في v1 لا تُعاد بنفس الشكل، ولكلٍّ سببٌ في
الدستور أو في حادثةٍ موثّقة:

1. **الأرصدة المخزَّنة.** جرد T302 وجد في `userss` ثلاثة أعمدة رصيد مشتقّة
   (`total_insurance_paid`, `wallet`, `purchases_balance`) وكلها تُهمَل. أي
   شاشةٍ في v1 تقرأ عموداً منها تُعاد في v2 مشتقّةً من الدفتر — الرقم نفسه
   لا يعني الحساب نفسه.
2. **٢٠٨ من ٢٢٤ مساراً في v1 تحمل فحص تسجيل دخولٍ بلا صلاحيةٍ خلفه** —
   مكتوبٌ بالحرف في تعليق `admin_v2/index.php` نفسه، وهو سبب وجود قائمة
   السماح للشريك هناك. في v2 كل صفحةٍ لها `capability` واحدة تُظهرها في
   الشريط وتأذن بفتحها (`apps/console/navigation.py`)، ولا صفحة بلا واحدة —
   يحرسه `ops/checks/every_capability_guards_something.py`.
3. **الشاشات المكرّرة.** v1 فيه `auctions/manage` و`auctions/management`
   و`auctions/edit-hub` و`auctions/quick-edit` — أربع بوّاباتٍ إلى العمل
   نفسه. عدد الشاشات ليس هدفاً؛ تغطية **الأفعال** هي الهدف.

---

## الترتيب المقترح للإغلاق

بحسب ما يستعمله المالك يومياً (Q4 في `specs/000-roadmap.md` لم يُحسم بعد،
وهذا الترتيب افتراضٌ يُراجَع معه):

| # | الحزمة | يغطّي | حجم تقديري |
|---|---|---|---|
| ~~٠~~ | ~~ما لا يحتاج هجرةً~~ | ~~الأرشيف · مزايدات المزاد · الدفعات · الإشعارات~~ | **✅ T826** |
| ١ | المال المتبقّي | `PackageController` · `FinanceController` الباقي · `RefundController` | ٢١ مساراً |
| ٢ | ما بعد البيع والخروج | `AfterSalesController` | ٢٠ مساراً |
| ٣ | الشريك كاملاً | `PartnerConsoleController` · `PartnerPaymentsController` | ٢١ مساراً |
| ٤ | الفواتير الستّ | `BillController` الباقي · `InvoiceController` | ١٩ مساراً |
| ٥ | التقارير | `AnalyticsController` | ١٥ مساراً |
| ٦ | الملّاك | `OwnersConsoleController` · `OwnersAuctionBidsController` | ٨ مسارات |
| ٧ | الحساب والإدارة | `AccountController` · `CardsController` · `NewsTickerController` · `SectionController` | ١٣ مساراً |
| ٨ | المتفرّقات | `BookingController` · `CampaignController` · `OrderRequestController` | ١٣ مساراً |

كل حزمةٍ تُفتح تاسكاتٍ في `specs/009-admin-console/tasks.md`، ولا تُغلق إلا
بشاشةٍ محروسةٍ باختبارٍ يفتحها بكل دور — كما تفعل `test_navigation.py` اليوم.
