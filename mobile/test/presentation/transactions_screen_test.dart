import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/app/providers.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/money.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/ledger_movement.dart';
import 'package:haraj_mobile/domain/wallet/entities/wallet_balance.dart';

import '../support/fake_wallet_repository.dart';
import '../support/pump_localized.dart';

/// T712 — الكشف: كل حركة تقول ماذا حدث بالعربية، والترقيم لا ينتهي فجأة.
void main() {
  LedgerMovement movement({
    required String id,
    String description = 'إيداع تأمين',
    String amount = '2500.00',
    LedgerDirection direction = LedgerDirection.incoming,
    String? reference,
  }) => LedgerMovement(
    id: id,
    description: description,
    bucketLabel: 'تأمين متاح',
    money: Money(amount: amount, currency: 'SAR'),
    direction: direction,
    occurredAt: DateTime.utc(2026, 8, 30, 7, 30),
    reference: reference,
  );

  LedgerPage pageOf(
    List<LedgerMovement> movements, {
    bool hasMore = false,
    int page = 1,
    int total = 2,
  }) => LedgerPage(
    movements: movements,
    hasMore: hasMore,
    page: page,
    total: total,
  );

  testWidgets('كل حركة تعرض وصف الخادم ومبلغه كما وصل', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pages: <int, LedgerPage>{
              1: pageOf(<LedgerMovement>[
                movement(id: 'E1', reference: 'AUC-91'),
              ], total: 1),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('إيداع تأمين'), findsOneWidget);
    // المبلغ كما وصل: بلا فاصلة آلاف ولا تقريب ولا رمز عملة مترجم.
    expect(find.text('2500.00 SAR'), findsOneWidget);
    expect(find.textContaining('AUC-91'), findsOneWidget);
    expect(find.textContaining('تأمين متاح'), findsOneWidget);
  });

  testWidgets('الاتجاه يظهر بإشارته كما قاله الخادم', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pages: <int, LedgerPage>{
              1: pageOf(<LedgerMovement>[
                movement(id: 'E1'),
                movement(
                  id: 'E2',
                  description: 'حجز تأمين لمزاد',
                  direction: LedgerDirection.outgoing,
                ),
              ]),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('+'), findsOneWidget);
    expect(find.text('−'), findsOneWidget);
  });

  testWidgets('كشف فارغ يقول ذلك ولا يترك الشاشة تدور', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pages: <int, LedgerPage>{
              1: pageOf(const <LedgerMovement>[], total: 0),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('لا حركات.'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('فشل الخادم يعرض رسالته العربية كما جاءت', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pageFailures: <int, Failure>{
              1: const ApiFailure(
                code: 'TOKEN_EXPIRED',
                message: 'انتهت الجلسة، سجّل الدخول من جديد.',
              ),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.text('انتهت الجلسة، سجّل الدخول من جديد.'), findsOneWidget);
  });

  testWidgets('الترقيم يضيف الصفحة التالية ولا يستبدل ما عُرض', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pages: <int, LedgerPage>{
              1: pageOf(
                <LedgerMovement>[
                  movement(id: 'E1', description: 'إيداع تأمين'),
                ],
                hasMore: true,
                total: 2,
              ),
              2: pageOf(
                <LedgerMovement>[
                  movement(id: 'E2', description: 'ردّ حجز بعد انتهاء المزاد'),
                ],
                page: 2,
                total: 2,
              ),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('تحميل المزيد'));
    await tester.pumpAndSettle();

    expect(find.text('إيداع تأمين'), findsOneWidget);
    expect(find.text('ردّ حجز بعد انتهاء المزاد'), findsOneWidget);
    expect(find.text('تحميل المزيد'), findsNothing);
  });

  testWidgets('فشل الصفحة التالية لا يمحو ما وصل فعلاً', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            pages: <int, LedgerPage>{
              1: pageOf(<LedgerMovement>[movement(id: 'E1')], hasMore: true),
            },
            pageFailures: <int, Failure>{
              2: const TransportFailure(TransportProblem.offline),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('تحميل المزيد'));
    await tester.pumpAndSettle();

    expect(find.text('إيداع تأمين'), findsOneWidget);
    expect(find.text('لا يوجد اتصال بالإنترنت.'), findsOneWidget);
  });

  testWidgets('الترشيح يصل من المسار إلى الخادم', (tester) async {
    final repository = FakeWalletRepository(
      pages: <int, LedgerPage>{
        1: pageOf(<LedgerMovement>[movement(id: 'E1')], total: 1),
      },
    );

    await pumpRoute(
      tester,
      '/wallet/transactions?bucket=${WalletBucketKind.insuranceHeld.name}',
      overrides: [walletRepositoryProvider.overrideWithValue(repository)],
    );
    await tester.pumpAndSettle();

    expect(repository.askedBuckets.single, WalletBucketKind.insuranceHeld);
    expect(find.text('مرشَّح على دلو واحد.'), findsOneWidget);
  });

  testWidgets('بيانات محفوظة تظهر بعلامة «آخر تحديث»', (tester) async {
    await pumpRoute(
      tester,
      '/wallet/transactions',
      overrides: [
        walletRepositoryProvider.overrideWithValue(
          FakeWalletRepository(
            origin: DataOrigin.cache,
            pages: <int, LedgerPage>{
              1: pageOf(<LedgerMovement>[movement(id: 'E1')], total: 1),
            },
          ),
        ),
      ],
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('بيانات محفوظة'), findsOneWidget);
  });
}
