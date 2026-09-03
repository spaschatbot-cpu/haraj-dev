import 'package:haraj_mobile/domain/common/failure.dart';
import 'package:haraj_mobile/domain/common/snapshot.dart';
import 'package:haraj_mobile/domain/wallet/entities/ledger_movement.dart';
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
    this.origin = DataOrigin.network,
    DateTime? fetchedAt,
  }) : fetchedAt = fetchedAt ?? DateTime.utc(2026, 9, 1, 10);

  final WalletBalance? balance;
  final Failure? balanceFailure;
  final Map<int, LedgerPage> pages;
  final Map<int, Failure> pageFailures;
  final DataOrigin origin;
  final DateTime fetchedAt;

  final List<WalletBucketKind?> askedBuckets = <WalletBucketKind?>[];
  final List<int> askedPages = <int>[];

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

  Snapshot<T> _wrap<T>(T value) =>
      Snapshot<T>(value: value, origin: origin, fetchedAt: fetchedAt);
}
