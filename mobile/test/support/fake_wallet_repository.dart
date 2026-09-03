import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/ledger_movement.dart';
import 'package:haraj_mobile/domain/wallet/entities/top_up.dart';
import 'package:haraj_mobile/domain/wallet/entities/wallet_balance.dart';
import 'package:haraj_mobile/domain/wallet/repositories/wallet_repository.dart';

/// مستودع محفظة مزيَّف لاختبارات الشاشات.
///
/// الشاشات تُختبر عبر عقد النطاق لا عبر dio: اختبار شاشة يمرّ على HTTP يختبر
/// طبقة البيانات مرة ثانية، ويسقط لأسباب لا علاقة لها بما يُعرض.
final class FakeWalletRepository implements WalletRepository {
  FakeWalletRepository({
    this.balance,
    this.balanceFailure,
    this.pages = const <int, LedgerPage>{},
    this.pageFailures = const <int, Failure>{},
    this.startedTopUp,
    this.topUpStatuses = const <TopUp>[],
    this.startTopUpFailure,
    this.readTopUpFailure,
    this.origin = DataOrigin.network,
    DateTime? fetchedAt,
  }) : fetchedAt = fetchedAt ?? DateTime.utc(2026, 9, 1, 10);

  final WalletBalance? balance;
  final Failure? balanceFailure;
  final Map<int, LedgerPage> pages;
  final Map<int, Failure> pageFailures;

  /// النيّة التي يرجعها الخادم عند البدء.
  final TopUp? startedTopUp;

  /// ما يقوله الخادم عن الحالة، سؤالاً بعد سؤال. الأخيرة تتكرّر.
  final List<TopUp> topUpStatuses;

  final Failure? startTopUpFailure;
  final Failure? readTopUpFailure;
  final DataOrigin origin;
  final DateTime fetchedAt;

  final List<WalletBucketKind?> askedBuckets = <WalletBucketKind?>[];
  final List<int> askedPages = <int>[];

  /// المراجع التي سُئل عنها الخادم — الدليل على أن الحالة مقروءة منه.
  final List<String> askedReferences = <String>[];

  @override
  Future<Snapshot<WalletBalance>> loadBalance() async {
    final failure = balanceFailure;
    if (failure != null) throw failure;
    return _wrap(balance!);
  }

  @override
  Future<Snapshot<LedgerPage>> loadTransactions({
    int page = 1,
    WalletBucketKind? bucket,
  }) async {
    askedPages.add(page);
    askedBuckets.add(bucket);
    final failure = pageFailures[page];
    if (failure != null) throw failure;
    return _wrap(pages[page]!);
  }

  @override
  Future<TopUp> startTopUp() async {
    final failure = startTopUpFailure;
    if (failure != null) throw failure;
    return startedTopUp!;
  }

  @override
  Future<TopUp> readTopUp(String reference) async {
    askedReferences.add(reference);
    final failure = readTopUpFailure;
    if (failure != null) throw failure;
    final index = askedReferences.length - 1;
    return topUpStatuses[index < topUpStatuses.length
        ? index
        : topUpStatuses.length - 1];
  }

  Snapshot<T> _wrap<T>(T value) =>
      Snapshot<T>(value: value, origin: origin, fetchedAt: fetchedAt);
}
