import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/notifications/repositories/push_service.dart';
import 'package:haraj_mobile/domain/notifications/usecases/register_this_device.dart';

import '../support/fake_push.dart';

/// T716 — «تسجيل الجهاز ⚠️ يُربط بالمستخدم من الرمز لا من معامل».
void main() {
  ({
    RegisterThisDevice usecase,
    FakePushService push,
    RecordingDeviceRegistry registry,
    FakeAuthRepository auth,
  })
  build({
    bool signedIn = true,
    bool permissionGranted = true,
    String? token = 'fcm-token-abcdef',
    DevicePlatform platform = DevicePlatform.android,
  }) {
    final push = FakePushService(
      permissionGranted: permissionGranted,
      token: token,
      platform: platform,
    );
    final registry = RecordingDeviceRegistry();
    final auth = FakeAuthRepository(signedIn: signedIn);
    return (
      usecase: RegisterThisDevice(push: push, registry: registry, auth: auth),
      push: push,
      registry: registry,
      auth: auth,
    );
  }

  test('التسجيل يرسل الرمز والمنصة ولا شيء غيرهما', () {
    // العقد نفسه لا يحمل حقل مالك؛ هذا الاختبار يثبت أن الاستدعاء لا يحاول
    // تمرير واحد من طرف آخر. الحارس على العقد في
    // test/architecture/device_registration_has_no_owner_field_test.dart
    final it = build(platform: DevicePlatform.ios);

    return it.usecase().then((outcome) {
      expect(outcome, PushRegistrationOutcome.registered);
      expect(it.registry.registrations, [
        (token: 'fcm-token-abcdef', platform: DevicePlatform.ios),
      ]);
    });
  });

  test('بلا جلسة لا تسجيل — ولا يُطلب الإذن أصلاً', () async {
    // طلب الإذن من مستخدم لم يدخل بعد يستهلك الفرصة الوحيدة لطلبه على iOS،
    // ثم يفشل التسجيل بـ401 على أي حال.
    final it = build(signedIn: false);

    expect(await it.usecase(), PushRegistrationOutcome.notSignedIn);
    expect(it.push.permissionAsked, isFalse);
    expect(it.registry.registrations, isEmpty);
  });

  test('رفض الإذن حالة مسمّاة لا صمت', () async {
    final it = build(permissionGranted: false);

    expect(await it.usecase(), PushRegistrationOutcome.permissionDenied);
    expect(it.registry.registrations, isEmpty);
  });

  test('إذن بلا رمز من المزوّد حالة مسمّاة كذلك', () async {
    // بناء بلا إعداد Firebase، أو جهاز بلا خدمات Google.
    final it = build(token: null);

    expect(await it.usecase(), PushRegistrationOutcome.noToken);
    expect(it.registry.registrations, isEmpty);
  });

  test('التسجيل يُطلب والجلسة قائمة', () async {
    // لو استُدعي بعد محو الرموز لردّ الخادم 401. الاختبار يقرأ حالة الجلسة
    // لحظة النداء نفسها، لا بعده.
    late bool sessionAtCallTime;
    final push = FakePushService();
    final auth = FakeAuthRepository();
    final registry = RecordingDeviceRegistry(
      onRegister: () => sessionAtCallTime = auth.signedIn,
    );

    await RegisterThisDevice(push: push, registry: registry, auth: auth)();

    expect(sessionAtCallTime, isTrue);
  });

  group('تدوير الرمز', () {
    test('رمز جديد من المزوّد يُعاد تسجيله', () async {
      // FCM يبدّل الرمز من تلقاء نفسه. بلا هذا يصمت الجهاز صمتاً تامّاً ولا
      // يشكو أحد: لا يفتقد المستخدم إشعاراً لم يعلم أنه أُرسل.
      final it = build();
      final subscription = it.usecase.followTokenRotations();

      it.push.tokenRefreshController.add('fcm-token-rotated');
      await Future<void>.delayed(Duration.zero);

      expect(it.registry.registrations.single.token, 'fcm-token-rotated');

      await subscription.cancel();
      await it.push.close();
    });

    test('تدوير بعد الخروج لا يعيد ربط الجهاز بمن خرج', () async {
      final it = build(signedIn: false);
      final subscription = it.usecase.followTokenRotations();

      it.push.tokenRefreshController.add('fcm-token-rotated');
      await Future<void>.delayed(Duration.zero);

      expect(it.registry.registrations, isEmpty);

      await subscription.cancel();
      await it.push.close();
    });

    test('فشل التسجيل عند التدوير لا يرمي من داخل المجرى', () async {
      // عطب يخرج من مستمع مجرى يصل إلى `FlutterError` بلا شاشة تعرضه.
      final it = build();
      it.registry.failWith = const TransportFailure(TransportProblem.offline);
      final subscription = it.usecase.followTokenRotations();

      it.push.tokenRefreshController.add('fcm-token-rotated');

      await expectLater(
        Future<void>.delayed(const Duration(milliseconds: 10)),
        completes,
      );

      await subscription.cancel();
      await it.push.close();
    });
  });
}
