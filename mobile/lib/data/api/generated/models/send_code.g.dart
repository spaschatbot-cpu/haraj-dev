// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'send_code.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SendCode _$SendCodeFromJson(Map<String, dynamic> json) => SendCode(
  phone: json['phone'] as String,
  purpose: json['purpose'] == null
      ? null
      : SendCodePurposeEnum.fromJson(json['purpose'] as String),
);

Map<String, dynamic> _$SendCodeToJson(SendCode instance) => <String, dynamic>{
  'phone': instance.phone,
  'purpose': _$SendCodePurposeEnumEnumMap[instance.purpose],
};

const _$SendCodePurposeEnumEnumMap = {
  SendCodePurposeEnum.login: 'login',
  SendCodePurposeEnum.changePhone: 'change_phone',
  SendCodePurposeEnum.recover: 'recover',
  SendCodePurposeEnum.$unknown: r'$unknown',
};
