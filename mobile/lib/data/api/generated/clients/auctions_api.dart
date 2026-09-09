// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/auction_card.dart';
import '../models/auction_page.dart';
import '../models/phase.dart';
import '../models/state.dart';
import '../models/state2.dart';
import '../models/vehicle_page.dart';

part 'auctions_api.g.dart';

@RestApi()
abstract class AuctionsApi {
  factory AuctionsApi(Dio dio, {String? baseUrl}) = _AuctionsApi;

  /// قائمة المزادات.
  ///
  /// `GET /api/v1/auctions/` — the auctions a caller may see, newest first.
  ///
  /// [state] - * `draft` - مسودة.
  /// * `scheduled` - مجدول.
  /// * `live` - جارٍ.
  /// * `ended` - منتهٍ.
  /// * `settled` - مُسوّى.
  /// * `cancelled` - ملغى.
  @GET('/api/v1/auctions/')
  Future<AuctionPage> auctionsList({
    @Query('state') State? state,
    @Query('limit') int? limit = 20,
    @Query('offset') int? offset = 0,
  });

  /// تفاصيل المزاد.
  ///
  /// `GET /api/v1/auctions/{id}/` — one auction, in the list's own shape.
  ///
  /// Built by `cards.auction_card` with the same annotations the list uses, so.
  /// the detail page and the row a customer tapped cannot disagree about how many.
  /// cars an auction holds. An auction the caller may not see is a 404: a 403.
  /// would confirm it exists, which is enough to enumerate auctions before they.
  /// open.
  @GET('/api/v1/auctions/{id}/')
  Future<AuctionCard> auctionsRetrieve({@Path('id') required int id});

  /// مركبات المزاد.
  ///
  /// `GET /api/v1/auctions/{id}/vehicles/` — one auction's cars.
  ///
  /// [phase] - * `soon` - قريباً.
  /// * `active` - نشط.
  /// * `ended` - منتهي.
  ///
  /// [state] - * `draft` - مسودة.
  /// * `listed` - معروضة.
  /// * `bidding` - تحت المزايدة.
  /// * `awaiting_decision` - بانتظار قرار المالك.
  /// * `awarded` - مرسّاة.
  /// * `rejected` - مرفوضة.
  /// * `invoiced` - مفوترة.
  /// * `paid` - مسدَّدة.
  /// * `released` - خرجت.
  /// * `withdrawn` - مسحوبة.
  /// * `relisted` - معادة للعرض.
  @GET('/api/v1/auctions/{id}/vehicles/')
  Future<VehiclePage> auctionsVehiclesList({
    @Path('id') required int id,
    @Query('limit') int? limit = 20,
    @Query('offset') int? offset = 0,
    @Query('auction') int? auction,
    @Query('make') String? make,
    @Query('phase') Phase? phase,
    @Query('search') String? search,
    @Query('state') State2? state,
    @Query('year_from') int? yearFrom,
    @Query('year_to') int? yearTo,
  });
}
