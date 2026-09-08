# منطق المحفظة في v1 — كما هو مكتوبٌ في الكود، لا كما يُقال عنه

قراءةٌ من `D:\haraj 1\applicationtest` (٨ سبتمبر ٢٠٢٦). المصادر:
`src/Support/InsuranceSettlement.php` · `InsuranceCalculator.php` ·
`SubscriptionStatus.php` · `CustomerLedger.php` · `WalletHealth.php` ·
`Controllers/Client/{WalletApiController,WalletTopupApiController,OdooWebhookApiController,BidApiController}.php` ·
`Controllers/Admin/{FinanceController,RefundController,AnalyticsController,WalletHealthController,BidEligibilityController}.php` ·
`wallet_topup_card_done.php` · `moyasar_webhook.php` · `menu/wallet.php` · `docs/REBUILD-LOGIC.md` §٧.

الغرض: مرجعٌ واحد لكل من يبني مقابل هذه الشاشات في v2، بدل أن يقرأ كلٌّ ١٥ ألف سطر.

---

## ١ — أين تجلس الفلوس

| الجدول/العمود | دوره الفعلي |
|---|---|
| `insurance_deposits` | **الدفتر.** صفٌّ = وديعة ١٠٬٠٠٠. `status` ∈ free · held · locked · refunded · confiscated. يحمل `linked_auction_id` · `linked_invoice_id` · `odoo_payment_id` · `void_reason` · طوابع `held_at/locked_at/refunded_at/confiscated_at`. |
| `userss.total_insurance_paid` | **ظلٌّ مُشتق** = `SUM(amount) WHERE status NOT IN (refunded, confiscated)`. يُعاد حسابه بـ`recomputeShadow` بعد كل تغيير. `currentBalance()` يقرأ الدفتر أولاً ولا يقع على العمود إلا لعميلٍ بلا صفوف. |
| `userss.purchases_balance` · `userss.wallet` | **متروكان** منذ pivot ٢٠٢٦‑٠٥‑١٩: `IncomingPaymentDistributor::distribute` بلا مستدعٍ، و`transferExcessToPurchases` تعود `0.0` فوراً. |
| `wallet_transactions` | **أثرٌ ورقي** لا مصدر رصيد: `type` (bank_transfer · cash_receipt · card_topup · manual_credit · transfer_to/from_purchases…) · `category` (insurance / purchase_balance) · `odoo_reference` · `transfer_request_id` · `note`. |
| `transfer_requests` (`request_type='wallet_topup'`) | طلبُ شحنٍ بنكي مع إيصال. `status` ∈ pending · processing · completed · rejected · cancelled. `odoo_payment_id` يُختم بعد الدفع لأودو. |
| `refunds_requests` | مفتاحُه **شريك أودو** (`customer_id`) لا المستخدم. `status` enum (pending/approved/rejected — ويُكتب فيه completed/deducted أيضاً) · `payment_state` مرآة أودو (draft/posted/cancelled/pending_odoo/odoo_failed) · `deducted_at` = رمز التفرّد للخصم · `iban_account` · `iban_image`. |
| `customer_links` | إغلاق (user_id ↔ odoo_customer_id). `CustomerLedger` يقيس كلَّ شيء على المجموعة لا على حسابٍ واحد. |
| `payments_test` | مرآةٌ تاريخية للاشتراكات (Moyasar/Odoo) — احتياط `subscriptionAlreadyConfirmed`. |
| `insurance_payments` | جدول قديم (تأمين لكل مزاد) — صفٌّ تجريبي واحد. يُعرض في السجل فقط. |
| `wallet_logs` | **لا يوجد** في القاعدة. شاشة «سجل المحفظة» تقع على `refunds_requests` وتعرضها على أنها سجل محفظة. |

**القاعدة الحاكمة:** الوديعة وحدةٌ ثابتة ١٠٬٠٠٠. لا تجزئة في الدخول ولا في الخروج
(الاسترداد ١٠٬٠٠٠ بالضبط، الشحن اليدوي والخصم مضاعفات ١٠٬٠٠٠). الاستثناء الوحيد:
الويبهوك يسجّل مبلغاً غير ١٠k كصفٍّ مع تحذير في `notes` حتى يبقى `SUM` صادقاً.

---

## ٢ — الدخول (الشحن)

### ٢‑١ تحويل بنكي (من التطبيق)
1. `WalletTopupApiController::submit`: المبلغ = ١٠٬٠٠٠ بالضبط · صورة إيصال إلزامية
   (jpg/png/webp/pdf) · **طلبٌ معلّق واحد في وقتٍ واحد** (409 `PENDING_SUBSCRIPTION_EXISTS`).
2. يُدرَج `transfer_requests` pending، ثم يُدفع لأودو كمسودة
   `createAppSubscriptionPayment` ويُختم `odoo_payment_id` (فشلُ أودو لا يُسقط الطلب).
3. **لا رصيد يتحرّك هنا.** الاعتماد في أودو، ثم ويبهوك.

### ٢‑٢ ويبهوك أودو `wallet-topup` / `cash-receipt`
- يُسجَّل في `odoo_inbox` أولاً («استقبِل ثم قرِّر»).
- `event` غير `posted` → لا اعتماد (`created/updated` تحمل payment_id ناقصاً — كان سبب
  الاعتماد المزدوج). استثناء: `updated` يحمل `invoice_id` يُطبَّق على الفاتورة **ويُلغي**
  أي وديعة فُتحت لنفس الدفعة (حادثة محمود العليوي).
- **دفعةٌ تحمل فاتورة لا تدخل المحفظة أبداً** (`tryInvoicePayment`).
- كاش بغير ١٠٬٠٠٠ وبلا `subscription_id` → مرفوض ومسجَّل، لا يُعتمد.
- طبقات التفرّد قبل الاعتماد: `reference` · `transfer_request_id` · `odoo_payment_id`
  عبر المسارين · صدى البطاقة (`moyasar_<id>` placeholder) · `subscriptionAlreadyConfirmed` ·
  `isEchoOfLocalCredit`.
- الاعتماد = `wallet_transactions` + صفّ `insurance_deposits` free + `recomputeShadow`
  + `transfer_requests.status='completed'` — في معاملةٍ واحدة تحت `GET_LOCK`.

### ٢‑٣ بطاقة / Apple Pay (Moyasar)
- `wallet_topup_card_done.php` (رجوع المتصفح) و`moyasar_webhook.php` (سيرفر‑سيرفر)
  كلاهما يعتمد، تحت قفل `webhook_payment:<id>` وتفرّد `odoo_reference='moyasar_<id>'`.
- تُنشأ وديعة free بـ`odoo_payment_id` مؤقّت، ثم تُدفع لأودو، وحين يُصدّي أودو تُختم
  بالرقم الحقيقي بدل اعتمادٍ ثانٍ (`reconcileCardPlaceholderDeposit`).

### ٢‑٤ شحن يدوي (أدمن — `finance/wallet-credit`)
- الحقول: عميل (قائمة منسدلة لـ«السجلات المكتملة» فقط) · مبلغ (مضاعفات ١٠k) · سبب من
  خمسة ثابتة: كاش · تحويل بنكي · دفعة أودو يدوية · تعديل إداري · استرداد.
- يكتب `wallet_transactions` (`manual_credit`, `odoo_reference='manual_credit_<uid>_<ts>'`)
  + `adminCreditDeposits(units)`. **بلا مرجعٍ خارجي ولا تفرّد**: الضغط مرّتين يعتمد مرّتين.
- تحته جدولان: آخر ٢٠ شحنة يدوية (#، العميل، المبلغ، الملاحظة، التاريخ).

---

## ٣ — المزايدة (`BidApiController::reserveInsuranceForBid`) — داخل معاملة البيع

1. **`lockUnpaidWinners(user)` أولاً**: كل مزادٍ منتهٍ عليه فاتورة غير مسدَّدة يُقفل عليه
   وديعة (free أولاً، وإلا **تُسرق held من مزادٍ آخر** — قاعدة المالك D1‑ب). قبلها وبعدها
   `releaseRedundantLocks` (وديعتان على دَينٍ واحد → تُحرَّر الأضعف).
2. وديعة `held` لهذا المزاد نفسه؟ → أعد استعمالها (وديعة واحدة لكل مزاد مهما كثرت المزايدات).
3. وإلا: أقدم وديعة `free` بمبلغ **≥ ١٠٬٠٠٠** (`FOR UPDATE`) → `held` + `linked_auction_id`.
4. وإلا: رفض «يجب دفع تأمين كامل (10,000 ريال)».

- طلبُ استردادٍ معلّق يحجب المزايدة إن كان عدد الطلبات ≥ عدد الـfree.
- حذفُ المزايدة: إن كانت آخر مزايدةٍ نشطة في المزاد → `held → free`.
- المطلوب للمزايدة ثابت ١٠٬٠٠٠ (قاعدة `10k × (1+N)` معطَّلة — `resolveRequiredInsurance`).
- استثناءٌ مكتوبٌ في الكود: `DUES_LOCK_EXEMPT_USERS = [8982]` لا تُقفل ودائعه على ديونه.

---

## ٤ — التسوية: متى تتحرّك الوديعة

| الحدث | الدالة | الحركة |
|---|---|---|
| قبول عرض (تعيين فائز) | `lockHeldForWinner` | `held → locked` + `linked_invoice_id`. لا held؟ يقفل free. |
| رفض خاسر لحظياً | `freeIfFullyLost` | كل مزايداته مرفوضة **ولم يفز بشيء** → `held → free` فوراً. |
| «إرسال الفواتير للكل» / إنهاء يدوي | `settleAuction(…, releaseNonWinners=true)` | الفائز يُقفل؛ الخاسر يُحرَّر **فقط** إن كانت كل مزايداته مرفوضة. |
| كرون الإنهاء | `settleAllEnded → settleAuction(…, false)` | يقفل الفائزين، **لا يحرّر أحداً أبداً**. |
| تراجع عن فائز | `freeUserAuctionDeposit` | `held/locked → free` إن لم يبقَ له فوزٌ ولا مزايدة حيّة. |
| سداد فاتورة | `releaseOnInvoicePaid` / `releaseAllPaid` | `locked → free` **فقط حين لا تبقى فاتورة غير مسدَّدة في نفس المزاد** (وديعة واحدة تغطّي المزاد كله). |
| فتح صفحة المحفظة | self‑heal | `settleAllEnded()` + `releaseAllPaid(user)`. |

المسبِّبات الموثّقة في الكود: تحريرُ «غير الفائزين» عند التسوية حرّر ٢٣٠+ وديعة لفائزين
لم يُقبل عرضهم بعد (المزادان 1004/1006) — فصار الخاسر = «كل مزايداته مرفوضة» لا «لم يفز».

---

## ٥ — الاسترداد

### ٥‑١ من العميل (`WalletApiController::refund`)
شروطٌ بترتيبها: ١٠٬٠٠٠ بالضبط · IBAN سعودي صالح + **صورة IBAN إلزامية** · جلسة
مصادَقة · جوّال موثَّق · **لا مزايدة نشطة في مزادٍ حيّ** (حيّ = status active **و**
`end_time` في المستقبل) · رصيد ≥ ١٠k · ثم `settleAllEnded` + `releaseAllPaid` +
`autoLockFreeDepositsToUnsecuredDues` + `lockUnpaidWinners` · **مجموع** الـfree ≥ ١٠k
(وإلا `DEPOSIT_HELD` / `DEPOSIT_LOCKED` / `NO_FREE_DEPOSIT`) · طلبٌ معلّق واحد فقط.

ثم: يُدرَج الصفّ محلياً `status=pending, payment_state=draft` **قبل** نداء أودو
(الويبهوك يصل قبل رجوع النداء)، ثم `createRefund` في أودو، ثم تُختم الأرقام.
**لا خصم عند الطلب** (قرار ٢٠٢٦‑٠٦‑٠٥): الرصيد يبقى حتى يرحّل أودو.

### ٥‑٢ ويبهوك `refund-updated`
- `posted` → `(approved, posted)` · `cancelled` → `(rejected, cancelled)` · غيره → `(pending, draft)`.
- لا صفّ محلي (استردادٌ أُنشئ في أودو مباشرة) → يُدرَج **ويُخصم** إن كان posted.
- الخصم `debitWalletForRefund`: تفرّد بالمبلغ على وسم `refund_request #<id>` (REGEXP
  محدود الحدود — `#5` لا يطابق `#50`)، ثم `refundDebitByAmount`:
  **free → held → locked** أقدم أولاً؛ وديعة أكبر من المتبقّي تُقصّ جزئياً؛
  **locked على فاتورة ما زالت غير مسدَّدة لا تُسحب** (عجزٌ → `RefundShortfalls` يدوي)؛
  ما سُحب من held يُلغي مزايدات العميل النشطة في ذلك المزاد.
- `deducted_at` يُقرأ تحت `FOR UPDATE` فلا يخصم ويبهوكان متزامنان مرّتين.
- أودو **يفوز دائماً**: posted على صفٍّ مرفوض محلياً يُخصم رغم ذلك.

### ٥‑٣ من الأدمن (`/refunds`)
- **فحص عميل** (بالجوال/الهوية/الاسم): الرصيد · المزايدات النشطة · الفواتير غير المسدَّدة
  (عدد ومبلغ) · عدد الطلبات · الطلبات المعلّقة.
- **اعتماد**: `markOldestFreeAs(units, refunded)` بما لم يُخصم بعد، إلغاء المزايدات إن
  لم يبقَ free/held، ثم `createRefund` في أودو (`payment_state=posted` أو `odoo_failed`).
- **خصم مباشر (من صفحة الاستردادات)**: مضاعفات ١٠k، نداء أودو `/create/refunds`
  **أولاً**، ثم `markOldestFreeAs(refunded)` + صفّ `status='deducted'`.
- تعديل/حذف صفّ الطلب (مبلغ، بيان، IBAN).
- الأعمدة: # · الاسم · الجوال · المبلغ · رقم الدفع · البيان · الآيبان · الحالة · حالة
  Odoo · رقم Odoo · صورة الآيبان · التاريخ · إجراء.

### ٥‑٤ خصم مباشر من التأمين (`finance/direct-deduct`)
بحث بالاسم/الجوال → صفّ (الاسم · الجوال · الرصيد المتاح · «خصم لحظي») → نافذة: نوع
العملية + ملاحظة + مبلغ. التنفيذ: `markOldestFreeAs(units, 'confiscated')`. **بلا أودو،
بلا سبب إلزامي، بلا سقفٍ إلا الرصيد.**

### ٥‑٥ استرداد يدوي (`finance/manual-refund`)
نداء أودو `/create/refunds` + صفّ `refunds_requests` draft + SMS للعميل. **لا يمسّ الدفتر**؛
الخصم يأتي لاحقاً من ويبهوك `refund-updated`.

---

## ٦ — الرقابة (قراءة فقط)

- **صحّة المحفظة** (`cron_wallet_health` يومياً → `wallet_health_findings`): ٩ فحوص —
  `overdebited` (خرج نقداً أكثر مما استلم) · `unclassified_void` (إلغاء بلا سبب — يحجب
  الخصم الآلي) · `orphan_money` (شريك أودو بلا حساب) · `inbox_unresolved` (مال ينتظر
  صاحبه، يُعدّ **بالدفعة** لا بالرسالة) · `shadow_drift` (العمود ≠ الدفتر) ·
  `live_with_void_reason` · `bidding_blocked` (طلب استرداد يحجز وديعة) ·
  `webhook_failure` · `odoo_balance_mismatch` (النقطة غير موجودة في أودو → يبلّغ غيابه).
  يُفتح البلاغ ويُغلق وحده؛ الأدمن يؤشّر «رأيته» فقط.
- **`CustomerLedger::headroom`**: كم يجوز خصمه = (استردادات مدفوعة − ودائع أُلغيت نقداً)؛
  إلغاءٌ بلا سببٍ مسجَّل → صفر ومحجوب.
- **لماذا لا يستطيع العميل المزايدة؟**: يعيد فحوص البوابة بلا كتابة + آخر ١٢ رفضاً من
  `logs/bid_refusals.log`.
- **تقرير المحفظة**: `SUM(total_insurance_paid)` من العمود (لا من الدفتر) — بحث · حدّ
  أدنى/أقصى · ترتيب · CSV.
- **سجل المحفظة**: يقرأ `wallet_logs` وهو غير موجود → يعرض `refunds_requests`.
- **صفحة المستخدم**: حركات المحفظة (٢٠٠) · ودائع التأمين (٢٠٠) · تحذير «free محجوزة
  لديونه» من `duesNeedingLockCount`.
- **الويدجت** (`walletStatsData`): إجمالي الدفتر النشط · ودائع نشطة · مستردّة · نموّ شهري.

---

## ٧ — ما يراه العميل (`menu/wallet.php`)

الرصيد (من الدفتر) · حالة الاشتراك (`hasActive`: ظلّ ≥ ١٠k **أو** ودائع نشطة ≥ ١٠k) ·
سجلّ الاشتراكات (`transfer_requests` ≥ ١٠k مع تطبيع الحالة، وربط الاستردادات FIFO) ·
جدول الودائع بترتيب free → held → locked → refunded · «متاح فعلاً» = free −
`duesNeedingLockCount` (و`DUES_UNKNOWN` = يُخفى زرّ الاسترداد ولا يُدّعى التوفّر) ·
أزرار: شحن (١٠٬٠٠٠ ثابت، بطاقة أو تحويل) · طلب استرداد · سجلّ الحركات
(`/wallet/history?type=insurance|purchase_payment`).

---

## ٨ — الأعطال التي كلّفت مالاً (كما يعدّها v1 عن نفسه)

| العطل | الأثر | ما أصلحه v1 |
|---|---|---|
| تحرير «غير الفائز» عند التسوية | ٢٣٠+ وديعة تحرّرت لفائزين | خاسر = كل مزايداته مرفوضة |
| رصيدٌ مخزَّن يُكتب مباشرة | انحراف ٥٤٨ عميلاً / ٩٠٬٠٠٠ مخفية | `recomputeShadow` كاتبٌ وحيد + `shadow_drift` |
| استردادٌ بلا شرط «لا مستحقات» | ~١٩٠٬٠٠٠ | `autoLock` + `lockUnpaidWinners` قبل الاسترداد |
| خصم الاسترداد من free فقط | «الاسترداد لم يسحب» يومياً | `refundDebitByAmount` free→held→locked |
| وديعتان على دَينٍ واحد | عميل بسيارة واحدة وتأمينه ٠ | `releaseRedundantLocks` |
| تفرّد `LIKE '%#5%'` | `#50` عُدّ مخصوماً | REGEXP محدود |
| `''` في عمود رقمي (1366) | ٢٨ استرداداً ضاع ٤ أيام | NULL عند الحدود |
| صدى البطاقة من أودو | عميل دفع ١٠k فاعتُمد ٢٠k | placeholder `moyasar_<id>` |
| `updated` يُهمَل وفيه `invoice_id` | ١٠k فاتورة صارت تأميناً ١١ يوماً | تطبيق الفاتورة على غير posted |
| ٦٠ عميلاً ×١ ريال تجريبي يفتح استرداد ١٠k | | free **بالمبلغ** ≥ ١٠k لا بالعدد |

---

## ٩ — v1 ↔ v2: ما تطابق وما يحتاج قرار المالك

| الموضوع | v1 | v2 (`apps.money` + `bidding`) | الحال |
|---|---|---|---|
| الوديعة وحدة ١٠k | نعم | `whole_deposits_in`؛ غير المضاعف → `suspense` | ✓ |
| الرصيد | ظلّ يُعاد حسابه | `Account.balance` كاش تحت قفل + `verify_ledger` + CHECK ≥ ٠ | ✓ أقوى |
| حجز/قفل مسمّى | `linked_auction_id/invoice_id` | `Hold(auction\|invoice)` + قيد واحد نشط لكل (عميل، مزاد) | ✓ |
| تحرير الخاسر | فقط حين **كل** مزايداته مرفوضة، وعند «إرسال الفواتير للكل» | `settle_holds`: يُحفظ لمن ما زال منافساً أو فائزاً، ويُحرَّر الباقي عند التسوية | ⚠ توقيت مختلف: v2 يحرّر عند التسوية الآلية لا عند «إرسال الفواتير» |
| وديعة واحدة للمزاد كله | نعم (تُحرَّر حين تُسدَّد كل فواتيره) | `pledge_auction_hold` + `_release_holds_on` (آخر فاتورة) | ✓ |
| المدين والمزايدة | يُقفل وديعةً على الدَّين **ويسمح** بالمزايدة إن بقيت له وديعة حرّة ثانية | `UNPAID_DUES` يرفض أي مدين (إلا باستثناءٍ مكتوب `money.exception`) | ⚠ **قرار**: هل يزايد المدين بوديعة ثانية؟ |
| سرقة held لتأمين دَين (D1‑ب) | نعم | لا | ⚠ **قرار** |
| طلب استرداد معلّق يحجب المزايدة | نعم | `spendable = free − refund_pending` | ✓ |
| خصم الاسترداد الذي رحّله أودو | free → held → locked، ويلغي المزايدات | من free فقط؛ العجز → `RefundShortfall` طابور يدوي (HR‑09) | ⚠ **قرار**: v2 أكثر حذراً، v1 يطيع أودو |
| شحن يدوي | مبلغ + سبب من ٥، بلا مرجع | مرجع الحوالة إلزامي (مفتاح تفرّد) + سبب حرّ | ✓ أقوى |
| خصم مباشر | مبلغ حرّ، confiscated، بلا سبب | مصادرة حجزٍ بعينه / سداد فاتورة / استرداد — بلا خانة حرّة | ✓ بالتصميم |
| شحن بتحويل بنكي + إيصال (طلب من العميل) | `transfer_requests` + مراجعة | **غير موجود**: `TopupListCreateView` بطاقة فقط؛ التحويل يصل من أودو مباشرة | ⚠ **نقص**: لا شاشة «طلبات شحن» ولا رفع إيصال |
| استرداد يدوي (أدمن يفتح طلباً لعميل) | صفحة | لا | ⚠ نقص |
| إجراءات الاستردادات (فحص/اعتماد/خصم/تعديل) | نعم | `console:refunds` قائمة وعدّادات فقط؛ التنفيذ عبر أودو → `refund.confirmed` | ⚠ **قرار**: هل يعتمد الأدمن من اللوحة أم من أودو فقط؟ |
| سجل المحفظة | مكسور (يعرض الاستردادات) | `money-ledger` قيود حقيقية | ✓ |
| تقرير المحفظة | `SUM(عمود)` | من الدفتر | ✓ |
| صحّة المحفظة | ٩ فحوص + بلاغات تُفتح وتُغلق | `money-health`: ٤ فحوص حيّة بلا جدول بلاغات | ⚠ ناقصٌ فيه: orphan/inbox/webhook/odoo‑mismatch والبلاغات المستمرّة |
| استثناء عميل من قفل الديون | ثابت في الكود `[8982]` | `Hold.exception_granted_by` + ملاحظة + تدقيق | ✓ أقوى |
