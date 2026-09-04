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
  reservePrice: json['reserve_price'] as String?,
  currentBidAmount: json['current_bid_amount'] as String,
  currency: json['currency'] as String,
  bidsCount: (json['bids_count'] as num).toInt(),
  auctionId: json['auction_id'] as String,
  phase: AuctionPhase.fromJson(json['phase'] as String),
  auctionEndsAt: DateTime.parse(json['auction_ends_at'] as String),
);

Map<String, dynamic> _$VehicleCardToJson(VehicleCard instance) =>
    <String, dynamic>{
      'id': instance.id,
      'lot_number': instance.lotNumber,
      'title': instance.title,
      'thumbnail_url': instance.thumbnailUrl,
      'reserve_price': instance.reservePrice,
      'current_bid_amount': instance.currentBidAmount,
      'currency': instance.currency,
      'bids_count': instance.bidsCount,
      'auction_id': instance.auctionId,
      'phase': _$AuctionPhaseEnumMap[instance.phase]!,
      'auction_ends_at': instance.auctionEndsAt.toIso8601String(),
    };

const _$AuctionPhaseEnumMap = {
  AuctionPhase.upcoming: 'upcoming',
  AuctionPhase.active: 'active',
  AuctionPhase.ended: 'ended',
  AuctionPhase.$unknown: r'$unknown',
};
