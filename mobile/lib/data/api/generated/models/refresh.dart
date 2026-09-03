// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'refresh.g.dart';

@JsonSerializable()
class Refresh {
  const Refresh({required this.refresh});

  factory Refresh.fromJson(Map<String, Object?> json) =>
      _$RefreshFromJson(json);

  final String refresh;

  Map<String, Object?> toJson() => _$RefreshToJson(this);
}
