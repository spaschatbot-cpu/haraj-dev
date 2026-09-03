// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'start_phone_change_response.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

StartPhoneChangeResponse _$StartPhoneChangeResponseFromJson(
  Map<String, dynamic> json,
) => StartPhoneChangeResponse(
  sentToCurrent: json['sent_to_current'] as bool,
  sentToNew: json['sent_to_new'] as bool,
  expiresAt: DateTime.parse(json['expires_at'] as String),
  resendAfter: (json['resend_after'] as num).toInt(),
);

Map<String, dynamic> _$StartPhoneChangeResponseToJson(
  StartPhoneChangeResponse instance,
) => <String, dynamic>{
  'sent_to_current': instance.sentToCurrent,
  'sent_to_new': instance.sentToNew,
  'expires_at': instance.expiresAt.toIso8601String(),
  'resend_after': instance.resendAfter,
};
