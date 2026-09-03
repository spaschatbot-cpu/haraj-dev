// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

/// حالة تأمين المزايد في مزاد بعينه — يشتقّها الخادم من الحجوزات
@JsonEnum()
enum InsuranceState {
  @JsonValue('none')
  none('none'),
  @JsonValue('held')
  held('held'),
  @JsonValue('locked')
  locked('locked'),
  @JsonValue('released')
  released('released'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const InsuranceState(this.json);

  factory InsuranceState.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<InsuranceState> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
