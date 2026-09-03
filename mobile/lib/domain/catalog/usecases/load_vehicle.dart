import '../../common/snapshot.dart';
import '../entities/vehicle_detail.dart';
import '../repositories/catalog_repository.dart';

/// «وريني هذه المركبة.» (T709)
final class LoadVehicle {
  const LoadVehicle(this._repository);

  final CatalogRepository _repository;

  Future<Snapshot<VehicleDetail>> call(String vehicleId) =>
      _repository.loadVehicle(vehicleId);
}
