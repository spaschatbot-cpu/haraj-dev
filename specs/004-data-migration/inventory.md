# T302 — جرد قاعدة v1

**المصدر:** نسخة الإنتاج التي سلّمها المالك في 2026-09-05
(`hara_clone_v1_data_20260905_1444.sql.gz`، MySQL 8.0.46، `utf8mb4`) —
**تجهيزةُ اختبار، لا مصدر الترحيل.** الترحيل الفعلي يجري من الخادم الحيّ
(T301). وهي تصلح للجرد لأن الجرد سؤالٌ عن الشكل لا عن اللحظة.

**كيف قُرئت:** بقراءةٍ متدفّقة للـgzip تستخرج البنية والعدّ فقط — بلا خادم
MySQL، وبلا استبقاء صفٍّ واحد من المحتوى. الجرد لا يحتاج اسم عميل ولا رقم
هويّة، والنسخة تحملهما.

⚠️ **النسخة لا تدخل المستودع أبداً**، ولا يُنسخ منها صفٌّ إلى ملفّ هنا. وهي
تحمل — إضافةً إلى بيانات العملاء — كلمات مرور ورموز جلسات (`userss.password`،
`session_token`، `remember_token_hash`، `verification_code`) وجدولَي
`settings` و`app_settings` اللذين قد يحملان مفاتيح تكامل. **لا شيء من ذلك
يُرحَّل، ولا يُقرأ آلياً** (المادة ٥-٣).

## الأرقام

| | العدد |
|---|---|
| الجداول | **192** |
| الصفوف | **1,376,275** |
| جداول حيّة | 104 (1,221,205 صفاً) |
| لقطات حوادث | 47 (155,070 صفاً) |
| جداول فارغة | 41 |
| **بلا قرار بعد** | **0** |

---

## ما كشفه الجرد نفسه — ستّة، ولم يكن أربعة منها في جدول الفخاخ

### ١ — ثلاثة أعمدة رصيد مشتقّة على `userss`، لا واحد

يحذّر `spec.md` من `total_insurance_paid` وحده. والجدول يحمل ثلاثة:
`total_insurance_paid` و`wallet` و`purchases_balance`. **الثلاثة تُهمَل**، لا
واحد — والدفتر يُبنى من الأحداث (المبدأ الحاكم). عمودٌ محذَّرٌ منه وعمودان
مثله بلا تحذير هو بالضبط كيف يتسرّب رصيدٌ منسوخ.

### ٢ — `invoices_odoo_loopbak_20260606` فيه **786** صفاً بالضبط

الرقم الذي تذكره الوثائق لحلقة 2026-06-06 موجودٌ في البيانات كجدولِ نسخةٍ
احتياطية باسمه وتاريخه. الحادثة ليست روايةً في وثيقة، هي صفوفٌ يمكن عدّها —
وهي أساس تقرير الفروق (T313).

### ٣ — سبعةٌ وأربعون جدولَ لقطة، وأسماؤها سِجلّ الحوادث

`insurance_deposits_bak_20260726_overdebit` · `..._20260728_duplocks` ·
`..._20260729_odoo_withdraw` · `..._20260820_154246_dupacct` ·
`..._20260812_151258_release3` · `invoices_odoo_late_dupe_purge_20260607` ·
`invoices_odoo_bak_20260801_stale` · `bids_preend_20260606_185855` — وغيرها.
كلٌّ منها لحظةٌ أُخذت فيها نسخة قبل إصلاح يدوي. **لا يُرحَّل منها شيء**، وكلها
تُقرأ في T313: هي الجواب على «لماذا يختلف رصيد هذا العميل».

وبعضها باسم شخص (`abubakr_20260805_bak_bids` · `..._mahmoud` · `..._nidal` ·
`zaar` · `qomah` · `rubel` · `phantom` · `hehewala`) — إصلاحاتٌ فردية بأسماء
من أجراها أو من وقعت عليه.

### ٤ — `vehicle_images` **فارغ**، والصور في `car_images`

الجدول الأحدث (`vehicle_images`، وفيه `image_blob longblob`) صفر صفّاً؛
والصور الفعلية ٩٢٬٠٢٤ صفاً في `car_images`، **مساراتٍ لا كتلاً**. وهو يشير
إلى `details` عبر `id_details` — لا إلى `auction_vehicles`. أي ترحيلٍ للصور
يمرّ بـ`details` أولاً.

وهذا يخصّ HR-12 مباشرةً: الـ١٣ جيجابايت ملفّاتٌ على القرص لا صفوفٌ في القاعدة،
فإعادة بناء الطبقات (`rebuild_image_tiers`) تحتاج الملفّات نفسها لا هذه النسخة.

### ٥ — خمسة جداول باسم «فواتير»

`invoices_odoo` (12,434) هو الحيّ. ومعه `invoices` (فارغ) و`invoices_odoo2`
(فارغ) و`invoices_oddo1` (4، بخطأ إملائي) و`invoicesone` (4). **الاسم وحده لا
يكفي لتمييز المصدر**، والبانِي يسمّي جدوله صراحةً.

### ٦ — `bids_backup_auction_name` فيه 84,005 صفاً بثلاثة أعمدة

نسخةٌ من المزايدات مفتاحُها **اسم المزاد**. أي أن المزادات عُرّفت بأسمائها في
وقتٍ ما، ومعها `auction_name` (6 صفوف). يُقرأ عند بناء المزادات (T308) قبل
الاعتماد على أي معرّف رقمي قديم.

---

## أ — الجداول الحيّة (104)

| الجدول | الصفوف | الوجهة | السبب |
|---|---:|---|---|
| `notifications` | 543,354 | لا يُرحَّل | ٥٤٣ ألف إشعار مُسلَّم — تاريخٌ لا يُقرأ، ونظامنا يُنشئ إشعاراته |
| `bids` | 119,985 | يُرحَّل | ١٢٠ ألف مزايدة — تاريخ المزايدة كاملاً |
| `haraj_chat_conversations` | 93,295 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `haraj_chat_messages` | 93,261 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `car_images` | 92,024 | يُرحَّل | ٩٢ ألف صورة — مسارات لا كتل. **وهي جدول الصور الحقيقي** |
| `sms_log` | 74,861 | أرشيف | ٧٥ ألف رسالة — دليلٌ تنظيمي، لا حالة |
| `userss` | 44,039 | يُرحَّل | المستخدمون والشركات (T306). **والأعمدة المشتقّة الثلاثة تُهمَل** — انظر أدناه |
| `favorites` | 20,300 | يُرحَّل | المفضّلة — لها نظير (`apps/auctions/favourites.py`) |
| `payments_odoo` | 18,704 | يُرحَّل | الدفعات كما جاءت من أودو — مصدر أحداث الدفتر |
| `bid_edit_audit` | 18,533 | يُرحَّل | سجلّ تعديل المزايدة — نظيره HR-07 عندنا |
| `customer_links` | 14,708 | يُرحَّل | رسم الهوية (T307) — وهو أول ما يُبنى، إذ لا يُنسب ريال قبله |
| `auction_vehicles` | 13,079 | يُرحَّل | المركبات (T308). **`status` ضُغط مرّة لوسيط أضيق** — يُقرأ من المصدر الأوسع |
| `invoices_odoo` | 12,434 | يُرحَّل | الفواتير (T309). **`auction_id` فاسد يحمل `vehicle_id`** — الربط عبر `auction_vehicles` |
| `otp_events` | 10,273 | لا يُرحَّل | ١٠ آلاف حدث تحقّق — منتهية الصلاحية بطبيعتها |
| `details` | 8,801 | يُرحَّل | تفاصيل المركبة، و`car_images.id_details` يشير إليه |
| `plate_delivery_management` | 7,904 | يُرحَّل | تسليم اللوحات — تكملة ما بعد البيع |
| `auctions_claims` | 7,847 | يُرحَّل | مطالبات المزاد — لها أثر مالي |
| `odoo_inbox` | 5,639 | أرشيف | ٥٦٣٩ رسالة واردة — **دليلٌ ثمين للفروق (T313)**، ولا تُعاد معالجتها |
| `wallet_transactions` | 4,907 | يُرحَّل | حركات المحفظة — الحدث لا الرصيد |
| `refunds_requests` | 3,289 | يُرحَّل | الاسترداد. **`customer_id` يقابل `userss.id_customer` لا `userss.id`** |
| `recipient_id_images` | 2,673 | يُرحَّل | صور هويّة المستلم — **بيانات شخصية، تُنقل بحذر** |
| `vehicle_exits` | 2,652 | يُرحَّل | أوامر الخروج — شاشة غير مخطَّطة عندنا بعد (ش1) |
| `insurance_deposits` | 2,143 | يُرحَّل | أحداث الوديعة، منها يُبنى الدفتر (T310) بحالتها كما هي |
| `odoo_payment_pushes` | 1,140 | أرشيف | سجلّ ما دُفع إلى أودو — دليلٌ للفروق (T313) لا مصدر حالة |
| `payments_intents` | 1,096 | يُرحَّل | نوايا الشحن، تُطابَق بها الدفعات المعلّقة |
| `products_stock` | 931 | يراجَع | ٩٣١ صفاً؛ لا نظير في v2 — يُقرَّر مع المالك |
| `role_card_permissions` | 849 | لا يُرحَّل | نفسه |
| `auction_translation_options` | 615 | يُهمَل | ترجمة خيارات في لوحة قديمة |
| `transfer_requests` | 232 | يُرحَّل | طلبات التحويل — حركة مال لها أثر |
| `queue_tickets` | 221 | لا يُرحَّل | طابور مراجعين — خارج النطاق |
| `support_messages` | 220 | لا يُرحَّل | دعم — خارج نطاق v2 |
| `wallet_health_findings` | 183 | أرشيف | ١٨٣ نتيجة فحص صحّة — نظيرها عندنا `verify_ledger` يعيد الحساب |
| `admin_login_attempts` | 134 | أرشيف | محاولات دخول — دليلٌ أمني، لا حالة |
| `management_card_overrides` | 99 | لا يُرحَّل | استثناءات صلاحيات اللوحة القديمة |
| `partner_payments` | 84 | يُرحَّل | مستحقّات الشركاء |
| `cards` | 80 | لا يُرحَّل | بطاقات لوحة v1 — عنصر واجهة |
| `auctions` | 56 | يُرحَّل | ٥٦ مزاداً — كل التاريخ (قرار Q3) |
| `webhook_failures` | 46 | أرشيف | ٤٦ إخفاقاً — دليل |
| `card_permissions` | 45 | لا يُرحَّل | نفسه |
| `moyasar_payments` | 40 | يُرحَّل | شحن البطاقة — بوابة الدفع |
| `management` | 37 | لا يُرحَّل | موظّفو اللوحة القديمة — الأدوار عندنا أربعة و`StaffGrant` هو الأثر (T803/T822) |
| `company_payment` | 28 | يُرحَّل | دفعات الشركات |
| `insurance_refund_shortfalls` | 25 | يُرحَّل | ٢٥ صفاً — طابور العجز، ونظيره `odoo.RefundShortfall` (HR-09) |
| `haraj_chat_sessions` | 24 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `messages` | 22 | لا يُرحَّل | خارج النطاق |
| `chat_typing` | 16 | لا يُرحَّل | حالة لحظية |
| `roles` | 14 | لا يُرحَّل | أدوار v1؛ عندنا أربعة معرَّفة في `core/permissions.py` |
| `account_page_settings` | 12 | لا يُرحَّل | إعداد عرض |
| `haraj_chat_notifications` | 12 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `management10` | 12 | لا يُرحَّل | نسخة ثانية من الجدول نفسه |
| `waiver_requests` | 12 | يُرحَّل | استثناءات التأمين — قرار مالك موثَّق (T515) |
| `conversations` | 11 | لا يُرحَّل | خارج النطاق |
| `files` | 11 | أرشيف | أحد عشر ملفاً |
| `odoo_logs` | 11 | أرشيف | سجلّ أودو |
| `qr_codes` | 11 | لا يُرحَّل | رموز تُولَّد من جديد |
| `auction_campaigns` | 9 | يراجَع | تسع حملات؛ لا نظير في v2 |
| `user_card_permissions` | 9 | لا يُرحَّل | نفسه |
| `merchants_auctions_sheet` | 8 | أرشيف | ورقة تجّار — ثمانية صفوف، دليلٌ لا مصدر |
| `conversation_ratings` | 7 | لا يُرحَّل | خارج النطاق |
| `auction_name` | 6 | أرشيف | أسماء مزادات قديمة — يفسّر `bids_backup_auction_name` |
| `odoo_customer_sync_pending` | 6 | أرشيف | ستّة صفوف معلّقة — تُراجَع يدوياً |
| `role_section_permissions` | 6 | لا يُرحَّل | نفسه |
| `vehicles` | 6 | يراجَع | ستّة صفوف وجدول `auction_vehicles` هو المستعمل — يُقرَّر بعد فحص الستّة |
| `chat_departments` | 5 | لا يُرحَّل | خارج النطاق |
| `departments` | 5 | لا يُرحَّل | أقسام الدعم — خارج نطاق v2 |
| `haraj_chat_departments` | 5 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `management_audit_log` | 5 | أرشيف | تدقيق اللوحة القديمة — يُقرأ ولا يُرحَّل |
| `social_media` | 5 | لا يُرحَّل | روابط عرض |
| `themes1` | 5 | لا يُرحَّل | نفسه |
| `wallet_logs` | 5 | أرشيف | خمسة صفوف — سجلّ محفظة قديم |
| `audit_log` | 4 | أرشيف | أربعة صفوف — تدقيق عامّ قديم |
| `auto_bids` | 4 | يُرحَّل | المزايدة الآلية — أربعة صفوف |
| `dept_status` | 4 | لا يُرحَّل | نفسه |
| `haraj_chat_staff_departments` | 4 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `haraj_departments` | 4 | لا يُرحَّل | بنية الدعم القديمة — خارج النطاق |
| `insurance_companies` | 4 | يراجَع | أربع شركات تأمين؛ لا نظير في v2 |
| `invoices_oddo1` | 4 | أرشيف | خطأ إملائي في الاسم، أربعة صفوف — **دليلٌ على جدولٍ ثانٍ للفواتير** |
| `invoicesone` | 4 | أرشيف | نفسه، أربعة صفوف |
| `queue_departments` | 4 | لا يُرحَّل | نفسه |
| `support_replies` | 4 | لا يُرحَّل | نفسه |
| `themes` | 4 | لا يُرحَّل | سمات واجهة v1 |
| `admin_sections` | 3 | لا يُرحَّل | أقسام اللوحة القديمة |
| `firebase_tokens` | 3 | لا يُرحَّل | رموز أجهزة تنتهي — تُجمَع من جديد |
| `news_ticker` | 3 | لا يُرحَّل | شريط أخبار |
| `auction_translations` | 2 | يُهمَل | نفسه |
| `categories` | 2 | لا يُرحَّل | صفّان — تصنيف عرض |
| `haraj_chat_staff` | 2 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `insurance_cars` | 2 | يراجَع | صفّان، وعلاقته بـ`auction_vehicles` غير واضحة |
| `statistics` | 2 | لا يُرحَّل | صفّان — أرقام محسوبة |
| `vehicle_receipt` | 2 | يُرحَّل | إيصال الاستلام — صفّان |
| `aftersales_hidden_auctions` | 1 | يُهمَل | إخفاء عرضٍ في لوحة قديمة — قرار عرض لا بيانات |
| `amount` | 1 | يراجَع | جدولٌ باسم `amount` وصفٌّ واحد — يُفحص يدوياً |
| `app_meta` | 1 | لا يُرحَّل | بيانات نسخة التطبيق |
| `app_settings` | 1 | يراجَع يدوياً | نفسه |
| `chat_sessions` | 1 | لا يُرحَّل | خارج النطاق |
| `companies` | 1 | يراجَع | صفٌّ واحد — والشركات عندنا على `accounts.Company` |
| `customer_features` | 1 | يراجَع | صفٌّ واحد |
| `haraj_chat_ratings` | 1 | لا يُرحَّل | محادثات الدعم — خارج نطاق v2 كلّياً |
| `haraj_conversation_meta` | 1 | لا يُرحَّل | بنية الدعم القديمة — خارج النطاق |
| `haraj_staff` | 1 | لا يُرحَّل | بنية الدعم القديمة — خارج النطاق |
| `home_showcase` | 1 | لا يُرحَّل | عرض الصفحة الرئيسية |
| `packages` | 1 | يراجَع | صفٌّ واحد؛ `userss.id_package` يشير إليه |
| `settings` | 1 | يراجَع يدوياً | **قد يحمل مفاتيح تكامل — لا يُقرأ آلياً ولا يُرحَّل** (المادة ٥-٣) |
| `staff` | 1 | لا يُرحَّل | صفٌّ واحد؛ نموذج الموظّفين عندنا `User.is_staff` |

---

## ب — لقطات الحوادث (47)

**لا يُرحَّل منها شيء.** وكلها تُقرأ في T313 — هي الدليل على كل فرقٍ سيظهر.

| الجدول | الصفوف |
|---|---:|
| `bids_backup_auction_name` | 84,005 |
| `bids_preend_20260606_185855` | 46,707 |
| `auction_vehicles_preend_20260606_185855` | 8,806 |
| `av_status_bak_20260602` | 8,804 |
| `insurance_deposits_bak_20260717_190209` | 1,231 |
| `insurance_deposits_bak_20260716_165410` | 1,204 |
| `insurance_deposits_bak_20260820_144954_voidreason` | 1,068 |
| `invoices_odoo_bak_20260620` | 1,046 |
| `invoices_odoo_loopbak_20260606` | 786 |
| `insurance_deposits_preend_20260606_185855` | 692 |
| `vehicle_exits_bak_20260716_145551` | 466 |
| `insurance_deposits_fix_bak_20260718` | 58 |
| `invoices_odoo_bak_20260728_backfill` | 38 |
| `insurance_deposits_bak_20260729_odoo_withdraw` | 27 |
| `management_old_backup_20260607` | 18 |
| `insurance_deposits_bak_20260728_duplocks` | 16 |
| `insurance_deposits_bak_20260726_overdebit` | 13 |
| `invoices_odoo_bak_20260801_stale` | 12 |
| `pull_20260803_bak` | 12 |
| `insurance_deposits_bak_20260729_missed2` | 10 |
| `abubakr_20260805_bak_bids` | 6 |
| `restore_20260805_bak` | 5 |
| `bids_bak_20260821_143655_mahmoud` | 3 |
| `fix68_bak_deposits` | 3 |
| `insurance_deposits_bak_20260812_151258_release3` | 3 |
| `invoices_odoo_deleted_bak` | 3 |
| `invoices_odoo_late_dupe_purge_20260607` | 3 |
| `insurance_deposits_bak_20260620` | 2 |
| `insurance_deposits_bak_20260725_ajlan` | 2 |
| `insurance_deposits_bak_20260725_muheet` | 2 |
| `insurance_deposits_bak_20260726_athyah` | 2 |
| `insurance_deposits_bak_20260820_154246_dupacct` | 2 |
| `last2_20260805_bak` | 2 |
| `zaar_20260805_bak` | 2 |
| `abubakr_20260805_bak_deposits` | 1 |
| `bids_bak_20260812_152428_nidal` | 1 |
| `insurance_deposits_bak_20260729_msuliman` | 1 |
| `insurance_deposits_bak_20260812_152428_nidal` | 1 |
| `insurance_deposits_bak_20260821_143655_mahmoud` | 1 |
| `phantom_20260805_bak` | 1 |
| `qomah_20260805_bak` | 1 |
| `rubel_20260805_bak` | 1 |
| `undo_11603_bak_bids` | 1 |
| `undo_11603_bak_vehicles` | 1 |
| `userss_bak_20260820_154444_jawad` | 1 |
| `bids_backup_20260214` | 0 |
| `hehewala` | 0 |

---

## ج — الجداول الفارغة (41)

صفر صفّاً، فلا شيء يُرحَّل. مذكورةٌ بالاسم لأن «لا جدول بلا قرار مكتوب» يشمل
الفارغ: قارئٌ لاحقاً يحتاج أن يعرف أنها نُظر إليها ووُجدت فارغة، لا أنها
فاتت.

`admin_notifications` · `api_tokens` · `attendance` · `auction_park_logs` · `bank_transfers` · `chat_agent_departments` · `chat_agents` · `chat_conversations` · `chat_messages` · `chat_ratings` · `delivery_requests` · `employees` · `fcm_tokens` · `haraj_chat_agents` · `haraj_support_tickets` · `home_showcase_items` · `insurance_payments` · `invoices` · `invoices_odoo2` · `invoicesonepayment` · `logs` · `merchants_sheet` · `notifications_payment` · `office_qr_tokens` · `paid_com` · `partial_payments` · `payment_intents` · `payments` · `payments_test` · `purchases` · `queue_counters` · `refund_requests` · `requests` · `shares` · `support_chat_sessions` · `support_tickets` · `translation_options` · `turn_bookings` · `user_auctions` · `user_tokens` · `vehicle_images`

---

## بوابة إغلاق T302

- [x] كل جدول من الـ192 له قرارٌ مكتوب وسببه.
- [ ] **الجداول المعلَّمة «يراجَع» تحتاج فحصاً يدوياً** قبل T303 — وهي قليلة
      وصغيرة، وكلها إما ستّة صفوف أو أقلّ أو جدولٌ لا نظير له في v2.
- [ ] **T301 لا تمسّها هذه النسخة.** النسخة تجهيزةُ اختبار بقول المالك،
      والترحيل الفعلي يجري من الخادم الحيّ عبر حساب القراءة فقط الذي تطلبه
      تلك التاسك. ومعيار D6 يخصّ الخادم، ولا يُثبَت بوجود نسخة على قرصٍ آخر.
