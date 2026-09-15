// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'customer_document.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CustomerDocument _$CustomerDocumentFromJson(Map<String, dynamic> json) =>
    CustomerDocument(
      kind: json['kind'] as String,
      label: json['label'] as String,
      uploadedAt: json['uploaded_at'] == null
          ? null
          : DateTime.parse(json['uploaded_at'] as String),
      file: json['file'] as String?,
      note: json['note'] as String,
      uploadedByStaff: json['uploaded_by_staff'] as bool,
    );

Map<String, dynamic> _$CustomerDocumentToJson(CustomerDocument instance) =>
    <String, dynamic>{
      'kind': instance.kind,
      'label': instance.label,
      'uploaded_at': instance.uploadedAt?.toIso8601String(),
      'file': instance.file,
      'note': instance.note,
      'uploaded_by_staff': instance.uploadedByStaff,
    };
