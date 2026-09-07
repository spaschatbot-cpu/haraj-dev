import 'dart:io';

import 'package:dio/dio.dart';
import 'package:haraj_mobile/data/api/generated/clients/bids_api.dart';
import 'package:haraj_mobile/data/api/generated/models/bid.dart';
import 'package:haraj_mobile/data/api/generated/models/bid_status.dart';
import 'package:haraj_mobile/data/api/generated/models/bid_submission.dart';
import 'package:haraj_mobile/data/api/generated/models/paginated_bid_list.dart';

/// عميل مزايدة مزيَّف يسجّل ما أُرسل إليه.
///
/// تسجيل الأجسام المُرسَلة ليس ترفاً: أهم ما يُختبر في هذا التاسك أن
/// `confirm_lower` **لا يُرفع إلا في نداءٍ ثانٍ**، وأن المبلغ يصل كما كُتب بلا
/// تطبيع. كلاهما لا يُرى في القيمة المرجَعة، بل فيما خرج من التطبيق.
final class FakeBidsApi implements BidsApi {
  FakeBidsApi({this.bid, this.page});

  /// ما يُرَدّ على `bidsPlace` و`bidsWithdraw` عند النجاح.
  Bid? bid;

  /// ما يُرَدّ على `bidsMineList`.
  PaginatedBidList? page;

  /// يُرمى بدل الردّ، إن وُضع.
  Object? failWith;

  final List<BidSubmission> submissions = <BidSubmission>[];
  final List<String> withdrawn = <String>[];
  int mineCalls = 0;

  @override
  Future<Bid> bidsPlace({
    required String vehicleId,
    required BidSubmission body,
  }) async {
    submissions.add(body);
    final failure = failWith;
    if (failure != null) throw failure;
    return bid!;
  }

  @override
  Future<Bid> bidsWithdraw({required String bidId}) async {
    withdrawn.add(bidId);
    final failure = failWith;
    if (failure != null) throw failure;
    return bid!;
  }

  @override
  Future<PaginatedBidList> bidsMineList({int? page, int? pageSize}) async {
    mineCalls++;
    final failure = failWith;
    if (failure != null) throw failure;
    return this.page!;
  }
}

/// مزايدة كما يرسلها الخادم.
Bid serverBid({
  String id = 'BID-1',
  String vehicleId = 'V-1',
  String amount = '12600.00',
  String currency = 'SAR',
  BidStatus status = BidStatus.placed,
  String statusLabel = 'مزايدة قائمة',
  String? vehicleTitle = 'تويوتا كامري 2021',
  DateTime? placedAt,
}) => Bid(
  id: id,
  vehicleId: vehicleId,
  amount: amount,
  currency: currency,
  status: status,
  statusLabel: statusLabel,
  vehicleTitle: vehicleTitle,
  placedAt: placedAt ?? DateTime.utc(2026, 9, 1, 7, 30),
);

/// رفضٌ بالشكل الموحّد — نفس الظرف الذي يردّ به الخادم الحقيقي.
DioException refusal({
  required String code,
  required String message,
  int statusCode = 409,
  Map<String, Object?> detail = const <String, Object?>{},
}) => DioException(
  requestOptions: RequestOptions(path: '/api/v1/vehicles/V-1/bids'),
  type: DioExceptionType.badResponse,
  response: Response<Object?>(
    requestOptions: RequestOptions(path: '/api/v1/vehicles/V-1/bids'),
    statusCode: statusCode,
    data: <String, Object?>{
      'error': <String, Object?>{
        'code': code,
        'message': message,
        'detail': detail,
      },
    },
  ),
);

/// انقطاع شبكة — الخادم لم يتكلّم أصلاً.
DioException offline() => DioException(
  requestOptions: RequestOptions(path: '/api/v1/bids/mine'),
  type: DioExceptionType.connectionError,
  error: const SocketException('offline'),
);
