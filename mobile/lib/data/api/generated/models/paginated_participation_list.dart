// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'participation.dart';

part 'paginated_participation_list.g.dart';

@JsonSerializable()
class PaginatedParticipationList {
  const PaginatedParticipationList({
    required this.count,
    required this.results,
    this.next,
    this.previous,
  });

  factory PaginatedParticipationList.fromJson(Map<String, Object?> json) =>
      _$PaginatedParticipationListFromJson(json);

  final int count;
  final String? next;
  final String? previous;
  final List<Participation> results;

  Map<String, Object?> toJson() => _$PaginatedParticipationListToJson(this);
}
