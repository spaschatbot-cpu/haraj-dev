import '../../common/snapshot.dart';
import '../entities/purchase.dart';
import '../repositories/activity_repository.dart';

/// «إيش اللي رسا عليّ، وفين وصلت كل مركبة؟»
final class LoadMyPurchases {
  const LoadMyPurchases(this._repository);

  final ActivityRepository _repository;

  Future<Snapshot<List<Purchase>>> call() => _repository.loadPurchases();
}
