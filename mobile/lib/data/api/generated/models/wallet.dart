// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'wallet_bucket.dart';

part 'wallet.g.dart';

@JsonSerializable()
class Wallet {
  const Wallet({required this.buckets, required this.asOf});

  factory Wallet.fromJson(Map<String, Object?> json) => _$WalletFromJson(json);

  final List<WalletBucket> buckets;
  @JsonKey(name: 'as_of')
  final DateTime asOf;

  Map<String, Object?> toJson() => _$WalletToJson(this);
}
