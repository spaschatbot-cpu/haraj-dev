// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'phase_counts.g.dart';

/// عدد المركبات في كل تبويب — **الثلاثة من لحظة واحدة**.
@JsonSerializable()
class PhaseCounts {
  const PhaseCounts({
    required this.upcoming,
    required this.active,
    required this.ended,
  });

  factory PhaseCounts.fromJson(Map<String, Object?> json) =>
      _$PhaseCountsFromJson(json);

  final int upcoming;
  final int active;
  final int ended;

  Map<String, Object?> toJson() => _$PhaseCountsToJson(this);
}
