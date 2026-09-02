// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_registration.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DeviceRegistration _$DeviceRegistrationFromJson(Map<String, dynamic> json) =>
    DeviceRegistration(
      token: json['token'] as String,
      platform: DeviceRegistrationPlatform.fromJson(json['platform'] as String),
    );

Map<String, dynamic> _$DeviceRegistrationToJson(DeviceRegistration instance) =>
    <String, dynamic>{
      'token': instance.token,
      'platform': _$DeviceRegistrationPlatformEnumMap[instance.platform]!,
    };

const _$DeviceRegistrationPlatformEnumMap = {
  DeviceRegistrationPlatform.android: 'android',
  DeviceRegistrationPlatform.ios: 'ios',
  DeviceRegistrationPlatform.$unknown: r'$unknown',
};
