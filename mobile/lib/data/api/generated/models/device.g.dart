// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Device _$DeviceFromJson(Map<String, dynamic> json) => Device(
  id: (json['id'] as num).toInt(),
  platform: json['platform'] as String,
  createdAt: DateTime.parse(json['created_at'] as String),
  tokenTail: json['token_tail'] as String,
);

Map<String, dynamic> _$DeviceToJson(Device instance) => <String, dynamic>{
  'id': instance.id,
  'platform': instance.platform,
  'created_at': instance.createdAt.toIso8601String(),
  'token_tail': instance.tokenTail,
};
