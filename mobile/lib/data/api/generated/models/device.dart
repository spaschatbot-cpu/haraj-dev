// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'device.g.dart';

/// A registered handset, as its owner sees it.
@JsonSerializable()
class Device {
  const Device({
    required this.id,
    required this.platform,
    required this.createdAt,
    required this.tokenTail,
  });

  factory Device.fromJson(Map<String, Object?> json) => _$DeviceFromJson(json);

  final int id;
  final String platform;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  /// آخر ستة أحرف، للتمييز فقط
  @JsonKey(name: 'token_tail')
  final String tokenTail;

  Map<String, Object?> toJson() => _$DeviceToJson(this);
}
