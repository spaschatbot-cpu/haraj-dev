// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'auction_card.g.dart';

/// The auction row, as `cards.auction_card` builds it.
@JsonSerializable()
class AuctionCard {
  const AuctionCard({
    required this.id,
    required this.number,
    required this.title,
    required this.state,
    required this.stateLabel,
    required this.startsAt,
    required this.endsAt,
    required this.vehicleCount,
    required this.openVehicleCount,
  });

  factory AuctionCard.fromJson(Map<String, Object?> json) =>
      _$AuctionCardFromJson(json);

  final int id;
  final int number;
  final String title;
  final String state;
  @JsonKey(name: 'state_label')
  final String stateLabel;
  @JsonKey(name: 'starts_at')
  final DateTime startsAt;
  @JsonKey(name: 'ends_at')
  final DateTime endsAt;
  @JsonKey(name: 'vehicle_count')
  final int? vehicleCount;
  @JsonKey(name: 'open_vehicle_count')
  final int? openVehicleCount;

  Map<String, Object?> toJson() => _$AuctionCardToJson(this);
}
