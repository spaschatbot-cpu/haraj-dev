// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'phase_counts.g.dart';

/// The three tab counters, in the one response that carries the page.
///
/// Three named fields and not a map keyed by phase: a generated Dart or.
/// TypeScript client turns the first into three typed getters and the second.
/// into `Map<String, int>?`, and a screen reading `counts['activ']` compiles.
@JsonSerializable()
class PhaseCounts {
  const PhaseCounts({
    required this.soon,
    required this.active,
    required this.ended,
  });

  factory PhaseCounts.fromJson(Map<String, Object?> json) =>
      _$PhaseCountsFromJson(json);

  final int soon;
  final int active;
  final int ended;

  Map<String, Object?> toJson() => _$PhaseCountsToJson(this);
}
