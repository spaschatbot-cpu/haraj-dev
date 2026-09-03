import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/models/top_up_intent.dart';
import 'package:haraj_mobile/data/api/generated/models/top_up_intent_status.dart';
import 'package:haraj_mobile/data/wallet/wallet_repository_impl.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/wallet/entities/top_up.dart';

import '../support/fake_wallet_api.dart';
import '../support/memory_response_cache.dart';

/// T713 — الشحن بالبطاقة: المبلغ من الخادم، والنتيجة من الخادم.
void main() {
  const pending = TopUpIntent(
    reference: 'TOP-1',
    amount: '5000.00',
    currency: 'SAR',
    redirectUrl: 'https://pay.example.invalid/checkout/TOP-1',
    status: TopUpIntentStatus.pending,
    statusLabel: 'بانتظار الدفع',
  );

  const succeeded = TopUpIntent(
    reference: 'TOP-1',
    amount: '5000.00',
    currency: 'SAR',
    redirectUrl: 'https://pay.example.invalid/checkout/TOP-1',
    status: TopUpIntentStatus.succeeded,
    statusLabel: 'تمّ الشحن',
  );

  test('البدء لا يرسل مبلغاً ولا مفتاح مبلغ', () async {
    final api = FakeWalletApi(topUpIntent: pending);
    final repository = WalletRepositoryImpl(
      api: api,
      cache: MemoryResponseCache(),
    );

    final intent = await repository.startTopUp();

    // المبلغ يحدّده الخادم، والخلفية ترفض طلباً يسمّي مبلغه.
    expect(api.lastTopUpRequest?.preset, isNull);
    expect(intent.money.amount, '5000.00');
    expect(intent.checkoutUrl, 'https://pay.example.invalid/checkout/TOP-1');
    expect(intent.statusLabel, 'بانتظار الدفع');
    expect(intent.isPending, isTrue);
  });

  test('الحالة تُقرأ من نقطة الخادم بمرجع النيّة', () async {
    final api = FakeWalletApi(
      topUpIntent: pending,
      topUpStatuses: const <TopUpIntent>[succeeded],
    );
    final repository = WalletRepositoryImpl(
      api: api,
      cache: MemoryResponseCache(),
    );

    final settled = await repository.readTopUp('TOP-1');

    expect(api.askedReferences, <String>['TOP-1']);
    expect(settled.hasSucceeded, isTrue);
    // الوصف من الخادم: لا خريطة حالات في التطبيق.
    expect(settled.statusLabel, 'تمّ الشحن');
  });

  test('حالة الشحن لا تُحفظ في الكاش', () async {
    final cache = MemoryResponseCache();
    final repository = WalletRepositoryImpl(
      api: FakeWalletApi(topUpStatuses: const <TopUpIntent>[succeeded]),
      cache: cache,
    );

    await repository.readTopUp('TOP-1');

    // «تمّ الشحن» محفوظة تُقرأ بعد ساعة على أنها الآن.
    expect(cache.writeCount, 0);
  });

  test('انقطاع أثناء السؤال عطبٌ يُرمى، لا نجاح ولا فشل في الدفع', () async {
    final repository = WalletRepositoryImpl(
      api: FakeWalletApi(topUpStatuses: const <TopUpIntent>[succeeded])
        ..failWith = DioException(
          requestOptions: RequestOptions(path: '/api/v1/wallet/topup-intents'),
          type: DioExceptionType.connectionError,
          error: const SocketException('offline'),
        ),
      cache: MemoryResponseCache(),
    );

    await expectLater(
      repository.readTopUp('TOP-1'),
      throwsA(isA<TransportFailure>()),
    );
  });

  test('حالة لم يرها هذا الإصدار تصل بوصفها العربي', () async {
    final repository = WalletRepositoryImpl(
      api: FakeWalletApi(
        topUpStatuses: const <TopUpIntent>[
          TopUpIntent(
            reference: 'TOP-1',
            amount: '5000.00',
            currency: 'SAR',
            redirectUrl: 'https://pay.example.invalid/checkout/TOP-1',
            status: TopUpIntentStatus.$unknown,
            statusLabel: 'قيد المراجعة لدى البنك',
          ),
        ],
      ),
      cache: MemoryResponseCache(),
    );

    final intent = await repository.readTopUp('TOP-1');

    expect(intent.status, TopUpStatus.unknown);
    // ما لا يعرفه التطبيق برمجياً يقرؤه المستخدم بكلام الخادم.
    expect(intent.statusLabel, 'قيد المراجعة لدى البنك');
    expect(intent.hasSucceeded, isFalse);
  });
}
