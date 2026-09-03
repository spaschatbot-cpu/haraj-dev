import '../../common/snapshot.dart';
import '../entities/invoice.dart';
import '../repositories/activity_repository.dart';

/// «إيش عليّ، وكم سدّدت، وكم باقي؟»
final class LoadMyInvoices {
  const LoadMyInvoices(this._repository);

  final ActivityRepository _repository;

  Future<Snapshot<List<Invoice>>> call() => _repository.loadInvoices();
}
