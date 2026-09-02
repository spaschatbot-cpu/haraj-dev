// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'device_platform.dart';

part 'device.g.dart';

@JsonSerializable()
class Device {
  const Device({
    required this.id,
    required this.platform,
    required this.registeredAt,
  });

  factory Device.fromJson(Map<String, Object?> json) => _$DeviceFromJson(json);

  final String id;
  final DevicePlatform platform;
  @JsonKey(name: 'registered_at')
  final DateTime registeredAt;

  Map<String, Object?> toJson() => _$DeviceToJson(this);
}
