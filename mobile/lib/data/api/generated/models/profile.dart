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
    required this.fullName,
    required this.lockedFields,
    this.nationalId,
    this.companyName,
  });

  factory Profile.fromJson(Map<String, Object?> json) =>
      _$ProfileFromJson(json);

  final String id;
  final String phone;
  @JsonKey(name: 'full_name')
  final String fullName;
  @JsonKey(name: 'national_id')
  final String? nationalId;
  @JsonKey(name: 'company_name')
  final String? companyName;

  /// الحقول المقفولة وسبب قفلها العربي
  @JsonKey(name: 'locked_fields')
  final List<LockedField> lockedFields;

  Map<String, Object?> toJson() => _$ProfileToJson(this);
}
