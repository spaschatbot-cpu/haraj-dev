// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'registration_gap.g.dart';

@JsonSerializable()
class RegistrationGap {
  const RegistrationGap({required this.field, required this.label});

  factory RegistrationGap.fromJson(Map<String, Object?> json) =>
      _$RegistrationGapFromJson(json);

  final String field;

  /// اسمُ الحقل بالعربيّة، جاهزٌ للعرض
  final String label;

  Map<String, Object?> toJson() => _$RegistrationGapToJson(this);
}
