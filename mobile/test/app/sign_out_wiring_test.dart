import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';

import '../support/fake_push.dart'
    show FakePushService, RecordingDeviceRegistry;
import '../support/fake_repositories.dart';
import '../support/pump_app.dart';

/// T716 من طرف التوصيل: زرّ الخروج في الشاشة يصل فعلاً إلى `SignOut`.
///
/// `test/domain/sign_out_test.dart` يحرس الترتيب داخل حالة الاستعمال، لكنه
/// يبنيها بيده — فيمرّ وهو لا يعرف إن كانت الشاشة تستدعيها أصلاً. هذا الاختبار
/// يضغط الزرّ الذي يضغطه المستخدم: بلا ذلك يبقى الجهاز مربوطاً بمن خرج، فيرى
/// من يدخل بعده على نفس الجوال إشعارات مزايداتٍ وفواتيرَ ليست له.
void main() {
  testWidgets('الخروج من الملف الشخصي يُنسي الجهاز قبل محو الرمزين', (
    tester,
  ) async {
    final journal = <String>[];
    final push = FakePushService();
    final registry = RecordingDeviceRegistry(
      onUnregister: () => journal.add('أُلغي تسجيل الجهاز'),
    );
    final auth = FakeAuthRepository(
      storedSession: true,
      onSignOut: () => journal.add('مُحي الرمزان'),
    );

    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(auth),
        profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
        pushServiceProvider.overrideWithValue(push),
        deviceRegistryProvider.overrideWithValue(registry),
      ],
      location: '/profile',
    );

    await tester.tap(find.byIcon(Icons.logout));
    await tester.pumpAndSettle();

    expect(registry.unregistrations, <String>['fcm-token-abcdef']);
    expect(push.tokenDeleted, isTrue);
    // الترتيب لا الحدثان: إلغاء التسجيل بعد محو الرمزين يُردّ بـ401.
    expect(journal, <String>['أُلغي تسجيل الجهاز', 'مُحي الرمزان']);
    expect(currentLocation(container), '/sign-in');
  });

  testWidgets('خروجٌ لم يُبلَّغ به الخادم لا يحتجز المستخدم على شاشته', (
    tester,
  ) async {
    // مَن يسلّم جهازه الآن لغيره لا يُقال له «حاول لاحقاً»: الرمز يُبطَل على أي
    // حال فينقطع الاستقبال، والجلسة تُمحى.
    final push = FakePushService();
    final registry = RecordingDeviceRegistry()
      ..failWith = const TransportFailure(TransportProblem.offline);

    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(
          FakeAuthRepository(storedSession: true),
        ),
        profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
        pushServiceProvider.overrideWithValue(push),
        deviceRegistryProvider.overrideWithValue(registry),
      ],
      location: '/profile',
    );

    await tester.tap(find.byIcon(Icons.logout));
    await tester.pumpAndSettle();

    expect(push.tokenDeleted, isTrue);
    expect(currentLocation(container), '/sign-in');
  });
}
