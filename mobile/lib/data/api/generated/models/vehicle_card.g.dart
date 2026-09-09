// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_card.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehicleCard _$VehicleCardFromJson(Map<String, dynamic> json) => VehicleCard(
  id: (json['id'] as num).toInt(),
  auctionId: (json['auction_id'] as num).toInt(),
  auctionNumber: (json['auction_number'] as num).toInt(),
  auctionTitle: json['auction_title'] as String,
  auctionState: json['auction_state'] as String,
  phase: json['phase'] as String,
  auctionStartsAt: DateTime.parse(json['auction_starts_at'] as String),
  auctionEndsAt: DateTime.parse(json['auction_ends_at'] as String),
  lotNumber: (json['lot_number'] as num).toInt(),
  reference: json['reference'] as String,
  title: json['title'] as String,
  make: json['make'] as String,
  model: json['model'] as String,
  year: (json['year'] as num).toInt(),
  colour: json['colour'] as String,
  colourLabel: json['colour_label'] as String,
  odometerKm: (json['odometer_km'] as num?)?.toInt(),
  condition: json['condition'] as String,
  conditionLabel: json['condition_label'] as String,
  location: json['location'] as String,
  adminFee: json['admin_fee'] as String,
  adminFeeWithVat: json['admin_fee_with_vat'] as String,
  state: json['state'] as String,
  thumbnailUrl: json['thumbnail_url'] as String?,
);

Map<String, dynamic> _$VehicleCardToJson(VehicleCard instance) =>
    <String, dynamic>{
      'id': instance.id,
      'auction_id': instance.auctionId,
      'auction_number': instance.auctionNumber,
      'auction_title': instance.auctionTitle,
      'auction_state': instance.auctionState,
      'phase': instance.phase,
      'auction_starts_at': instance.auctionStartsAt.toIso8601String(),
      'auction_ends_at': instance.auctionEndsAt.toIso8601String(),
      'lot_number': instance.lotNumber,
      'reference': instance.reference,
      'title': instance.title,
      'make': instance.make,
      'model': instance.model,
      'year': instance.year,
      'colour': instance.colour,
      'colour_label': instance.colourLabel,
      'odometer_km': instance.odometerKm,
      'condition': instance.condition,
      'condition_label': instance.conditionLabel,
      'location': instance.location,
      'admin_fee': instance.adminFee,
      'admin_fee_with_vat': instance.adminFeeWithVat,
      'state': instance.state,
      'thumbnail_url': instance.thumbnailUrl,
    };
