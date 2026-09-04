import '../../common/snapshot.dart';
import '../entities/vehicle_feed.dart';
import '../entities/vehicle_query.dart';
import '../repositories/catalog_repository.dart';

/// «وريني مركبات هذا التبويب، ومعها كم في كل تبويب.»
///
/// طلبٌ واحد لأن الجواب واحد: الشاشة تعرض الشبكة والعدّادات معاً، وسؤالهما
/// مفرَّقين يجعل الرقم على التبويب من لحظةٍ غير لحظة ما تحته.
///
/// ورقيقة عمداً كأخواتها: قواعد المزادات في `apps/auctions/services.py`، وليس
/// للتطبيق منها شيء يحسبه — قيمتها أنها الاسم الذي تناديه طبقة العرض.
final class LoadVehicleFeed {
  const LoadVehicleFeed(this._repository);

  final CatalogRepository _repository;

  Future<Snapshot<VehicleFeed>> call(VehicleQuery query) =>
      _repository.loadVehicleFeed(query);
}
