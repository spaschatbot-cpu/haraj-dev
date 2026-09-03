// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'start_phone_change_response.g.dart';

@JsonSerializable()
class StartPhoneChangeResponse {
  const StartPhoneChangeResponse({
    required this.sentToCurrent,
    required this.sentToNew,
    required this.expiresAt,
    required this.resendAfter,
  });

  factory StartPhoneChangeResponse.fromJson(Map<String, Object?> json) =>
      _$StartPhoneChangeResponseFromJson(json);

  @JsonKey(name: 'sent_to_current')
  final bool sentToCurrent;
  @JsonKey(name: 'sent_to_new')
  final bool sentToNew;
  @JsonKey(name: 'expires_at')
  final DateTime expiresAt;
  @JsonKey(name: 'resend_after')
  final int resendAfter;

  Map<String, Object?> toJson() => _$StartPhoneChangeResponseToJson(this);
}
