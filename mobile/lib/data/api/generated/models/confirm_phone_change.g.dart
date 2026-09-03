// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'confirm_phone_change.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ConfirmPhoneChange _$ConfirmPhoneChangeFromJson(Map<String, dynamic> json) =>
    ConfirmPhoneChange(
      newPhone: json['new_phone'] as String,
      currentCode: json['current_code'] as String,
      newCode: json['new_code'] as String,
    );

Map<String, dynamic> _$ConfirmPhoneChangeToJson(ConfirmPhoneChange instance) =>
    <String, dynamic>{
      'new_phone': instance.newPhone,
      'current_code': instance.currentCode,
      'new_code': instance.newCode,
    };
