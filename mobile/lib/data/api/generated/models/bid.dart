// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'bid.g.dart';

/// A bid as the owner of it sees it.
///
/// Never anybody else's: a sealed auction's whole property is that bidders.
/// cannot see each other's numbers, so there is no endpoint here that lists the.
/// bids *on* a car — only the bids *by* the caller.
@JsonSerializable()
class Bid {
  const Bid({
    required this.id,
    required this.vehicleId,
    required this.auctionId,
    required this.lotNumber,
    required this.vehicleTitle,
    required this.amount,
    required this.placedAt,
    required this.isWithdrawn,
    required this.isSuperseded,
  });

  factory Bid.fromJson(Map<String, Object?> json) => _$BidFromJson(json);

  final int id;
  @JsonKey(name: 'vehicle_id')
  final int vehicleId;
  @JsonKey(name: 'auction_id')
  final int auctionId;
  @JsonKey(name: 'lot_number')
  final int lotNumber;
  @JsonKey(name: 'vehicle_title')
  final String vehicleTitle;
  final String amount;
  @JsonKey(name: 'placed_at')
  final DateTime placedAt;
  @JsonKey(name: 'is_withdrawn')
  final bool isWithdrawn;
  @JsonKey(name: 'is_superseded')
  final bool isSuperseded;

  Map<String, Object?> toJson() => _$BidToJson(this);
}
