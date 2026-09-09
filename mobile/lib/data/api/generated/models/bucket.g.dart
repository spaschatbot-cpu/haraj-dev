// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'bucket.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Bucket _$BucketFromJson(Map<String, dynamic> json) => Bucket(
  kind: json['kind'] as String,
  label: json['label'] as String,
  amount: json['amount'] as String,
  entryCount: (json['entry_count'] as num).toInt(),
  statement: json['statement'] as String,
);

Map<String, dynamic> _$BucketToJson(Bucket instance) => <String, dynamic>{
  'kind': instance.kind,
  'label': instance.label,
  'amount': instance.amount,
  'entry_count': instance.entryCount,
  'statement': instance.statement,
};
