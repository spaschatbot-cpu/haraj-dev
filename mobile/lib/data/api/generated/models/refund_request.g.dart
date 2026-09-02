// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'refund_request.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

RefundRequest _$RefundRequestFromJson(Map<String, dynamic> json) =>
    RefundRequest(
      reference: json['reference'] as String,
      amount: json['amount'] as String,
      currency: json['currency'] as String,
      status: RefundRequestStatus.fromJson(json['status'] as String),
      statusLabel: json['status_label'] as String,
      requestedAt: DateTime.parse(json['requested_at'] as String),
    );

Map<String, dynamic> _$RefundRequestToJson(RefundRequest instance) =>
    <String, dynamic>{
      'reference': instance.reference,
      'amount': instance.amount,
      'currency': instance.currency,
      'status': _$RefundRequestStatusEnumMap[instance.status]!,
      'status_label': instance.statusLabel,
      'requested_at': instance.requestedAt.toIso8601String(),
    };

const _$RefundRequestStatusEnumMap = {
  RefundRequestStatus.requested: 'requested',
  RefundRequestStatus.sent: 'sent',
  RefundRequestStatus.confirmed: 'confirmed',
  RefundRequestStatus.rejected: 'rejected',
  RefundRequestStatus.$unknown: r'$unknown',
};
