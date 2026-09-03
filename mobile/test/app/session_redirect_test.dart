import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';

import '../support/fake_repositories.dart';
import '../support/pump_app.dart';

/// T706 — «إعادة التوجيه عند 401».
///
/// المسار كاملاً: اعتراض المصادقة يرفع `SessionSignal.reportLost()` بعد 401 لم
/// ينفع معه التجديد، والموجّه ينقل المستخدم إلى الدخول أياً كانت الشاشة
/// المفتوحة. الاختبار يرفع الإشارة نفسها التي يرفعها الاعتراض، فما يُختبر هو
/// الطريق من الإشارة إلى الشاشة لا محاكاة له.
void main() {
  testWidgets('سقوط الجلسة ينقل من أي شاشة إلى الدخول ويقول لماذا', (
    tester,
  ) async {
    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(
          FakeAuthRepository(storedSession: true),
        ),
        profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
      ],
      location: '/profile',
    );
    expect(currentLocation(container), '/profile');

    container.read(sessionSignalProvider).reportLost();
    await tester.pumpAndSettle();

    expect(currentLocation(container), '/sign-in');
    // ومن قُذف إلى شاشة الدخول بلا سبب يظنّ التطبيق تعطّل.
    expect(find.text('انتهت جلستك. سجّل الدخول من جديد.'), findsOneWidget);
  });

  testWidgets('شاشة محمية بلا جلسة تعيد إلى الدخول', (tester) async {
    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
        profileRepositoryProvider.overrideWithValue(FakeProfileRepository()),
      ],
      location: '/profile',
    );

    expect(currentLocation(container), '/sign-in');
  });

  testWidgets('مستخدم داخل لا يرى شاشة الدخول', (tester) async {
    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(
          FakeAuthRepository(storedSession: true),
        ),
      ],
      location: '/sign-in',
    );

    expect(currentLocation(container), '/');
  });
}
