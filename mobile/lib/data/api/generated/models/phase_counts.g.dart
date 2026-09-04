// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'phase_counts.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PhaseCounts _$PhaseCountsFromJson(Map<String, dynamic> json) => PhaseCounts(
  upcoming: (json['upcoming'] as num).toInt(),
  active: (json['active'] as num).toInt(),
  ended: (json['ended'] as num).toInt(),
);

Map<String, dynamic> _$PhaseCountsToJson(PhaseCounts instance) =>
    <String, dynamic>{
      'upcoming': instance.upcoming,
      'active': instance.active,
      'ended': instance.ended,
    };
