import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/providers.dart';
import '../../domain/common/failure.dart';
import '../../domain/common/snapshot.dart';
import '../../domain/wallet/entities/ledger_movement.dart';
import '../../domain/wallet/entities/wallet_balance.dart';

/// حالة شاشة الحركات: ما عُرض، وهل بقي مزيد، وماذا حدث لآخر محاولة تحميل.
///
/// `snapshot` يحمل الحركات ومصدرها معاً حتى تبقى علامة «آخر تحديث» صادقة بعد
/// الترقيم: الصفحات التالية لا تغيّر لحظة الجلب الأولى ولا مصدرها.
final class TransactionsState {
  const TransactionsState({
    required this.snapshot,
    required this.hasMore,
    required this.total,
    this.isLoadingMore = false,
    this.loadMoreFailure,
  });

  final Snapshot<List<LedgerMovement>> snapshot;

  /// من الخادم (`next`) لا من حساب في الشاشة.
  final bool hasMore;

  /// عدد الحركات كلها كما قاله الخادم — عدد لا مبلغ.
  final int total;

  final bool isLoadingMore;

  /// فشل **الصفحة التالية** وحده. ما عُرض يبقى معروضاً: إسقاط الكشف كله لأن
  /// صفحة تاسعة لم تصل يمحو من الشاشة حركات وصلت فعلاً.
  final Failure? loadMoreFailure;

  List<LedgerMovement> get movements => snapshot.value;

  TransactionsState copyWith({
    Snapshot<List<LedgerMovement>>? snapshot,
    bool? hasMore,
    int? total,
    bool? isLoadingMore,
    Failure? loadMoreFailure,
    bool clearLoadMoreFailure = false,
  }) => TransactionsState(
    snapshot: snapshot ?? this.snapshot,
    hasMore: hasMore ?? this.hasMore,
    total: total ?? this.total,
    isLoadingMore: isLoadingMore ?? this.isLoadingMore,
    loadMoreFailure: clearLoadMoreFailure
        ? null
        : loadMoreFailure ?? this.loadMoreFailure,
  );
}

/// كشف الحركات لدلو بعينه، أو للحساب كله حين تكون العائلة `null`.
final transactionsControllerProvider = AsyncNotifierProvider.autoDispose
    .family<TransactionsController, TransactionsState, WalletBucketKind?>(
      TransactionsController.new,
    );

/// يتذكّر أي صفحة وصلنا إليها، ولا يعرف شيئاً آخر.
///
/// **لا حساب هنا:** لا جمع مبالغ، ولا اشتقاق «هل بقي مزيد» من طول القائمة —
/// كلاهما من الخادم. الشيء الوحيد الذي يحسبه التطبيق هو رقم الصفحة التالية،
/// وهو ليس مالاً.
final class TransactionsController extends AsyncNotifier<TransactionsState> {
  TransactionsController(this.bucket);

  /// الدلو المطلوب. `null` تعني الكشف كله.
  final WalletBucketKind? bucket;

  int _lastPage = 1;

  @override
  Future<TransactionsState> build() async {
    final snapshot = await ref.watch(loadWalletTransactionsProvider)(
      bucket: bucket,
    );
    _lastPage = snapshot.value.page;
    return TransactionsState(
      snapshot: snapshot.map((page) => page.movements),
      hasMore: snapshot.value.hasMore,
      total: snapshot.value.total,
    );
  }

  /// يطلب الصفحة التالية ويضيفها إلى ما عُرض.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || !current.hasMore || current.isLoadingMore) return;

    state = AsyncData(
      current.copyWith(isLoadingMore: true, clearLoadMoreFailure: true),
    );

    try {
      final next = await ref.read(loadWalletTransactionsProvider)(
        page: _lastPage + 1,
        bucket: bucket,
      );
      _lastPage = next.value.page;
      state = AsyncData(
        current.copyWith(
          snapshot: Snapshot<List<LedgerMovement>>(
            value: <LedgerMovement>[
              ...current.movements,
              ...next.value.movements,
            ],
            // مصدر الصفحة الأولى ولحظتها هما ما تعنيه علامة «آخر تحديث».
            origin: current.snapshot.origin,
            fetchedAt: current.snapshot.fetchedAt,
          ),
          hasMore: next.value.hasMore,
          total: next.value.total,
          isLoadingMore: false,
        ),
      );
    } on Failure catch (failure) {
      state = AsyncData(
        current.copyWith(isLoadingMore: false, loadMoreFailure: failure),
      );
    }
  }

  /// إعادة المحاولة من أول الكشف.
  Future<void> refresh() async {
    _lastPage = 1;
    ref.invalidateSelf();
    await future;
  }
}
