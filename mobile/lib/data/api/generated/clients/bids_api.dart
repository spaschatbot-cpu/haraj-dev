// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/bid.dart';
import '../models/bid_page.dart';
import '../models/bid_quote.dart';

part 'bids_api.g.dart';

@RestApi()
abstract class BidsApi {
  factory BidsApi(Dio dio, {String? baseUrl}) = _BidsApi;

  /// سحب مزايدة.
  ///
  /// `POST /api/v1/bids/{id}/withdraw/` — pull a bid back.
  ///
  /// The bid is fetched **filtered by the caller** rather than fetched and then.
  /// checked, so somebody else's bid id is a 404 and not a 403. The service.
  /// refuses it a second time anyway (`NotYourBid`) — the two guards are not.
  /// redundant: this one decides what a stranger learns, that one is the rule.
  @POST('/api/v1/bids/{id}/withdraw/')
  Future<Bid> bidsWithdraw({@Path('id') required int id});

  /// مزايداتي.
  ///
  /// `GET /api/v1/bids/mine/` — the caller's own bids, and only those.
  @GET('/api/v1/bids/mine/')
  Future<BidPage> bidsMine({
    @Query('include_history') bool? includeHistory = false,
    @Query('limit') int? limit = 20,
    @Query('offset') int? offset = 0,
  });

  /// السعر مع الضريبة.
  ///
  /// `POST /api/v1/bids/quote/` — «السعر + الضريبة (15%)» لمبلغٍ يُكتب الآن.
  ///
  /// نافذةُ v1 تعرض سطراً يتغيّر مع كل حرفٍ يكتبه المزايد: «السعر + الضريبة.
  /// (15%): ٠ ر.س». في v1 يُحسب في المتصفّح؛ **وهنا لا يمكن أن يُحسب هناك**.
  /// و`ops/checks/web_money_is_never_computed.mjs` يمنعه بحقّ — نسخةٌ ثانية من.
  /// معادلة الضريبة تختلف عن الأولى يوم تتغيّر النسبة، وتختلف صامتة.
  ///
  /// فالرقم يُطلَب. رحلةٌ إلى الخادم لضربتين، نعم — والثمن مقصود: النسبة يقولها.
  /// `money.tax_added_to` وحدها، ومبلغٌ يقبله هذا العرض هو مبلغٌ تقبله.
  /// المزايدة لأن النمط واحد.
  ///
  /// **ولا يكتب شيئاً**: لا قيد، ولا مزايدة، ولا صفّ. `POST` لأن المبلغ جسمٌ.
  /// لا يُوضع في مسار — مبالغُ العملاء لا تُكتب في عناوين تُسجَّل في كل وسيط.
  /// بينهم وبيننا.
  ///
  /// ويحتاج جلسةً كما تحتاجها المزايدة نفسها: الشاشة التي تعرض هذا السطر هي.
  /// الشاشة التي فيها صندوق المزايدة، ولا تُعرَض لزائرٍ غير داخل.
  @MultiPart()
  @POST('/api/v1/bids/quote/')
  Future<BidQuote> bidsQuote({@Part(name: 'amount') required String amount});
}
