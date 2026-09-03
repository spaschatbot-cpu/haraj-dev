import '../../common/snapshot.dart';
import '../entities/ledger_movement.dart';
import '../entities/wallet_balance.dart';
import '../repositories/wallet_repository.dart';

/// «وريني الحركات التي وراء هذا الرقم.»
///
/// وجود `bucket` هنا هو المادة ١-٦ عملياً: كل مبلغ في المحفظة يُفتح على القيود
/// التي تفسّره. والترشيح يُرسَل إلى الخادم ولا يقع في الشاشة — الشاشة التي
/// ترشّح بنفسها تحتاج أن تعرف أي قيد يخصّ أي دلو، وتلك قاعدة يملكها الدفتر.
final class LoadWalletTransactions {
  const LoadWalletTransactions(this._repository);

  final WalletRepository _repository;

  Future<Snapshot<LedgerPage>> call({int page = 1, WalletBucketKind? bucket}) =>
      _repository.loadTransactions(page: page, bucket: bucket);
}
