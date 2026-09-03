import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';

import '../support/fake_repositories.dart';
import '../support/fake_wallet_repository.dart';
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

  testWidgets('سقوط الجلسة على المحفظة ينقل إلى الدخول لا يترك دوّامة', (
    tester,
  ) async {
    // الشاشة المفتوحة عند سقوط الجلسة نادراً ما تكون الملف الشخصي: إشعار شحنٍ
    // يفتح المحفظة، وإشعار مزايدة يفتح المزايدات. حراسةُ `/profile` وحدها تترك
    // صاحب المحفظة يشاهد فشل شبكة بلا مخرج ولا سبب.
    final container = await pumpApp(
      tester,
      overrides: [
        authRepositoryProvider.overrideWithValue(
          FakeAuthRepository(storedSession: true),
        ),
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            balanceFailure: const TransportFailure(TransportProblem.offline),
          ),
        ),
      ],
      location: '/wallet',
    );
    expect(currentLocation(container), '/wallet');

    container.read(sessionSignalProvider).reportLost();
    await tester.pumpAndSettle();

    expect(currentLocation(container), '/sign-in');
    expect(find.text('انتهت جلستك. سجّل الدخول من جديد.'), findsOneWidget);
  });

  testWidgets('كل شاشة تحتاج جلسة تُغلق أمام من لا جلسة له', (tester) async {
    // رابط عميق من إشعار قد يصل إلى جهاز خرج صاحبه منه.
    for (final location in const <String>[
      '/profile',
      '/profile/company',
      '/wallet',
      '/wallet/topup',
      '/wallet/transactions',
      '/bids',
      '/vehicles/340/bid',
      '/my-activity',
    ]) {
      final container = await pumpApp(
        tester,
        overrides: [
          authRepositoryProvider.overrideWithValue(FakeAuthRepository()),
        ],
        location: location,
      );

      expect(
        currentLocation(container),
        '/sign-in',
        reason: '«$location» فُتح بلا جلسة',
      );
    }
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
