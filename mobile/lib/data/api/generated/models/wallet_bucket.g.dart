// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wallet_bucket.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

WalletBucket _$WalletBucketFromJson(Map<String, dynamic> json) => WalletBucket(
  kind: WalletBucketKind.fromJson(json['kind'] as String),
  label: json['label'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
  holds: (json['holds'] as List<dynamic>?)
      ?.map((e) => WalletHold.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$WalletBucketToJson(WalletBucket instance) =>
    <String, dynamic>{
      'kind': _$WalletBucketKindEnumMap[instance.kind]!,
      'label': instance.label,
      'amount': instance.amount,
      'currency': instance.currency,
      'holds': instance.holds,
    };

const _$WalletBucketKindEnumMap = {
  WalletBucketKind.wallet: 'wallet',
  WalletBucketKind.insuranceFree: 'insurance_free',
  WalletBucketKind.insuranceHeld: 'insurance_held',
  WalletBucketKind.insuranceLocked: 'insurance_locked',
  WalletBucketKind.$unknown: r'$unknown',
};
