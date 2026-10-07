// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// * `pending` - بانتظار الدفع.
/// * `succeeded` - تمت.
/// * `failed` - فشلت.
/// * `cancelled` - ألغاها العميل.
/// * `expired` - انتهت مهلتها.
/// * `disputed` - محل نزاع.
@JsonEnum()
enum PaymentIntentStateEnum {
  @JsonValue('pending')
  pending('pending'),
  @JsonValue('succeeded')
  succeeded('succeeded'),
  @JsonValue('failed')
  failed('failed'),
  @JsonValue('cancelled')
  cancelled('cancelled'),
  @JsonValue('expired')
  expired('expired'),
  @JsonValue('disputed')
  disputed('disputed'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const PaymentIntentStateEnum(this.json);

  factory PaymentIntentStateEnum.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<PaymentIntentStateEnum> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
