// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/paginated_vehicle_card_list.dart';
import '../models/vehicle.dart';

part 'vehicles_api.g.dart';

@RestApi()
abstract class VehiclesApi {
  factory VehiclesApi(Dio dio, {String? baseUrl}) = _VehiclesApi;

  /// مركبات المزاد — بحث وترشيح
  @GET('/api/v1/auctions/{auctionId}/vehicles')
  Future<PaginatedVehicleCardList> auctionVehiclesList({
    @Path('auctionId') required String auctionId,
    @Query('search') String? search,
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// تفاصيل مركبة
  @GET('/api/v1/vehicles/{vehicleId}')
  Future<Vehicle> vehiclesRetrieve({
    @Path('vehicleId') required String vehicleId,
  });
}
