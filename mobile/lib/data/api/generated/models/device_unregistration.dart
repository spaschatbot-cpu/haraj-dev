// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'device_unregistration.g.dart';

@JsonSerializable()
class DeviceUnregistration {
  const DeviceUnregistration({required this.token});

  factory DeviceUnregistration.fromJson(Map<String, Object?> json) =>
      _$DeviceUnregistrationFromJson(json);

  final String token;

  Map<String, Object?> toJson() => _$DeviceUnregistrationToJson(this);
}
