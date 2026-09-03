// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'live_bid.dart';
import 'live_vehicle.dart';

part 'live_state.g.dart';

/// حمولة إطار `event: state`. مزايدات المتصل نفسه، وحالات عامة للمركبات التي يزايد عليها — لا رقم منافس ولا «أنت الأعلى».
///
@JsonSerializable()
class LiveState {
  const LiveState({required this.bids, required this.vehicles});

  factory LiveState.fromJson(Map<String, Object?> json) =>
      _$LiveStateFromJson(json);

  final List<LiveBid> bids;
  final List<LiveVehicle> vehicles;

  Map<String, Object?> toJson() => _$LiveStateToJson(this);
}
