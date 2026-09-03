// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'top_up_intent.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

TopUpIntent _$TopUpIntentFromJson(Map<String, dynamic> json) => TopUpIntent(
  reference: json['reference'] as String,
  amount: json['amount'] as String,
  currency: json['currency'] as String,
  redirectUrl: json['redirect_url'] as String,
  status: TopUpIntentStatus.fromJson(json['status'] as String),
  statusLabel: json['status_label'] as String,
);

Map<String, dynamic> _$TopUpIntentToJson(TopUpIntent instance) =>
    <String, dynamic>{
      'reference': instance.reference,
      'amount': instance.amount,
      'currency': instance.currency,
      'redirect_url': instance.redirectUrl,
      'status': _$TopUpIntentStatusEnumMap[instance.status]!,
      'status_label': instance.statusLabel,
    };

const _$TopUpIntentStatusEnumMap = {
  TopUpIntentStatus.pending: 'pending',
  TopUpIntentStatus.succeeded: 'succeeded',
  TopUpIntentStatus.cancelled: 'cancelled',
  TopUpIntentStatus.failed: 'failed',
  TopUpIntentStatus.$unknown: r'$unknown',
};
