// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vehicle_feed_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

VehicleFeedPage _$VehicleFeedPageFromJson(Map<String, dynamic> json) =>
    VehicleFeedPage(
      count: (json['count'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => VehicleCard.fromJson(e as Map<String, dynamic>))
          .toList(),
      counts: PhaseCounts.fromJson(json['counts'] as Map<String, dynamic>),
      next: json['next'] as String?,
      previous: json['previous'] as String?,
    );

Map<String, dynamic> _$VehicleFeedPageToJson(VehicleFeedPage instance) =>
    <String, dynamic>{
      'count': instance.count,
      'next': instance.next,
      'previous': instance.previous,
      'results': instance.results,
      'counts': instance.counts,
    };
