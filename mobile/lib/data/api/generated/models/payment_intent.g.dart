// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'payment_intent.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PaymentIntent _$PaymentIntentFromJson(Map<String, dynamic> json) =>
    PaymentIntent(
      reference: json['reference'] as String,
      checkoutUrl: json['checkout_url'] as String,
      amount: json['amount'] as String,
      purpose: PaymentIntentPurposeEnum.fromJson(json['purpose'] as String),
      purposeLabel: json['purpose_label'] as String,
      stateLabel: json['state_label'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      currency: json['currency'] as String?,
      state: json['state'] == null
          ? null
          : PaymentIntentStateEnum.fromJson(json['state'] as String),
      gateway: json['gateway'] as String?,
      gatewayStatusRaw: json['gateway_status_raw'] as String?,
    );

Map<String, dynamic> _$PaymentIntentToJson(PaymentIntent instance) =>
    <String, dynamic>{
      'reference': instance.reference,
      'checkout_url': instance.checkoutUrl,
      'amount': instance.amount,
      'currency': instance.currency,
      'purpose': _$PaymentIntentPurposeEnumEnumMap[instance.purpose]!,
      'purpose_label': instance.purposeLabel,
      'state': _$PaymentIntentStateEnumEnumMap[instance.state],
      'state_label': instance.stateLabel,
      'gateway': instance.gateway,
      'gateway_status_raw': instance.gatewayStatusRaw,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt.toIso8601String(),
    };

const _$PaymentIntentPurposeEnumEnumMap = {
  PaymentIntentPurposeEnum.insuranceDeposit: 'insurance_deposit',
  PaymentIntentPurposeEnum.$unknown: r'$unknown',
};

const _$PaymentIntentStateEnumEnumMap = {
  PaymentIntentStateEnum.pending: 'pending',
  PaymentIntentStateEnum.succeeded: 'succeeded',
  PaymentIntentStateEnum.failed: 'failed',
  PaymentIntentStateEnum.cancelled: 'cancelled',
  PaymentIntentStateEnum.expired: 'expired',
  PaymentIntentStateEnum.disputed: 'disputed',
  PaymentIntentStateEnum.$unknown: r'$unknown',
};
