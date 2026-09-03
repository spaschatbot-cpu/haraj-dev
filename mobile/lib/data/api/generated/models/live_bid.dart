// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'live_bid.g.dart';

@JsonSerializable()
class LiveBid {
  const LiveBid({
    required this.id,
    required this.vehicleId,
    required this.amount,
    required this.isWithdrawn,
    required this.isSuperseded,
  });

  factory LiveBid.fromJson(Map<String, Object?> json) =>
      _$LiveBidFromJson(json);

  final String id;
  @JsonKey(name: 'vehicle_id')
  final String vehicleId;

  /// نصّ عشري كما في الدفتر
  final String amount;
  @JsonKey(name: 'is_withdrawn')
  final bool isWithdrawn;
  @JsonKey(name: 'is_superseded')
  final bool isSuperseded;

  Map<String, Object?> toJson() => _$LiveBidToJson(this);
}
