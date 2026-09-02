// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'profile.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Profile _$ProfileFromJson(Map<String, dynamic> json) => Profile(
  id: json['id'] as String,
  phone: json['phone'] as String,
  fullName: json['full_name'] as String,
  lockedFields: (json['locked_fields'] as List<dynamic>)
      .map((e) => LockedField.fromJson(e as Map<String, dynamic>))
      .toList(),
  nationalId: json['national_id'] as String?,
  companyName: json['company_name'] as String?,
);

Map<String, dynamic> _$ProfileToJson(Profile instance) => <String, dynamic>{
  'id': instance.id,
  'phone': instance.phone,
  'full_name': instance.fullName,
  'national_id': instance.nationalId,
  'company_name': instance.companyName,
  'locked_fields': instance.lockedFields,
};
