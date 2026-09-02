// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'top_up_intent_request.g.dart';

@JsonSerializable()
class TopUpIntentRequest {
  const TopUpIntentRequest({required this.preset});

  factory TopUpIntentRequest.fromJson(Map<String, Object?> json) =>
      _$TopUpIntentRequestFromJson(json);

  /// مفتاح مبلغ معرَّف في الخادم — التطبيق لا يرسل مبلغاً
  final String preset;

  Map<String, Object?> toJson() => _$TopUpIntentRequestToJson(this);
}
