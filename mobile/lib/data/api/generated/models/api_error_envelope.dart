// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'error.dart';

part 'api_error_envelope.g.dart';

/// غلافُ كل خطأ تردّ به هذه الواجهة — بلا استثناء. يُبنى في `apps.core.exceptions.envelope` وحدها، فلا عرضٌ يخترع شكلاً ثانياً.
@JsonSerializable()
class ApiErrorEnvelope {
  const ApiErrorEnvelope({required this.error});

  factory ApiErrorEnvelope.fromJson(Map<String, Object?> json) =>
      _$ApiErrorEnvelopeFromJson(json);

  final Error error;

  Map<String, Object?> toJson() => _$ApiErrorEnvelopeToJson(this);
}
