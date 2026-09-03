// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'invoice.dart';
import 'purchase_state.dart';

part 'purchase.g.dart';

@JsonSerializable()
class Purchase {
  const Purchase({
    required this.id,
    required this.vehicleId,
    required this.lotNumber,
    required this.title,
    required this.auctionTitle,
    required this.awardedAmount,
    required this.currency,
    required this.awardedAt,
    required this.state,
    required this.stateLabel,
    this.invoice,
  });

  factory Purchase.fromJson(Map<String, Object?> json) =>
      _$PurchaseFromJson(json);

  final String id;
  @JsonKey(name: 'vehicle_id')
  final String vehicleId;
  @JsonKey(name: 'lot_number')
  final String lotNumber;
  final String title;
  @JsonKey(name: 'auction_title')
  final String auctionTitle;

  /// سعر الرسوّ كما رحّله الخادم — نصّ عشري يُعرض كما وصل
  @JsonKey(name: 'awarded_amount')
  final String awardedAmount;
  final String currency;
  @JsonKey(name: 'awarded_at')
  final DateTime awardedAt;
  final PurchaseState state;

  /// حالة المركبة بالعربية من الخادم
  @JsonKey(name: 'state_label')
  final String stateLabel;
  final Invoice? invoice;

  Map<String, Object?> toJson() => _$PurchaseToJson(this);
}
