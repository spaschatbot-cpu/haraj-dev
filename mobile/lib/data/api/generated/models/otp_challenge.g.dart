// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'otp_challenge.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

OtpChallenge _$OtpChallengeFromJson(Map<String, dynamic> json) => OtpChallenge(
  expiresAt: DateTime.parse(json['expires_at'] as String),
  resendAfterSeconds: (json['resend_after_seconds'] as num).toInt(),
);

Map<String, dynamic> _$OtpChallengeToJson(OtpChallenge instance) =>
    <String, dynamic>{
      'expires_at': instance.expiresAt.toIso8601String(),
      'resend_after_seconds': instance.resendAfterSeconds,
    };
