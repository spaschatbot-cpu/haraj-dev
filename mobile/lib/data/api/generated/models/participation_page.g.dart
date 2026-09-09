// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'participation_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ParticipationPage _$ParticipationPageFromJson(Map<String, dynamic> json) =>
    ParticipationPage(
      total: (json['total'] as num).toInt(),
      results: (json['results'] as List<dynamic>)
          .map((e) => Participation.fromJson(e as Map<String, dynamic>))
          .toList(),
    );

Map<String, dynamic> _$ParticipationPageToJson(ParticipationPage instance) =>
    <String, dynamic>{'total': instance.total, 'results': instance.results};
