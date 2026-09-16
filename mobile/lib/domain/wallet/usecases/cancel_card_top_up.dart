import '../entities/top_up.dart';
import '../repositories/wallet_repository.dart';

/// «ألغِ طلبَ الشحن الذي بدأتُه ولم أُكمله».
final class CancelCardTopUp {
  const CancelCardTopUp(this._repository);

  final WalletRepository _repository;

  Future<TopUp> call(String reference) => _repository.cancelTopUp(reference);
}
