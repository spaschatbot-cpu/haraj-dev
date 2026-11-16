// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// * `azure` - أزرق.
/// * `sea` - أزرق بحري.
/// * `gold` - ذهبي.
/// * `violet` - بنفسجي.
/// * `teal` - فيروزي.
/// * `emerald` - أخضر.
/// * `amber` - كهرماني.
/// * `rose` - وردي.
@JsonEnum()
enum AccentEnum {
  @JsonValue('azure')
  azure('azure'),
  @JsonValue('sea')
  sea('sea'),
  @JsonValue('gold')
  gold('gold'),
  @JsonValue('violet')
  violet('violet'),
  @JsonValue('teal')
  teal('teal'),
  @JsonValue('emerald')
  emerald('emerald'),
  @JsonValue('amber')
  amber('amber'),
  @JsonValue('rose')
  rose('rose'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const AccentEnum(this.json);

  factory AccentEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<AccentEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
