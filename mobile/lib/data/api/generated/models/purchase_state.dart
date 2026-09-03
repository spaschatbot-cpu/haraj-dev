// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// حالة المركبة التي رست على المشتري
@JsonEnum()
enum PurchaseState {
  @JsonValue('awarded')
  awarded('awarded'),
  @JsonValue('invoiced')
  invoiced('invoiced'),
  @JsonValue('paid')
  paid('paid'),
  @JsonValue('handed_over')
  handedOver('handed_over'),
  @JsonValue('cancelled')
  cancelled('cancelled'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const PurchaseState(this.json);

  factory PurchaseState.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<PurchaseState> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
