// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'live_bid.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LiveBid _$LiveBidFromJson(Map<String, dynamic> json) => LiveBid(
  id: json['id'] as String,
  vehicleId: json['vehicle_id'] as String,
  amount: json['amount'] as String,
  isWithdrawn: json['is_withdrawn'] as bool,
  isSuperseded: json['is_superseded'] as bool,
);

Map<String, dynamic> _$LiveBidToJson(LiveBid instance) => <String, dynamic>{
  'id': instance.id,
  'vehicle_id': instance.vehicleId,
  'amount': instance.amount,
  'is_withdrawn': instance.isWithdrawn,
  'is_superseded': instance.isSuperseded,
};
