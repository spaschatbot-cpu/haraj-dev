# P2-04 · الاستردادات

> `RefundController` · 1,069 سطر · `refunds_requests` = 3,287 صفاً.

## `refunds_requests` — 14 عموداً
`id` · `customer_id` (**= `userss.id_customer` لا `userss.id`**) · `amount` ·
`memo` · `payment_code` · `odoo_payment_id` · `payment_name` · `status` ·
`payment_state` · `iban_account` · `iban_image` · `requested_at` · `deducted_at` · `created_at`

## قواعد
1. **`status` لا يحتوي `cancelled`** — استخدم `rejected`. كتابة كلمة أودو حرفياً في
   الـenum يُبطل القيد كله تحت STRICT.
2. **الخصم مؤجَّل**: الوديعة تبقى حتى يرحّل أودو الاسترداد فعلاً.
3. **بوابة المزايدة تمنع** استعمال وديعة عليها طلب استرداد قائم — وإلا خرج المال مرتين.
4. **الإلغاء يتم في أودو** لا عندنا؛ يصلنا عبر ويبهوك.
5. **الاسترداد المدفوع بلا خصم في الدفتر** يدخل `insurance_refund_shortfalls`
   (25 صفاً) — واقرأ تحذير الخصم الزائد قبل تشغيل أي تسوية.

## معايير القبول
- [ ] لا استرداد يُصرف مرتين
- [ ] لا خصم يتجاوز ما يملكه العميل فعلاً
