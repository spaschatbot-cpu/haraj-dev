// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'wallet_bucket_kind.dart';
import 'wallet_hold.dart';

part 'wallet_bucket.g.dart';

@JsonSerializable()
class WalletBucket {
  const WalletBucket({
    required this.kind,
    required this.label,
    required this.amount,
    required this.currency,
    this.holds,
  });

  factory WalletBucket.fromJson(Map<String, Object?> json) =>
      _$WalletBucketFromJson(json);

  final WalletBucketKind kind;

  /// اسم الدلو بالعربية من الخادم
  final String label;

  /// نصّ عشري — **ممنوع جمع الدلاء في التطبيق**
  final String amount;
  final String currency;

  /// سبب كل حجز — أي مزاد، أي فاتورة
  final List<WalletHold>? holds;

  Map<String, Object?> toJson() => _$WalletBucketToJson(this);
}
