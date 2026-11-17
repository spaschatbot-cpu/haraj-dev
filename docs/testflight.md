# رفعُ التطبيق إلى TestFlight

البناءُ والتوقيعُ والرفعُ آليّةٌ في `.github/workflows/mobile-release.yml`
(ماك GitHub). وما يبقى بيد المالك **مرّةً واحدة** أربعُ خطواتٍ عند Apple،
وحسابُ Shorebird، ثمّ خمسةُ أسرارٍ في GitHub.

> **منذ ١٧ نوفمبر ٢٠٢٦ يُبنى عبر Shorebird** (كان `mobile-testflight.yml`):
> كي تصل التعديلاتُ الصغيرة إلى نسخة TestFlight ترقيعاً بلا بناءٍ جديد — انظر
> `docs/code-push.md`. وبناءٌ لم يُصدره Shorebird لا يقبل ترقيعاً أبداً.

## ما في البناء

| | |
|---|---|
| الاسم على الشاشة | حراج واحد |
| المعرّف (Bundle ID) | `sa.harajwahed.harajMobile` — يُغيَّر بمتغيّر `IOS_BUNDLE_ID` |
| الخادم | `https://haraj.spas.sa` (طورُ staging كحزمة الـAPK — يظهر شريطُ «تجريب») |
| الإصدار | من `pubspec.yaml` (اليوم `1.0.0`)، ورقمُ البناء رقمُ تشغيل السير |
| الإشعارات | 🟡 **مطفأةٌ في هذا البناء**: لا `GoogleService-Info.plist` ولا مفتاح APNs بعد، والتطبيقُ يعمل بدونها (`push_service_factory.dart`) |

## من جهة Apple — مرّةً واحدة

1. **حسابُ مطوّر Apple مدفوع** (Apple Developer Program). ومنه
   **Team ID** من developer.apple.com ← Membership.
2. **سجلُّ التطبيق** في appstoreconnect.apple.com ← Apps ← **+** ← New App:
   المنصّة iOS، الاسم «حراج واحد»، اللغة العربيّة، والـBundle ID
   `sa.harajwahed.harajMobile` (إن لم يظهر في القائمة يُسجَّل أوّلاً في
   developer.apple.com ← Identifiers ← **+** ← App IDs).
   > **إن كان لتطبيق v1 سجلٌّ في المتجر** ويُراد أن يحلّ v2 محلَّه عند
   > المستخدمين: لا سجلّ جديد — يُوضع معرّفُ v1 في متغيّر `IOS_BUNDLE_ID`،
   > ويُشغَّل السير بإصدارٍ أكبر من المنشور.
3. **مفتاح API**: App Store Connect ← Users and Access ← Integrations ←
   App Store Connect API ← **+**، الدور **Admin** (التوقيعُ السحابيّ لا
   يُتاح لأدنى منه). يُحفظ **Issuer ID** و**Key ID**، ويُنزَّل ملفُّ
   `AuthKey_XXXX.p8` — **يُنزَّل مرّةً واحدة فقط**.
4. **المختبِرون**: التطبيق ← TestFlight ← Internal Testing ← **+** مجموعة،
   ويُضاف إليها أعضاءُ الفريق (حتى ١٠٠، بلا مراجعة Apple). وللمختبِرين من
   خارج الفريق External Testing — أوّلُ بناءٍ فيها يمرّ بمراجعةٍ قصيرة.

## في GitHub — مرّةً واحدة

المستودع ← Settings ← Secrets and variables ← Actions ← **New repository secret**:

| السرّ | القيمة |
|---|---|
| `SHOREBIRD_TOKEN` | من `docs/code-push.md` |
| `APPLE_TEAM_ID` | Team ID |
| `APP_STORE_CONNECT_KEY_ID` | Key ID |
| `APP_STORE_CONNECT_ISSUER_ID` | Issuer ID |
| `APP_STORE_CONNECT_KEY_P8` | محتوى ملفّ `.p8` كاملاً، من `-----BEGIN` إلى `-----END` |

## كلَّ مرّةٍ يُراد بناءٌ جديد

Actions ← **mobile-release** ← Run workflow (المنصّات: `ios` أو `both`).
نحو ٢٥ دقيقةً للبناء، ثمّ ١٠–٣٠ دقيقةً لمعالجة Apple، فيظهر للمختبِرين في
تطبيق TestFlight. **والتعديلاتُ بعده لا تحتاج هذا** — `mobile-patch` يكفي ما
لم يتغيّر شيءٌ أصليّ (`docs/code-push.md`).

**وما قد يقع في أوّل تشغيل:**

- «الأسرار حاضرة» أو «مفتاح Shorebird حاضر» يسقط ← سرٌّ غائبٌ واسمُه في الرسالة.
- 🟡 «التوقيع والرفع» يسقط على أرشيفٍ بلا توقيع ← لم يُجرَّب هذا المسارُ بعدُ
  على حسابنا. البديلُ الموثَّق: شهادةُ توزيعٍ ‎.p12 وملفُّ تزويدٍ في الأسرار،
  و`--export-options-plist` بتوقيعٍ يدويّ بدلَ `--no-codesign`.
- `No profiles for '…' were found` ← المفتاح ليس Admin، أو المعرّف غير
  مسجَّل (الخطوة ٢).
- `The bundle version must be higher` ← بناءٌ بالرقم نفسه رُفع؛ يُعاد التشغيل.
  **ولا يُترك لـApple أن تغيّر الرقمَ عند الرفع** (`manageAppVersionAndBuildNumber`
  مطفأ): لو تغيّر لما طابق إصدارَ Shorebird ولما وصله ترقيع.
- `This bundle is invalid. The value for key CFBundleShortVersionString…` ←
  الإصدار أصغرُ من المنشور؛ يُكتب أكبرُ منه في خانة «version» عند التشغيل.
