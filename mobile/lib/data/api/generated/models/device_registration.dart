// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'device_registration_platform.dart';

part 'device_registration.g.dart';

@JsonSerializable()
class DeviceRegistration {
  const DeviceRegistration({required this.token, required this.platform});

  factory DeviceRegistration.fromJson(Map<String, Object?> json) =>
      _$DeviceRegistrationFromJson(json);

  final String token;
  final DeviceRegistrationPlatform platform;

  Map<String, Object?> toJson() => _$DeviceRegistrationToJson(this);
}
