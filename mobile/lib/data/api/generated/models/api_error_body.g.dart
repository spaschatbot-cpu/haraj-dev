// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'api_error_body.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ApiErrorBody _$ApiErrorBodyFromJson(Map<String, dynamic> json) => ApiErrorBody(
  code: json['code'] as String,
  message: json['message'] as String,
  details: json['details'],
);

Map<String, dynamic> _$ApiErrorBodyToJson(ApiErrorBody instance) =>
    <String, dynamic>{
      'code': instance.code,
      'message': instance.message,
      'details': instance.details,
    };
