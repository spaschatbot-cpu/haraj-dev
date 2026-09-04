// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/auction_phase.dart';
import '../models/paginated_vehicle_card_list.dart';
import '../models/vehicle.dart';
import '../models/vehicle_feed_page.dart';

part 'vehicles_api.g.dart';

@RestApi()
abstract class VehiclesApi {
  factory VehiclesApi(Dio dio, {String? baseUrl}) = _VehiclesApi;

  /// مركبات المزاد — بحث وترشيح
  @GET('/api/v1/auctions/{auctionId}/vehicles/')
  Future<PaginatedVehicleCardList> auctionVehiclesList({
    @Path('auctionId') required String auctionId,
    @Query('search') String? search,
    @Query('make') String? make,
    @Query('year_from') int? yearFrom,
    @Query('year_to') int? yearTo,
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// مركبات عبر المزادات — صفحة واحدة وعدّادات التبويبات معها.
  ///
  /// طلب **واحد** يرجّع صفحة المركبات وعدّادات الأطوار الثلاثة معاً.
  ///
  /// العدّادات ليست ترفاً في الاستجابة: التبويبات الثلاثة تُرسم كلها في كل حال، فهي تحتاج الأرقام الثلاثة كلها في كل حال. طلبها مفرّقةً — كما في v1، ستّة طلبات لثلاثة أرقام — يجعل كل رقم من لحظة، فلا يساوي مجموع التبويبات شيئاً، ويظهر تبويبٌ يقول «٣» ثم يُفتح فيه صفرٌ لأن المزاد أُقفل بين الطلبين.
  ///
  /// و`phase` هنا هو بعينه `phase` في `?phase=` على عنوان الشاشة وفي حقل الكرت: معنى واحد باسم واحد.
  @GET('/api/v1/vehicles/')
  Future<VehicleFeedPage> vehiclesList({
    @Query('phase') AuctionPhase? phase,
    @Query('search') String? search,
    @Query('make') String? make,
    @Query('year_from') int? yearFrom,
    @Query('year_to') int? yearTo,
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// تفاصيل مركبة
  @GET('/api/v1/vehicles/{vehicleId}/')
  Future<Vehicle> vehiclesRetrieve({
    @Path('vehicleId') required String vehicleId,
  });
}
