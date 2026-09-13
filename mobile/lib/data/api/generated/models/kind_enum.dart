// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// * `cr` - السجل التجاري.
/// * `tax` - الشهادة الضريبية.
/// * `id` - صورة الهوية.
/// * `iban` - صورة الآيبان.
@JsonEnum()
enum KindEnum {
  @JsonValue('cr')
  cr('cr'),
  @JsonValue('tax')
  tax('tax'),
  @JsonValue('id')
  id('id'),
  @JsonValue('iban')
  iban('iban'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const KindEnum(this.json);

  factory KindEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<KindEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
