import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:haraj_mobile/data/api/generated/clients/wallet_api.dart';
import 'package:haraj_mobile/data/api/generated/models/wallet.dart';
import 'package:haraj_mobile/data/api/generated/models/wallet_bucket.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/wallet_bucket_kind.dart'
    as api;
import 'package:haraj_mobile/data/api/generated/models/wallet_hold.dart' as api;
import 'package:haraj_mobile/data/local/cache/response_cache.dart';
import 'package:haraj_mobile/data/wallet/wallet_repository_impl.dart';
import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/wallet_balance.dart';

import '../support/fake_wallet_api.dart';
import '../support/memory_response_cache.dart';

/// T704 — «آخر استجابة معروفة لكل شاشة، مع طابع آخر تحديث» (معيار H5).
void main() {
  final asOf = DateTime.utc(2026, 9, 1, 10);
  final fetchedAt = DateTime.utc(2026, 9, 1, 10, 0, 5);

  final serverWallet = Wallet(
    asOf: asOf,
    buckets: <api.WalletBucket>[
      const api.WalletBucket(
        kind: api.WalletBucketKind.insuranceFree,
        label: 'تأمين متاح',
        amount: '10000.00',
        currency: 'SAR',
      ),
      const api.WalletBucket(
        kind: api.WalletBucketKind.insuranceHeld,
        label: 'محجوز لمزايدة',
        amount: '2500.00',
        currency: 'SAR',
        holds: <api.WalletHold>[
          api.WalletHold(
            reference: 'AUC-91',
            reason: 'محجوز لمزاد الرياض ١٢',
            amount: '2500.00',
            currency: 'SAR',
          ),
        ],
      ),
    ],
  );

  WalletRepositoryImpl buildRepository(WalletApi api, ResponseCache cache) =>
      WalletRepositoryImpl(api: api, cache: cache, clock: () => fetchedAt);

  test('النجاح يرجع نسخة طازجة ويكتبها في الكاش', () async {
    final cache = MemoryResponseCache();
    final repository = buildRepository(
      FakeWalletApi(wallet: serverWallet),
      cache,
    );

    final snapshot = await repository.loadBalance();

    expect(snapshot.origin, DataOrigin.network);
    expect(snapshot.fetchedAt, fetchedAt);
    expect(cache.writeCount, 1);
    expect(await cache.read(CacheKeys.wallet), isNotNull);
  });

  test('المبالغ تبقى نصّاً كما وصلت — بلا تنسيق ولا تحويل', () async {
    final repository = buildRepository(
      FakeWalletApi(wallet: serverWallet),
      MemoryResponseCache(),
    );

    final buckets = (await repository.loadBalance()).value.buckets;

    expect(buckets.first.money.amount, '10000.00');
    expect(buckets.first.money.currency, 'SAR');
    // ولا مجموع: الفيز 008 يمنع جمع الدلاء في رقم واحد.
    expect(buckets.map((bucket) => bucket.money.amount), <String>[
      '10000.00',
      '2500.00',
    ]);
  });

  test('كل حجز يصل بسببه ومرجعه — لا فلوس محجوزة «كده»', () async {
    final repository = buildRepository(
      FakeWalletApi(wallet: serverWallet),
      MemoryResponseCache(),
    );

    final held = (await repository.loadBalance()).value.buckets.firstWhere(
      (bucket) => bucket.kind == WalletBucketKind.insuranceHeld,
    );

    expect(held.holds, hasLength(1));
    expect(held.holds.single.reference, 'AUC-91');
    expect(held.holds.single.reason, 'محجوز لمزاد الرياض ١٢');
  });

  test('انقطاع الشبكة بعد نجاح سابق يعرض المحفوظ بطابعه', () async {
    final cache = MemoryResponseCache();
    final api = FakeWalletApi(wallet: serverWallet);
    final repository = buildRepository(api, cache);

    await repository.loadBalance();
    api.failWith = _offlineException();

    final snapshot = await repository.loadBalance();

    expect(snapshot.origin, DataOrigin.cache);
    expect(snapshot.isStale, isTrue);
    // الطابع لحظة **الجلب**، لا لحظة القراءة من الكاش — وإلا كذبت العلامة.
    expect(snapshot.fetchedAt, fetchedAt);
    expect(snapshot.value.buckets.first.money.amount, '10000.00');
    // الحقول المتداخلة تنجو من دورة الحفظ والقراءة: خريطة `toJson()` تحوي
    // نماذج غير مفكوكة، فحفظها بلا ترميز يمرّ ثم يفشل عند القراءة وحدها.
    final held = snapshot.value.buckets.last;
    expect(held.holds.single.reason, 'محجوز لمزاد الرياض ١٢');
  });

  test('انقطاع الشبكة بلا كاش يرمي العطب ولا يرجع محفظة فارغة', () async {
    final api = FakeWalletApi(wallet: serverWallet)
      ..failWith = _offlineException();
    final repository = buildRepository(api, MemoryResponseCache());

    // «رصيدك صفر» أسوأ من «تعذّر التحديث»: قارئها يظنّ فلوسه ضاعت.
    await expectLater(
      repository.loadBalance(),
      throwsA(isA<TransportFailure>()),
    );
  });

  test('خطأ ردّ به الخادم لا يُخفى خلف بيانات قديمة', () async {
    final cache = MemoryResponseCache();
    final api = FakeWalletApi(wallet: serverWallet);
    final repository = buildRepository(api, cache);

    await repository.loadBalance();
    api.failWith = DioException(
      requestOptions: RequestOptions(path: '/api/v1/wallet'),
      type: DioExceptionType.badResponse,
      response: Response<Object?>(
        requestOptions: RequestOptions(path: '/api/v1/wallet'),
        statusCode: 401,
        data: <String, Object?>{
          'error': <String, Object?>{
            'code': 'TOKEN_EXPIRED',
            'message': 'انتهت الجلسة، سجّل الدخول من جديد.',
          },
        },
      ),
    );

    // الخادم تكلّم: رسالته هي الحقيقة، وإخفاؤها خلف كاش يكذب على المستخدم.
    await expectLater(repository.loadBalance(), throwsA(isA<ApiFailure>()));
  });

  test('كاش تالف يُعامل كغياب كاش لا كعطب', () async {
    final cache = _CorruptCache();
    final api = FakeWalletApi(wallet: serverWallet)
      ..failWith = _offlineException();
    final repository = buildRepository(api, cache);

    await expectLater(
      repository.loadBalance(),
      throwsA(isA<TransportFailure>()),
    );
  });
}

DioException _offlineException() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/wallet'),
  type: DioExceptionType.connectionError,
  error: const SocketException('offline'),
);

/// كاش يرجع محتوى لا يطابق شكل المخطط — كما يحدث بعد تغيّر المخطط.
final class _CorruptCache implements ResponseCache {
  @override
  Future<CachedDocument?> read(String key) async => CachedDocument(
    rawJson: '{"unexpected": true}',
    fetchedAtUtc: DateTime.utc(2026),
  );

  @override
  Future<void> write(
    String key,
    String rawJson, {
    required DateTime fetchedAtUtc,
  }) async {}

  @override
  Future<void> clear() async {}
}
