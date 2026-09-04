# P4-03 · صحة المحفظة

> **14 طلباً** وهي التي تكشف اختفاء المال. `/admin_v2/wallet-health` ·
> `wallet_health_findings` = 182 صفاً · فحص يومي 05:00 UTC.

## الفحوص التسعة
`overdebited` · `unclassifiedVoids` · `orphanMoney` · `pendingInbox` · `shadowDrift` ·
`liveWithVoidReason` · `biddingBlocked` · `droppedWebhooks` · `odooBalanceMismatch`

## قواعد
1. **الاتساق الداخلي ليس حقيقة** — الدفتر قد يوافق نفسه ويخالف أودو.
   لذلك `odooBalanceMismatch` موجود، **وهو معطَّل** حتى تنشر أودو
   `POST /get/customer/insurance`.
2. **لا تبالغ في أي مبلغ.** عمود المبلغ = المال الناقص فعلاً، لا أي رقم آخر.
3. النتائج تُفتح وتُغلق **من تلقائها** — لا إغلاق يدوي يخفي مشكلة قائمة.
4. الفحص مبني على المجموعات (`customer_links`) لا على الحسابات المفردة.

## معايير القبول
- [ ] الفحص يمرّ على 14,708 مجموعة في ثوانٍ
- [ ] كل نتيجة تشير إلى العميل والمبلغ والسبب
- [ ] لا نتيجة تبقى مفتوحة بعد زوال سببها
