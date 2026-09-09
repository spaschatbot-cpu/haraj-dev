// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bid.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Bid _$BidFromJson(Map<String, dynamic> json) => Bid(
  id: (json['id'] as num).toInt(),
  vehicleId: (json['vehicle_id'] as num).toInt(),
  auctionId: (json['auction_id'] as num).toInt(),
  lotNumber: (json['lot_number'] as num).toInt(),
  vehicleTitle: json['vehicle_title'] as String,
  amount: json['amount'] as String,
  placedAt: DateTime.parse(json['placed_at'] as String),
  isWithdrawn: json['is_withdrawn'] as bool,
  isSuperseded: json['is_superseded'] as bool,
);

Map<String, dynamic> _$BidToJson(Bid instance) => <String, dynamic>{
  'id': instance.id,
  'vehicle_id': instance.vehicleId,
  'auction_id': instance.auctionId,
  'lot_number': instance.lotNumber,
  'vehicle_title': instance.vehicleTitle,
  'amount': instance.amount,
  'placed_at': instance.placedAt.toIso8601String(),
  'is_withdrawn': instance.isWithdrawn,
  'is_superseded': instance.isSuperseded,
};
