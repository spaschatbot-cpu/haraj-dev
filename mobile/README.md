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
