// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'purchase.g.dart';

/// A vehicle this customer won, with the invoice that followed it.
@JsonSerializable()
class Purchase {
  const Purchase({
    required this.id,
    required this.lotNumber,
    required this.make,
    required this.model,
    required this.year,
    required this.state,
    required this.awardedPrice,
    required this.awardedAt,
    required this.auction,
    required this.invoice,
  });

  factory Purchase.fromJson(Map<String, Object?> json) =>
      _$PurchaseFromJson(json);

  final int id;
  @JsonKey(name: 'lot_number')
  final int lotNumber;
  final String make;
  final String model;
  final int year;
  final String state;
  @JsonKey(name: 'awarded_price')
  final String awardedPrice;
  @JsonKey(name: 'awarded_at')
  final DateTime awardedAt;
  final Map<String, dynamic> auction;
  final Map<String, dynamic>? invoice;

  Map<String, Object?> toJson() => _$PurchaseToJson(this);
}
