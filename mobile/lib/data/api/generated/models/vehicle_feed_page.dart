// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'phase_counts.dart';
import 'vehicle_card.dart';

part 'vehicle_feed_page.g.dart';

@JsonSerializable()
class VehicleFeedPage {
  const VehicleFeedPage({
    required this.count,
    required this.results,
    required this.counts,
    this.next,
    this.previous,
  });

  factory VehicleFeedPage.fromJson(Map<String, Object?> json) =>
      _$VehicleFeedPageFromJson(json);

  /// عدد نتائج هذا التبويب بهذه المعايير — لا مجموع الأطوار
  final int count;
  final String? next;
  final String? previous;
  final List<VehicleCard> results;
  final PhaseCounts counts;

  Map<String, Object?> toJson() => _$VehicleFeedPageToJson(this);
}
