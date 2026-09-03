// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'token_pair.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

TokenPair _$TokenPairFromJson(Map<String, dynamic> json) => TokenPair(
  access: json['access'] as String,
  refresh: json['refresh'] as String,
  expiresIn: (json['expires_in'] as num).toInt(),
  expiresAt: DateTime.parse(json['expires_at'] as String),
  user: json['user'] == null
      ? null
      : AuthenticatedUser.fromJson(json['user'] as Map<String, dynamic>),
);

Map<String, dynamic> _$TokenPairToJson(TokenPair instance) => <String, dynamic>{
  'access': instance.access,
  'refresh': instance.refresh,
  'expires_in': instance.expiresIn,
  'expires_at': instance.expiresAt.toIso8601String(),
  'user': instance.user,
};
