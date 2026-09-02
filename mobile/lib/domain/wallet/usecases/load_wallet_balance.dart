import '../../common/snapshot.dart';
import '../entities/wallet_balance.dart';
import '../repositories/wallet_repository.dart';

/// «اعرض لي حالة فلوسي.»
///
/// الـusecase هنا رقيقة عمداً: قواعد المال كلها في الخادم، والتطبيق لا يملك
/// منها شيئاً يحسبه (المبدأ الحاكم للفيز 008: الشاشة لا تحسب مالاً). قيمتها
/// أنها الاسم الذي تناديه طبقة العرض، فتبقى العرض جاهلة بمصدر البيانات.
final class LoadWalletBalance {
  const LoadWalletBalance(this._repository);

  final WalletRepository _repository;

  Future<Snapshot<WalletBalance>> call() => _repository.loadBalance();
}
