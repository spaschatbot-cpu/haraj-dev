// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'bucket.dart';
import 'hold.dart';

part 'wallet.g.dart';

@JsonSerializable()
class Wallet {
  const Wallet({
    required this.currency,
    required this.total,
    required this.available,
    required this.heldForAuctions,
    required this.lockedForDues,
    required this.buckets,
    required this.holds,
    required this.asOf,
  });

  factory Wallet.fromJson(Map<String, Object?> json) => _$WalletFromJson(json);

  final String currency;
  final String total;
  final String available;
  @JsonKey(name: 'held_for_auctions')
  final String heldForAuctions;
  @JsonKey(name: 'locked_for_dues')
  final String lockedForDues;
  final List<Bucket> buckets;
  final List<Hold> holds;
  @JsonKey(name: 'as_of')
  final DateTime asOf;

  Map<String, Object?> toJson() => _$WalletToJson(this);
}
