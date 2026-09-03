// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/paginated_invoice_list.dart';
import '../models/paginated_purchase_list.dart';

part 'invoices_api.g.dart';

@RestApi()
abstract class InvoicesApi {
  factory InvoicesApi(Dio dio, {String? baseUrl}) = _InvoicesApi;

  /// فواتيري
  @GET('/api/v1/invoices/')
  Future<PaginatedInvoiceList> invoicesList({
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });

  /// مشترياتي — ما رسا عليّ، ومعه فاتورته.
  ///
  /// الفاتورة تأتي **داخل** المشترى لا بمطابقة معرّفات في التطبيق — نفس ما تفعله نقطة المشتريات في الخلفية (`PurchaseSerializer.get_invoice`).
  @GET('/api/v1/purchases/')
  Future<PaginatedPurchaseList> purchasesList({
    @Query('page') int? page,
    @Query('page_size') int? pageSize,
  });
}
