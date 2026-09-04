# P1-04 · المستخدمون

> **1,620 طلب** · `UserController` · 1,189 سطر · 12 مساراً · 13 جدولاً.
> `userss` = 43,884 صفاً · 51 عموداً.

## المجموعات في `userss`

**الهوية** — `id` · `phone` (**UNIQUE**) · `arabic_name` (= الشركة) ·
`english_name` (= المندوب) · `identity_type` · `identity_number` · `birth_date` ·
`gender` · `type_of_account` · `cr_number` · `vat_number`

**الحالة** — `block_status` · `blocked_until` · `mobile_verified` ·
`verification_code` · `code_expiry` · `failed_attempts` · `last_attempt_time`

**المال** — `total_insurance_paid` (**مشتق**) · `purchases_balance` · `wallet` ·
`id_customer` (رقم عميل أودو — **ليس فريداً**) · `iban_account`

**العنوان الوطني (ZATCA)** — `country` · `city` · `district` · `street` ·
`building_no` · `additional_no` · `zip` · `plot_number` · `address`

**المرفقات** — `identity_image` · `commerce_image` · `company_image` ·
`tax_image` · `national_address_image` · `passport_image` · `profile_image`

**التقنية** — `player_id` · `fcm_token` · `session_token` · `remember_token_hash` ·
`remember_token_expires_at` · `id_package` · `active_auctions_count`

## قواعد

1. **اعرض `arabic_name`** — هو اسم الشركة، والشركة هي الطرف المتعاقد.
2. **`phone` فريد** — صف بجوال `''` يحجب إنشاء أي صف جديد بجوال فارغ.
3. **رقم الهوية يُقفل بعد ضبطه** — لكن القفل يسري على القيم **الصحيحة** فقط.
4. **الحفظ تحت STRICT** — enum أو INT فارغ يُبطل الـUPDATE كله بصمت.
5. **مطابقة الموظفين بالجوال بآخر 9 أرقام** — `management` يخزّن `05…` و`userss`
   يخزّن `+9665…`؛ المقارنة النصية لا تتطابق أبداً.

## معايير القبول

- [ ] البحث بالاسم/الجوال/الهوية أقل من ثانية على 43,884 صفاً
- [ ] الحفظ الجزئي لا يُبطل بقية الحقول
- [ ] تغيير الجوال يمرّ بتحقق
- [ ] التصدير المتدفّق لا يستهلك أكثر من بضعة ميجابايت
