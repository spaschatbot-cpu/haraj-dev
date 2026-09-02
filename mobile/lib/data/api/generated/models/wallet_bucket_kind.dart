// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

@JsonEnum()
enum WalletBucketKind {
  @JsonValue('wallet')
  wallet('wallet'),
  @JsonValue('insurance_free')
  insuranceFree('insurance_free'),
  @JsonValue('insurance_held')
  insuranceHeld('insurance_held'),
  @JsonValue('insurance_locked')
  insuranceLocked('insurance_locked'),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const WalletBucketKind(this.json);

  factory WalletBucketKind.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<WalletBucketKind> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
