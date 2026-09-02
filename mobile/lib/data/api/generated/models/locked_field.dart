// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'locked_field.g.dart';

@JsonSerializable()
class LockedField {
  const LockedField({required this.field, required this.reason});

  factory LockedField.fromJson(Map<String, Object?> json) =>
      _$LockedFieldFromJson(json);

  final String field;

  /// سبب عربي جاهز للعرض
  final String reason;

  Map<String, Object?> toJson() => _$LockedFieldToJson(this);
}
