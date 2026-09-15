# مسحُ مسارات اللوحة كلِّها — ٢٠٢٦-٠٩-١٣

**السؤال:** ما الذي ينكسر في الشاشات التي **لم تُفتح قطّ**؟ فُتحت في الجلسات
السابقة عيّنةٌ نحوَ خمسَ عشرةَ شاشة، والباقي مقروءٌ لا مرئيّ — و«رؤيةُ الشاشة
تعمل قياس، وقراءةُ الكود ليست قياساً».

**البيئة:** `localhost:8001` (و`127.0.0.1:8001` للمسح الآليّ — الخادم يستمع
على `127.0.0.1` وحدها) على `haraj2_t307`: ٤٤٬٠٣٦ مستخدماً · ٥٥ مزاداً ·
١٢٬٩٨١ مركبة · ١٦٣٬٢٨٣ مزايدة · ١٢٬٣٢٤ فاتورة · ١٧٬٦٥٢ حركة. بموظّفٍ كاملِ
الصلاحية `966500000000`.

## الأرقام

**١٢٣ مساراً** تحت `console/` — العددُ مقيسٌ بـ`get_resolver()` لا منقولاً
(١٨٤ مساراً في المشروع كلّه، منها ١٢٣ تحت `console/`).

| الصنف | العدد |
|---|---|
| فُتحت وعُرضت (٢٠٠ HTML) | **٨١** |
| `POST` فقط — لا تُفتح بالتصفّح، وليس ذلك عطلاً | **٢٩** |
| تحتاج حالةً غير موجودة في القاعدة (٤٠٤) | **١١** |
| تنزيل (ملفُّ إكسل) | **١** |
| **أعادت عطلاً وأُصلحت** | **١** |
| **المجموع** | **١٢٣** |

وثلاثةُ أعطالٍ أُصلحت (واحدٌ منها في المسارات الفاشلة، واثنان في شاشاتٍ فُتحت
بـ٢٠٠ ولكنّها تعرض خطأً):

1. **`console/analytics/profit/` — كان يقتل عمليّة الخادم** (لا ٥٠٠: انقطاعُ
   اتصالٍ ثم رفضٌ، أي أن اللوحةَ كلَّها تسقط معه).
2. **`console/invoices/status/` — يطبع `paid` إنجليزيّةً** وسطَ عربيّةٍ كاملة،
   على الشاشة الوحيدة الموجَّهة إلى خارج الشركة.
3. **`_form.html` — عنوانُ «Row stamp» الإنجليزيّ** ظاهرٌ في «تعديل عميل»
   و«بيانات الشركة».

## الأعطال الثلاثة — ما كان وما صار

### ١ — تقرير الأرباح كان يقتل الخادم

`console/analytics/profit/` وحده من بين ١٢٣ لم يُرجع شيئاً: انقطاعُ اتصال، ثم
**رفضُ اتصالٍ على المنفذ ٨٠٠١** — العمليّةُ ماتت. ولم يكن ٥٠٠، فلا أثرَ في
سجلّ أخطاءٍ يقود إليه.

والسبب قِيس في `pg_stat_activity`: أربعةُ خوادمَ خلفيّةٍ عالقةٌ على استعلامٍ
واحد، أقدمُها **١٠ دقائقَ و٤١ ثانية**، شكلُه
`SELECT COUNT(*) FROM (SELECT DISTINCT …)`.

ومصدرُه سطرٌ واحد في `profit_totals`:

```python
"with_bids": rows.filter(vehicles__bids__isnull=False).distinct().count()
```

و`rows` هنا **ليست قاعدةً نظيفة**: هي مخرجُ `profit_rows` بأربعةِ
`Count/Sum` فوق ضمِّ `vehicles`. فإضافةُ ضمِّ `vehicles__bids` فوق ذلك تُنتج
حاصلَ ضربٍ ديكارتيّاً (١٢٬٩٨١ مركبةً × ١٦٣٬٢٨٣ مزايدة) يُغلَّف في
`COUNT(*) FROM (SELECT DISTINCT …)` على ثمانيةَ عشرَ عموداً.

**قِيس الفرق على القاعدة نفسها:**

| الاستعلام | فوق طبقة التجميع | على قاعدةٍ نظيفة |
|---|---|---|
| `with_bids` | **يتجاوز ٢٠ ثانية بحدٍّ زمنيّ؛ ١٠ دقائقَ+ بلا حدّ حتى تموت العمليّة** | **٠٫٢٤ ثانية، والجواب ٢١** |
| `count()` | ٠٫٠٠ ثانية | ٠٫٠٠ ثانية |
| `revenue` | ٠٫٠١ ثانية | ٠٫٠١ ثانية |
| الفواتير `__in` | ٠٫٠٢ ثانية | ٠٫٠٢ ثانية |

**الإصلاح:** فُصلت `profit_base` — المزاداتُ بمرشّحاتها **بلا تجميع** — وصارت
`profit_totals` تأخذها بدل صفوف الشاشة. والشاشةُ بعده **٢٠٠ في ٠٫٤٥ ثانية**
بـ٥٥ صفّاً، وبالمرشّحات أيضاً (`?state=ended` ٠٫٦٧ ثانية · `?from=1&to=10`
٠٫٢٩ ثانية). `backend/apps/console/analytics.py`.

> وأخطرُ ما فيه أن العطلَ **ليس شاشةً معطّلة**: من يفتحها يُسقط اللوحةَ على كلِّ
> من يعمل عليها، ويترك خادماً خلفيّاً يحرق المعالج حتى يُقتَل باليد.

### ٢ — «حالة فاتورة» تجيب بالإنجليزية

الشاشة تُجيب جهةً من **خارج** الشركة (التأمين والجهات)، ووصفُها على نفسها
يقول ذلك. وكانت تعرض:

```
حالة المركبة   مسودة
حالتها         paid
```

سطران متجاوران، أحدهما بـ`get_state_display` عربيّةً والآخر قيمةَ العمود
خاماً. والسائلُ من خارج الشركة لا يملك ما يترجم له الكلمة.

**الإصلاح:** `lookup()` تُرجع `InvoiceState(...).label`. رُئي بعده على الشاشة:
«حالتها **مسدَّدة**». `backend/apps/console/billing.py`.

### ٣ — «Row stamp» إنجليزيّةً في استمارتين

`_form.html` كان يلفّ على `form` كلِّها، فحارسُ التزامن `row_stamp` — وهو
`HiddenInput` — يأخذ عنواناً يولّده جانغو من اسمه: **«Row stamp»** فوق `<p>`
فارغةٍ لا حقلَ فيها. رُئي على «تعديل عميل» و«بيانات الشركة» — والثانيةُ تضعه
في **وسط** الاستمارة بين «ملاحظة» و«رقم المبنى». (استمارتا المركبة والمزاد
تكتبان `row_stamp` بأيديهما فلم يُصبهما.)

**الإصلاح:** `form.hidden_fields` أوّلاً بلا عنوان، ثم `form.visible_fields`.
والحقلُ المخفيّ باقٍ في الصفحتين — قِيس بعد الإصلاح: العنوانُ غاب و
`name="row_stamp"` باقٍ، فالحارسُ لم يُمسّ.

## «فارغةٌ ولها بيانات» — ما فُحص ولم يكن عطلاً

الفراغُ قُورن بالقاعدة قبل أن يُسمّى عطلاً، ولم يُخترَع صفٌّ لملء شاشة:

| الشاشة | ما تقول | ما في القاعدة | الحكم |
|---|---|---|---|
| ما بعد البيع · الخروج · المزايدات المقبولة | صفر | **صفرُ مركبةٍ `AWARDED`** | صحيح — `import_v1` ينقل المزايدات ولا يُرسي |
| الإشعارات · صندوق أودو · طلبات الاسترداد · محاولات الدفع · الشحن البنكي · صلاحيات فوق الدور | صفر | صفرُ صفٍّ في جدولها | صحيح |
| `console/auctions/1/bids/` | صفٌّ واحد (فراغ) | **مزاد ١ فيه صفرُ مزايدة** | صحيح — وبمزاد ٣٨ (١٤٬٦٧٠ مزايدة) خمسون صفّاً |
| تقرير مزايدات مستخدم · بحث عن سيارة · حالة فاتورة · لماذا لا يزايد | فارغةٌ بلا معامل | — | **مقصود** ومكتوبٌ في كودها: «لا تفتح على أصفار» |

وأُعيد فتحُ كلِّ مسارٍ ذي معاملٍ بمفاتيحَ **غنيّةٍ بالبيانات** بعد أن تبيّن أن
المفتاح الأول رقيق: مزاد ٣٨ (١٤٬٦٧٠ مزايدة · ٣٣٧ مركبة) · مركبة ٨٠٠٧ (١٩٦
مزايدة) · عميل ٧١٩٣ (٦١٠ فواتير) · فاتورة ٦٧٩٧٩ (٨٢٠٬٩٤٢٫٤٥ مسدَّدة). وعرضت
صفوفَها: ١٩٦ · ١١٧ · ٦٧ · ٥٥ صفّاً.

**ولم يُوجد رقمٌ يناقض القاعدة.** فُحص أبرزُ المشتبَهين: بطاقةُ «أعلى ٩٩٥٪ عن
الأسبوع الماضي» على رئيسيّةٍ رسمُها البيانيّ ستّةُ أصفار — والقياسُ من القاعدة
٤٣٬٣٦٢ هذا الأسبوع مقابل ٣٬٩٦٠ في الذي قبله، أي **٩٩٥٪ صحيحة**، والأصفارُ
صحيحةٌ كذلك (لا مزايدةَ بين ٠٩-٠٧ و٠٩-١٢).

## نصٌّ إنجليزيّ وسط عربيّ — ما وُجد

أُحصيت الكلماتُ اللاتينيّة في `<main>` كلِّ شاشةٍ فُتحت، خارجَ الشريط الجانبيّ:

* **عطلٌ وأُصلح:** `paid` في «حالة فاتورة» · `Row stamp` في استمارتين.
* **مقصودٌ ومكتوبٌ عليه:** «حالة أودو الخام `posted` — كلام أودو، لا يُبنى
  عليه» · رموزُ القدرات في «صلاحيات فوق الدور» · `PROTECT`/`on_delete` في شرح
  رفض الحذف · `ZATCA` · `MVPI` · `CVT` · `Excel` · `CSV`.
* **بياناتٌ مُرحَّلة لا قوالب:** عناوينُ مزاداتِ v1 (`Auction #38`) · ملاحظةُ
  ربط أودو على ملفّ العميل (`source=column · confidence=confirmed`) — نصٌّ
  كتبه الترحيل في القاعدة، لا سطرٌ في قالب. 🟡 **لم يُصلَح** — إصلاحُه تعديلُ
  بياناتٍ مُرحَّلة لا تعديلُ شاشة.

## 🟡 الشاشتان اللتان لم تُريا — وأين انقطع الطريق

`T837` تركهما: زرُّ «تأكيد النقل» وصفحةُ «إقرار الخروج». وقد رُئي أن اللسان
فارغٌ فعلاً (صفرُ أمرِ خروجٍ · صفرُ مركبةٍ `PAID`/`RELEASED`)، **ولم يُمكن
صنعُ الحالة من اللوحة.** والطريقُ انقطع في موضعين، وكلاهما مقيس:

**١ — لا زرَّ لتغيير حالة مركبة في اللوحة كلِّها.**
`console:vehicle-state` (`console/vehicles/<pk>/state/`) هو **الكتابةُ الوحيدة
على شاشات المركبات** بنصّ كودها، ومسجَّلٌ في `navigation.PAGES` باسم «تغيير
حالة المركبة» وقدرةِ `AUCTIONS_MANAGE` — **ولا قالبَ ولا جافاسكربت يشير إليه**
(بُحث في `templates/` و`apps/console/static/` عن الاسم وعن المسار الحرفيّ:
صفرُ نتيجة). ورُئي على الشاشة: صفحةُ المركبة ٢٥٩٤٦ فيها رابطان اثنان لا غير
(«رجوع» و«المزاد»)، وشاشةُ المزاد ٥٥ أزرارُها لكلِّ مركبة: رفعُ صورة · تبديلُ
شريك · الصور · تعديل · إخفاء — **ولا زرَّ حالة**.

**٢ — والأبوابُ الأخرى تطلب مزايدةً قائمة.** `partners.award` هو المسارُ
الآخرُ الوحيد إلى `AWARDED`، و`settlement.award_to` يرفض بلا
`Bid.objects.live()` على المركبة. وحالاتُ المركبات في القاعدة: `draft`
١١٬٩٥٥ · `listed` ٧٣٨ · `rejected` ٢٨٨ — **صفرٌ في `bidding` و`awaiting_decision`**،
فشاشةُ العروض لا تجد ما تقرّر فيه. والمزايدةُ فعلُ عميلٍ عبر
`api/v1/vehicles/<pk>/bids/`، **ولا شاشةَ في اللوحة تُزايد** (بُحث: صفرُ نتيجة
لـ`place_bid`/`Bid.objects.create` في `apps/console/`).

> فالسلسلةُ `draft → listed → bidding → awarded → invoiced → paid` مقطوعةٌ
> عند أوّل حلقةٍ من اللوحة، ومقطوعةٌ ثانيةً عند المزايدة. ولم تُصنع الحالةُ
> بحقنِ صفٍّ في القاعدة، ولم تُمسّ بياناتُ الإنتاج المرحَّلة لصنعها —
> إرساءُ مركبةٍ حقيقيّةٍ على عميلٍ حقيقيّ يُصدر فاتورةً ويحجز مالاً، وذلك ثمنٌ
> لا يُدفع لرؤية رسمٍ.

## 🟡 وثلاثةُ أفعالٍ لا زرَّ لها — نظيرُها في v1 موجود

مُسح كلُّ مسارٍ باسمه بحثاً عمّن يشير إليه. وبعد استثناء ما تبنيه
`navigation.py` وما تناديه جافاسكربت بمسارٍ حرفيّ (`marketing` · `visibility` ·
`display-image` · `quick-update` · `exit-edit` — وكلُّها موجودةٌ في
`auction_detail.html` و`auctions_quick_edit.html` و`vehicle_exit.html`)، بقيت
**أربعةٌ لا يشير إليها شيء**:

| المسار | ما يفعله بنصّ كوده | نظيرُ v1 |
|---|---|---|
| `console:vehicle-state` | «الكتابةُ الوحيدة على هذه الشاشات» | — |
| `console:exit-upload` | «رفعُ الإقرار الموقّع» | «📎 رفع الموقّع» |
| `console:exit-lift-ban` | «رفعُ الحظر عن خروجٍ بلا لوحات» | — |
| `console:exit-note` | «حفظُ ملاحظةِ متابعةٍ على أمر الخروج» | — |

وهي تعمل — تكتب وتسجّل في السجلّ وتُعيد التوجيه — **ولا يستطيع موظّفٌ بلوغَها
من اللوحة**. وثلاثةٌ منها على شاشة الخروج نفسِها التي لم تُرَ بسجلّ، فقد يكون
غيابُها مقصوداً حتى يوجد سجلّ؛ **وذلك ما لم يُقَس، فهو 🟡 لا حكم.**

## ما لم يُرَ في هذا المسح

* **الحالةُ المرئيّة لِما يحتاج صفّاً غيرَ موجود:** ١١ مساراً تُرجع ٤٠٤ لأن
  جدولَها فارغ (٦ منها على أوامر الخروج · ٢ على صندوق أودو · ٢ على الأدوار ·
  ١ على طلبات الاسترداد).
* **مسلكُ الكتابة في ٢٩ مساراً `POST`** — فُتحت بـGET فأعادت ٣٠٢/٤٠٥/٤٠٣ كما
  ينبغي، **ولم يُضغط زرُّها**. ولم يُضغط حذفٌ ولا إلغاءٌ على بياناتٍ مُرحَّلة.
* **المظهرُ الداكن ولقطاتُ الشاشة:** المسحُ جرى بقراءة الـDOM والنصّ لا
  باللقطات (١٢٣ لقطةً لا تُقرأ)، واللقطاتُ للمواضع ذاتِ الشكّ البصريّ.

## التحقّق الأخير

أُعيد المسحُ كلُّه بعد الإصلاحات الثلاثة:
**١٢٣ مساراً · ٨٣ × ٢٠٠ · ٢٢ × ٣٠٢ · ٥ × ٤٠٥ · ١ × ٤٠٣ · ١٢ × ٤٠٤ ·
صفرُ ٥٠٠ وصفرُ انقطاع.** والفرقُ الوحيد عن المسح الأول هو
`console/analytics/profit/`: من **انقطاعٍ يقتل الخادم** إلى **٢٠٠**.
و`ruff check apps/` و`manage.py check` نظيفان.

> **ملاحظةٌ على المسح لا على اللوحة:** تسجيلُ دخول الموظّف محدودٌ بـ**٥
> محاولاتٍ في الساعة للحساب و١٠ للعنوان** (`throttled_staff_login`)، والمسحُ
> المتكرّر يستنفدها فيعود ٤٢٩. والعدّادُ في `LocMemCache` داخل عمليّة الخادم،
> فإقلاعٌ جديدٌ يصفّره — وذلك في التطوير وحده حيث الكاشُ في الذاكرة.

## الجدول — كلُّ مسارٍ وحالتُه

`pk` المستعمَل في المسح الأول: مزاد ١ · مركبة ٦٣١٢ · عميل ١٠٨٢ · فاتورة ٦١٥٣٤
· مشرف ١١١٨٤ · حجز ١ · حركة ١. ثم أُعيد فتحُ ذواتِ المعامل بمفاتيحَ غنيّة
(أعلاه).

| # | المسار | الاسم | الحالة | ما رُئي |
|---|---|---|---|---|
| 1 | `console/` | `home` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 2 | `console/columns/save/` | `columns-save` | POST | ٤٠٣ — POST بـCSRF |
| 3 | `console/sign-out/` | `sign-out` | POST | ٤٠٥ — POST فقط |
| 4 | `console/why-no-bid/` | `why-no-bid` | فُتحت | فارغةٌ بلا معامل؛ بـ`?phone=` «لا محاولات مرفوضة» |
| 5 | `console/auctions/` | `auctions` | فُتحت | ٢٠٠ · 25 صفّاً |
| 6 | `console/auctions/new/` | `auction-new` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 7 | `console/auctions/<int:pk>/edit/` | `auction-edit` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 8 | `console/auctions/<int:pk>/state/` | `auction-state` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 9 | `console/auctions/<int:pk>/showcase/` | `auction-showcase` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 10 | `console/auctions/<int:pk>/reschedule/` | `auction-reschedule` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 11 | `console/auctions/<int:pk>/fees/` | `auction-fees` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 12 | `console/auctions/<int:pk>/delete/` | `auction-delete` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 13 | `console/auctions/<int:pk>/end-now/` | `auction-end-now` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 14 | `console/auctions/<int:pk>/` | `auction-detail` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 15 | `console/auctions/<int:pk>/vehicles/bulk/` | `auction-vehicles-bulk` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 16 | `console/auctions/<int:pk>/vehicles/import/` | `auction-vehicles-import` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 17 | `console/auctions/<int:pk>/bids/` | `auction-bids` | فُتحت | صفٌّ واحد (فراغ) — **صحيح**: مزاد ١ فيه صفرُ مزايدة؛ بمزاد ٣٨ خمسون صفّاً |
| 18 | `console/archive/` | `auction-archive` | فُتحت | ٢٠٠ · 100 صفّاً |
| 19 | `console/archive/<int:pk>/vehicles/` | `archive-auction-vehicles` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 20 | `console/auctions/manage/` | `auctions-manage` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 21 | `console/auctions/bulk/` | `auctions-bulk` | فُتحت | ٢٠٠ · 9 صفّاً |
| 22 | `console/auctions/quick-edit/` | `auctions-quick-edit` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 23 | `console/vehicles/<int:pk>/quick-update/` | `vehicle-quick-update` | POST | ٤٠٥ — POST فقط |
| 24 | `console/reminders/` | `reminders` | فُتحت | ٢٠٠ · 5 صفّاً |
| 25 | `console/reminders/<int:pk>/send/` | `reminder-send` | POST | POST فقط (٣٠٢ بمفتاحِ مزادٍ صحيح ٥٥) |
| 26 | `console/bids/live/` | `live-bids` | فُتحت | ٢٠٠ · 1 صفّاً |
| 27 | `console/bids/vehicles/` | `vehicle-bids` | فُتحت | ٢٠٠ · 50 صفّاً |
| 28 | `console/bids/vehicles/<int:pk>/list/` | `vehicle-bid-list` | فُتحت | ٢٠٠ · 102 صفّاً |
| 29 | `console/bids/accepted/` | `accepted-bids` | فُتحت | ٢٠٠ · 1 صفّاً |
| 30 | `console/bids/accepted/summary/` | `accepted-summary` | فُتحت | ٢٠٠ · 6 صفّاً |
| 31 | `console/analytics/` | `analytics` | فُتحت | ٢٠٠ · 6 صفّاً |
| 32 | `console/analytics/bids/` | `analytics-bids` | فُتحت | ٢٠٠ · 22 صفّاً |
| 33 | `console/analytics/active/` | `active-auction` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 34 | `console/analytics/profit/` | `profit-report` | أُصلح | ٢٠٠ — كان **يقتل عمليّة الخادم**؛ بعد الإصلاح ٠٫٤٥ ثانية، ٥٥ صفّاً |
| 35 | `console/owners/` | `owners-console` | فُتحت | ٢٠٠ · 7 صفّاً |
| 36 | `console/owners/bids/` | `auction-bids-index` | فُتحت | ٢٠٠ · 50 صفّاً |
| 37 | `console/refunds/` | `refunds` | فُتحت | ٢٠٠ · 7 صفّاً |
| 38 | `console/wallet/credit/` | `wallet-credit` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 39 | `console/wallet/deduct/` | `direct-deduct` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 40 | `console/wallet/bank-topups/` | `bank-topups` | فُتحت | ٢٠٠ · 5 صفّاً |
| 41 | `console/analytics/insurance/` | `insurance-report` | فُتحت | ٢٠٠ · 52 صفّاً |
| 42 | `console/admins/` | `admins` | فُتحت | ٢٠٠ · 2 صفّاً |
| 43 | `console/admins/page-control/` | `page-control` | فُتحت | ٢٠٠ · 2 صفّاً |
| 44 | `console/settings/` | `settings` | فُتحت | ٢٠٠ · 26 صفّاً |
| 45 | `console/account/password/` | `password-change` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 46 | `console/users/bids-report/` | `user-bids` | فُتحت | فارغةٌ بلا معامل عمداً؛ بـ`?phone=` ٣٦ صفّاً و٧٬٢٩٧ مزايدة |
| 47 | `console/vehicles/catalog/` | `vehicle-catalog` | فُتحت | ٢٠٠ · 50 صفّاً |
| 48 | `console/vehicles/search/` | `vehicle-search` | فُتحت | فارغةٌ بلا معامل عمداً؛ بـ`?vin=` صفٌّ واحد |
| 49 | `console/after-sales/` | `after-sales` | فُتحت | صفر — **صحيح**: الترحيل لا يُرسي |
| 50 | `console/vehicle-exit/` | `vehicle-exit` | فُتحت | الألسنةُ الأربعة صفرٌ — **صحيح**: صفرُ مركبةٍ `PAID` |
| 51 | `console/vehicle-exit/<int:pk>/create/` | `exit-create` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 52 | `console/vehicle-exit/<int:pk>/declaration/` | `exit-declaration` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 53 | `console/vehicle-exit/gate/` | `exit-gate` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 54 | `console/vehicle-exit/<int:pk>/transfer/` | `exit-transfer` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 55 | `console/vehicle-exit/<int:pk>/lift-ban/` | `exit-lift-ban` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 56 | `console/vehicle-exit/<int:pk>/upload/` | `exit-upload` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 57 | `console/vehicle-exit/<int:pk>/edit/` | `exit-edit` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 58 | `console/vehicle-exit/<int:pk>/note/` | `exit-note` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 59 | `console/ended-decisions/` | `ended-decisions` | فُتحت | ٢٠٠ · 50 صفّاً |
| 60 | `console/invoices/status/` | `invoice-lookup` | فُتحت | أُصلح: كانت تطبع `paid` إنجليزيّةً، صارت «مسدَّدة» (٨ صفوف بشاسيهٍ حقيقيّ) |
| 61 | `console/invoices/export/` | `invoices-export` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 62 | `console/partner/` | `partner-console` | فُتحت | ٢٠٠ · 8 صفّاً |
| 63 | `console/partner/auctions/` | `partner-auctions` | فُتحت | ٢٠٠ · 50 صفّاً |
| 64 | `console/partner/state/soon/` | `partner-soon` | فُتحت | ٢٠٠ · 1 صفّاً |
| 65 | `console/partner/state/active/` | `partner-active` | فُتحت | ٢٠٠ · 1 صفّاً |
| 66 | `console/partner/state/ended/` | `partner-ended` | فُتحت | ٢٠٠ · 50 صفّاً |
| 67 | `console/partner/vehicles/` | `partner-vehicles` | فُتحت | ٢٠٠ · 50 صفّاً |
| 68 | `console/partner/vehicles/<int:pk>/rule/` | `partner-rule` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 69 | `console/partner/settlement/unpaid/` | `partner-unpaid` | فُتحت | ٢٠٠ · 1 صفّاً |
| 70 | `console/partner/settlement/paid/` | `partner-paid` | فُتحت | ٢٠٠ · 1 صفّاً |
| 71 | `console/partner/payments/` | `partner-payments` | فُتحت | ٢٠٠ · 1 صفّاً |
| 72 | `console/partner/approve/` | `partner-payments-approve` | فُتحت | ٢٠٠ · 3 صفّاً |
| 73 | `console/vehicles/` | `vehicles` | فُتحت | ٢٠٠ · 25 صفّاً |
| 74 | `console/vehicles/new/` | `vehicle-new` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 75 | `console/vehicles/export/` | `vehicles-export` | تنزيل | ملفُّ إكسل ١٫٢ م.ب |
| 76 | `console/vehicles/import/` | `vehicles-import` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 77 | `console/vehicles/import/rejections/` | `vehicles-import-errors` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 78 | `console/vehicles/<int:pk>/edit/` | `vehicle-edit` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 79 | `console/vehicles/<int:pk>/images/` | `vehicle-images` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 80 | `console/vehicles/<int:pk>/display-image/` | `vehicle-display-image` | POST | ٤٠٥ — POST فقط |
| 81 | `console/vehicles/<int:pk>/` | `vehicle-detail` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 82 | `console/vehicles/<int:pk>/state/` | `vehicle-state` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 83 | `console/vehicles/<int:pk>/marketing/` | `vehicle-marketing` | POST | ٤٠٥ — POST فقط |
| 84 | `console/vehicles/<int:pk>/visibility/` | `vehicle-visibility` | POST | ٤٠٥ — POST فقط |
| 85 | `console/vehicles/<int:pk>/relist/` | `vehicle-relist` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 86 | `console/partners/` | `partner-decisions` | فُتحت | ٢٠٠ · 1 صفّاً |
| 87 | `console/partners/<int:pk>/` | `partner-offers` | فُتحت | ٢٠٠ · 1 صفّاً |
| 88 | `console/partners/<int:pk>/award/` | `partner-award` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 89 | `console/partners/<int:pk>/reject/` | `partner-reject` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 90 | `console/customers/` | `customers` | فُتحت | ٢٠٠ · 25 صفّاً |
| 91 | `console/customers/<int:pk>/` | `customer-detail` | فُتحت | ٢٠٠ · 100 صفّاً |
| 92 | `console/customers/<int:pk>/odoo-link/` | `customer-odoo-link` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 93 | `console/customers/<int:pk>/documents/` | `customer-documents` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 94 | `console/customers/<int:pk>/edit/` | `customer-edit` | فُتحت | أُصلح: كان عنوانُ «Row stamp» الإنجليزيّ ظاهراً |
| 95 | `console/customers/<int:pk>/company/` | `company-edit` | فُتحت | أُصلح: «Row stamp» ظاهرٌ وسطَ الاستمارة |
| 96 | `console/customers/<int:pk>/access/` | `customer-access` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 97 | `console/customers/<int:pk>/delete/` | `customer-delete` | فُتحت | ٢٠٠ · 9 صفّاً |
| 98 | `console/refunds/queue/` | `refund-queue` | فُتحت | ٢٠٠ · 2 صفّاً |
| 99 | `console/refunds/<int:pk>/resolve/` | `refund-resolve` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 100 | `console/payments/attempts/` | `payment-attempts` | فُتحت | ٢٠٠ · 1 صفّاً |
| 101 | `console/staff/<int:pk>/grants/` | `staff-grants` | فُتحت | ٢٠٠ · 1 صفّاً |
| 102 | `console/admins/new/` | `admin-new` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 103 | `console/admins/<int:pk>/edit/` | `admin-edit` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 104 | `console/admins/<int:pk>/password-reset/` | `admin-password-reset` | فُتحت | ٢٠٠ · شاشةُ نموذجٍ/بطاقات (لا جدول) |
| 105 | `console/admins/<int:pk>/delete/` | `admin-delete` | فُتحت | ٢٠٠ · 7 صفّاً |
| 106 | `console/admins/roles/<slug:slug>/edit/` | `role-edit` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 107 | `console/admins/roles/<slug:slug>/delete/` | `role-delete` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 108 | `console/invoices/` | `invoices` | فُتحت | ٢٠٠ · 25 صفّاً |
| 109 | `console/invoices/<int:pk>/` | `invoice-detail` | فُتحت | ٢٠٠ · 2 صفّاً |
| 110 | `console/payments/` | `payments` | فُتحت | ٢٠٠ · 1 صفّاً |
| 111 | `console/money/` | `money-ledger` | فُتحت | ٢٠٠ · 50 صفّاً |
| 112 | `console/money/<int:pk>/` | `money-customer` | فُتحت | ٢٠٠ · 7 صفّاً |
| 113 | `console/money/<int:pk>/actions/` | `money-actions` | فُتحت | ٢٠٠ · 2 صفّاً |
| 114 | `console/money/holds/<int:pk>/confiscate/` | `money-confiscate` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 115 | `console/money/holds/<int:pk>/exception/` | `money-exception` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 116 | `console/money/transactions/<int:pk>/correct/` | `money-correct` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
| 117 | `console/health/` | `money-health` | فُتحت | ٢٠٠ · 6 صفّاً |
| 118 | `console/notifications/` | `notifications` | فُتحت | ٢٠٠ · 1 صفّاً |
| 119 | `console/audit/` | `audit` | فُتحت | ٢٠٠ · 32 صفّاً |
| 120 | `console/inbox/` | `odoo-inbox` | فُتحت | ٢٠٠ · 1 صفّاً |
| 121 | `console/inbox/<int:pk>/` | `odoo-message` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 122 | `console/inbox/<int:pk>/replay/` | `odoo-replay` | حالة غائبة | ٤٠٤ — لا صفَّ لهذه الحالة في القاعدة |
| 123 | `console/inbox/gateway-retry/` | `gateway-retry` | POST | ٣٠٢ على GET — كتابةٌ بـPOST |
