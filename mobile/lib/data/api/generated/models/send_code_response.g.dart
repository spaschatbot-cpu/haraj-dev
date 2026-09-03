// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'send_code_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SendCodeResponse _$SendCodeResponseFromJson(Map<String, dynamic> json) =>
    SendCodeResponse(
      sent: json['sent'] as bool,
      expiresAt: DateTime.parse(json['expires_at'] as String),
      resendAfter: (json['resend_after'] as num).toInt(),
    );

Map<String, dynamic> _$SendCodeResponseToJson(SendCodeResponse instance) =>
    <String, dynamic>{
      'sent': instance.sent,
      'expires_at': instance.expiresAt.toIso8601String(),
      'resend_after': instance.resendAfter,
    };
