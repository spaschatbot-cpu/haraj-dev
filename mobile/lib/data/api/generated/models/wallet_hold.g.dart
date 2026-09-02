// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wallet_hold.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

WalletHold _$WalletHoldFromJson(Map<String, dynamic> json) => WalletHold(
  reference: json['reference'] as String,
  reason: json['reason'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
);

Map<String, dynamic> _$WalletHoldToJson(WalletHold instance) =>
    <String, dynamic>{
      'reference': instance.reference,
      'reason': instance.reason,
      'amount': instance.amount,
      'currency': instance.currency,
    };
