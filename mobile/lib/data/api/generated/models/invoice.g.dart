// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'invoice.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Invoice _$InvoiceFromJson(Map<String, dynamic> json) => Invoice(
  id: json['id'] as String,
  number: json['number'] as String,
  totalAmount: json['total_amount'] as String,
  paidAmount: json['paid_amount'] as String,
  dueAmount: json['due_amount'] as String,
  currency: json['currency'] as String,
  status: InvoiceStatus.fromJson(json['status'] as String),
  statusLabel: json['status_label'] as String,
  issuedAt: DateTime.parse(json['issued_at'] as String),
  insuranceLock: json['insurance_lock'] == null
      ? null
      : InsuranceLock.fromJson(json['insurance_lock'] as Map<String, dynamic>),
);

Map<String, dynamic> _$InvoiceToJson(Invoice instance) => <String, dynamic>{
  'id': instance.id,
  'number': instance.number,
  'total_amount': instance.totalAmount,
  'paid_amount': instance.paidAmount,
  'due_amount': instance.dueAmount,
  'currency': instance.currency,
  'status': _$InvoiceStatusEnumMap[instance.status]!,
  'status_label': instance.statusLabel,
  'issued_at': instance.issuedAt.toIso8601String(),
  'insurance_lock': instance.insuranceLock,
};

const _$InvoiceStatusEnumMap = {
  InvoiceStatus.open: 'open',
  InvoiceStatus.partiallyPaid: 'partially_paid',
  InvoiceStatus.paid: 'paid',
  InvoiceStatus.cancelled: 'cancelled',
  InvoiceStatus.$unknown: r'$unknown',
};
