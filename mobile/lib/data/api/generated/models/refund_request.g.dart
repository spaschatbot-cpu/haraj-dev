// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'refund_request.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

RefundRequest _$RefundRequestFromJson(Map<String, dynamic> json) =>
    RefundRequest(
      id: (json['id'] as num).toInt(),
      reference: json['reference'] as String,
      amount: json['amount'] as String,
      stateLabel: json['state_label'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      state: json['state'] == null
          ? null
          : RefundRequestStateEnum.fromJson(json['state'] as String),
    );

Map<String, dynamic> _$RefundRequestToJson(RefundRequest instance) =>
    <String, dynamic>{
      'id': instance.id,
      'reference': instance.reference,
      'amount': instance.amount,
      'state': _$RefundRequestStateEnumEnumMap[instance.state],
      'state_label': instance.stateLabel,
      'created_at': instance.createdAt.toIso8601String(),
    };

const _$RefundRequestStateEnumEnumMap = {
  RefundRequestStateEnum.requested: 'requested',
  RefundRequestStateEnum.sent: 'sent',
  RefundRequestStateEnum.confirmed: 'confirmed',
  RefundRequestStateEnum.rejected: 'rejected',
  RefundRequestStateEnum.cancelled: 'cancelled',
  RefundRequestStateEnum.$unknown: r'$unknown',
};
