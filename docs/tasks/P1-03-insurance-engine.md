# P1-03 · محرك التأمينات

> ليست صفحة بل **المحرك تحت كل الصفحات**: `src/Support/InsuranceSettlement.php`.
> الوديعة = 10,000 ر.س · `insurance_deposits` = 2,095 صفاً.
> أخطر كود في النظام: خطأ هنا يعني مالاً يختفي أو عميلاً يزايد بلا تأمين.

## دورة الوديعة

```
free ──حجز مزايدة──► held ──مستحقات──► locked ──سداد──► free
  │                                        │
  └────────► refunded (استرداد)            └────► confiscated (مصادرة)
```

## `insurance_deposits` — 14 عموداً

`id` · `user_id` · `amount` · `status` · `void_reason` · `odoo_payment_id` ·
`linked_auction_id` · `linked_invoice_id` · `created_at` · `held_at` · `locked_at` ·
`refunded_at` · `confiscated_at` · `notes`

- **`status`** هو الحقيقة. و`userss.total_insurance_paid` عمود **مشتق** منه —
  له كاتب واحد فقط، ولا يُعدَّل بـ`± delta` أبداً (delta أعمى أخفى 90,000 عن 7 عملاء).
- **`void_reason`** يجيب «لماذا خرجت هذه الوديعة؟» — `refund` · `odoo_payout` ·
  `reversal` · `owner_correction` · `auto_release` · `confiscation`.
  ما لا يُثبَت لا يُخمَّن: الغموض يمنع الخصم بدل أن يفترضه.
- **`linked_auction_id` + `linked_invoice_id`** معاً على صفٍّ واحد = استثناء يدوي
  يجعل وديعة واحدة تؤمّن دَينين، بلا تعديل كود.

## الدوال المحورية

| الدالة | تفعل |
|---|---|
| `resolveDuesNeedingLock()` | **المصدر الوحيد** لسؤال «أي دَين يحتاج قفلاً؟» — يقرؤه المحرك وشاشة العرض معاً |
| `lockUnpaidWinners()` | يقفل وديعة لكل دَين غير مؤمَّن — يُنادى **داخل مسار المزايدة** |
| `releaseAllPaid()` | يحرّر الوديعة حين تُسدَّد كل فواتير مزادها |
| `releaseRedundantLocks()` | يفكّ قفلاً مكرراً على نفس الدَّين — لا يفكّ لمجرد اختفاء دَين |

## مصائد

1. **`invoices_odoo.status` مجمَّد** — يُكتب `draft` عند الإدراج ولا يُحدَّث أبداً.
   **لا تبنِ شرطاً عليه.** `PaymentStatus` هو المُصان.
2. **`id_customer` ليس فريداً** — عميل أودو واحد قد يقابل 2–3 حسابات. أي مقارنة بين
   مال مفهرَس بعميل أودو وودائع مفهرسة بالمستخدم يجب أن تمرّ بـ`customer_links`.
3. **`refunds_requests.customer_id` = `userss.id_customer` وليس `userss.id`.**
4. **اختبر منطق المال تحت `sql_mode` الإنتاج** لا تحت `sql_mode=''`.
5. **غياب الدفعة من أودو ليس دليلاً على أن المال لم يتحرك** — قد يكون timeout.

## معايير القبول

- [ ] `SUM(insurance_deposits)` لكل عميل = `total_insurance_paid`
- [ ] مدين لا يستطيع المزايدة إلا بتأمين جديد
- [ ] لا وديعتان مقفولتان على دَين واحد
- [ ] كل وديعة خارجة تحمل `void_reason`
