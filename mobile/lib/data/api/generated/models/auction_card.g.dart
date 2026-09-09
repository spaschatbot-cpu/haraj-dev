// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auction_card.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

AuctionCard _$AuctionCardFromJson(Map<String, dynamic> json) => AuctionCard(
  id: (json['id'] as num).toInt(),
  number: (json['number'] as num).toInt(),
  title: json['title'] as String,
  state: json['state'] as String,
  stateLabel: json['state_label'] as String,
  startsAt: DateTime.parse(json['starts_at'] as String),
  endsAt: DateTime.parse(json['ends_at'] as String),
  vehicleCount: (json['vehicle_count'] as num?)?.toInt(),
  openVehicleCount: (json['open_vehicle_count'] as num?)?.toInt(),
);

Map<String, dynamic> _$AuctionCardToJson(AuctionCard instance) =>
    <String, dynamic>{
      'id': instance.id,
      'number': instance.number,
      'title': instance.title,
      'state': instance.state,
      'state_label': instance.stateLabel,
      'starts_at': instance.startsAt.toIso8601String(),
      'ends_at': instance.endsAt.toIso8601String(),
      'vehicle_count': instance.vehicleCount,
      'open_vehicle_count': instance.openVehicleCount,
    };
