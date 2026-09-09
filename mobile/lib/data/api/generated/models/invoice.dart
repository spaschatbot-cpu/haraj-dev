// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'invoice_state_enum.dart';

part 'invoice.g.dart';

@JsonSerializable()
class Invoice {
  const Invoice({
    required this.id,
    required this.number,
    required this.amount,
    required this.amountPaid,
    required this.outstanding,
    required this.stateLabel,
    required this.issuedAt,
    required this.paymentMethods,
    this.state,
    this.dueAt,
  });

  factory Invoice.fromJson(Map<String, Object?> json) =>
      _$InvoiceFromJson(json);

  final int id;
  final String number;
  final String amount;
  @JsonKey(name: 'amount_paid')
  final String amountPaid;
  final String outstanding;
  final InvoiceStateEnum? state;
  @JsonKey(name: 'state_label')
  final String stateLabel;
  @JsonKey(name: 'issued_at')
  final DateTime issuedAt;
  @JsonKey(name: 'due_at')
  final DateTime? dueAt;

  /// The only two ways a purchase is ever paid for. Card is not one.
  @JsonKey(name: 'payment_methods')
  final List<Map<String, dynamic>> paymentMethods;

  Map<String, Object?> toJson() => _$InvoiceToJson(this);
}
