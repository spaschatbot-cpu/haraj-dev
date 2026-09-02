// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'bid_status.dart';

part 'bid.g.dart';

@JsonSerializable()
class Bid {
  const Bid({
    required this.id,
    required this.vehicleId,
    required this.amount,
    required this.currency,
    required this.status,
    required this.statusLabel,
    required this.placedAt,
    this.vehicleTitle,
  });

  factory Bid.fromJson(Map<String, Object?> json) => _$BidFromJson(json);

  final String id;
  @JsonKey(name: 'vehicle_id')
  final String vehicleId;
  @JsonKey(name: 'vehicle_title')
  final String? vehicleTitle;
  final String amount;
  final String currency;
  final BidStatus status;

  /// وصف عربي من الخادم — لا خريطة حالات في التطبيق
  @JsonKey(name: 'status_label')
  final String statusLabel;
  @JsonKey(name: 'placed_at')
  final DateTime placedAt;

  Map<String, Object?> toJson() => _$BidToJson(this);
}
