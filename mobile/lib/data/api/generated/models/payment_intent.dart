// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'payment_intent_purpose_enum.dart';
import 'payment_intent_state_enum.dart';

part 'payment_intent.g.dart';

@JsonSerializable()
class PaymentIntent {
  const PaymentIntent({
    required this.reference,
    required this.checkoutUrl,
    required this.amount,
    required this.purpose,
    required this.purposeLabel,
    required this.stateLabel,
    required this.createdAt,
    required this.updatedAt,
    this.currency,
    this.state,
    this.gateway,
    this.gatewayStatusRaw,
  });

  factory PaymentIntent.fromJson(Map<String, Object?> json) =>
      _$PaymentIntentFromJson(json);

  final String reference;

  /// Where to send this customer to pay, or `""` when nowhere.
  ///
  /// A url on **our** server, never the gateway's. Both clients then have one.
  /// thing to do with it — send the customer there — and neither ever learns.
  /// what a Moyasar is; switching gateway changes `apps.money.gateway` and.
  /// rebuilds nothing (`docs` in that module say why at length).
  ///
  /// Empty when the intent cannot be paid — because it is finished, or.
  /// because this environment has no gateway. A client showing a button for a.
  /// succeeded top-up offers to take a second deposit; one showing it with no.
  /// gateway sends a customer to a refusal. The absence of the control is the.
  /// correct interface for both, and the *server* produces that absence so.
  /// neither client has to remember to check.
  @JsonKey(name: 'checkout_url')
  final String checkoutUrl;
  final String amount;
  final String? currency;
  final PaymentIntentPurposeEnum purpose;
  @JsonKey(name: 'purpose_label')
  final String purposeLabel;
  final PaymentIntentStateEnum? state;
  @JsonKey(name: 'state_label')
  final String stateLabel;
  final String? gateway;
  @JsonKey(name: 'gateway_status_raw')
  final String? gatewayStatusRaw;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime updatedAt;

  Map<String, Object?> toJson() => _$PaymentIntentToJson(this);
}
