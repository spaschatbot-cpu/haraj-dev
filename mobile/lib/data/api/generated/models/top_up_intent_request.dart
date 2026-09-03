// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'top_up_intent_request.g.dart';

@JsonSerializable()
class TopUpIntentRequest {
  const TopUpIntentRequest({this.preset});

  factory TopUpIntentRequest.fromJson(Map<String, Object?> json) =>
      _$TopUpIntentRequestFromJson(json);

  /// مفتاح مبلغ معرَّف في الخادم. اختياري لأن الخادم هو من يحدّد المبلغ أصلاً (`deposit_amount_for` في الخلفية)، وطلب بلا مفتاح يعني «المبلغ الذي تقرّره أنت». التطبيق لا يرسل مبلغاً في أي حال.
  ///
  final String? preset;

  Map<String, Object?> toJson() => _$TopUpIntentRequestToJson(this);
}
