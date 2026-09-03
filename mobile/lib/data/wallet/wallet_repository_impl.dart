import 'dart:convert';

import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/wallet_balance.dart';
import '../../domain/wallet/repositories/wallet_repository.dart';
import '../api/api_call.dart';
import '../api/generated/clients/wallet_api.dart';
import '../api/generated/models/paginated_ledger_entry_list.dart' as api;
import '../api/generated/models/wallet.dart' as api;
import '../local/cache/response_cache.dart';
import 'wallet_mapper.dart';

/// المحفظة: الخادم أولاً، والكاش شبكة أمان عند **صمت** الخادم وحده.
///
/// هذا المستودع هو الشريحة المرجعية للبذرة: من هنا تُنسخ بقية المستودعات بعد
/// تثبيت المخطط (T621). ما يجب أن يُنسخ معه هو القرار التالي، لا الشكل فقط.
final class WalletRepositoryImpl implements WalletRepository {
  WalletRepositoryImpl({
    required WalletApi api,
    required ResponseCache cache,
    DateTime Function()? clock,
  }) : _api = api,
       _cache = cache,
       _clock = clock ?? DateTime.now;

  final WalletApi _api;
  final ResponseCache _cache;
  final DateTime Function() _clock;

  @override
  Future<Snapshot<WalletBalance>> loadBalance() async {
    try {
      final wallet = await callApi(_api.walletRetrieve);
      final fetchedAt = _clock().toUtc();
      await _cache.write(
        CacheKeys.wallet,
        jsonEncode(wallet.toJson()),
        fetchedAtUtc: fetchedAt,
      );
      return Snapshot.fresh(wallet.toDomain(), at: fetchedAt);
    } on TransportFailure {
      // الخادم لم يتكلّم: نعرض آخر ما نعرف مع علامة «آخر تحديث» (H5).
      final cached = await _readBalanceCache();
      if (cached != null) return cached;
      // لا كاش: نرمي العطب. **لا نرجع محفظة فارغة** — «رصيدك صفر» أسوأ من
      // «تعذّر التحديث»، وقارئها يظنّ فلوسه ضاعت.
      rethrow;
    }
    // `ApiFailure` تمرّ كما هي عمداً: الخادم **تكلّم** (401، 403…) ورسالته
    // العربية هي الحقيقة. إخفاؤها خلف بيانات قديمة يكذب على المستخدم.
  }

  @override
  Future<Snapshot<LedgerPage>> loadTransactions({
    int page = 1,
    WalletBucketKind? bucket,
  }) async {
    final key = CacheKeys.walletTransactions(bucket: bucket?.name);
    try {
      final response = await callApi(
        () => _api.walletTransactionsList(page: page, bucket: bucket?.toWire()),
      );
      final fetchedAt = _clock().toUtc();
      if (page == 1) {
        await _cache.write(
          key,
          jsonEncode(response.toJson()),
          fetchedAtUtc: fetchedAt,
        );
      }
      return Snapshot.fresh(response.toDomain(page: page), at: fetchedAt);
    } on TransportFailure {
      // صفحة تالية بلا شبكة ليست حالة كاش: المحفوظ هو الصفحة الأولى وحدها،
      // وإرجاعه هنا يعيد للمستخدم أول الكشف وكأنه آخره.
      if (page != 1) rethrow;
      final cached = await _readTransactionsCache(key);
      if (cached != null) return cached;
      rethrow;
    }
  }

  Future<Snapshot<WalletBalance>?> _readBalanceCache() async {
    final document = await _cache.read(CacheKeys.wallet);
    if (document == null) return null;
    try {
      final wallet = api.Wallet.fromJson(document.decode());
      return Snapshot.cached(
        wallet.toDomain(),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      // كاش من نسخة مخطط أقدم لم يعد يُفكّ: يُعامل كغياب كاش، لا كعطب.
      return null;
    }
  }

  Future<Snapshot<LedgerPage>?> _readTransactionsCache(String key) async {
    final document = await _cache.read(key);
    if (document == null) return null;
    try {
      final list = api.PaginatedLedgerEntryList.fromJson(document.decode());
      return Snapshot.cached(
        list.toDomain(page: 1),
        storedAt: document.fetchedAtUtc,
      );
    } on Object {
      return null;
    }
  }
}
