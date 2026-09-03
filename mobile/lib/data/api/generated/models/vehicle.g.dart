// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Vehicle _$VehicleFromJson(Map<String, dynamic> json) => Vehicle(
  id: json['id'] as String,
  lotNumber: json['lot_number'] as String,
  title: json['title'] as String,
  images: (json['images'] as List<dynamic>).map((e) => e as String).toList(),
  specifications: (json['specifications'] as List<dynamic>)
      .map((e) => Specification.fromJson(e as Map<String, dynamic>))
      .toList(),
  reservePrice: json['reserve_price'] as String?,
  currentBidAmount: json['current_bid_amount'] as String,
  currency: json['currency'] as String,
  biddingOpen: json['bidding_open'] as bool,
  minimumNextBidAmount: json['minimum_next_bid_amount'] as String?,
);

Map<String, dynamic> _$VehicleToJson(Vehicle instance) => <String, dynamic>{
  'id': instance.id,
  'lot_number': instance.lotNumber,
  'title': instance.title,
  'images': instance.images,
  'specifications': instance.specifications,
  'reserve_price': instance.reservePrice,
  'current_bid_amount': instance.currentBidAmount,
  'minimum_next_bid_amount': instance.minimumNextBidAmount,
  'currency': instance.currency,
  'bidding_open': instance.biddingOpen,
};
