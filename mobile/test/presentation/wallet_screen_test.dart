import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/ledger_movement.dart';
import 'package:haraj_mobile/domain/wallet/entities/wallet_balance.dart';

import '../support/fake_wallet_repository.dart';
import '../support/pump_localized.dart';

/// T711 — المحفظة: ثلاثة أرقام لا واحد، ولكل رقم بابٌ على قيوده.
void main() {
  final balance = WalletBalance(
    asOf: DateTime.utc(2026, 9, 1, 7),
    buckets: const <WalletBucket>[
      WalletBucket(
        kind: WalletBucketKind.insuranceFree,
        label: 'تأمين متاح',
        money: Money(amount: '10000.00', currency: 'SAR'),
        holds: <WalletHold>[],
      ),
      WalletBucket(
        kind: WalletBucketKind.insuranceHeld,
        label: 'محجوز لمزادات',
        money: Money(amount: '2500.00', currency: 'SAR'),
        holds: <WalletHold>[
          WalletHold(
            reference: 'AUC-91',
            reason: 'محجوز لمزاد الرياض ١٢',
            money: Money(amount: '2500.00', currency: 'SAR'),
          ),
        ],
      ),
      WalletBucket(
        kind: WalletBucketKind.insuranceLocked,
        label: 'مقفول على مستحقات',
        money: Money(amount: '500.00', currency: 'SAR'),
        holds: <WalletHold>[],
      ),
    ],
  );

  Future<void> pumpWallet(
    WidgetTester tester, {
    required FakeWalletRepository repository,
  }) async {
    await pumpRoute(
      tester,
      '/wallet',
      overrides: [walletRepositoryProvider.overrideWithValue(repository)],
    );
    await tester.pumpAndSettle();
  }

  testWidgets('كل دلو بمبلغه واسمه من الخادم', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(balance: balance),
    );

    expect(find.text('تأمين متاح'), findsOneWidget);
    expect(find.text('10000.00 SAR'), findsOneWidget);
    expect(find.text('محجوز لمزادات'), findsOneWidget);
    expect(find.text('مقفول على مستحقات'), findsOneWidget);
    expect(find.text('500.00 SAR'), findsOneWidget);
  });

  testWidgets('لا رقم واحد يجمع الدلاء — معيار H4', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(balance: balance),
    );

    // 10000 + 2500 + 500. رقم واحد يشمل المحجوز هو ما جعل عميل v1 يزايد على
    // فلوس مربوطة بمزاد آخر.
    for (final sum in <String>[
      '13000.00 SAR',
      '13000.00',
      '12500.00 SAR',
      '10500.00 SAR',
    ]) {
      expect(find.text(sum), findsNothing, reason: 'مجموع محسوب في الشاشة');
    }
  });

  testWidgets('كل حجز يظهر بسببه ومرجعه', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(balance: balance),
    );

    expect(find.text('لماذا هذا المبلغ محجوز'), findsOneWidget);
    expect(find.text('محجوز لمزاد الرياض ١٢'), findsOneWidget);
    expect(find.textContaining('AUC-91'), findsOneWidget);
  });

  testWidgets('الرقم يُفتح على الحركات التي تفسّره — المادة ١-٦', (
    tester,
  ) async {
    final repository = FakeWalletRepository(
      balance: balance,
      pages: <int, LedgerPage>{
        1: const LedgerPage(
          movements: <LedgerMovement>[],
          hasMore: false,
          page: 1,
          total: 0,
        ),
      },
    );

    await pumpWallet(tester, repository: repository);

    // الدلو المحجوز هو الثاني في الترتيب.
    await tester.tap(find.text('الحركات التي تفسّر هذا الرقم').at(1));
    await tester.pumpAndSettle();

    expect(find.text('كشف الحركات'), findsOneWidget);
    // فُتح الكشف **مرشَّحاً على هذا الدلو**، لا على كل الحركات.
    expect(repository.askedBuckets.single, WalletBucketKind.insuranceHeld);
  });

  testWidgets('دلو لا يعرفه هذا الإصدار يُعرض بلا مدخل كشف', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(
        balance: WalletBalance(
          asOf: DateTime.utc(2026, 9, 1, 7),
          buckets: const <WalletBucket>[
            WalletBucket(
              kind: WalletBucketKind.unknown,
              label: 'دلو جديد من الخادم',
              money: Money(amount: '1.00', currency: 'SAR'),
              holds: <WalletHold>[],
            ),
          ],
        ),
      ),
    );

    // القيمة الجديدة لا تُسقط الشاشة (المادة ٢-٣)، ولا تفتح كشفاً غير مرشَّح
    // يبدو كأنه تفسير لرقمها.
    expect(find.text('دلو جديد من الخادم'), findsOneWidget);
    expect(find.text('1.00 SAR'), findsOneWidget);
    expect(find.text('الحركات التي تفسّر هذا الرقم'), findsNothing);
  });

  testWidgets('فشل الخادم يعرض رسالته ولا يعرض رصيداً صفرياً', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(
        balanceFailure: const ApiFailure(
          code: 'TOKEN_EXPIRED',
          message: 'انتهت الجلسة، سجّل الدخول من جديد.',
        ),
      ),
    );

    expect(find.text('انتهت الجلسة، سجّل الدخول من جديد.'), findsOneWidget);
    expect(find.textContaining('0.00'), findsNothing);
  });

  testWidgets('بيانات محفوظة تظهر بعلامة «آخر تحديث»', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(
        balance: balance,
        origin: DataOrigin.cache,
      ),
    );

    expect(find.textContaining('بيانات محفوظة'), findsOneWidget);
  });

  testWidgets('لحظة قراءة الدفتر تُعرض بالتوقيت السعودي', (tester) async {
    await pumpWallet(
      tester,
      repository: FakeWalletRepository(balance: balance),
    );

    // 07:00 بتوقيت UTC هي 10:00 في السعودية — التحويل في saudi_time وحدها.
    expect(find.textContaining('10:00'), findsOneWidget);
  });
}
