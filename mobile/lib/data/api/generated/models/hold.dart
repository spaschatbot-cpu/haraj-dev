// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'reason_enum.dart';

part 'hold.g.dart';

/// A claim on part of the customer's insurance, and what it is claimed for.
@JsonSerializable()
class Hold {
  const Hold({
    required this.id,
    required this.amount,
    required this.reason,
    required this.reasonLabel,
    required this.auction,
    required this.invoice,
    required this.createdAt,
  });

  factory Hold.fromJson(Map<String, Object?> json) => _$HoldFromJson(json);

  final int id;
  final String amount;
  final ReasonEnum reason;
  @JsonKey(name: 'reason_label')
  final String reasonLabel;
  final Map<String, dynamic>? auction;
  final Map<String, dynamic>? invoice;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;

  Map<String, Object?> toJson() => _$HoldToJson(this);
}
