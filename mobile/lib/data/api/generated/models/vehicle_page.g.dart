// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehiclePage _$VehiclePageFromJson(Map<String, dynamic> json) => VehiclePage(
  total: (json['total'] as num).toInt(),
  counts: PhaseCounts.fromJson(json['counts'] as Map<String, dynamic>),
  results: (json['results'] as List<dynamic>)
      .map((e) => VehicleCard.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$VehiclePageToJson(VehiclePage instance) =>
    <String, dynamic>{
      'total': instance.total,
      'counts': instance.counts,
      'results': instance.results,
    };
