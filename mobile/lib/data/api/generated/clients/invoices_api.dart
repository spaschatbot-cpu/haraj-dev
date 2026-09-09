// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/invoice.dart';
import '../models/method_enum.dart';
import '../models/paginated_invoice_list.dart';

part 'invoices_api.g.dart';

@RestApi()
abstract class InvoicesApi {
  factory InvoicesApi(Dio dio, {String? baseUrl}) = _InvoicesApi;

  /// [limit] - عدد النتائج التي يجب إرجاعها في كل صفحة.
  ///
  /// [offset] - الفهرس الأولي الذي يجب البدء منه لإرجاع النتائج.
  @GET('/api/v1/invoices/')
  Future<PaginatedInvoiceList> v1InvoicesList({
    @Query('limit') int? limit,
    @Query('offset') int? offset,
  });

  @GET('/api/v1/invoices/{id}/')
  Future<Invoice> v1InvoicesRetrieve({@Path('id') required int id});

  /// Settle one invoice from the balance the customer already has with us.
  ///
  /// There is no card branch here and no card purpose to reach for: a purchase is.
  /// paid from deposited money or by a bank transfer the bank confirms.
  ///
  /// [method] - الافتراضيّ حين لا يُرسَل الحقل: `balance`.
  @MultiPart()
  @POST('/api/v1/invoices/{id}/pay/')
  Future<Invoice> v1InvoicesPayCreate({
    @Path('id') required int id,
    @Part(name: 'method') MethodEnum? method,
  });
}
