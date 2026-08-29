# نتائج T101 — أول تشغيل للنموذج الأولي

التاريخ: 2026-08-29 · PostgreSQL 17.11 · Django 5.2.17 · Python 3.13

هذا ما فعله الكود فعلاً في أول مرة يُشغَّل فيها، لا ما كان متوقَّعاً منه.

## البيئة

النموذج لم يكن قد شُغِّل ولا مرة لأن PostgreSQL لم يكن مثبَّتاً. التثبيت عبر
`winget` فشل بـ403 من `get.enterprisedb.com` (وخرج بكود 0 رغم الفشل)، فاستُعملت
حزمة الملفات التنفيذية المحمولة:

```
D:/pgsql17/            الملفات التنفيذية
D:/pgsql17/data/       مجلد البيانات
المنفذ 5432 · قاعدة haraj2 · مستخدم haraj · مصادقة trust على الحلقة المحلية
```

> **ملاحظة للفيز 001:** هذا التثبيت اليدوي مؤقت. التاسك T003 يجب أن يجعل تجهيز
> القاعدة خطوة موصوفة قابلة لإعادة التطبيق، لا سلسلة أوامر في تاريخ محادثة.

## النتيجة

```
17 اختباراً · 16 ناجحاً · 1 فاشل · 97 ثانية
الهجرات: مرّت كلها على PostgreSQL بلا تعديل
```

## الفشل الوحيد

### F-001 — حارس «لا تعكس المعاملة مرتين» يرفع الاستثناء الخطأ

**الاختبار:** `TestReversal::test_a_transaction_cannot_be_reversed_twice`
**الملف:** `backend/apps/money/services.py:184`

```python
if hasattr(txn, "reversed_by"):
    raise MoneyError(f"txn {txn.pk} was already reversed by {txn.reversed_by_id}")
#                                                            ^^^^^^^^^^^^^^^^^^
# AttributeError: 'Transaction' object has no attribute 'reversed_by_id'
```

**السبب:** `reversed_by` هو الطرف العكسي لعلاقة واحد-لواحد، وDjango لا يولّد له
`_id` — ذلك يوجد على الطرف المالك (`reverses_id`) فقط. الشرط نفسه صحيح ويكتشف
الحالة؛ رسالة الخطأ هي التي تنهار.

**الأثر الحقيقي:** الحارس **يعمل** — المعاملة لا تُعكس مرتين. لكنه يخرج بـ
`AttributeError` بدل `MoneyError`، فيصل للمستخدم كخطأ 500 غامض بدل رفض مفهوم،
ولا يلتقطه أي كود يمسك `MoneyError`.

**الإصلاح المقترح:** `txn.reversed_by.pk`. يُنفَّذ في التاسك T108.

**الدرس:** المسار الذي لم يُختبر لا يعمل، ولو بدا صحيحاً بالقراءة. هذا السطر
قُرئ عدة مرات قبل التشغيل ولم ينتبه إليه أحد.

## ما ثبت أنه يعمل

| السلوك | الاختبار |
|---|---|
| الإيداع يوازن، والدلو الخارجي يصير سالباً | `test_a_deposit_moves_the_money_and_balances` |
| الدفعة نفسها مرتين تُقيَّد مرة | `test_the_same_payment_heard_twice_credits_once` |
| المعاملة غير المتوازنة تُرفض ولا تترك أثراً | `test_an_unbalanced_movement_is_refused` |
| الخصم الزائد يُرفض عبر الخدمة | `test_a_customer_bucket_cannot_go_negative` |
| **قاعدة البيانات نفسها ترفض الرصيد السالب** | `test_the_database_refuses_a_negative_balance_even_without_the_service` |
| العكس يُرجع الفلوس ويُبقي الأصل بقيوده | `test_a_reversal_undoes_the_money_and_keeps_the_history` |
| الحجز ينقل من المتاح للمحجوز | `test_bidding_moves_insurance_from_free_to_held` |
| عشرون مزايدة في مزاد = حجز واحد | `test_bidding_twice_in_one_auction_holds_once` |
| المحجوز لا يُسترد | `test_held_money_cannot_be_refunded_away` |
| **المدين لا يسترد — بلا بوابة مكتوبة** | `test_a_debtors_deposit_is_locked_and_cannot_be_refunded` |
| الفلوس بلا صاحب تُحفظ في المعلّق | `test_money_we_cannot_place_is_kept_not_dropped` |
| `verify_ledger` نظيف على دفتر سليم | `test_a_clean_ledger_reports_nothing` |
| `verify_ledger` يصطاد رصيداً متلاعباً به | `test_a_tampered_balance_is_caught` |
| `verify_ledger` يصطاد محجوزاً بلا حجز | `test_held_money_without_a_hold_is_caught` |

القيد الحاسم — `CHECK` منع الرصيد السالب — **اختُبر بتخطّي طبقة الخدمة والكتابة
مباشرةً في الجدول**، ورفضته قاعدة البيانات. هذا هو الشيء الذي كان سيمنع خصم
الـ20,000 المزدوج في v1.

## ما لم يُختبر بعد

لا يوجد في النموذج أي اختبار تزامن بخيوط حقيقية. كل ما سبق تسلسلي. التاسكات
T105 و T106 و T110 هي التي تغطي هذا، وهي المكان الذي تظهر فيه أخطاء القفل
عادةً — فلا يجوز اعتبار المحرّك مُثبتاً قبلها.
