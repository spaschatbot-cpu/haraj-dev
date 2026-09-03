// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'live_vehicle.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LiveVehicle _$LiveVehicleFromJson(Map<String, dynamic> json) => LiveVehicle(
  id: json['id'] as String,
  state: json['state'] as String,
  stateLabel: json['state_label'] as String,
  auctionState: json['auction_state'] as String,
);

Map<String, dynamic> _$LiveVehicleToJson(LiveVehicle instance) =>
    <String, dynamic>{
      'id': instance.id,
      'state': instance.state,
      'state_label': instance.stateLabel,
      'auction_state': instance.auctionState,
    };
