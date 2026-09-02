// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auction.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Auction _$AuctionFromJson(Map<String, dynamic> json) => Auction(
  id: json['id'] as String,
  title: json['title'] as String,
  status: AuctionStatus.fromJson(json['status'] as String),
  startsAt: DateTime.parse(json['starts_at'] as String),
  endsAt: DateTime.parse(json['ends_at'] as String),
  vehiclesCount: (json['vehicles_count'] as num).toInt(),
);

Map<String, dynamic> _$AuctionToJson(Auction instance) => <String, dynamic>{
  'id': instance.id,
  'title': instance.title,
  'status': _$AuctionStatusEnumMap[instance.status]!,
  'starts_at': instance.startsAt.toIso8601String(),
  'ends_at': instance.endsAt.toIso8601String(),
  'vehicles_count': instance.vehiclesCount,
};

const _$AuctionStatusEnumMap = {
  AuctionStatus.draft: 'draft',
  AuctionStatus.scheduled: 'scheduled',
  AuctionStatus.running: 'running',
  AuctionStatus.ended: 'ended',
  AuctionStatus.settled: 'settled',
  AuctionStatus.cancelled: 'cancelled',
  AuctionStatus.$unknown: r'$unknown',
};
