// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ledger_entry.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LedgerEntry _$LedgerEntryFromJson(Map<String, dynamic> json) => LedgerEntry(
  id: (json['id'] as num).toInt(),
  transaction: json['transaction'] as String,
  kind: json['kind'] as String,
  description: json['description'] as String,
  bucket: json['bucket'] as String,
  bucketLabel: json['bucket_label'] as String,
  amount: json['amount'] as String,
  direction: json['direction'] as String,
  occurredAt: DateTime.parse(json['occurred_at'] as String),
  memo: json['memo'] as String,
);

Map<String, dynamic> _$LedgerEntryToJson(LedgerEntry instance) =>
    <String, dynamic>{
      'id': instance.id,
      'transaction': instance.transaction,
      'kind': instance.kind,
      'description': instance.description,
      'bucket': instance.bucket,
      'bucket_label': instance.bucketLabel,
      'amount': instance.amount,
      'direction': instance.direction,
      'occurred_at': instance.occurredAt.toIso8601String(),
      'memo': instance.memo,
    };
