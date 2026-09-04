# TASK 04: سجل تدقيق المزايدات وحماية النزاهة (Bid Audit Trail & Integrity)

## ١. الهدف ونطاق المهمة
بناء سجل تدقيق مالي غير قابل للحذف أو التعديل (Append-Only Audit Log) يوثق كل عملية إنشاء أو تعديل أو إلغاء لمزايدة، بما يضمن الشفافية الكاملة، ويوفر الأدلة القانونية والفنية عند حدوث نزاعات مع العملاء أو مراجعة نتائج المزادات.

---

## ٢. الأهمية ومعدل الاستخدام
- **الأهمية:** 🔴 حرجة جداً (Legal & Audit Trail) — كان هذا السجل هو الدليل القاطع الوحيد لحل شكاوى العملاء الرسمية واستعادة الحقوق المالية.
- **معدل التنفيذ:** يُسجل مع كل عملية كتابة في جدول `bids`.

---

## ٣. هيكل جدول التدقيق `bid_edit_audit`

```sql
CREATE TABLE `bid_edit_audit` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `bid_id` int(10) unsigned NOT NULL,
  `user_id` int(10) unsigned NOT NULL,
  `auction_id` int(10) unsigned NOT NULL,
  `vehicle_id` int(10) unsigned NOT NULL,
  `old_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `new_amount` decimal(15,2) NOT NULL DEFAULT '0.00',
  `source` enum('client_web', 'client_app', 'admin_override', 'cron_system') NOT NULL DEFAULT 'client_web',
  `actor_id` int(10) unsigned NULL COMMENT 'معرف المشرف إذا كان التعديل إدارياً',
  `actor_name` varchar(120) NULL COMMENT 'اسم المشرف أو العميل',
  `ip_address` varchar(45) NOT NULL,
  `user_agent` text NULL,
  `action_type` enum('create', 'increase', 'downgrade', 'cancel') NOT NULL,
  `edited_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_bid_id` (`bid_id`),
  KEY `idx_user_vehicle` (`user_id`, `vehicle_id`),
  KEY `idx_auction_id` (`auction_id`),
  KEY `idx_edited_at` (`edited_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## ٤. القواعد الصارمة لسجل التدقيق
1. **قاعدة الـ Append-Only:** لا توجد أوامر `UPDATE` أو `DELETE` نهائياً على هذا الجدول. أي خطأ في الإدخال يتم تصحيحه بقيد جديد لاحق.
2. **المعاملة الذرية (Atomic Transaction):** تسجيل حركة التدقيق يتم **داخل نفس المعاملة** (`DB Transaction`) الخاصة بحفظ المزايدة. إذا فشل تسجيل التدقيق، تفشل عملية المزايدة بأكملها ولا يتم حفظ السعر الجديد.
3. **توثيق التعديل الإداري:** إذا قام المالك أو المشرف بتعديل مزايدة نيابة عن العميل أو بطلب رسمي، يتم إدراج `source = 'admin_override'` مع تخزين `actor_id` و `actor_name` الإداري لتوضيح من أجرى التعديل وسببه.

---

## ٥. معايير القبول والاختبار
- [ ] كل حركة مزايدة يترتب عليها إنشاء صف جديد في `bid_edit_audit`.
- [ ] السعر القديم والجديد دقيقان تماماً مع توثيق نوع الحركة (`increase` أو `downgrade`).
- [ ] استحالة تعديل المزايدة دون إدراج سجل التدقيق المقابل لها في المعاملة.
