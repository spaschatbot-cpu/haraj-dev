// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'verify_code.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VerifyCode _$VerifyCodeFromJson(Map<String, dynamic> json) => VerifyCode(
  phone: json['phone'] as String,
  code: json['code'] as String,
  fullName: json['full_name'] as String?,
);

Map<String, dynamic> _$VerifyCodeToJson(VerifyCode instance) =>
    <String, dynamic>{
      'phone': instance.phone,
      'code': instance.code,
      'full_name': instance.fullName,
    };
