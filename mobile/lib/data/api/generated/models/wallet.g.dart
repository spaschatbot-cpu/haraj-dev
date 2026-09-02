// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wallet.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Wallet _$WalletFromJson(Map<String, dynamic> json) => Wallet(
  buckets: (json['buckets'] as List<dynamic>)
      .map((e) => WalletBucket.fromJson(e as Map<String, dynamic>))
      .toList(),
  asOf: DateTime.parse(json['as_of'] as String),
);

Map<String, dynamic> _$WalletToJson(Wallet instance) => <String, dynamic>{
  'buckets': instance.buckets,
  'as_of': instance.asOf.toIso8601String(),
};
