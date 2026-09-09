# شروط المزاد واتخاذ القرار — v1 ⇄ v2

مصدر v1 (قراءةً فقط): `AuctionController` · `BidApiController` · `AuctionBidsAdminController` ·
`OwnersAuctionBidsController` · `BillController`/`BillDecisionService` · `PartnerConsoleController` ·
`PartnerVehicleLock` · `OdooService` · `AuctionVat`.
مصدر v2: `apps/auctions` · `apps/bidding` · `apps/money` · `apps/console`.

---

## أ — شروط المزاد

| الشرط | v1 | v2 | الحكم |
|---|---|---|---|
| **التأمين** | `auctions.insurance_amount` — الواجهة `readonly=10000`، **والخادم يقبل أي قيمة** (`storeFees` بلا CSRF) | `Auction.deposit_required` (١٠٬٠٠٠)، تعديلٌ بشاشة الرسوم خلف `AUCTIONS_MANAGE` بسبب وقيد تدقيق | v2 أسلم |
| **الرسوم الإدارية** | `auctions.fees` (افتراضي ٨٠٠) — **بندٌ مستقلّ في فاتورة أودو**: `fees*(1+vat)` | `Auction.admin_fee` (٨٠٠) — **رقمٌ معروضٌ فقط؛ لا يدخل فاتورةً ولا حركةً دفترية** | ⚠️ **v2 لا يُحصِّلها** |
| **الضريبة** | `auctions.vat_type` لكل مزاد — **متعارضٌ داخلياً**: مثبّتة ١٥٪ حرفياً عند تسجيل المزايدة وتعديلها، ومحترَمةٌ عند الفوترة والعرض | نسبةٌ واحدة `VAT_RATE=0.15` للمنصّة، و`tax_of` الموضعُ الوحيد الذي يضرب فيها | v2 أسلم (v1 يتعارض مع نفسه) |
| **خطوة الزيادة** | `auctions.increment` — **معطّلةٌ وظيفياً**: تُقرأ وتُعاد في `meta.minimum_increment` ولا تُفحَص | لا وجود لها | لا تُنقَل — ميتةٌ في v1 |
| **الحدّ الأدنى** | **لا يوجد إطلاقاً** — مظروفٌ مغلق، أي مبلغ > 0 عرضٌ صحيح | `MINIMUM_BID=1000` أرضيةٌ واحدة (لا تقرأ المزاد ولا المركبة) | فرقٌ متعمَّد — يحتاج قرار المالك |
| **نوع المزاد** | `type_auctions` (open/close)؛ المزاد الكبير **قسراً** `close` | لا حقل — الكلّ مغلقٌ ضمناً | مطابقٌ عملياً |
| **تجاوز لكل سيارة** | `settings_override` (increment · fees · vat_type) — **الكود كامل ولا واجهة تملؤه**، فيبقى `NULL` دائماً | لا وجود له | لا يُنقَل — ميتٌ في v1 |
| **تذكير الرسائل** | `sms_reminder_time` + إرسالٌ فعليّ | `sms_reminder_at` **يُخزَّن ولا يُرسَل** (لا مهمّة تقرؤه) | ناقصٌ في v2 (بقرار المادة ٥-٢) |

### الخلاصة الماليّة الوحيدة الخطيرة
v1 يُصدر فاتورةً ببندين: **المركبة** + **رسومٌ إدارية ٨٠٠ شاملةً الضريبة**.
v2 يُصدرها ببندٍ واحد (`awarded_price`)، و`admin_fee` لا يُذكر في `apps/money` إطلاقاً.
**أي ٨٠٠ ر.س عن كل سيارةٍ تُباع لا تُحصَّل.**

---

## ب — اتخاذ القرار على المزايدات

### v1: ثلاثة مسارات متوازية، بلا مصدر حقيقةٍ واحد

| المسار | يكتب في | الحال |
|---|---|---|
| `AuctionController::approveBid` | `auction_vehicles.approval_status` | بلا CSRF، ويستعمل جدول التأمين **القديم** `insurance_payments` |
| `OwnersAuctionBidsController` | `winner_user_id`/`final_price`/`winning_bid_id`/`awarded_at` + `bids.status`/`rank` | اللوحة الحديثة؛ يُصدر الفاتورة فوراً |
| `BillDecisionService` (bills) | `bids.offer_status` (pending/accepted/rejected) | **المستعمَل يومياً**، وهو المرتبط بالفوترة والتسوية |

**وفعلان متعاكسان اسمُهما «رفض»:**
- `rejectWinner` → يسترد التأمين **ويرقّي المزايد التالي**.
- `BillDecisionService::rejectBid` → يرفض **كلّ** مزايدات السيارة، **بلا استرداد وبلا ترقية** («لا فائز لهذه السيارة»).

**لحظة الحسم الماليّ الوحيدة:** `invoiceAllAccepted` ← `InsuranceSettlement::settleAuction` — الفائزون تبقى ودائعهم مقفولة ومن عداهم تُحرَّر.

### v2: مصدرٌ واحد

القرار **لا يُخزَّن كحقل**، بل يُستدلّ من ثلاثة متّسقة: **الحالة** (`awaiting_decision → awarded | rejected`) + **حقول الترسية** (`awarded_to`/`awarded_price`/`awarded_at`) + **سجلّ التدقيق**.
- `settlement.decide_vehicle`: لا مزايدة → رفض · أقلّ من سعر الوقوف → **قرار المالك** · وإلا ترسية.
- `award_to` قرارُ شريكٍ يدويّ (يتحقّق أن المزايدة حيّةٌ على هذه المركبة)، و`replace_winner` ينقل الترسية ويلغي الفاتورة القديمة ويحرّر أقفالها.
- `settle_holds`: المنافس على مركبةٍ لم تُحسم يبقى تأمينه محجوزاً — وكلُّ حجزٍ يأخذ صفّاً في التقرير ولو لم يتغيّر.

---

## ج — ما ينقص v2 فعلاً (لا يُنقَل منه ميتُ v1)

| # | الناقص | الدليل | الخطورة |
|---|---|---|---|
| ١ | **تحصيل الرسم الإداري** | v1 بندٌ في الفاتورة؛ v2 `admin_fee` معروضٌ ولا يُحصَّل | **مالٌ لا يُجبى** |
| ٢ | **قفل قرار الشريك** | v1 `PartnerVehicleLock`: سيارةُ تسويقٍ لم يقرّر فيها الشريك **لا يُتَّخذ عليها قرار**. v2 عنده `is_marketing` **وبلا أيّ قفل** | قرارٌ يُتَّخذ فوق رأس الشريك |
| ٣ | **حقل السبب في شاشة العروض** | `partners.award` يقرأ `reason` ويمرّره لـ`replace_winner` **التي تشترطه**، و`partner_offers.html` لا يرسله → كلُّ نقلِ ترسيةٍ بسببٍ فارغ | سجلٌّ أعمى |
| ٤ | **حراسة القرار** | `console:vehicle-state` خلف `AUCTIONS_MANAGE` تنقل `awaiting_decision → awarded` — **بلا `PARTNERS_DECIDE`** | تجاوزُ صلاحية |
| ٥ | **`replace_winner` لا يُفوتر** | توثيقها يقول «فاتورة جديدة وقفل وديعته»، والكود لا ينفّذه | توثيقٌ كاذب |
| ٦ | **إرسال تذكير الرسائل** | `sms_reminder_at` يُخزَّن ولا يُقرأ | ميزةٌ ناقصة |

## د — ما لا يُنقَل من v1 (ميتٌ أو معطوب)
`increment` (معطّلة) · `settings_override` (بلا واجهة) · `vat_type` لكل مزاد (يتعارض مع تثبيت ١٥٪) ·
ثلاثيّة أعمدة القرار (`approval_status` + `offer_status` + `status`) · جدولا التأمين المتوازيان ·
صفحات `owners_console` اليتيمة الأربع ومساراتها الثلاثة غير المعرَّفة.

---

## هـ — مخالفتان لقواعد v2 نفسها (وُجدتا أثناء المسح)

الحرّاس الآلية (`ops/checks/*`) **حُذفت بقرار المالك** ٨ سبتمبر ٢٠٢٦ مع حزمة
الاختبارات (`ad916d2`، مذكورٌ في `CLAUDE.md`) — فغيابها ليس اكتشافاً. لكن
غيابها يعني أن القواعد الموصوفة في التعليقات صارت **أعرافاً يدوية**، وقد
انحرف عنها الكود فعلاً في موضعين:

| # | المخالفة | الموضع | لماذا تهمّ |
|---|---|---|---|
| ١ | `replace_winner` يكتب `Vehicle.state` مباشرةً بـ`save(update_fields=[…, "state"])` | `apps/bidding/settlement.py:447-451` | يتجاوز `move_vehicle` «الكاتب الوحيد»، ويتجاوز `VEHICLE_MOVES` — ولا نقلة `awarded → awarded` فيها أصلاً |
| ٢ | `_undo_award` و`cancel_auction` يكتبان `invoice.state = CANCELLED` مباشرةً | `apps/bidding/settlement.py` | بدل المرور بـ`derive_invoice_state` |

وفي `justfile` وصفاتٌ **فارغة الجسد** (تعليقٌ بلا أمر): `lint-money` ·
`lint-rules` · `check` · `check-migrations` · `check-deploy` · `web-check` ·
`web-lint-rules`. فوصفة `ci` تنادي سبعاً منها ولا يُنفَّذ فعلياً إلا
`ruff check` و`ruff format --check` و`test`. ووصفةٌ فارغة **تمرّ بنجاح** —
وهو أسوأ من وصفةٍ محذوفة، لأن الأخضر يقول إن الفحص جرى.
