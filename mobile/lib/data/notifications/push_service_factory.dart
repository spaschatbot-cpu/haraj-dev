import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import '../../domain/notifications/repositories/push_service.dart';
import 'firebase_push_service.dart';
import 'unconfigured_push_service.dart';

/// يبني خدمة الإشعارات المناسبة لهذا البناء.
///
/// إعداد Firebase يأتي من ملفات المنصة (`google-services.json` و
/// `GoogleService-Info.plist`) التي **لا تُرفع إلى المستودع** (المادة ٥-٣)،
/// وتضعها خطوة النشر لكل بيئة على حدة. غيابها ليس خطأ يستحق سقوط التطبيق:
/// الإشعارات وحدها تُطفأ، والباقي يعمل.
Future<PushService> resolvePushService() async {
  try {
    await Firebase.initializeApp();
    return FirebasePushService(
      FirebaseMessaging.instance,
      platform: FirebasePushService.currentPlatform,
    );
  } on Object {
    // نصنّف ولا نبتلع: النوع المرجَع هو التصنيف نفسه، ويظهر في نتيجة التسجيل
    // بوصفها `noToken` لا بوصفها نجاحاً صامتاً.
    return const UnconfiguredPushService();
  }
}
