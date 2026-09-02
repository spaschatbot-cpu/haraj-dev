// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'invoice_status.dart';

part 'invoice.g.dart';

@JsonSerializable()
class Invoice {
  const Invoice({
    required this.id,
    required this.number,
    required this.totalAmount,
    required this.paidAmount,
    required this.dueAmount,
    required this.currency,
    required this.status,
    required this.statusLabel,
    required this.issuedAt,
  });

  factory Invoice.fromJson(Map<String, Object?> json) =>
      _$InvoiceFromJson(json);

  final String id;
  final String number;
  @JsonKey(name: 'total_amount')
  final String totalAmount;
  @JsonKey(name: 'paid_amount')
  final String paidAmount;

  /// يأتي محسوباً من الخادم — التطبيق لا يطرح
  @JsonKey(name: 'due_amount')
  final String dueAmount;
  final String currency;
  final InvoiceStatus status;
  @JsonKey(name: 'status_label')
  final String statusLabel;
  @JsonKey(name: 'issued_at')
  final DateTime issuedAt;

  Map<String, Object?> toJson() => _$InvoiceToJson(this);
}
