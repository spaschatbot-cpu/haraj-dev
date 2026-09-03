// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'purchase.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Purchase _$PurchaseFromJson(Map<String, dynamic> json) => Purchase(
  id: json['id'] as String,
  vehicleId: json['vehicle_id'] as String,
  lotNumber: json['lot_number'] as String,
  title: json['title'] as String,
  auctionTitle: json['auction_title'] as String,
  awardedAmount: json['awarded_amount'] as String,
  currency: json['currency'] as String,
  awardedAt: DateTime.parse(json['awarded_at'] as String),
  state: PurchaseState.fromJson(json['state'] as String),
  stateLabel: json['state_label'] as String,
  invoice: json['invoice'] == null
      ? null
      : Invoice.fromJson(json['invoice'] as Map<String, dynamic>),
);

Map<String, dynamic> _$PurchaseToJson(Purchase instance) => <String, dynamic>{
  'id': instance.id,
  'vehicle_id': instance.vehicleId,
  'lot_number': instance.lotNumber,
  'title': instance.title,
  'auction_title': instance.auctionTitle,
  'awarded_amount': instance.awardedAmount,
  'currency': instance.currency,
  'awarded_at': instance.awardedAt.toIso8601String(),
  'state': _$PurchaseStateEnumMap[instance.state]!,
  'state_label': instance.stateLabel,
  'invoice': instance.invoice,
};

const _$PurchaseStateEnumMap = {
  PurchaseState.awarded: 'awarded',
  PurchaseState.invoiced: 'invoiced',
  PurchaseState.paid: 'paid',
  PurchaseState.handedOver: 'handed_over',
  PurchaseState.cancelled: 'cancelled',
  PurchaseState.$unknown: r'$unknown',
};
