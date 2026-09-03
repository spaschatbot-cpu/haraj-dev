import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/models/ledger_entry.dart';
import 'package:haraj_mobile/data/api/generated/models/ledger_entry_direction.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_ledger_entry_list.dart';
import 'package:haraj_mobile/data/api/generated/models/wallet_bucket_kind.dart'
    as api;
import 'package:haraj_mobile/data/local/cache/response_cache.dart';
import 'package:haraj_mobile/data/wallet/wallet_repository_impl.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/ledger_movement.dart';
import 'package:haraj_mobile/domain/wallet/entities/wallet_balance.dart';

import '../support/fake_wallet_api.dart';
import '../support/memory_response_cache.dart';

/// T712 — كشف الحركات: ما يصل من الخادم يصل كما هو، والترشيح يذهب إليه.
void main() {
  final fetchedAt = DateTime.utc(2026, 9, 1, 10);

  LedgerEntry entry({
    required String id,
    String description = 'إيداع تأمين',
    String amount = '2500.00',
    LedgerEntryDirection direction = LedgerEntryDirection.valueIn,
    String? reference,
  }) => LedgerEntry(
    id: id,
    description: description,
    bucketLabel: 'تأمين متاح',
    bucket: api.WalletBucketKind.insuranceFree,
    amount: amount,
    currency: 'SAR',
    direction: direction,
    occurredAt: DateTime.utc(2026, 8, 30, 7, 30),
    reference: reference,
  );

  PaginatedLedgerEntryList page({
    required List<LedgerEntry> results,
    String? next,
    int count = 2,
  }) => PaginatedLedgerEntryList(count: count, next: next, results: results);

  WalletRepositoryImpl buildRepository(
    FakeWalletApi api,
    ResponseCache cache,
  ) => WalletRepositoryImpl(api: api, cache: cache, clock: () => fetchedAt);

  test('الحركة تصل بوصفها العربي ومبلغها نصّاً كما أرسله الخادم', () async {
    final repository = buildRepository(
      FakeWalletApi(
        pages: <int, PaginatedLedgerEntryList>{
          1: page(
            results: <LedgerEntry>[entry(id: 'E1', reference: 'AUC-91')],
          ),
        },
      ),
      MemoryResponseCache(),
    );

    final movement =
        (await repository.loadTransactions()).value.movements.single;

    expect(movement.description, 'إيداع تأمين');
    expect(movement.money.amount, '2500.00');
    expect(movement.money.currency, 'SAR');
    expect(movement.bucketLabel, 'تأمين متاح');
    expect(movement.reference, 'AUC-91');
  });

  test('الاتجاه من الخادم لا من إشارة المبلغ', () async {
    final repository = buildRepository(
      FakeWalletApi(
        pages: <int, PaginatedLedgerEntryList>{
          1: page(
            results: <LedgerEntry>[
              entry(id: 'E1'),
              // نفس المبلغ الموجب تماماً، واتجاه مضادّ: لو اشتُقّ الاتجاه من
              // شكل الرقم لظهر السطران بإشارة واحدة.
              entry(id: 'E2', direction: LedgerEntryDirection.out),
            ],
          ),
        },
      ),
      MemoryResponseCache(),
    );

    final movements = (await repository.loadTransactions()).value.movements;

    expect(movements.first.direction, LedgerDirection.incoming);
    expect(movements.last.direction, LedgerDirection.outgoing);
    expect(movements.first.money.amount, movements.last.money.amount);
  });

  test('اتجاه لم نره لا يُسقط الكشف', () async {
    final repository = buildRepository(
      FakeWalletApi(
        pages: <int, PaginatedLedgerEntryList>{
          1: page(
            results: <LedgerEntry>[
              entry(id: 'E1', direction: LedgerEntryDirection.$unknown),
            ],
          ),
        },
      ),
      MemoryResponseCache(),
    );

    final movement =
        (await repository.loadTransactions()).value.movements.single;

    expect(movement.direction, LedgerDirection.unknown);
    expect(movement.money.amount, '2500.00');
  });

  test('الترشيح على دلو يُرسَل إلى الخادم — لا ترشيح في التطبيق', () async {
    final walletApi = FakeWalletApi(
      pages: <int, PaginatedLedgerEntryList>{
        1: page(results: <LedgerEntry>[entry(id: 'E1')]),
      },
    );
    final repository = buildRepository(walletApi, MemoryResponseCache());

    await repository.loadTransactions(bucket: WalletBucketKind.insuranceHeld);

    expect(walletApi.askedBuckets.single, api.WalletBucketKind.insuranceHeld);
  });

  test('«بقي مزيد» من الخادم لا من طول القائمة', () async {
    final repository = buildRepository(
      FakeWalletApi(
        pages: <int, PaginatedLedgerEntryList>{
          1: page(
            results: <LedgerEntry>[entry(id: 'E1')],
            next:
                'https://api.example.invalid/api/v1/wallet/transactions?page=2',
          ),
          2: page(results: <LedgerEntry>[entry(id: 'E2')]),
        },
      ),
      MemoryResponseCache(),
    );

    expect((await repository.loadTransactions()).value.hasMore, isTrue);
    expect((await repository.loadTransactions(page: 2)).value.hasMore, isFalse);
  });

  test('كشف مرشَّح يُحفظ بمفتاح خاص به لا فوق الكشف الكامل', () async {
    final cache = MemoryResponseCache();
    final repository = buildRepository(
      FakeWalletApi(
        pages: <int, PaginatedLedgerEntryList>{
          1: page(results: <LedgerEntry>[entry(id: 'E1')]),
        },
      ),
      cache,
    );

    await repository.loadTransactions(bucket: WalletBucketKind.insuranceHeld);

    // لو تشارك الاثنان مفتاحاً لعُرض المرشَّح لاحقاً بلا اتصال على أنه الكشف
    // الكامل — كشف بثقوب لا يعرف قارئه مكانها.
    expect(await cache.read(CacheKeys.walletTransactions()), isNull);
    expect(
      await cache.read(
        CacheKeys.walletTransactions(
          bucket: WalletBucketKind.insuranceHeld.name,
        ),
      ),
      isNotNull,
    );
  });

  test('انقطاع الشبكة يعرض الصفحة الأولى المحفوظة بطابعها', () async {
    final cache = MemoryResponseCache();
    final api = FakeWalletApi(
      pages: <int, PaginatedLedgerEntryList>{
        1: page(results: <LedgerEntry>[entry(id: 'E1')]),
      },
    );
    final repository = buildRepository(api, cache);

    await repository.loadTransactions();
    api.failWith = _offlineException();

    final snapshot = await repository.loadTransactions();

    expect(snapshot.origin, DataOrigin.cache);
    expect(snapshot.fetchedAt, fetchedAt);
    expect(snapshot.value.movements.single.description, 'إيداع تأمين');
  });

  test('صفحة تالية بلا شبكة تفشل ولا تعيد أول الكشف', () async {
    final cache = MemoryResponseCache();
    final api = FakeWalletApi(
      pages: <int, PaginatedLedgerEntryList>{
        1: page(
          results: <LedgerEntry>[entry(id: 'E1')],
          next: 'next',
        ),
      },
    );
    final repository = buildRepository(api, cache);

    await repository.loadTransactions();
    api.failWith = _offlineException();

    // الكاش يحمل الصفحة الأولى وحدها؛ إرجاعه هنا يعرض أول الكشف مكان آخره.
    await expectLater(
      repository.loadTransactions(page: 2),
      throwsA(isA<TransportFailure>()),
    );
  });
}

DioException _offlineException() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/wallet/transactions'),
  type: DioExceptionType.connectionError,
  error: const SocketException('offline'),
);
