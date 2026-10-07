// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// * `draft` - مسودة.
/// * `open` - مستحقة.
/// * `partial` - مسدَّدة جزئياً.
/// * `paid` - مسدَّدة.
/// * `cancelled` - ملغاة.
@JsonEnum()
enum InvoiceStateEnum {
  @JsonValue('draft')
  draft('draft'),
  @JsonValue('open')
  open('open'),
  @JsonValue('partial')
  partial('partial'),
  @JsonValue('paid')
  paid('paid'),
  @JsonValue('cancelled')
  cancelled('cancelled'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const InvoiceStateEnum(this.json);

  factory InvoiceStateEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<InvoiceStateEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
