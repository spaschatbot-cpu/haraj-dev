// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'hold.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Hold _$HoldFromJson(Map<String, dynamic> json) => Hold(
  id: (json['id'] as num).toInt(),
  amount: json['amount'] as String,
  reason: ReasonEnum.fromJson(json['reason'] as String),
  reasonLabel: json['reason_label'] as String,
  auction: json['auction'] as Map<String, dynamic>?,
  invoice: json['invoice'] as Map<String, dynamic>?,
  createdAt: DateTime.parse(json['created_at'] as String),
);

Map<String, dynamic> _$HoldToJson(Hold instance) => <String, dynamic>{
  'id': instance.id,
  'amount': instance.amount,
  'reason': _$ReasonEnumEnumMap[instance.reason]!,
  'reason_label': instance.reasonLabel,
  'auction': instance.auction,
  'invoice': instance.invoice,
  'created_at': instance.createdAt.toIso8601String(),
};

const _$ReasonEnumEnumMap = {
  ReasonEnum.bidding: 'bidding',
  ReasonEnum.dues: 'dues',
  ReasonEnum.$unknown: r'$unknown',
};
