// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

import '../models/paginated_purchase_list.dart';

part 'purchases_api.g.dart';

@RestApi()
abstract class PurchasesApi {
  factory PurchasesApi(Dio dio, {String? baseUrl}) = _PurchasesApi;

  /// Vehicles awarded to the caller, each with its live invoice.
  ///
  /// [limit] - عدد النتائج التي يجب إرجاعها في كل صفحة.
  ///
  /// [offset] - الفهرس الأولي الذي يجب البدء منه لإرجاع النتائج.
  @GET('/api/v1/purchases/')
  Future<PaginatedPurchaseList> v1PurchasesList({
    @Query('limit') int? limit,
    @Query('offset') int? offset,
  });
}
