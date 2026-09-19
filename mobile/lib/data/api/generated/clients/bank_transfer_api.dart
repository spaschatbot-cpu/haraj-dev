// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/bank_transfer.dart';

part 'bank_transfer_api.g.dart';

@RestApi()
abstract class BankTransferApi {
  factory BankTransferApi(Dio dio, {String? baseUrl}) = _BankTransferApi;

  /// حساب الحوالة البنكية.
  ///
  /// `GET /api/v1/bank-transfer/` — حسابُ الشركة الذي يُحوَّل إليه. T954.
  ///
  /// ## لماذا نقطةٌ لا نصٌّ في التطبيق.
  ///
  /// الحسابُ بيانُ شركةٍ يتغيّر، ومكتوباً في التطبيق يعني إصداراً جديداً على.
  /// المتجرَين لتغيير رقم. وv1 يخزّنه في `account_page_settings` ويحرّره من.
  /// اللوحة للسبب نفسِه. وهنا في بيئة الخادم (`BANK_TRANSFER_*`).
  ///
  /// ## وما يُبنى عليها.
  ///
  /// قناتان لشحن التأمين — ميسر والحوالة — وكان زرُّ الحوالة يردّ «قريباً».
  /// بلا رقم حساب. **والفاتورةُ حوالةٌ وحدَها** بعد أن أُغلق السدادُ من رصيد.
  /// التأمين (انظر :class:`InvoicePayView`).
  ///
  /// ## ومفتوحةٌ لمن لم يدخل.
  ///
  /// `AllowAny` بقصد: من يقرأ الشروطَ قبل التسجيل يسأل «كيف أدفع؟»، والحسابُ.
  /// الذي تُعلنه الشركةُ لاستقبال الحوالات ليس سرّاً — هو على فواتيرها.
  /// وموقعها. وإخفاؤه خلف تسجيل دخولٍ يمنع سؤالاً مشروعاً ولا يحمي شيئاً.
  @GET('/api/v1/bank-transfer/')
  Future<BankTransfer> v1BankTransferRetrieve();
}
