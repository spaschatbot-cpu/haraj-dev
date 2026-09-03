import '../../common/snapshot.dart';
import '../entities/auction_summary.dart';
import '../repositories/catalog_repository.dart';

/// «وريني المزادات الجارية والقادمة.» (T707)
///
/// رقيقة عمداً: قواعد المزادات كلها في `apps/auctions/services.py`، وليس
/// للتطبيق منها شيء يحسبه. قيمتها أنها الاسم الذي تناديه طبقة العرض، فتبقى
/// العرض جاهلةً بمصدر البيانات.
final class LoadHomeAuctions {
  const LoadHomeAuctions(this._repository);

  final CatalogRepository _repository;

  Future<Snapshot<HomeAuctions>> call() => _repository.loadHomeAuctions();
}
