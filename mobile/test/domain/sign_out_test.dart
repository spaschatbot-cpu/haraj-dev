import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/domain/auth/usecases/sign_out.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/notifications/usecases/forget_this_device.dart';

import '../support/fake_push.dart';

/// T716 — «وإلغاء التسجيل عند الخروج».
void main() {
  ({SignOut usecase, FakePushService push, RecordingDeviceRegistry registry})
  build({List<String>? order}) {
    final push = FakePushService();
    final registry = RecordingDeviceRegistry(
      onUnregister: () => order?.add('unregister'),
    );
    final auth = FakeAuthRepository(
      onSignOut: () => order?.add('clear-tokens'),
    );
    return (
      usecase: SignOut(
        auth: auth,
        forgetDevice: ForgetThisDevice(push: push, registry: registry),
      ),
      push: push,
      registry: registry,
    );
  }

  test('الخروج يُبلغ الخادم ويُبطل الرمز', () async {
    final it = build();

    expect(await it.usecase(), ForgetDeviceOutcome.unregistered);
    expect(it.registry.unregistrations, ['fcm-token-abcdef']);
    expect(it.push.tokenDeleted, isTrue);
  });

  test('إلغاء التسجيل يسبق محو الرموز — والترتيب هو التاسك كله', () async {
    // بعد محو الرمزين لا شيء يثبت للخادم من صاحب الجهاز، فيردّ 401 ويبقى
    // الجهاز مربوطاً بمن خرج — ومن يدخل بعده على نفس الجوال يرى إشعارات
    // مزايدات ليست له.
    final order = <String>[];
    await build(order: order).usecase();

    expect(order, ['unregister', 'clear-tokens']);
  });

  test('انقطاع الشبكة لا يحتجز المستخدم داخل حسابه', () async {
    // من يسلّم جوّاله لغيره الآن لا يُقال له «حاول لاحقاً». الرمز يُبطل على أي
    // حال فينقطع الاستقبال، والحالة تخرج باسمها لا بوصفها نجاحاً.
    final it = build();
    it.registry.failWith = const TransportFailure(TransportProblem.offline);

    expect(
      await it.usecase(),
      ForgetDeviceOutcome.tokenDeletedButServerNotTold,
    );
    expect(it.push.tokenDeleted, isTrue);
  });

  test('جهاز بلا رمز أصلاً حالة مسمّاة', () async {
    final push = FakePushService(token: null);
    final registry = RecordingDeviceRegistry();
    final usecase = SignOut(
      auth: FakeAuthRepository(),
      forgetDevice: ForgetThisDevice(push: push, registry: registry),
    );

    expect(await usecase(), ForgetDeviceOutcome.nothingToForget);
    expect(registry.unregistrations, isEmpty);
  });

  test('الخروج يمحو الجلسة مهما كانت نتيجة إلغاء التسجيل', () async {
    final push = FakePushService();
    final registry = RecordingDeviceRegistry()
      ..failWith = const TransportFailure(TransportProblem.offline);
    final auth = FakeAuthRepository();

    await SignOut(
      auth: auth,
      forgetDevice: ForgetThisDevice(push: push, registry: registry),
    )();

    expect(auth.signedIn, isFalse);
  });
}
