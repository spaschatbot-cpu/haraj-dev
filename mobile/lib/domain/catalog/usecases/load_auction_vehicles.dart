import '../../common/snapshot.dart';
import '../entities/vehicle_query.dart';
import '../repositories/catalog_repository.dart';

/// «وريني مركبات هذا المزاد بهذه المعايير.» (T708)
///
/// المعايير تعبر كما هي إلى الخادم. لا يوجد في هذا المسار موضع واحد يرشّح أو
/// يرتّب أو يقصّ — لو وُجد لصار للسؤال «أي المركبات تطابق؟» جوابان.
final class LoadAuctionVehicles {
  const LoadAuctionVehicles(this._repository);

  final CatalogRepository _repository;

  Future<Snapshot<VehiclePage>> call(String auctionId, VehicleQuery query) =>
      _repository.loadAuctionVehicles(auctionId, query);
}
