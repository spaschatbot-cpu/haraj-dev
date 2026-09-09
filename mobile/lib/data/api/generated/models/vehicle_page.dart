// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'phase_counts.dart';
import 'vehicle_card.dart';

part 'vehicle_page.g.dart';

/// A page of cars, its total, and the three tab counters.
///
/// The counters ride along on **every** vehicle page, whichever tab was asked.
/// for, because all three tabs are on screen at all times. Splitting them into.
/// a second endpoint is what v1 did — six requests to draw three numbers — and.
/// it made the three numbers three different moments.
@JsonSerializable()
class VehiclePage {
  const VehiclePage({
    required this.total,
    required this.counts,
    required this.results,
  });

  factory VehiclePage.fromJson(Map<String, Object?> json) =>
      _$VehiclePageFromJson(json);

  final int total;
  final PhaseCounts counts;
  final List<VehicleCard> results;

  Map<String, Object?> toJson() => _$VehiclePageToJson(this);
}
