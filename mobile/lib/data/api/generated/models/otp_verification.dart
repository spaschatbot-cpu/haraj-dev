// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'otp_verification.g.dart';

@JsonSerializable()
class OtpVerification {
  const OtpVerification({required this.phone, required this.code});

  factory OtpVerification.fromJson(Map<String, Object?> json) =>
      _$OtpVerificationFromJson(json);

  final String phone;
  final String code;

  Map<String, Object?> toJson() => _$OtpVerificationToJson(this);
}
