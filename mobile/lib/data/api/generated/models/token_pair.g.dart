// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'token_pair.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

TokenPair _$TokenPairFromJson(Map<String, dynamic> json) => TokenPair(
  access: json['access'] as String,
  refresh: json['refresh'] as String,
  accessExpiresAt: DateTime.parse(json['access_expires_at'] as String),
  isNewUser: json['is_new_user'] as bool,
);

Map<String, dynamic> _$TokenPairToJson(TokenPair instance) => <String, dynamic>{
  'access': instance.access,
  'refresh': instance.refresh,
  'access_expires_at': instance.accessExpiresAt.toIso8601String(),
  'is_new_user': instance.isNewUser,
};
