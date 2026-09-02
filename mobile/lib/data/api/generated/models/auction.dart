// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'auction_status.dart';

part 'auction.g.dart';

@JsonSerializable()
class Auction {
  const Auction({
    required this.id,
    required this.title,
    required this.status,
    required this.startsAt,
    required this.endsAt,
    required this.vehiclesCount,
  });

  factory Auction.fromJson(Map<String, Object?> json) =>
      _$AuctionFromJson(json);

  final String id;
  final String title;
  final AuctionStatus status;

  /// ISO-8601 بتوقيت UTC — التحويل للعرض في التطبيق
  @JsonKey(name: 'starts_at')
  final DateTime startsAt;
  @JsonKey(name: 'ends_at')
  final DateTime endsAt;
  @JsonKey(name: 'vehicles_count')
  final int vehiclesCount;

  Map<String, Object?> toJson() => _$AuctionToJson(this);
}
