// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ledger_entry.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LedgerEntry _$LedgerEntryFromJson(Map<String, dynamic> json) => LedgerEntry(
  id: json['id'] as String,
  description: json['description'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
  direction: LedgerEntryDirection.fromJson(json['direction'] as String),
  occurredAt: DateTime.parse(json['occurred_at'] as String),
  reference: json['reference'] as String?,
);

Map<String, dynamic> _$LedgerEntryToJson(LedgerEntry instance) =>
    <String, dynamic>{
      'id': instance.id,
      'description': instance.description,
      'amount': instance.amount,
      'currency': instance.currency,
      'direction': _$LedgerEntryDirectionEnumMap[instance.direction]!,
      'occurred_at': instance.occurredAt.toIso8601String(),
      'reference': instance.reference,
    };

const _$LedgerEntryDirectionEnumMap = {
  LedgerEntryDirection.debit: 'debit',
  LedgerEntryDirection.credit: 'credit',
  LedgerEntryDirection.$unknown: r'$unknown',
};
