// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ledger_entry.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

LedgerEntry _$LedgerEntryFromJson(Map<String, dynamic> json) => LedgerEntry(
  id: json['id'] as String,
  description: json['description'] as String,
  bucketLabel: json['bucket_label'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
  direction: LedgerEntryDirection.fromJson(json['direction'] as String),
  occurredAt: DateTime.parse(json['occurred_at'] as String),
  bucket: json['bucket'] == null
      ? null
      : WalletBucketKind.fromJson(json['bucket'] as String),
  reference: json['reference'] as String?,
);

Map<String, dynamic> _$LedgerEntryToJson(LedgerEntry instance) =>
    <String, dynamic>{
      'id': instance.id,
      'description': instance.description,
      'bucket': _$WalletBucketKindEnumMap[instance.bucket],
      'bucket_label': instance.bucketLabel,
      'amount': instance.amount,
      'currency': instance.currency,
      'direction': _$LedgerEntryDirectionEnumMap[instance.direction]!,
      'occurred_at': instance.occurredAt.toIso8601String(),
      'reference': instance.reference,
    };

const _$WalletBucketKindEnumMap = {
  WalletBucketKind.wallet: 'wallet',
  WalletBucketKind.insuranceFree: 'insurance_free',
  WalletBucketKind.insuranceHeld: 'insurance_held',
  WalletBucketKind.insuranceLocked: 'insurance_locked',
  WalletBucketKind.$unknown: r'$unknown',
};

const _$LedgerEntryDirectionEnumMap = {
  LedgerEntryDirection.valueIn: 'in',
  LedgerEntryDirection.out: 'out',
  LedgerEntryDirection.$unknown: r'$unknown',
};
