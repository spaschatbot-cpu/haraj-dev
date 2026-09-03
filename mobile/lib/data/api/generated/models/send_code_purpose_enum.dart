// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// login دخول أو تسجيل · change_phone تغيير رقم الجوال · recover استعادة الحساب.
///
@JsonEnum()
enum SendCodePurposeEnum {
  @JsonValue('login')
  login('login'),
  @JsonValue('change_phone')
  changePhone('change_phone'),
  @JsonValue('recover')
  recover('recover'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const SendCodePurposeEnum(this.json);

  factory SendCodePurposeEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<SendCodePurposeEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
