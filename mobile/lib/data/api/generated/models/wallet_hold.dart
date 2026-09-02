// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'wallet_hold.g.dart';

@JsonSerializable()
class WalletHold {
  const WalletHold({
    required this.reference,
    required this.reason,
    required this.amount,
    required this.currency,
  });

  factory WalletHold.fromJson(Map<String, Object?> json) =>
      _$WalletHoldFromJson(json);

  /// معرّف المزاد أو الفاتورة
  final String reference;

  /// سبب عربي جاهز للعرض
  final String reason;
  final String amount;
  final String currency;

  Map<String, Object?> toJson() => _$WalletHoldToJson(this);
}
