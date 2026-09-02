// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Device _$DeviceFromJson(Map<String, dynamic> json) => Device(
  id: json['id'] as String,
  platform: DevicePlatform.fromJson(json['platform'] as String),
  registeredAt: DateTime.parse(json['registered_at'] as String),
);

Map<String, dynamic> _$DeviceToJson(Device instance) => <String, dynamic>{
  'id': instance.id,
  'platform': _$DevicePlatformEnumMap[instance.platform]!,
  'registered_at': instance.registeredAt.toIso8601String(),
};

const _$DevicePlatformEnumMap = {
  DevicePlatform.android: 'android',
  DevicePlatform.ios: 'ios',
  DevicePlatform.$unknown: r'$unknown',
};
