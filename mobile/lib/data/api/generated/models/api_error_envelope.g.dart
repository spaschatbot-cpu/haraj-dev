// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'api_error_envelope.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ApiErrorEnvelope _$ApiErrorEnvelopeFromJson(Map<String, dynamic> json) =>
    ApiErrorEnvelope(
      error: ApiErrorBody.fromJson(json['error'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$ApiErrorEnvelopeToJson(ApiErrorEnvelope instance) =>
    <String, dynamic>{'error': instance.error};
