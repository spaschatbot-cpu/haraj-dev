// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

@JsonEnum()
enum State2 {
  @JsonValue('draft')
  draft('draft'),
  @JsonValue('listed')
  listed('listed'),
  @JsonValue('bidding')
  bidding('bidding'),
  @JsonValue('awaiting_decision')
  awaitingDecision('awaiting_decision'),
  @JsonValue('awarded')
  awarded('awarded'),
  @JsonValue('rejected')
  rejected('rejected'),
  @JsonValue('invoiced')
  invoiced('invoiced'),
  @JsonValue('paid')
  paid('paid'),
  @JsonValue('released')
  released('released'),
  @JsonValue('withdrawn')
  withdrawn('withdrawn'),
  @JsonValue('relisted')
  relisted('relisted'),
  @JsonValue('')
  empty(''),

  /// Default value for all unparsed values, allows backward compatibility when adding new values on the backend.
  $unknown(null);

  const State2(this.json);

  factory State2.fromJson(String json) =>
      values.firstWhere((e) => e.json == json, orElse: () => $unknown);

  final String? json;

  @override
  String toString() => json?.toString() ?? super.toString();

  /// Returns all defined enum values excluding the $unknown value.
  static List<State2> get $valuesDefined =>
      values.where((value) => value != $unknown).toList();
}
