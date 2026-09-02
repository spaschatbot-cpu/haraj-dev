// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'specification.g.dart';

@JsonSerializable()
class Specification {
  const Specification({required this.label, required this.value});

  factory Specification.fromJson(Map<String, Object?> json) =>
      _$SpecificationFromJson(json);

  /// تسمية عربية من الخادم
  final String label;
  final String value;

  Map<String, Object?> toJson() => _$SpecificationToJson(this);
}
