// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/bid.dart';
import '../models/phase.dart';
import '../models/state2.dart';
import '../models/vehicle_card.dart';
import '../models/vehicle_images.dart';
import '../models/vehicle_page.dart';

part 'vehicles_api.g.dart';

@RestApi()
abstract class VehiclesApi {
  factory VehiclesApi(Dio dio, {String? baseUrl}) = _VehiclesApi;

  /// قائمة المركبات.
  ///
  /// `GET /api/v1/vehicles/` — cars across auctions, searched and filtered.
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
  @GET('/api/v1/vehicles/')
  Future<VehiclePage> vehiclesList({
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

  /// تفاصيل المركبة.
  ///
  /// `GET /api/v1/vehicles/{id}/` — one car, through the one card builder.
  ///
  /// T609's whole requirement is that this returns the *same* fields as the list.
  /// It does so by construction rather than by discipline: both call.
  /// `cards.vehicle_card`, and there is no second assembly of a vehicle anywhere.
  /// (`ops/checks/one_vehicle_card.py` fails the build if one appears).
  ///
  /// A car the caller may not see is a 404, not a 403. A 403 confirms the row.
  /// exists, which is enough to enumerate an auction before it opens.
  @GET('/api/v1/vehicles/{id}/')
  Future<VehicleCard> vehiclesRetrieve({@Path('id') required int id});

  /// وضع مزايدة.
  ///
  /// `POST /api/v1/vehicles/{id}/bids/` — bid, or be told exactly why not.
  ///
  /// Lowering a standing bid is refused the first time with.
  /// `lower_needs_confirm` and accepted when the caller comes back with.
  /// ``confirm_lower``. That two-step is T506: lowering is a real feature of a.
  /// sealed auction and also exactly what a fat finger does, so it costs one.
  /// deliberate extra round trip.
  ///
  /// The car is resolved through `visible_vehicles`, so bidding on something the.
  /// caller cannot see is a 404 — the same answer as a car that does not exist,.
  /// which is what stops the endpoint being used to probe an unopened auction.
  @MultiPart()
  @POST('/api/v1/vehicles/{id}/bids/')
  Future<Bid> bidsPlace({
    @Path('id') required int id,
    @Part(name: 'amount') required String amount,
    @Part(name: 'confirm_lower') bool? confirmLower = false,
  });

  /// صور المركبة.
  ///
  /// `GET /api/v1/vehicles/{id}/images/` — معرض صور المركبة. HR-12ب.
  ///
  /// الطبقتان (بطاقة ومعاينة) تُولَّدان منذ HR-12 وتُخزَّنان على القرص، **ولم.
  /// تكن لهما قناة**: الكرت يحمل صورة الغلاف بمقاس بطاقةٍ واحدة، وشاشة.
  /// التفاصيل كانت تُكبّرها. هذه هي القناة.
  ///
  /// **ونقطةٌ منفصلة لا حقلٌ على الكرت**، وهو القرار الذي علّقه HR-12ب:.
  /// T609 يشترط أن تُعيد التفاصيل حقول القائمة نفسها، فتوسيعُ الكرت بمصفوفة.
  /// صورٍ يخالفه ويحتاج استثناءً مكتوباً في `one_vehicle_card`. والأهمّ أنه.
  /// يُثقل ما لا يحتاج: صفحةُ خمسين سيارةً بتسع صورٍ لكلٍّ تحمل أربعمئة صفٍّ.
  /// لتُقرأ منها تسعةٌ حين يُضغط كرتٌ واحد. فالكرت كما هو، والمعرض بطلبه.
  ///
  /// الرؤية هي رؤية المركبة نفسها (`visible_vehicles`)، وسيارةٌ لا يراها.
  /// المتصل **404** لا 403 — تأكيدُ وجود الصفّ وحده يكفي لعدّ مزادٍ قبل أن.
  /// يُفتح.
  @GET('/api/v1/vehicles/{id}/images/')
  Future<VehicleImages> vehiclesImagesList({@Path('id') required int id});
}
