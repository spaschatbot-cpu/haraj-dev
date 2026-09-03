// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'live_vehicle.g.dart';

@JsonSerializable()
class LiveVehicle {
  const LiveVehicle({
    required this.id,
    required this.state,
    required this.stateLabel,
    required this.auctionState,
  });

  factory LiveVehicle.fromJson(Map<String, Object?> json) =>
      _$LiveVehicleFromJson(json);

  final String id;
  final String state;

  /// وصف عربي من الخادم — لا خريطة حالات في التطبيق
  @JsonKey(name: 'state_label')
  final String stateLabel;
  @JsonKey(name: 'auction_state')
  final String auctionState;

  Map<String, Object?> toJson() => _$LiveVehicleToJson(this);
}
