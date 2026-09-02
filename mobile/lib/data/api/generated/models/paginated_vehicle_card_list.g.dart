// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_vehicle_card_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedVehicleCardList _$PaginatedVehicleCardListFromJson(
  Map<String, dynamic> json,
) => PaginatedVehicleCardList(
  count: (json['count'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => VehicleCard.fromJson(e as Map<String, dynamic>))
      .toList(),
  next: json['next'] as String?,
  previous: json['previous'] as String?,
);

Map<String, dynamic> _$PaginatedVehicleCardListToJson(
  PaginatedVehicleCardList instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
