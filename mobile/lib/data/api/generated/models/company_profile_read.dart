// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'company_profile_read.g.dart';

@JsonSerializable()
class CompanyProfileRead {
  const CompanyProfileRead({
    required this.isComplete,
    this.name,
    this.representativeName,
    this.commercialRegister,
    this.vatNumber,
    this.buildingNumber,
    this.street,
    this.district,
    this.city,
    this.postalCode,
  });

  factory CompanyProfileRead.fromJson(Map<String, Object?> json) =>
      _$CompanyProfileReadFromJson(json);

  final String? name;
  @JsonKey(name: 'representative_name')
  final String? representativeName;
  @JsonKey(name: 'commercial_register')
  final String? commercialRegister;
  @JsonKey(name: 'vat_number')
  final String? vatNumber;
  @JsonKey(name: 'building_number')
  final String? buildingNumber;
  final String? street;
  final String? district;
  final String? city;
  @JsonKey(name: 'postal_code')
  final String? postalCode;

  /// هل تكفي هذه البيانات لإصدار فاتورة ضريبية
  @JsonKey(name: 'is_complete')
  final bool isComplete;

  Map<String, Object?> toJson() => _$CompanyProfileReadToJson(this);
}
