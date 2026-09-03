// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'company_profile.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CompanyProfile _$CompanyProfileFromJson(Map<String, dynamic> json) =>
    CompanyProfile(
      name: json['name'] as String?,
      representativeName: json['representative_name'] as String?,
      commercialRegister: json['commercial_register'] as String?,
      vatNumber: json['vat_number'] as String?,
      buildingNumber: json['building_number'] as String?,
      street: json['street'] as String?,
      district: json['district'] as String?,
      city: json['city'] as String?,
      postalCode: json['postal_code'] as String?,
    );

Map<String, dynamic> _$CompanyProfileToJson(CompanyProfile instance) =>
    <String, dynamic>{
      'name': instance.name,
      'representative_name': instance.representativeName,
      'commercial_register': instance.commercialRegister,
      'vat_number': instance.vatNumber,
      'building_number': instance.buildingNumber,
      'street': instance.street,
      'district': instance.district,
      'city': instance.city,
      'postal_code': instance.postalCode,
    };
