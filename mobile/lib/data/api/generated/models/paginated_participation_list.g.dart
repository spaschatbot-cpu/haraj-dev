// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'paginated_participation_list.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaginatedParticipationList _$PaginatedParticipationListFromJson(
  Map<String, dynamic> json,
) => PaginatedParticipationList(
  count: (json['count'] as num).toInt(),
  results: (json['results'] as List<dynamic>)
      .map((e) => Participation.fromJson(e as Map<String, dynamic>))
      .toList(),
  next: json['next'] as String?,
  previous: json['previous'] as String?,
);

Map<String, dynamic> _$PaginatedParticipationListToJson(
  PaginatedParticipationList instance,
) => <String, dynamic>{
  'count': instance.count,
  'next': instance.next,
  'previous': instance.previous,
  'results': instance.results,
};
