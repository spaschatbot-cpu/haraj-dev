// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'auction_card.dart';
import 'participation_insurance.dart';

part 'participation.g.dart';

@JsonSerializable()
class Participation {
  const Participation({
    required this.auction,
    required this.bidsCount,
    required this.insurance,
  });

  factory Participation.fromJson(Map<String, Object?> json) =>
      _$ParticipationFromJson(json);

  final AuctionCard auction;
  @JsonKey(name: 'bids_count')
  final int bidsCount;
  final ParticipationInsurance insurance;

  Map<String, Object?> toJson() => _$ParticipationToJson(this);
}
