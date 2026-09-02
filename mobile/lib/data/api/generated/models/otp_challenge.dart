// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'otp_challenge.g.dart';

@JsonSerializable()
class OtpChallenge {
  const OtpChallenge({
    required this.expiresAt,
    required this.resendAfterSeconds,
  });

  factory OtpChallenge.fromJson(Map<String, Object?> json) =>
      _$OtpChallengeFromJson(json);

  @JsonKey(name: 'expires_at')
  final DateTime expiresAt;
  @JsonKey(name: 'resend_after_seconds')
  final int resendAfterSeconds;

  Map<String, Object?> toJson() => _$OtpChallengeToJson(this);
}
