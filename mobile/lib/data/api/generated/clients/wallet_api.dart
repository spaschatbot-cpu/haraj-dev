// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/paginated_ledger_entry_list.dart';
import '../models/refund_request.dart';
import '../models/refund_request_input.dart';
import '../models/top_up_intent.dart';
import '../models/top_up_intent_request.dart';
import '../models/wallet.dart';
import '../models/wallet_bucket_kind.dart';

part 'wallet_api.g.dart';

@RestApi()
abstract class WalletApi {
  factory WalletApi(Dio dio, {String? baseUrl}) = _WalletApi;

  /// المحفظة — الدلاء مفصَّلة بأسبابها.
  ///
  /// لا مجموع واحد. كل دلو ببيانه وسببه (أي مزاد، أي فاتورة) — قاعدة G5 في الفيز 007 وقاعدة العرض 2 في الفيز 008.
  @GET('/api/v1/wallet')
  Future<Wallet> walletRetrieve();

  /// كشف الحركات من القيود مباشرةً.
  ///
  /// الترشيح على دلو واحد هو النصف الثاني من المادة ١-٦: كل رقم في المحفظة يُفتح على القيود التي تفسّره. الترشيح يقع على الخادم لا في الشاشة — نظيره في الخلفية `bucket` في `StatementQuerySerializer`.
  ///
  /// [bucket] - دلو واحد بعينه — القيمة كما أرسلها الخادم في `WalletBucket.kind`.
  @GET('/api/v1/wallet/transactions')
  Future<PaginatedLedgerEntryList> walletTransactionsList({
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
    @Query('bucket') WalletBucketKind? bucket,
  });

  /// نيّة شحن — المبلغ من الخادم لا من الطلب
  @POST('/api/v1/wallet/topup-intents')
  Future<TopUpIntent> walletTopUpIntentCreate({
    @Body() required TopUpIntentRequest body,
  });

  /// حالة نيّة الشحن كما يعرفها الخادم.
  ///
  /// العودة من البوابة تُسنَد من هنا، لا من معاملات رابط العودة. المرجع ليس ادّعاءً: هو اسم صفّ كتبه الخادم قبل أن يصل العميل إلى البوابة أصلاً، والرصيد يتحرّك بتأكيد البوابة للخادم وحده. نظيره في الخلفية `GET /api/v1/wallet/topups/{reference}/`.
  @GET('/api/v1/wallet/topup-intents/{reference}')
  Future<TopUpIntent> walletTopUpIntentRetrieve({
    @Path('reference') required String reference,
  });

  /// طلب استرداد من المتاح فقط
  @POST('/api/v1/wallet/refund-requests')
  Future<RefundRequest> walletRefundRequestCreate({
    @Body() required RefundRequestInput body,
  });
}
