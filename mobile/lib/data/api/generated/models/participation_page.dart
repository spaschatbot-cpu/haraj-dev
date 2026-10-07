// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'participation.dart';

part 'participation_page.g.dart';

@JsonSerializable()
class ParticipationPage {
  const ParticipationPage({required this.total, required this.results});

  factory ParticipationPage.fromJson(Map<String, Object?> json) =>
      _$ParticipationPageFromJson(json);

  final int total;
  final List<Participation> results;

  Map<String, Object?> toJson() => _$ParticipationPageToJson(this);
}
