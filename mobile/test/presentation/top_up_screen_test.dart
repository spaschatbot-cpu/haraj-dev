import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/wallet/entities/top_up.dart';
import 'package:haraj_mobile/domain/wallet/gateways/checkout_launcher.dart';

import '../support/fake_wallet_repository.dart';
import '../support/pump_localized.dart';

/// T713 — العودة من البوابة: ناجحة، ملغاة، ومنقطعة.
///
/// الاختبارات الثلاثة تشترك في شيء واحد: **لا واحد منها يمرّر رابط عودة**.
/// الشاشة لا تقبل واحداً أصلاً؛ تسأل الخادم بمرجع النيّة، فما يعود في الرابط
/// لا يمكن أن يغيّر ما تعرضه (ولا رصيداً).
void main() {
  const intentPending = TopUp(
    reference: 'TOP-1',
    money: Money(amount: '5000.00', currency: 'SAR'),
    checkoutUrl: 'https://pay.example.invalid/checkout/TOP-1',
    status: TopUpStatus.pending,
    statusLabel: 'بانتظار الدفع',
  );

  const intentSucceeded = TopUp(
    reference: 'TOP-1',
    money: Money(amount: '5000.00', currency: 'SAR'),
    checkoutUrl: 'https://pay.example.invalid/checkout/TOP-1',
    status: TopUpStatus.succeeded,
    statusLabel: 'تمّ الشحن',
  );

  const intentCancelled = TopUp(
    reference: 'TOP-1',
    money: Money(amount: '5000.00', currency: 'SAR'),
    checkoutUrl: 'https://pay.example.invalid/checkout/TOP-1',
    status: TopUpStatus.cancelled,
    statusLabel: 'أُلغيت العملية',
  );

  Future<void> pumpTopUp(
    WidgetTester tester, {
    required FakeWalletRepository repository,
    _FakeLauncher? launcher,
  }) async {
    await pumpRoute(
      tester,
      '/wallet/topup',
      overrides: [
        walletRepositoryProvider.overrideWithValue(repository),
        checkoutLauncherProvider.overrideWithValue(launcher ?? _FakeLauncher()),
      ],
    );
    await tester.pumpAndSettle();
  }

  testWidgets('لا خانة مبلغ — الخادم يحدّده', (tester) async {
    await pumpTopUp(
      tester,
      repository: FakeWalletRepository(startedTopUp: intentPending),
    );

    expect(find.byType(TextField), findsNothing);
    expect(find.textContaining('المبلغ يحدّده النظام'), findsOneWidget);
  });

  testWidgets('البدء يكتب النيّة ثم يفتح البوابة بعنوان الخادم', (
    tester,
  ) async {
    final launcher = _FakeLauncher();
    await pumpTopUp(
      tester,
      repository: FakeWalletRepository(startedTopUp: intentPending),
      launcher: launcher,
    );

    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    expect(launcher.opened, <String>[
      'https://pay.example.invalid/checkout/TOP-1',
    ]);
    expect(find.text('بانتظار الدفع'), findsOneWidget);
    expect(find.text('5000.00 SAR'), findsOneWidget);
    expect(find.textContaining('TOP-1'), findsOneWidget);
  });

  testWidgets('عودة ناجحة: الحالة من الخادم بمرجع النيّة', (tester) async {
    final repository = FakeWalletRepository(
      startedTopUp: intentPending,
      topUpStatuses: const <TopUp>[intentSucceeded],
    );

    await pumpTopUp(tester, repository: repository);
    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('تحقّق من حالة الشحن'));
    await tester.pumpAndSettle();

    expect(repository.askedReferences, <String>['TOP-1']);
    expect(find.text('تمّ الشحن'), findsOneWidget);
    expect(find.text('بانتظار تأكيد البوابة للخادم.'), findsNothing);
  });

  testWidgets('عودة ملغاة: كلام الخادم كما هو، بلا تأويل', (tester) async {
    final repository = FakeWalletRepository(
      startedTopUp: intentPending,
      topUpStatuses: const <TopUp>[intentCancelled],
    );

    await pumpTopUp(tester, repository: repository);
    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('تحقّق من حالة الشحن'));
    await tester.pumpAndSettle();

    expect(find.text('أُلغيت العملية'), findsOneWidget);
    expect(find.text('تمّ الشحن'), findsNothing);
  });

  testWidgets('عودة منقطعة: انتظار معلن، لا نجاح مفترض', (tester) async {
    final repository = FakeWalletRepository(
      startedTopUp: intentPending,
      readTopUpFailure: const TransportFailure(TransportProblem.offline),
    );

    await pumpTopUp(tester, repository: repository);
    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('تحقّق من حالة الشحن'));
    await tester.pumpAndSettle();

    expect(find.text('لا يوجد اتصال بالإنترنت.'), findsOneWidget);
    // النيّة تبقى بحالتها الأخيرة المعروفة، والسؤال يبقى ممكناً.
    expect(find.text('بانتظار الدفع'), findsOneWidget);
    expect(find.text('تحقّق من حالة الشحن'), findsOneWidget);
  });

  testWidgets('تعذّر فتح البوابة لا يمحو النيّة', (tester) async {
    final launcher = _FakeLauncher(succeeds: false);
    await pumpTopUp(
      tester,
      repository: FakeWalletRepository(startedTopUp: intentPending),
      launcher: launcher,
    );

    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    // النيّة مكتوبة عند الخادم؛ محوها هنا يترك العميل بلا مرجع يسأل به.
    expect(find.textContaining('TOP-1'), findsOneWidget);
    expect(find.textContaining('تعذّر فتح صفحة الدفع'), findsOneWidget);

    await tester.tap(find.text('افتح صفحة الدفع'));
    await tester.pumpAndSettle();

    // المحاولة الثانية بالمرجع نفسه: لا نيّة ثانية معلَّقة عند الخادم.
    expect(launcher.opened, hasLength(2));
  });

  testWidgets('فشل البدء يعرض رسالة الخادم كما جاءت', (tester) async {
    await pumpTopUp(
      tester,
      repository: FakeWalletRepository(
        startTopUpFailure: const ApiFailure(
          code: 'TOPUP_DISABLED',
          message: 'الشحن بالبطاقة غير مفعّل حالياً.',
        ),
      ),
    );

    await tester.tap(find.text('ابدأ الشحن'));
    await tester.pumpAndSettle();

    expect(find.text('الشحن بالبطاقة غير مفعّل حالياً.'), findsOneWidget);
  });
}

/// بوابة مزيَّفة: تسجّل ما فُتح، ولا تفتح شيئاً.
final class _FakeLauncher implements CheckoutLauncher {
  _FakeLauncher({this.succeeds = true});

  final bool succeeds;
  final List<String> opened = <String>[];

  @override
  Future<bool> open(String url) async {
    opened.add(url);
    return succeeds;
  }
}
