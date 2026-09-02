// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, unused_import, invalid_annotation_target, unnecessary_import

import 'package:json_annotation/json_annotation.dart';

import 'refund_request_status.dart';

part 'refund_request.g.dart';

@JsonSerializable()
class RefundRequest {
  const RefundRequest({
    required this.reference,
    required this.amount,
    required this.currency,
    required this.status,
    required this.statusLabel,
    required this.requestedAt,
  });

  factory RefundRequest.fromJson(Map<String, Object?> json) =>
      _$RefundRequestFromJson(json);

  final String reference;
  final String amount;
  final String currency;
  final RefundRequestStatus status;
  @JsonKey(name: 'status_label')
  final String statusLabel;
  @JsonKey(name: 'requested_at')
  final DateTime requestedAt;

  Map<String, Object?> toJson() => _$RefundRequestToJson(this);
}
