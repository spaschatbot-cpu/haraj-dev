// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// * `requested` - مُقدَّم.
/// * `sent` - أُرسل للمحاسبة.
/// * `confirmed` - نُفِّذ.
/// * `rejected` - مرفوض.
/// * `cancelled` - ألغاه العميل.
@JsonEnum()
enum RefundRequestStateEnum {
  @JsonValue('requested')
  requested('requested'),
  @JsonValue('sent')
  sent('sent'),
  @JsonValue('confirmed')
  confirmed('confirmed'),
  @JsonValue('rejected')
  rejected('rejected'),
  @JsonValue('cancelled')
  cancelled('cancelled'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const RefundRequestStateEnum(this.json);

  factory RefundRequestStateEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<RefundRequestStateEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
