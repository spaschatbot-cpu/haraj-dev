// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/bid.dart';
import '../models/bid_submission.dart';
import '../models/paginated_bid_list.dart';

part 'bids_api.g.dart';

@RestApi()
abstract class BidsApi {
  factory BidsApi(Dio dio, {String? baseUrl}) = _BidsApi;

  /// وضع مزايدة — الخفض يحتاج تأكيداً صريحاً.
  ///
  /// الخفض يُرفض بـ409 ورمز lower_needs_confirm، وحمولة الرفض تحمل `standing` و`requested`. يُعاد الإرسال بـconfirm_lower=true بعد تأكيد المستخدم على المبلغين.
  @POST('/api/v1/vehicles/{vehicleId}/bids')
  Future<Bid> bidsPlace({
    @Path('vehicleId') required String vehicleId,
    @Body() required BidSubmission body,
  });

  /// مزايداتي
  @GET('/api/v1/bids/mine')
  Future<PaginatedBidList> bidsMineList({
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// سحب مزايدة.
  ///
  /// السحب يُعلَّم ولا يُحذف — تعود المزايدة بحالتها الجديدة. ملكية المزايدة قرار الخادم: مزايدة غيرك ترجع 404، لا 403.
  @POST('/api/v1/bids/{bidId}/withdraw')
  Future<Bid> bidsWithdraw({@Path('bidId') required String bidId});
}
