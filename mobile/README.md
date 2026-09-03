# تطبيق العميل — حراج واحد

تطبيق Flutter لعملاء المنصة. هذه **البذرة** (التاسكات T701–T705 من
[الفيز 008](../specs/008-flutter-app/tasks.md)): الأساس كامل، والشاشات لم تبدأ.

المراجع الملزِمة: [الدستور](../.specify/memory/constitution.md) ·
[دليل النظام](../docs/system-handbook.md) · [خطة الفريق](../docs/team-plan.md) ·
[خطة الفيز](../specs/008-flutter-app/plan.md)

---

## الأوامر

```bash
flutter pub get
flutter analyze          # يجب أن يخرج نظيفاً
flutter test             # يشمل اختبارات الفحص المعماري والنصّي
dart format .

bash tool/regenerate_api_client.sh   # بعد أي تغيير في مخطط OpenAPI
```

تشغيل على جهاز، مع تعريف البيئة (لا شيء منها مكتوب في الكود — المادة ٥-٣):

```bash
flutter run \
  --dart-define=HARAJ_ENV=development \
  --dart-define=HARAJ_API_BASE_URL=http://10.0.2.2:8000
```

## البنية — ثلاث طبقات، الاعتماد للداخل فقط

```
lib/
  main.dart          نقطة الدخول
  app/               جذر التركيب: الثيم، التوجيه، ربط الطبقات (providers)
  core/              إعدادات البناء (البيئة، عنوان الـAPI)
  domain/            كيانات وusecases وعقود المستودعات — Dart صافٍ
  data/              العميل المولَّد، المستودعات، الكاش، التخزين الآمن
  presentation/      شاشات وwidgets
  l10n/              ملفات ARB والترجمات المولَّدة
```

قاعدتان يفرضهما `test/architecture/layering_test.dart` نصّياً:

1. **`presentation` لا تستورد `data` أبداً** — تصل إليها عبر `domain` فقط.
   الاستثناء الوحيد `lib/app/providers.dart`: هو جذر التركيب، ولا يصدّر إلا
   أنواع النطاق.
2. **`domain` بلا Flutter ولا dio ولا drift** — يبقى قابلاً للاختبار بلا جهاز.

داخل كل طبقة التنظيم بالميزة (`auth/`، `wallet/`…).

## القواعد التي لا تُكسر

| القاعدة | أين تُفرض |
|---|---|
| **ممنوع `double` للفلوس** — المبالغ نصّ عشري وتُعرض كما وصلت | `test/architecture/money_is_text_test.dart` |
| **لا نصّ عربي داخل شاشة** — كل نصّ من ARB | `test/architecture/arabic_text_comes_from_arb_test.dart` |
| **الرموز في التخزين الآمن وحده** — لا في drift ولا في SharedPreferences | `test/architecture/tokens_stay_in_secure_storage_test.dart` |
| **لا نموذج API مكتوب بيد** — العميل كله مولَّد | `test/architecture/generated_client_test.dart` |
| **رسالة الخطأ من الخادم تُعرض كما جاءت** | `test/presentation/failure_view_test.dart` |

`Money` بلا `operator +` عمداً: أي حساب في الشاشة ينتج رقماً بلا قيد يقابله
(المادة ١-٦). المجاميع تأتي محسوبة من الخادم.

## عميل الـAPI (T702)

مولَّد بـ`swagger_parser` من مخطط OpenAPI إلى `lib/data/api/generated/`.
الإعداد في `swagger_parser.yaml`، والمولَّد **مرفوع في المستودع** حتى يعمل
`flutter analyze` بلا خطوة توليد، وحتى يكشف الـCI أي فرق بينه وبين المخطط.

> ⚠️ **المخطط الحالي مؤقّت.** `openapi/haraj-mock.yaml` يمثّل ما نعرفه من
> [الفيز 007](../specs/007-client-api/spec.md)، وهو موجود ليعمل خط التوليد قبل
> تثبيت العقد.
>
> **عند إغلاق T621:** نزّل `/api/schema/` من الخادم، بدّل `schema_path` في
> `swagger_parser.yaml` إليه، شغّل `tool/regenerate_api_client.sh`، واحذف
> `openapi/haraj-mock.yaml`. لا يتغيّر شيء آخر في الإعداد.

## الإشعارات (T716)

الخادم يضع في حمولة الإشعار مفتاح `type` ومعرّفات ما يشير إليه (`auction_id` /
`vehicle_id` / `invoice_id`)، والتطبيق يشتقّ منها الشاشة في **مكان واحد**:
`domain/notifications/usecases/resolve_push_destination.dart`. العنوان نفسه من
`app/routes.dart` التي يقرأ منها التوجيه أيضاً، فما يفتحه الإشعار وما يفتحه
الزرّ عنوان واحد (معيار H6).

نوع لم يره التطبيق من قبل يفتح الرئيسية ولا يُسقط الإشعار: التطبيق المنشور أقدم
من الخادم دائماً.

> ⚠️ **المالك يأتي من رمز الدخول، لا من جسم الطلب.** جسم التسجيل `{token,
> platform}` ولا شيء غيره — ثغرة IDOR في v1 كانت معرّف الحساب حقلاً في الجسم،
> فتسجيل جهاز باسم عميل آخر كان بُعد حقلٍ واحد. يحرسها
> `test/architecture/device_registration_has_no_owner_field_test.dart` على
> **العقد** نفسه، فيسقط عند أول إعادة توليد لو عاد الحقل.

الخروج يمرّ من `signOutProvider` وحده: يُبلغ الخادم **ثم** يمحو الرموز. العكس
يجعل الخادم يردّ 401 فيبقى الجهاز مربوطاً بمن خرج.

إعداد Firebase (`google-services.json` و`GoogleService-Info.plist`) لا يدخل
المستودع (المادة ٥-٣) — و`android/.gitignore` و`ios/.gitignore` يمنعانه، فالقاعدة
مفروضة لا موصى بها. ليس لأن الملف سرّ — فهو يُشحن داخل الحزمة — بل لأنه يسمّي
**مشروعاً بعينه**: ملف تجريب مرفوع يلتقطه بناء الإنتاج، فتذهب إشعارات عملاء
حقيقيين إلى مشروع اختبار. يوضع وقت النشر في `android/app/src/<flavor>/`.

بناء بلا إعداد يعمل وتُطفأ الإشعارات وحدها.

## بناء ونشر (T717 و T718)

```bash
HARAJ_API_BASE_URL=https://api.example.sa BUILD_NUMBER=42 \
  bash tool/build_release.sh android staging
```

السكربت يشتقّ `HARAJ_ENV` من الـflavor: **لا يمكن بناء حزمة تجريب تظنّ نفسها
إنتاجاً** — وهي الحالة التي أوصلت رسالة اختبار إلى عميل حقيقي في v1.

| البيئة | معرّف الحزمة | الاسم | اللافتة وختم الرسائل |
|---|---|---|---|
| `dev` | `…haraj_mobile.dev` | حراج (تطوير) | نعم |
| `staging` | `…haraj_mobile.staging` | حراج (تجريب) | نعم |
| `prod` | `…haraj_mobile` | حراج واحد | لا |

الأسرار كلها من البيئة: `HARAJ_KEYSTORE_PATH` و`HARAJ_KEYSTORE_PASSWORD`
و`HARAJ_KEY_ALIAS` و`HARAJ_KEY_PASSWORD`، أو من `android/key.properties`
المستثنى من git. **بناء `prod` بلا مفتاح توقيع يفشل عمداً** — حزمة إنتاج
موقَّعة بمفتاح التصحيح تبدو سليمة، ومفتاح التصحيح يملكه كل من استنسخ المستودع.

النطاق المدعوم مكتوب لا مفترَض (معيار H1): `minSdk = 28` (أندرويد 9)
و`IPHONEOS_DEPLOYMENT_TARGET = 14.0`. ولهذا `firebase_core` مقيَّد بالجيل 3:
الجيل 4 يرفع أدنى إصدار iOS إلى 15.

> **نقص معلَن:** مخططات Xcode لكل بيئة (نظير الـflavors) لم تُنشأ — إنشاؤها
> يحتاج Xcode على macOS، وبناء iOS اليوم يخرج بمعرّف حزمة واحد لكل البيئات.
> ولم يُشغَّل `flutter build` بنجاح في بيئة التطوير هذه (Gradle لا يفتح اتصال
> loopback عليها)؛ البناء يُتحقَّق منه في وظائف `mobile.yml`.

## العمل بلا اتصال (T704)

`ResponseCache` تحفظ آخر استجابة معروفة لكل مفتاح شاشة، نصّاً، مع طابع UTC.
المستودع يرجع `Snapshot` يحمل مصدر البيانات ولحظتها، و`StaleDataBanner` يعرض
«آخر تحديث» بالتوقيت السعودي عند القراءة من الكاش.

قرار مهم يُنسخ مع كل مستودع جديد: **الكاش يعوّض صمت الخادم لا كلامه.** خطأ ردّ
به الخادم (401، 403…) يمرّ برسالته ولا يُخفى خلف بيانات قديمة.

`WalletRepositoryImpl` هي الشريحة المرجعية — منها تُنسخ بقية المستودعات.

## ما لم يُنفَّذ بعد

شاشات المجموعة ب (T706 وما بعدها) لا تبدأ قبل تثبيت المخطط في T621 — نقطة
التزامن «ب» في خطة الفريق. `lib/presentation/seed/` شاشة مؤقّتة تُحذف مع أول
شاشة حقيقية.
