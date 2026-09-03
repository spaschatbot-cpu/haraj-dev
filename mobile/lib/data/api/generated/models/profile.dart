// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'locked_field.dart';

part 'profile.g.dart';

@JsonSerializable()
class Profile {
  const Profile({
    required this.id,
    required this.phone,
    required this.displayName,
    required this.fullName,
    required this.accountType,
    required this.nationalId,
    required this.nationalIdVerified,
    required this.phoneVerifiedAt,
    required this.hasCompanyProfile,
    required this.companyProfileComplete,
    required this.lockedFields,
    this.email,
  });

  factory Profile.fromJson(Map<String, Object?> json) =>
      _$ProfileFromJson(json);

  final int id;

  /// يتغيّر عبر مسار خاص
  final String phone;
  @JsonKey(name: 'display_name')
  final String displayName;
  @JsonKey(name: 'full_name')
  final String fullName;
  final String? email;
  @JsonKey(name: 'account_type')
  final String accountType;
  @JsonKey(name: 'national_id')
  final String nationalId;
  @JsonKey(name: 'national_id_verified')
  final bool nationalIdVerified;
  @JsonKey(name: 'phone_verified_at')
  final DateTime? phoneVerifiedAt;
  @JsonKey(name: 'has_company_profile')
  final bool hasCompanyProfile;
  @JsonKey(name: 'company_profile_complete')
  final bool companyProfileComplete;

  /// الحقول التي تُعرض ولا تُعدَّل، وسبب كلٍّ منها بالعربية
  @JsonKey(name: 'locked_fields')
  final List<LockedField> lockedFields;

  Map<String, Object?> toJson() => _$ProfileToJson(this);
}
