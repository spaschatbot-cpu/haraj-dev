# TASK 01: نموذج الوديعة كوحدة 10,000 ر.س وحساب الرصيد كدالة (Insurance Deposit Unit Model)

## ١. الهدف ونطاق المهمة
إعادة بناء نظام التأمين ليقوم على مفهوم **الودائع كوحدات مغلقة** بقيمة 10,000 ر.س للوحدة الواحدة، وليس كرصيد عائم قابل للتجزئة، وضمان أن رصيد التأمين هو **دالة حسابية مشتقة** (Calculated Function) من واقع دفتر الحركات، وليس حقلاً مخزناً في جدول العملاء.

---

## ٢. الأهمية ومعدل الاستخدام
- **الأهمية:** 🔴 أقصى درجات الخطورة المالية (Critical Core Accounting).
- **الدافع الميداني:** في النظام القديم، تخزين الرصيد في عمود `total_insurance_paid` أدى إلى انحراف الرصيد المخزن عن الحقيقة لـ **548 عميلاً** في حادثة واحدة استلزمت تدقيقاً يدوياً لأشهر.

---

## ٣. القواعد الجوهرية للوديعة (The 4 Golden Rules)
1. **الوديعة وحدة وليست رصيداً:** قيمة الوديعة الثابتة هي **10,000 ر.س بالضبط**. لا يمكن تجزئتها (لا يوجد دفع 2,500 للمزايدة). العميل يملك (0، 1، 2، ...) ودائع.
2. **الرصيد دالة وليس حقلاً (Balance is a Function):**
   ```sql
   Total_Balance = SUM(amount) WHERE status NOT IN ('refunded', 'confiscated')
   Available_Balance = SUM(amount) WHERE status = 'free'
   Held_Balance = SUM(amount) WHERE status = 'held'
   Locked_Balance = SUM(amount) WHERE status = 'locked'
   ```
   > ⛔ **قاعدة ممنوعة قطيعاً:** لا تقم بإضافة عمود باسم `insurance_balance` في جدول `userss`.
3. **حالات الوديعة الخمس (Deposit Lifecycle States):**
   - `free`: حرة ومتاحة للاستخدام في أي مزاد جديد.
   - `held`: محجوزة لمزايدة جارية في مزاد نشط.
   - `locked`: مرهونة لضمان فاتورة سيارة فاز بها العميل ولم يسددها بعد.
   - `refunded`: تم صرفها وإرجاعها لحساب العميل البنكي (حالة نهائية).
   - `confiscated`: تمت مصادرتها لصالح الشركة بسبب تخلّف العميل عن سداد قيمة السيارة (حالة نهائية).
4. **وديعة واحدة لكل مزاد:** وديعة واحدة بحالة `held` تكفي للمزايدة على جميع سيارات المزاد الواحد.

---

## ٤. هيكل جدول الودائع `insurance_deposits` (Ledger Model)

```sql
CREATE TABLE `insurance_deposits` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `amount` decimal(12,2) NOT NULL DEFAULT '10000.00',
  `status` enum('free', 'held', 'locked', 'refunded', 'confiscated') NOT NULL DEFAULT 'free',
  `linked_auction_id` int(11) NULL COMMENT 'المزاد المحجوزة له الوديعة أثناء النشاط',
  `linked_invoice_id` varchar(100) NULL COMMENT 'رقم الفاتورة المرهونة لها الوديعة عند الفوز',
  `payment_reference` varchar(191) NOT NULL COMMENT 'مرجع الدفعة البنكية أو بوابة الدفع',
  `held_at` datetime NULL,
  `locked_at` datetime NULL,
  `refunded_at` datetime NULL,
  `confiscated_at` datetime NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_user_status` (`user_id`, `status`),
  KEY `idx_linked_auction` (`linked_auction_id`),
  KEY `idx_linked_invoice` (`linked_invoice_id`),
  UNIQUE KEY `uk_payment_ref` (`payment_reference`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## ٥. قواعد العرض للعميل في الواجهة (Display States)
تُعرض حالة التأمين للعميل بناءً على دالة الحالة اللحظية:
1. **نشط ومتاح (Active):** يملك وديعة بحالة `free`. يُعرض له باللون الأخضر: `التأمين نشط ومتاح للمزايدة ✓`.
2. **محجوز لمستحقات (Locked Dues):** يملك ودائع ولكنها جميعاً بحالة `locked` أو `held`. يُعرض له باللون البرتقالي: `التأمين محجوز لمستحقات سابقة ⚠️ (سدد الفواتير لتحريره)`.
3. **غير مكتمل (No Deposits):** لا يملك أي ودائع نشطة. يُعرض له باللون الرمادي: `التأمين غير مدفوع (اشحن التأمين لتتمكن من المزايدة)`.
4. **تعذر التحقق (Unknown / Error):** في حال حدوث خطأ في الاتصال بالدفتر، يُعرض: `⏳ تعذر التحقق من التأمين، يرجى المحاولة لاحقاً`. **ممنوع قطيعاً الادعاء بتوفر التأمين عند فشل الفحص!**

---

## ٦. معايير القبول والاختبار
- [ ] الرصيد في كافة شاشات الأدمن والعميل يُحسب من واقع مجموع صفوف `insurance_deposits`.
- [ ] استحالة إنشاء وديعة بمبلغ غير 10,000 ريال دون موافقة إدارية خاصة موثقة.
- [ ] الودائع بالحالات `free`, `held`, `locked` تُحتسب جميعها ضمن القيمة الإجمالية لأموال العميل المودعة.
- [ ] الودائع بالحالات `refunded` و `confiscated` تخرج تماماً من أي حساب لرصيد العميل.
