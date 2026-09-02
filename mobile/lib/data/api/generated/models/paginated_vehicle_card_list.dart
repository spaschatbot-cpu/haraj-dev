// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'vehicle_card.dart';

part 'paginated_vehicle_card_list.g.dart';

@JsonSerializable()
class PaginatedVehicleCardList {
  const PaginatedVehicleCardList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedVehicleCardList.fromJson(Map<String, Object?> json) =>
      _$PaginatedVehicleCardListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<VehicleCard> results;

  Map<String, Object?> toJson() => _$PaginatedVehicleCardListToJson(this);
}
