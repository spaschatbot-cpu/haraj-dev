// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'purchase.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Purchase _$PurchaseFromJson(Map<String, dynamic> json) => Purchase(
  id: (json['id'] as num).toInt(),
  lotNumber: (json['lot_number'] as num).toInt(),
  make: json['make'] as String,
  model: json['model'] as String,
  year: (json['year'] as num).toInt(),
  state: json['state'] as String,
  awardedPrice: json['awarded_price'] as String,
  awardedAt: DateTime.parse(json['awarded_at'] as String),
  auction: json['auction'] as Map<String, dynamic>,
  invoice: json['invoice'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$PurchaseToJson(Purchase instance) => <String, dynamic>{
  'id': instance.id,
  'lot_number': instance.lotNumber,
  'make': instance.make,
  'model': instance.model,
  'year': instance.year,
  'state': instance.state,
  'awarded_price': instance.awardedPrice,
  'awarded_at': instance.awardedAt.toIso8601String(),
  'auction': instance.auction,
  'invoice': instance.invoice,
};
