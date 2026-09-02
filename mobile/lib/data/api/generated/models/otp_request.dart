// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'otp_request.g.dart';

@JsonSerializable()
class OtpRequest {
  const OtpRequest({required this.phone});

  factory OtpRequest.fromJson(Map<String, Object?> json) =>
      _$OtpRequestFromJson(json);

  final String phone;

  Map<String, Object?> toJson() => _$OtpRequestToJson(this);
}
