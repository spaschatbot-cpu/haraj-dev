// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'invoice.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Invoice _$InvoiceFromJson(Map<String, dynamic> json) => Invoice(
  id: (json['id'] as num).toInt(),
  number: json['number'] as String,
  amount: json['amount'] as String,
  amountPaid: json['amount_paid'] as String,
  outstanding: json['outstanding'] as String,
  stateLabel: json['state_label'] as String,
  issuedAt: DateTime.parse(json['issued_at'] as String),
  paymentMethods: (json['payment_methods'] as List<dynamic>)
      .map((e) => e as Map<String, dynamic>)
      .toList(),
  state: json['state'] == null
      ? null
      : InvoiceStateEnum.fromJson(json['state'] as String),
  dueAt: json['due_at'] == null
      ? null
      : DateTime.parse(json['due_at'] as String),
);

Map<String, dynamic> _$InvoiceToJson(Invoice instance) => <String, dynamic>{
  'id': instance.id,
  'number': instance.number,
  'amount': instance.amount,
  'amount_paid': instance.amountPaid,
  'outstanding': instance.outstanding,
  'state': _$InvoiceStateEnumEnumMap[instance.state],
  'state_label': instance.stateLabel,
  'issued_at': instance.issuedAt.toIso8601String(),
  'due_at': instance.dueAt?.toIso8601String(),
  'payment_methods': instance.paymentMethods,
};

const _$InvoiceStateEnumEnumMap = {
  InvoiceStateEnum.draft: 'draft',
  InvoiceStateEnum.open: 'open',
  InvoiceStateEnum.partial: 'partial',
  InvoiceStateEnum.paid: 'paid',
  InvoiceStateEnum.cancelled: 'cancelled',
  InvoiceStateEnum.$unknown: r'$unknown',
};
