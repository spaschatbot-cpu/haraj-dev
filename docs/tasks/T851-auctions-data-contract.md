# T851 — شاشة إدارة المزادات وشاشاتها الداخلية: عقدُ الداتا، وتصميمٌ حرّ

## القاعدةُ التي تحكم كلَّ ما تحت

المالك بالحرف:

> «مش عايز نفس التصميم أو طريقة العرض بتاعت النظام القديييييييم. أنا عايز
> الداتا بس، كلها، بدون زيادة أو نقص — لأني مظبّط اللي بيتعرض عشان مش عايز
> أعرض حاجة لحد مش من صلاحياته».

فهذه المهمّة **قاعدتان متضادّتان في الظاهر، ولا تعارض بينهما:**

| | |
|---|---|
| **الداتا** | عقدٌ مغلق. لا حقلَ يُضاف ولا حقلَ يُحذف. القائمةُ أدناه هي القائمة. |
| **التصميم والهيكلة** | **حرٌّ تماماً.** لا تنقل شكل v1 ولا ترتيبَ أعمدته ولا طريقةَ عرضه. اصنع أفضل ما تعرف. |

**ولماذا الداتا مغلقة:** كلُّ حقلٍ في القائمة قرّر المالكُ أن هذا الدور يراه.
وحقلٌ تضيفه «لأنه مفيد» يُري موظّفاً شيئاً لا صلاحيةَ له فيه — وهو ما حدث
فعلاً حين أُضيف جدولُ «المشاركون» بتأميناتِ العملاء وفواتيرهم إلى شاشةٍ
يفتحها كلُّ من يملك `auctions.view`. حُذف في `2fa5c20`، ولن يُعاد.

**🔴 مصدر v1 للقراءة فقط.** `D:\haraj 1\applicationtest` هو الكود الحيّ
لمنصّةٍ تعمل. المسموح: `ls` · `cat` · `sed -n` · `grep` · `find` · `wc` ·
`head` · `tail`. وممنوعٌ باتّاً كلُّ ما يكتب أو يحذف داخله.

---

## ١ — شاشة القائمة `/console/auctions/`

### أ) الحقول — واحدٌ وعشرون، لا اثنان وعشرون

هذه هي كلُّ ما يُعيده `AuctionController::datatable()` لكل صفّ
(`AuctionController.php:1436-1457`). موجودةٌ كلُّها عندنا الآن في
`engine.RowSummary` + حقول `Auction`:

| الحقل | المعنى | المصدر عندنا |
|---|---|---|
| `id` | رقم المزاد | `Auction.number` |
| `display_title` | اسم المزاد | `Auction.title` |
| `display_subtitle` | عيّنةُ سيارةٍ أو «عدد السيارات: N» | `RowSummary.sample` |
| `preview_image` | **رابطُ** مصغّرة | `RowSummary.thumbnail` |
| `vehicle_count` | عدد السيارات | `RowSummary.cars` |
| `brand_count` | عدد الماركات المتمايزة | `RowSummary.makes` |
| `sample_vehicle` | اسم سيارةٍ نموذجية | `RowSummary.sample` |
| `start_time` · `end_time` | الموعدان | `starts_at` · `ends_at` |
| `min_price` · `max_price` | مدى سعر الوقوف | `reserve_low` · `reserve_high` |
| `active_vehicle_count` | المعروضة الآن | `RowSummary.offered` |
| `priced_vehicle_count` | ما له سعرٌ مسجَّل | `RowSummary.with_reserve` |
| `vehicles_with_images` · `total_image_count` | تغطيةُ الصور وعددُها | `cars_with_images` · `images` |
| `bid_count` · `bidder_count` · `highest_bid` | المشاركة | `bids` · `bidders` · `top_bid` |
| `preview_site` / `id_park` | الساحة | `Auction.location` |
| `status` | الحالة | `engine.badge_of` |
| `type_auctions` | نوع المزاد | — (`close` في كل صفٍّ من النسخة) |

**وما ليس في القائمة فليس على الشاشة.** خصوصاً: **لا `deposit_required` ولا
`admin_fee` ولا أيّ رصيدِ عميلٍ أو فاتورة.** الرسمُ والتأمين يُحرَّران في
نافذة الرسوم — وهي فعلٌ لا عرض.

### ب) التصميم — حرّ، وهذه معايير الحكم لا وصفة

اصنع الشاشة كما يصنعها مصمّمٌ في ٢٠٢٦، لا كما رسمها DataTables في ٢٠١٩.
احكم على نفسك بهذه:

1. **الصفُّ يُقرأ بلمحة.** أحدَ عشرَ عموداً في جدولٍ واحد يجعل الموظّف يمسح
   يميناً ويساراً. اجمع ما يُقرأ معاً (العربيات والماركات والعيّنة رقمٌ واحد
   بثلاثة أسطر؛ الصور والتفعيل مؤشّرا **جاهزية** لا رقمان منفصلان).
2. **الجاهزيةُ تُرى قبل أن تُقرأ.** «٣٠٠ من ٦٨٣ لها صور» حقيقةٌ أهمُّ من
   الرقمين: نصفُ المزاد لا يُشترى. أعطها شكلاً — شريطاً، حلقةً، لوناً — لا
   سطرَ نصٍّ ثالثاً.
3. **الحالة هي أهمُّ خانة**، لأنها الوحيدة القابلة للنقر ولأن الخطأ فيها
   يُوقف مزاداً أو يفتحه قبل أوانه.
4. **الشاشة الضيّقة ليست جدولاً مقصوصاً.** قرِّر ماذا يصير الصفُّ على ٧٠٠
   بكسل — بطاقةً على الأرجح — ونفّذه.
5. **لا مكتبة.** لا DataTables ولا SweetAlert ولا Bootstrap: الترقيم
   والفرز على الخادم، و`<dialog>` نافذةُ المعيار، والرسائل عبر
   `django.contrib.messages`. نظامُ تنسيقٍ ثانٍ على شاشةٍ واحدة أسوأ من
   شاشةٍ أبسط.
6. **الرموز من `apps/console/icons.py`** — خطوطٌ لا مساحات
   (`fill:none` · `stroke:currentColor`). أيقونةٌ جديدة تُضاف هناك وتُسجَّل
   في `test_icons.py`.
7. **الألوان من الرموز في `app.css`**، ويقيسها `console_colours_are_readable`
   على ثمانٍ وأربعين توليفة مظهر. لا لونَ مكتوبٌ بيد.

---

## ٢ — الشاشات الداخلية

مسارات v1، وما تعرضه كلٌّ منها. **ابنِ الأولى الآن، واقرأ الباقي لتعرف أين
تذهب الأموال والمزايدات فلا تتسرّب إلى شاشةٍ ليست لها.**

| الشاشة | ماذا تعرض | حالتُها عندنا |
|---|---|---|
| **`{id}/vehicles` — سيارات المزاد وصورها** | `SELECT *` من `auction_vehicles` (نحو ٥٠ عموداً) + عدد صور كل سيارة + قفلُ النقل | `console:auction-detail` جزئية |
| `{id}/vehicles/quick-edit` | تعديلٌ سريع للعدّادات | `console:auctions-quick-edit` |
| `{id}/manage` | المزاد وسياراته في بطاقات | `console:auctions-manage` |
| **`{id}/bids` — المزايدات** | **هنا وحدها** تُعرض المزايدات بتفصيلها ومزايدوها | `console:auction-bids` |
| `bid-review` | مراجعة المزايدات والموافقة | `console:accepted-bids` |
| `{id}/export-excel` | تصدير سيارات المزاد | موجود |
| `/vehicles/search` | بحثٌ شامل عن مركبة | `console:vehicle-search` |

### شاشةُ السيارات — الحقولُ الحسّاسة

`auction_vehicles` تحمل حقولاً **مالية وقرارية** لا يراها كلُّ من يفتح
الشاشة. صنّفها هكذا ولا تخلط:

* **وصفُ السيارة** — `vehicle_name` · `make`/`vehicle_brand` · `model` ·
  `year`/`year_of_manufacture` · `mileage` · `the_color` · `Plate_number` ·
  `plate_type` · `chassis_number` · `vehicle_condition` · `condition_notes` ·
  `overview` · `fuel_type` · `runs_status` · `key_status` · `the_doors` ·
  `the_weight` · `mvpi_status` · `insurance_company` · `lot_number` ·
  `starting_price` · `status` · `display_image`
  → **`auctions.view` يكفي.**

* **نتيجةُ البيع ومالُها** — `winner_user_id` · `final_price` ·
  `winner_paid_at` · `payment_method` · `transaction_ref` ·
  `receipt_image_path` · `winning_bid_id` · `awarded_at` ·
  `approval_status` · `bidamount`
  → **لا تُعرض بـ`auctions.view`.** هذه شاشةُ ما‑بعد‑البيع والفواتير.

* **قرارُ الشريك** — `partner_decision` · `partner_decision_bid_id` ·
  `partner_decided_at` · `partner_decided_by`
  → شاشةُ قرارات الشركاء.

* **المعاينة** — `preview_site` · `inspection_days` · `time_periods` ·
  `inspection_report_media`

**وأعمدةٌ ميتةٌ في النسخة الحقيقية لا تُبنى لها واجهة:** `campaign_id`
و`settings_override` و`override_settings` و`vehicle_data` و`auto_bid`
و`is_marketing` و`claim_number` — اقرأها بنفسك قبل أن تبني، وإن وجدتها
فارغةً في كل صفٍّ فاذكر ذلك ولا تعرضها.

---

## ٣ — ما هو مبنيٌّ فعلاً، فلا تُعِد بناءه

الشاشة قائمةٌ وتعمل عند `2fa5c20`. **اقرأ هذه قبل أن تكتب سطراً:**

```
backend/apps/auctions/engine.py          ← المحرّك: كل سؤالٍ عن مزاد يمرّ به
backend/apps/console/auctions.py         ← عرضُ القائمة والتفصيل
backend/apps/console/auction_quick.py    ← النوافذ الأربع
backend/templates/console/auctions.html  ← القالب الحاليّ
backend/apps/console/static/console/     ← app.css · auctions.js · icons.py
```

`engine.summarise` يحسب كلَّ الأرقام في **أربعة استعلاماتٍ مجمَّعة**. لا
تستبدله بحلقة.

**وثلاثةُ عيوبٍ معروفةٌ تُصلَح ضمن هذا العمل** (كانت T850):

1. زرُّ «حذف» يفتح صفحة التعديل — سلّةُ زبالةٍ تقود إلى استمارة. والحذفُ
   مستحيلٌ في القاعدة (`PROTECT`)؛ البديل هو الإلغاء.
2. `services.cascade_auction_vehicles` تأخذ `old_status` ولا تقرؤه، وتخلط
   مفردات البادج بمفردات الحالة المخزَّنة.
3. تسلسلُ الحالات حلقةُ كتابةٍ **بلا معاملة** — مزادٌ بستّمئة سيارة يبقى
   نصفُه منقولاً إن انقطعت.

---

## ٤ — الحدود التي لا تُتجاوز

1. **حالةُ مزادٍ أو مركبة** تُكتب في `apps/auctions/services.py` وحدها.
2. **الدفتر** يُكتب في `apps/money/services.py` وحدها — ولا
   `Transaction.objects.create` في أي مكان، ولا في الاختبارات.
3. **نسبةُ الضريبة** تُقرأ في `apps/money/services.py` وحدها. لا تعرضها.
4. **ساعةُ المزاد** تُقرأ في `apps/auctions/engine.py` وحدها.
5. **الوقت** يُخزَّن UTC ويُعرض بتوقيت الرياض عبر `apps.core.time`.
6. **المال `Decimal`** دائماً، ولا يمرّ بعائم.
7. كل `<table>` داخل `<div class="scroller">`، وكل رابط بـ`{% url %}`.

**إن أرسبك حارسٌ فهو محقٌّ حتى يثبت العكس.** أصلح كودك لا الحارس.

---

## ٥ — التحقّق والتسليم

```bash
cd /d/haraj2/backend && .venv/Scripts/python.exe -m ruff check apps/ && .venv/Scripts/python.exe manage.py check
```

```bash
cd /d/haraj2 && for f in ops/checks/*.py; do backend/.venv/Scripts/python.exe "$f" >/dev/null 2>&1 || echo "FAIL $f"; done; echo done
```

**وافتحها في متصفّح** — `http://127.0.0.1:8001/console/auctions/`، دخول
`966500000001` / `Owner#2026#Haraj`. قِس: عرضٌ أفقيّ صفر على ١٤٤٠ و١٢٨٠،
والصفُّ مقروءٌ على ٧٠٠.

**التقرير:**

```
النتيجة: <سطر واحد>
الملفات: <مسار:سطر>
القياس: ruff ✔ · manage.py check ✔ · الحراس ٣١ ✔ · المتصفّح: <ما قِيس>
قرارات التصميم: <ماذا اخترت ولماذا — هذا هو الجزء الذي أحكم عليه>
حقولٌ لمستُها: <أيُّ حقلٍ أضفته أو حذفته من §١ — ويجب أن يكون "لا شيء">
🟡 ما لم يُقَس:
```

**لا `git commit` ولا `git push`.** الأساس النظيف `2fa5c20` — كلُّ ما يظهر
في `git diff` بعده هو عملُك.
