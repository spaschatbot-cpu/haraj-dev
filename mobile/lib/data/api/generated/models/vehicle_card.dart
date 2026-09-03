// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

part 'vehicle_card.g.dart';

@JsonSerializable()
class VehicleCard {
  const VehicleCard({
    required this.id,
    required this.lotNumber,
    required this.title,
    required this.thumbnailUrl,
    required this.reservePrice,
    required this.currentBidAmount,
    required this.currency,
    required this.bidsCount,
  });

  factory VehicleCard.fromJson(Map<String, Object?> json) =>
      _$VehicleCardFromJson(json);

  final String id;
  @JsonKey(name: 'lot_number')
  final String lotNumber;
  final String title;

  /// مصغَّرة فقط في القوائم — الحجم الكامل عند الفتح
  @JsonKey(name: 'thumbnail_url')
  final String? thumbnailUrl;

  /// سعر وقوف المركبة — الحقل **الوحيد** لسعرها (المادة ٨-٣ في دليل النظام، ونظيره `reserve_price` في مخطط الخادم المثبَّت). الفراغ يعني أن المالك لم يحدّد سعراً، وهو غير الصفر.
  ///
  @JsonKey(name: 'reserve_price')
  final String? reservePrice;

  /// نصّ عشري — يُعرض كما وصل
  @JsonKey(name: 'current_bid_amount')
  final String currentBidAmount;
  final String currency;
  @JsonKey(name: 'bids_count')
  final int bidsCount;

  Map<String, Object?> toJson() => _$VehicleCardToJson(this);
}
