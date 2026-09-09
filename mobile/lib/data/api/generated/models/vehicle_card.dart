// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'vehicle_card.g.dart';

/// The vehicle card — the same fields in the list and on the detail page.
///
/// T609's acceptance criterion is that those two are identical, and.
/// `test_vehicle_api.py` asserts it by comparing the key sets rather than by.
/// reading this class, so the guarantee does not depend on this file being.
/// kept honest by hand.
@JsonSerializable()
class VehicleCard {
  const VehicleCard({
    required this.id,
    required this.auctionId,
    required this.auctionNumber,
    required this.auctionTitle,
    required this.auctionState,
    required this.phase,
    required this.auctionStartsAt,
    required this.auctionEndsAt,
    required this.lotNumber,
    required this.reference,
    required this.title,
    required this.make,
    required this.model,
    required this.year,
    required this.colour,
    required this.colourLabel,
    required this.odometerKm,
    required this.condition,
    required this.conditionLabel,
    required this.location,
    required this.adminFee,
    required this.adminFeeWithVat,
    required this.state,
    required this.thumbnailUrl,
  });

  factory VehicleCard.fromJson(Map<String, Object?> json) =>
      _$VehicleCardFromJson(json);

  final int id;
  @JsonKey(name: 'auction_id')
  final int auctionId;
  @JsonKey(name: 'auction_number')
  final int auctionNumber;
  @JsonKey(name: 'auction_title')
  final String auctionTitle;
  @JsonKey(name: 'auction_state')
  final String auctionState;

  /// التبويب الذي يقرّره الخادم: `soon`، `active`، `ended`، أو `""` (فراغ) لمزادٍ خارج الثلاثة — مسودّةٍ أو ملغيّ، لا يراه إلا موظّف. الفراغ يُقرأ «غير معروف» ولا يُطوى في `ended` (المادة ٢-٣).
  final String phase;
  @JsonKey(name: 'auction_starts_at')
  final DateTime auctionStartsAt;
  @JsonKey(name: 'auction_ends_at')
  final DateTime auctionEndsAt;
  @JsonKey(name: 'lot_number')
  final int lotNumber;
  final String reference;
  final String title;
  final String make;
  final String model;
  final int year;
  final String colour;
  @JsonKey(name: 'colour_label')
  final String colourLabel;
  @JsonKey(name: 'odometer_km')
  final int? odometerKm;
  final String condition;
  @JsonKey(name: 'condition_label')
  final String conditionLabel;
  final String location;
  @JsonKey(name: 'admin_fee')
  final String adminFee;
  @JsonKey(name: 'admin_fee_with_vat')
  final String adminFeeWithVat;
  final String state;
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;

  Map<String, Object?> toJson() => _$VehicleCardToJson(this);
}
