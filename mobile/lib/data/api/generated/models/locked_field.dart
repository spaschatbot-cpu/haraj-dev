// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'locked_field.g.dart';

/// A field the customer can read but not write, and why not.
///
/// `reason` is Arabic and ready to put on a screen. It is a sentence rather.
/// than a code because there is no behaviour to branch on — the client shows.
/// the field closed and prints this beside it.
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
