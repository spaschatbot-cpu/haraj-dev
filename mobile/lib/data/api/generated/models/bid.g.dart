// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bid.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Bid _$BidFromJson(Map<String, dynamic> json) => Bid(
  id: json['id'] as String,
  vehicleId: json['vehicle_id'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
  status: BidStatus.fromJson(json['status'] as String),
  statusLabel: json['status_label'] as String,
  placedAt: DateTime.parse(json['placed_at'] as String),
  vehicleTitle: json['vehicle_title'] as String?,
);

Map<String, dynamic> _$BidToJson(Bid instance) => <String, dynamic>{
  'id': instance.id,
  'vehicle_id': instance.vehicleId,
  'vehicle_title': instance.vehicleTitle,
  'amount': instance.amount,
  'currency': instance.currency,
  'status': _$BidStatusEnumMap[instance.status]!,
  'status_label': instance.statusLabel,
  'placed_at': instance.placedAt.toIso8601String(),
};

const _$BidStatusEnumMap = {
  BidStatus.placed: 'placed',
  BidStatus.outbid: 'outbid',
  BidStatus.leading: 'leading',
  BidStatus.withdrawn: 'withdrawn',
  BidStatus.won: 'won',
  BidStatus.lost: 'lost',
  BidStatus.$unknown: r'$unknown',
};
