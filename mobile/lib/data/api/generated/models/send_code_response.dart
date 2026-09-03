// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'send_code_response.g.dart';

@JsonSerializable()
class SendCodeResponse {
  const SendCodeResponse({
    required this.sent,
    required this.expiresAt,
    required this.resendAfter,
  });

  factory SendCodeResponse.fromJson(Map<String, Object?> json) =>
      _$SendCodeResponseFromJson(json);

  final bool sent;

  /// ISO-8601 بتوقيت UTC — التحويل للعرض عند حافة العرض وحدها
  @JsonKey(name: 'expires_at')
  final DateTime expiresAt;

  /// ثوانٍ حتى يُسمح بطلب رمز جديد
  @JsonKey(name: 'resend_after')
  final int resendAfter;

  Map<String, Object?> toJson() => _$SendCodeResponseToJson(this);
}
