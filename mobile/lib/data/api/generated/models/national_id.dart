// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'national_id.g.dart';

@JsonSerializable()
class NationalId {
  const NationalId({required this.nationalId});

  factory NationalId.fromJson(Map<String, Object?> json) =>
      _$NationalIdFromJson(json);

  @JsonKey(name: 'national_id')
  final String nationalId;

  Map<String, Object?> toJson() => _$NationalIdToJson(this);
}
