// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'live_state.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LiveState _$LiveStateFromJson(Map<String, dynamic> json) => LiveState(
  bids: (json['bids'] as List<dynamic>)
      .map((e) => LiveBid.fromJson(e as Map<String, dynamic>))
      .toList(),
  vehicles: (json['vehicles'] as List<dynamic>)
      .map((e) => LiveVehicle.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$LiveStateToJson(LiveState instance) => <String, dynamic>{
  'bids': instance.bids,
  'vehicles': instance.vehicles,
};
