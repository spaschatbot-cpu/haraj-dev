# P1-05 · الفواتير والمدفوعات (أودو)

> `invoices_odoo` = 12,434 صفاً · `payments_odoo` = 18,688 · `odoo_inbox` = 5,422.
> `InvoiceController` + `PaymentController` + `OdooWebhookApiController`.
> **اقرأ `docs/claude-memory/odoo-integration-master-map.md` كاملاً قبل أي لمسة.**

## `invoices_odoo` — 21 عموداً

`invoice_id` (**int** — لا الاسم النصي) · `odoo_record_id` (= `account.move.id`) ·
`invoice_number` (`INV/2026/…`) · `customer_id` (عميل أودو) · `id_user` ·
`vehicle_id` · `auction_id` (**فاسد — يحمل vehicle_id**) · `amount` · `fees_amount` ·
`total` · `amount_residual` · `PaymentStatus` (**المُصان**) · `status` (**مجمَّد على draft**) ·
`source` · `odoo_payment_ref` · `created_at` · وحقول السيارة المكرَّرة

## كيف يصل المال

```
أودو ──webhook──► odoo_inbox (يُستقبَل أولاً، يُقرَّر لاحقاً) ──► المرآة
```

- أودو يرسل الدفعة **ثلاث مرات في الثانية نفسها**: `created` → `updated` → `posted`.
- **رابط الفاتورة يركب `updated` وحدها** — و`posted` يحمل `invoice_id: null`.
  إسقاط `updated` جعل دفعة سيارة تبدو اشتراك تأمين.
- الحالات المستقرّة: `paid` · `done` · `reconciled` · `cancelled` · `reversed`.

## مصائد

1. **أودو لا يعلن إلغاء الدفعة** — استطلعه.
2. **المذكرة هي مرجع الدفعة** — تكرارها يرفضه أودو (عطّل 223 محاولة سداد جزئي).
3. **مسودّة فارغة = دَين وهمي**: فتح نموذج فاتورة فارغ في أودو يرسل `created`
   بـ`invoice_id:"/"` وأصفار.
4. **الويبهوك يوثّق بالسرّ وحده** — بلا قيد عنوان ولا تحقق من وجود الفاتورة.
   نسخة من قاعدة أودو تحمل السرّ نفسه كتبت دَينين وهميين على عميل حقيقي.
5. **`odoo_record_id` يطابق `account.move.id`** — تحقّق بالاسم والعميل والمبلغ معاً.

## معايير القبول

- [ ] كل رسالة واردة تُسجَّل في `odoo_inbox` قبل أي قرار
- [ ] لا فاتورتان لسيارة واحدة
- [ ] المرآة تطابق أودو في العميل والمبلغ
- [ ] الفاتورة الملغاة لا تُحسب ديناً
