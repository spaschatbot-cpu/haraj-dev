// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'wallet.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Wallet _$WalletFromJson(Map<String, dynamic> json) => Wallet(
  currency: json['currency'] as String,
  total: json['total'] as String,
  available: json['available'] as String,
  heldForAuctions: json['held_for_auctions'] as String,
  lockedForDues: json['locked_for_dues'] as String,
  buckets: (json['buckets'] as List<dynamic>)
      .map((e) => Bucket.fromJson(e as Map<String, dynamic>))
      .toList(),
  holds: (json['holds'] as List<dynamic>)
      .map((e) => Hold.fromJson(e as Map<String, dynamic>))
      .toList(),
  asOf: DateTime.parse(json['as_of'] as String),
);

Map<String, dynamic> _$WalletToJson(Wallet instance) => <String, dynamic>{
  'currency': instance.currency,
  'total': instance.total,
  'available': instance.available,
  'held_for_auctions': instance.heldForAuctions,
  'locked_for_dues': instance.lockedForDues,
  'buckets': instance.buckets,
  'holds': instance.holds,
  'as_of': instance.asOf.toIso8601String(),
};
