// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'profile.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Profile _$ProfileFromJson(Map<String, dynamic> json) => Profile(
  id: (json['id'] as num).toInt(),
  phone: json['phone'] as String,
  displayName: json['display_name'] as String,
  fullName: json['full_name'] as String,
  accountType: json['account_type'] as String,
  nationalId: json['national_id'] as String,
  nationalIdVerified: json['national_id_verified'] as bool,
  phoneVerifiedAt: json['phone_verified_at'] == null
      ? null
      : DateTime.parse(json['phone_verified_at'] as String),
  hasCompanyProfile: json['has_company_profile'] as bool,
  companyProfileComplete: json['company_profile_complete'] as bool,
  lockedFields: (json['locked_fields'] as List<dynamic>)
      .map((e) => LockedField.fromJson(e as Map<String, dynamic>))
      .toList(),
  email: json['email'] as String?,
);

Map<String, dynamic> _$ProfileToJson(Profile instance) => <String, dynamic>{
  'id': instance.id,
  'phone': instance.phone,
  'display_name': instance.displayName,
  'full_name': instance.fullName,
  'email': instance.email,
  'account_type': instance.accountType,
  'national_id': instance.nationalId,
  'national_id_verified': instance.nationalIdVerified,
  'phone_verified_at': instance.phoneVerifiedAt?.toIso8601String(),
  'has_company_profile': instance.hasCompanyProfile,
  'company_profile_complete': instance.companyProfileComplete,
  'locked_fields': instance.lockedFields,
};
