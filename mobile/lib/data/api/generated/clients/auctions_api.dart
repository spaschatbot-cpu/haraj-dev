// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/auction.dart';
import '../models/auction_status.dart';
import '../models/paginated_auction_list.dart';
import '../models/paginated_participation_list.dart';

part 'auctions_api.g.dart';

@RestApi()
abstract class AuctionsApi {
  factory AuctionsApi(Dio dio, {String? baseUrl}) = _AuctionsApi;

  /// المزادات الجارية والقادمة
  @GET('/api/v1/auctions')
  Future<PaginatedAuctionList> auctionsList({
    @Query('status') AuctionStatus? status,
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// تفاصيل مزاد
  @GET('/api/v1/auctions/{auctionId}')
  Future<Auction> auctionsRetrieve({
    @Path('auctionId') required String auctionId,
  });

  /// مشاركاتي — المزادات التي دخلتها وحالة تأميني في كل واحد.
  ///
  /// حالة التأمين لكل مزاد **يشتقّها الخادم** من حجوزاته. لا تُركَّب في التطبيق من «مزايداتي» و«المحفظة»: التركيب قاعدة عمل، وقاعدة في الشاشة نسخة ثانية تفترق عن الأصل (المادة ٤-٥).
  @GET('/api/v1/participations')
  Future<PaginatedParticipationList> participationsList({
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });
}
