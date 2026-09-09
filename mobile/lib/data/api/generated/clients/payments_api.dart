// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:dio/dio.dart';
import 'package:retrofit/retrofit.dart';

part 'payments_api.g.dart';

@RestApi()
abstract class PaymentsApi {
  factory PaymentsApi(Dio dio, {String? baseUrl}) = _PaymentsApi;

  /// The gateway telling us what happened. The only path that credits a card.
  ///
  /// Stored raw and acknowledged before anything interprets it (Article 2-1), and.
  /// never dropped: a message we cannot use is kept with the reason written on it.
  /// (Article 2-2).
  @POST('/api/v1/payments/callback/')
  Future<void> v1PaymentsCallbackCreate();
}
