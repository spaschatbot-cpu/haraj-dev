// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'specification.dart';

part 'vehicle.g.dart';

@JsonSerializable()
class Vehicle {
  const Vehicle({
    required this.id,
    required this.lotNumber,
    required this.title,
    required this.images,
    required this.specifications,
    required this.currentBidAmount,
    required this.currency,
    required this.biddingOpen,
    this.minimumNextBidAmount,
  });

  factory Vehicle.fromJson(Map<String, Object?> json) =>
      _$VehicleFromJson(json);

  final String id;
  @JsonKey(name: 'lot_number')
  final String lotNumber;
  final String title;
  final List<String> images;
  final List<Specification> specifications;
  @JsonKey(name: 'current_bid_amount')
  final String currentBidAmount;
  @JsonKey(name: 'minimum_next_bid_amount')
  final String? minimumNextBidAmount;
  final String currency;
  @JsonKey(name: 'bidding_open')
  final bool biddingOpen;

  Map<String, Object?> toJson() => _$VehicleToJson(this);
}
