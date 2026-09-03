import 'dart:async';

import '../../auth/repositories/auth_repository.dart';
import '../../common/failure.dart';
import '../repositories/device_registry.dart';
import '../repositories/push_service.dart';

/// نتيجة محاولة التسجيل — **كل فرع له اسم**.
///
/// المادة ٢-٢ بروحها: لا مسار ينتهي بـ`return` صامت. «الإشعارات لا تصل» شكوى
/// لا تُشخَّص إلا إذا عرف التطبيق أيّ خطوة توقّفت: أذِن المستخدم؟ أعطى المزوّد
/// رمزاً؟ قَبِل الخادم؟
enum PushRegistrationOutcome {
  /// سُجّل الجهاز على حساب صاحب الجلسة.
  registered,

  /// لا جلسة — المالك يأتي من الرمز، فبلا رمز لا مالك.
  notSignedIn,

  /// المستخدم رفض إذن الإشعارات أو حجبه من إعدادات النظام.
  permissionDenied,

  /// أذِن المستخدم لكن المزوّد لم يعطِ رمزاً (لا إعداد Firebase في هذا البناء،
  /// أو لا خدمات Google على الجهاز).
  noToken,

  /// وصل الطلب إلى خادمنا فردّه، أو لم يصل أصلاً.
  ///
  /// لا يمنع التطبيق من العمل، ولا يُبتلع: مستخدم يشكو أن الإشعارات لا تصل
  /// يحتاج من يقول له عند أي خطوة توقّفت.
  serverRefused,
}

/// يسجّل هذا الجهاز لاستقبال إشعارات صاحب الجلسة الحالية (T716).
///
/// ⚠️ لا يُمرَّر معرّف حساب في أي خطوة: الخادم يقرأ المالك من رمز الدخول.
/// انظر `DeviceRegistry` لسبب ذلك بالتفصيل.
final class RegisterThisDevice {
  const RegisterThisDevice({
    required PushService push,
    required DeviceRegistry registry,
    required AuthRepository auth,
  }) : _push = push,
       _registry = registry,
       _auth = auth;

  final PushService _push;
  final DeviceRegistry _registry;
  final AuthRepository _auth;

  Future<PushRegistrationOutcome> call() async {
    // الترتيب مقصود: الجلسة أولاً. طلب الإذن من مستخدم لم يدخل بعد يستهلك
    // الفرصة الوحيدة لطلبه على iOS، ثم يفشل التسجيل بـ401 على أي حال.
    if (!await _auth.hasStoredSession()) {
      return PushRegistrationOutcome.notSignedIn;
    }
    if (!await _push.requestPermission()) {
      return PushRegistrationOutcome.permissionDenied;
    }

    final token = await _push.currentToken();
    if (token == null) return PushRegistrationOutcome.noToken;

    await _registry.register(token: token, platform: _push.platform);
    return PushRegistrationOutcome.registered;
  }

  /// يعيد التسجيل كلما دوّر المزوّد الرمز.
  ///
  /// FCM يبدّل الرمز من تلقاء نفسه — إعادة تثبيت، استرجاع نسخة احتياطية، مسح
  /// بيانات التطبيق. بلا هذا يصمت الجهاز صمتاً تامّاً ولا يشكو أحد، لأن
  /// المستخدم لا يفتقد إشعاراً لم يعلم أنه أُرسل.
  StreamSubscription<String> followTokenRotations() =>
      _push.tokenRefreshes().listen(_reregister);

  Future<void> _reregister(String token) async {
    if (!await _auth.hasStoredSession()) return;
    try {
      await _registry.register(token: token, platform: _push.platform);
    } on Failure {
      // تدوير رمز يفشل تسجيله لا يُسقط التطبيق: المزوّد سيدوّره ثانيةً، والفتحة
      // القادمة تعيد المحاولة عبر `call()`. رمي العطب من داخل مستمع مجرى يصل
      // إلى `FlutterError` بلا شاشة تعرضه ولا مستخدم يفهمه.
    }
  }
}
