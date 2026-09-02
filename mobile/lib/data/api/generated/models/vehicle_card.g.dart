// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_card.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehicleCard _$VehicleCardFromJson(Map<String, dynamic> json) => VehicleCard(
  id: json['id'] as String,
  lotNumber: json['lot_number'] as String,
  title: json['title'] as String,
  thumbnailUrl: json['thumbnail_url'] as String?,
  currentBidAmount: json['current_bid_amount'] as String,
  currency: json['currency'] as String,
  bidsCount: (json['bids_count'] as num).toInt(),
);

Map<String, dynamic> _$VehicleCardToJson(VehicleCard instance) =>
    <String, dynamic>{
      'id': instance.id,
      'lot_number': instance.lotNumber,
      'title': instance.title,
      'thumbnail_url': instance.thumbnailUrl,
      'current_bid_amount': instance.currentBidAmount,
      'currency': instance.currency,
      'bids_count': instance.bidsCount,
    };
