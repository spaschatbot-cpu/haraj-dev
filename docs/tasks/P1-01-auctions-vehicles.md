# P1-01 · المزادات والمركبات

> **11,635,019 طلب** — 96% من كل حركة لوحة الإدارة. ومعها 3,375,747 طلب صور تخدمها.
> `AuctionController` · 5,186 سطر · 50 مسار · 34 جدول.
> هذه أكبر صفحة في النظام وأخطرها على البيانات: منها تُنشأ المزادات وتُدخَل المركبات
> وتُرفع الصور وتُنقَل السيارات بين المزادات وتُنهى المزادات جماعياً.

---

## 1) ما تفعله

| المسار | الغرض |
|---|---|
| `GET /auctions` | قائمة المزادات (56 مزاداً) |
| `GET /auctions/{id}/vehicles` | **الشاشة الرئيسية** — مركبات المزاد وتعديلها |
| `GET /auctions/{id}/vehicles/quick-edit` | تعديل سريع بالجملة |
| `POST /auctions/{id}/vehicles/add` · `/update` · `/delete` | دورة حياة المركبة |
| `POST /auctions/{id}/vehicles/bulk-upload` | رفع مركبات من ملف |
| `POST /auctions/{id}/vehicles/bulk-status` · `bulk-marketing` · `bulk-move-auction` | عمليات جماعية |
| `POST /auctions/{a}/vehicles/{v}/images/upload` · `delete` · `set-display-image` | الصور |
| `GET  /vehicle-image/{imageId}` · `.../display-image` | بثّ الصور (3.3M طلب) |
| `POST /auctions/bulk/end-all-auctions` · `end-all-bids` | إنهاء جماعي ⚠️ |
| `GET  /auctions/{id}/export-excel` · `POST /auctions/import-csv` | التصدير والاستيراد |
| `GET  /vehicles/search` | بحث عام في كل المركبات |

---

## 2) الجداول والحقول

### `auctions` — 56 صفاً · 20 عموداً

| الحقل | النوع | ملاحظة |
|---|---|---|
| `id` | int | |
| `name_of_auction` | varchar | «مزاد 53» |
| `start_time` · `end_time` | datetime | **بتوقيت السعودية** — والـ`NOW()` بتوقيت UTC |
| `status` | enum | `not_active` · `active` · `soon` · `later` · `coming` · `relater` · `upcoming` · `ended` |
| `type_auctions` | varchar | نوع المزاد |
| `vat_type` | varchar | ⚠️ يُخزَّن أحياناً `15` وأحياناً `0.15` — طبِّعه بـ`AuctionVat` |
| `fees` | decimal | رسوم تُضاف قبل الضريبة |
| `insurance_amount` | decimal | التأمين المطلوب لدخول المزاد |
| `is_mega_auction` | tinyint | مزاد متعدد المركبات |
| `starting_price` · `increment` | decimal | مخلَّفات النموذج القديم (سيارة واحدة لكل مزاد) |
| `car_name` · `image` · `id_park` · `mileage` | varchar | نفس المخلَّفات — **لا تُحذف**، `admin2` يقرؤها |

**التوزيع الفعلي:** `not_active`=51 · `upcoming`=2 · `active`=**1** · `later`=1 · `ended`=1.
> المزاد الحيّ واحد في أي لحظة تقريباً — لكن الكود يجب ألّا يفترض ذلك.

### `auction_vehicles` — 13,079 صفاً · 56 عموداً

هذا هو الجدول المحوري. أعمدته أربع مجموعات:

**التعريف والعرض**
`id` · `auction_id` · `lot_number` (الموقف — varchar يحمل أرقاماً، **رتِّبه رقمياً**) ·
`vehicle_name` · `vehicle_brand` · `make` · `model` · `year` · `year_of_manufacture` ·
`the_color` · `mileage` · `Plate_number` (بحرف كبير) · `plate_type` · `chassis_number` ·
`claim_number` (**رقم المطالبة — المرجع المتفق عليه مع الشريك**) · `overview` ·
`display_image` · `fuel_type` · `the_doors` · `the_weight`

**الحالة والفحص**
`status` (varchar لا enum): `not_active`=11,915 · `active`=405 · `coming`=363 ·
`ended`=288 · `later`=107 · `soon`=1 —
`approval_status` (`approved`=6,132 · فارغ=6,947) · `activation_status` ·
`vehicle_condition` · `condition_notes` · `mvpi_status` · `runs_status` · `key_status` ·
`insurance_company` · `inspection_days` · `inspection_report_media` · `preview_site`

**البيع والترسية**
`starting_price` · `bidamount` · `auto_bid` · `winner_user_id` · `winning_bid_id` ·
`final_price` · `awarded_at` · `winner_paid_at` · `payment_method` · `transaction_ref` ·
`receipt_image_path`

**التسويق (الشريك)**
`is_marketing` (tinyint) · `partner_decision` (`accepted`=170 · `rejected`=1 · فارغ=12,908) ·
`partner_decision_bid_id` · `partner_decided_at` · `partner_decided_by`

**حقول JSON**
`vehicle_data` · `settings_override` · `override_settings` — longtext.
⚠️ ثلاثة أعمدة بأسماء متشابهة؛ تحقّق أيها المقروء فعلاً قبل الاعتماد على واحد.

### `bids` — 118,298 صفاً · 14 عموداً

| الحقل | ملاحظة |
|---|---|
| `id` · `auction_id` · `vehicle_id` · `user_id` | `vehicle_id` مملوء في **كل** الصفوف (0 فارغة) |
| `amount` | **int** — لا كسور |
| `amount_with_vat` · `paid_amount` | decimal |
| `status` | enum: `active`=74,921 · `not_active`=41,663 · `deleted`=1,717 |
| `offer_status` | enum: `rejected`=61,546 · `pending`=50,633 · `accepted`=6,122 |
| `is_auto` · `sms_sent` · `rank` · `created_at` | |
| `auction_name` | **int** رغم الاسم — لا تعتمد عليه |

> **الفرق بين العمودين:** `status` = هل المزايدة قائمة؟ · `offer_status` = ماذا قرّرت
> الإدارة فيها؟ سيارة لا فائز لها = كل مزايداتها `offer_status='rejected'` و`status`
> يبقى `active`.

### `vehicle_images` — 48,211 صفاً
الصور blobs في القاعدة (السبب الأول لحجم القاعدة 14GB). البثّ عبر
`/vehicle-image/{id}` و`thumb.php`. `display_image` في `auction_vehicles` قد يكون
مساراً نصياً أو يشير لصف هنا — تعامل مع الحالتين.

### `details` — 8,801 صفاً
مواصفات قديمة مفتاحها `car_id = auction_vehicles.id`. تُقرأ كاحتياطي حين تخلو
`auction_vehicles`.

---

## 3) قواعد لا تُكسر

1. **`invoices_odoo.auction_id` فاسد** — يحمل `vehicle_id`. اربط دائماً:
   `invoices_odoo.vehicle_id → auction_vehicles.id → auction_vehicles.auction_id`.
2. **`lot_number` نصّي** — الترتيب النصي يعطي 1, 10, 101, 2. رتّب بـ
   `CAST(... AS UNSIGNED)` ثم النص، والفارغ آخراً.
3. **التوقيت** — قارن دائماً `a.end_time <= CONVERT_TZ(NOW(),'+00:00','+03:00')`.
4. **حالة المزاد لها ثمانية قيم** لا اثنتين. أي شرط «منتهٍ» يجب أن يقبل
   `ended` · `not_active` · `closed` · `finished` · `end` **أو** `end_time` ماضياً.
5. **الصفحة الرئيسية للعميل فيها أربعة مسارات رسم للكروت وثلاث قوائم حقول مسموحة** —
   أي حقل جديد يجب أن يُضاف إليها كلها وإلا يختفي بصمت.
6. **الإنهاء الجماعي (`end-all-auctions` / `end-all-bids`) يمسّ كل المزادات الحية.**
   يحتاج تأكيداً يذكر العدد قبل التنفيذ.
7. **`status` في `auction_vehicles` كان قد تعرّض لسحق قيَمي سابقاً** واستُعيد من نسخة
   قديمة — لا تُضيّق النوع إلى enum بلا هجرة محسوبة.

---

## 4) الأداء

- 11.6M طلب + 3.3M صورة. أي استعلام هنا يجب أن يكون مفهرساً ومحدود الصفحات.
- قائمة المزادات كانت O(n²) وأُصلحت بـ`COUNT` + `LIMIT` في SQL بدل التجميع في PHP.
- الصور من القاعدة هي العنق الحقيقي — نقلها إلى القرص/CDN يخفض الحجم من 14GB إلى ~2GB.

---

## 5) معايير القبول

- [ ] قائمة المزادات تفتح في أقل من ثانية على 56 مزاداً و13,079 مركبة
- [ ] `/auctions/{id}/vehicles` يرتّب بالموقف رقمياً
- [ ] رفع صورة → تظهر فوراً في التطبيق واللوحة
- [ ] نقل مركبة بين مزادين ينقل معها مزايداتها وحالتها
- [ ] الإنهاء الجماعي يعرض العدد ويطلب تأكيداً
- [ ] التصدير يخرج xlsx ويُعاد رفعه كما هو
- [ ] المركبات المرتبطة بفواتير أودو تظل مربوطة عبر `vehicle_id` لا `auction_id`
