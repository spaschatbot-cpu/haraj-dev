# P5-01 · الأدمنية والصلاحيات

> **84 طلباً** · `AdminUserController` + `CardsController` + `SectionController`.
> `management` = 37 صفاً · `cards` = 80 · `role_card_permissions` = 849.

## البنية
```
management (الموظف) → role_key → role_card_permissions → cards (البطاقة)
                    ↘ management_card_overrides (استثناء لشخص بعينه)
```
`AdminV2Sections.php` يبني القائمة الجانبية من البطاقات الممنوحة.

## `management` — 9 أعمدة
`id` · `username` · `role_key` · `password` · `is_active` · `phone` ·
`local_token_version` · `created_at` · `updated_at`

## مصائد
1. **`hasRole()` متساهلة مع المالك** — ترجع true لكل دور حين يكون المستدعي مالكاً.
   لا تستعملها لسؤال «هل هذا المستخدم دوره X» (أقفلت المالك خارج اللوحة كلها مرة).
2. **لا تضع قوائم أدوار ثابتة فوق بوابات ACL** — البطاقة هي المرجع.
3. **`phone` يُخزَّن محلياً هنا ودولياً في `userss`** — طابق بآخر 9 أرقام.
4. `management10` جدول قديم بلا `phone`؛ الحيّ هو `management`.

## معايير القبول
- [ ] منح بطاقة يظهر أثره في القائمة فوراً
- [ ] الموظف لا يبلغ صفحة لا يملك بطاقتها ولو كتب الرابط
- [ ] كل موظف مسجَّل بجوال يرى زرّ اللوحة في التطبيق
